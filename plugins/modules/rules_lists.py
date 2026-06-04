#!/usr/bin/python

# Copyright: (c) 2026, Taylor Kimball
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import absolute_import, division, print_function

__metaclass__ = type

DOCUMENTATION = r"""
---
module: rules_lists
short_description: Manage cloudflare rules lists
description:
- Create, update, populate, and delete Cloudflare Rules lists by name.
author:
- Taylor Kimball (@tkimball83)
options:
  account_id:
    required: true
    type: str
    description:
    - Cloudflare account identifier.
  api_token:
    required: true
    type: str
    description:
    - Cloudflare API token.
  name:
    required: true
    type: str
    description:
    - Resource name.
  kind:
    type: str
    choices:
    - ip
    - redirect
    - hostname
    - asn
    description:
    - Resource kind.
    - Required when creating a Rules list.
  description:
    type: str
    description:
    - Description.
  elements:
    type: list
    elements: dict
    description:
    - Elements.
  state:
    type: str
    choices:
    - present
    - absent
    default: present
    description:
    - Desired state of the resource.
requirements:
- python >= 3.9
- cloudflare >= 4.3.1, < 5

"""

EXAMPLES = r"""
- name: Ensure Rules list exists
  linuxhq.cloudflare.rules_lists:
    account_id: "{{ account_id }}"
    api_token: "{{ cloudflare_api_token }}"
    name: uptime_robot
    kind: ip
    elements:
      - ip: 1.2.3.4
"""

RETURN = r"""
---
rules_list:
  description: Cloudflare Rules list.
  returned: when available
  type: dict
items_operation:
  description: Bulk operation returned when list items were updated.
  returned: when list items changed
  type: dict
message:
  returned: always
  type: str
  description:
  - Operation summary.

"""

from urllib.parse import urlencode

from ansible.module_utils.basic import AnsibleModule

from ansible_collections.linuxhq.cloudflare.plugins.module_utils.cloudflare_utils import (
    cloudflare_client,
    delete_result,
    find_by_field,
    post_result,
    put_result,
    serialize_resource,
    values_differ,
)

ITEMS_PER_PAGE = 500
MAX_ITEMS = 10000

ITEM_META_FIELDS = (
    "created_on",
    "id",
    "modified_on",
)

REDIRECT_DEFAULTS = {
    "include_subdomains": False,
    "preserve_path_suffix": False,
    "preserve_query_string": False,
    "subpath_matching": False,
}


def endpoint(account_id):
    return "/accounts/%s/rules/lists" % account_id


def item_endpoint(account_id, list_id):
    return "%s/%s" % (endpoint(account_id), list_id)


def items_endpoint(account_id, list_id):
    return "%s/items" % item_endpoint(account_id, list_id)


def normalize_items(items):
    normalized_items = {}
    for item in items or []:
        normalized = {}
        for key, value in item.items():
            if key in ITEM_META_FIELDS or value is None:
                continue

            if key == "comment" and value == "":
                continue

            if key == "hostname" and isinstance(value, dict):
                hostname = {}
                for hostname_key, hostname_value in value.items():
                    if hostname_value is not None:
                        hostname[hostname_key] = hostname_value

                if hostname.get("exclude_exact_hostname") is True:
                    hostname.pop("exclude_exact_hostname")

                value = hostname

            if key == "redirect" and isinstance(value, dict):
                redirect = {}
                for redirect_key, redirect_value in value.items():
                    if redirect_value is None:
                        continue

                    if (
                        redirect_key in REDIRECT_DEFAULTS
                        and redirect_value == REDIRECT_DEFAULTS[redirect_key]
                    ):
                        continue

                    redirect[redirect_key] = redirect_value

                value = redirect

            normalized[key] = value

        normalized_items[repr(sorted(normalized.items()))] = normalized

    return sorted(
        normalized_items.values(),
        key=lambda item: repr(sorted(item.items())),
    )


def main():
    module = AnsibleModule(
        argument_spec={
            "account_id": {"required": True, "type": "str"},
            "api_token": {"required": True, "type": "str", "no_log": True},
            "name": {"required": True, "type": "str"},
            "kind": {"type": "str", "choices": ["ip", "redirect", "hostname", "asn"]},
            "description": {"type": "str"},
            "elements": {"type": "list", "elements": "dict"},
            "state": {
                "type": "str",
                "choices": ["present", "absent"],
                "default": "present",
            },
        },
        supports_check_mode=True,
    )

    params = module.params
    state = params["state"]

    with cloudflare_client(module) as client:
        current = find_by_field(
            client, endpoint(params["account_id"]), "name", params["name"]
        )

        if state == "absent":
            if current is None:
                module.exit_json(changed=False, message="Rules list already absent")
            if module.check_mode:
                module.exit_json(
                    changed=True,
                    message="Rules list would be deleted",
                    rules_list=current,
                )
            delete_result(client, item_endpoint(params["account_id"], current["id"]))
            module.exit_json(
                changed=True,
                message="Rules list deleted",
                rules_list=current,
            )

        elif state == "present":
            if current is None and params.get("kind") is None:
                module.fail_json(msg="kind is required when creating a Rules list")

            changed = False
            items_changed = False
            items_operation = None

            if current is None:
                if module.check_mode:
                    module.exit_json(
                        changed=True, message="Rules list would be created"
                    )
                current = post_result(
                    client,
                    endpoint(params["account_id"]),
                    {
                        "description": params.get("description") or params["name"],
                        "kind": params["kind"],
                        "name": params["name"],
                    },
                )
                changed = True
            else:
                desired_description = params.get("description") or params["name"]
                if current.get("description") != desired_description:
                    if module.check_mode:
                        module.exit_json(
                            changed=True,
                            message="Rules list would be updated",
                            rules_list=current,
                        )
                    current = put_result(
                        client,
                        item_endpoint(params["account_id"], current["id"]),
                        {"description": desired_description},
                    )
                    changed = True

            if params.get("elements") is not None:
                if len(params["elements"]) > MAX_ITEMS:
                    module.fail_json(
                        msg="Rules lists support a maximum of %s elements" % MAX_ITEMS
                    )

                expected_count = min(
                    max(current.get("num_items") or 0, len(params["elements"])),
                    MAX_ITEMS,
                )
                current_items = []
                cursor = None

                while len(current_items) < MAX_ITEMS:
                    query = {"cursor": cursor, "per_page": ITEMS_PER_PAGE}
                    query = {
                        key: value for key, value in query.items() if value is not None
                    }
                    path = items_endpoint(params["account_id"], current["id"])
                    if query:
                        path = "%s?%s" % (path, urlencode(query))

                    response = (
                        serialize_resource(client.get(path, cast_to=object)) or {}
                    )

                    if isinstance(response, dict) and "result" in response:
                        result = response.get("result") or []
                        result_info = response.get("result_info") or {}
                    else:
                        result = response or []
                        result_info = {}

                    if isinstance(result, list):
                        page_items = result
                    else:
                        page_items = [result]

                    current_items.extend(page_items)

                    if len(current_items) >= expected_count:
                        break

                    if len(page_items) < ITEMS_PER_PAGE:
                        break

                    cursor = (result_info.get("cursors") or {}).get("after")
                    if not cursor:
                        break

                items_changed = values_differ(
                    normalize_items(current_items),
                    normalize_items(params["elements"]),
                )
                if module.check_mode and items_changed:
                    module.exit_json(
                        changed=True,
                        message="Rules list items would be updated",
                        rules_list=current,
                    )
                if items_changed:
                    items_operation = put_result(
                        client,
                        items_endpoint(params["account_id"], current["id"]),
                        params["elements"],
                    )

            if not changed and not items_changed:
                module.exit_json(
                    changed=False,
                    message="Rules list already present",
                    rules_list=current,
                )

            module.exit_json(
                changed=True,
                message="Rules list updated",
                rules_list=current,
                items_operation=items_operation,
            )

        else:
            module.fail_json(msg=f"Unsupported state: {state}")


if __name__ == "__main__":
    main()
