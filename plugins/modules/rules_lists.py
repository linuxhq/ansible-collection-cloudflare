#!/usr/bin/python
# -*- coding: utf-8 -*-
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import absolute_import, division, print_function

__metaclass__ = type

DOCUMENTATION = r"""
---
module: rules_lists
short_description: Manage cloudflare rules lists
description:
  - Create, update, populate, and delete Cloudflare Rules lists by name.
  - Item updates wait for the resulting bulk operation to complete and fail when
    Cloudflare reports the operation failed.
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
  operation_timeout:
    type: int
    default: 240
    description:
      - Maximum seconds to wait for the bulk item operation to complete, including
        retrying submission while another bulk operation is pending on the account.
      - Enforced as an upper bound; the remaining budget is applied to every
        submission and polling request as a single attempt, and the module handles
        retries within the budget.
      - Must be at least 1 second.
      - When executed asynchronously, the async budget must exceed this value.
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
  - cloudflare >= 5.5.0, < 6

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

import json
import time

from urllib.parse import urlencode

from ansible.module_utils.basic import AnsibleModule

from ansible_collections.linuxhq.cloudflare.plugins.module_utils.cloudflare_utils import (
    cloudflare,
    cloudflare_client,
    delete_result,
    fail_from_cloudflare_error,
    find_by_field,
    get_result,
    parse_list_response,
    post_result,
    put_result,
    serialize_resource,
    values_differ,
)

ITEMS_PER_PAGE = 500
OPERATION_POLL_SECONDS = 2

ITEM_META_FIELDS = (
    "created_on",
    "id",
    "modified_on",
)

REDIRECT_DEFAULTS = {
    "include_subdomains": False,
    "preserve_path_suffix": True,
    "preserve_query_string": False,
    "status_code": 301,
    "subpath_matching": False,
}


def canonical_item(item):
    return json.dumps(item, sort_keys=True, separators=(",", ":"))


def endpoint(account_id):
    return "/accounts/%s/rules/lists" % account_id


def item_endpoint(account_id, list_id):
    return "%s/%s" % (endpoint(account_id), list_id)


def items_endpoint(account_id, list_id):
    return "%s/items" % item_endpoint(account_id, list_id)


def operation_endpoint(account_id, operation_id):
    return "/accounts/%s/rules/lists/bulk_operations/%s" % (account_id, operation_id)


def pending_operation_error(exc):
    if getattr(exc, "status_code", None) not in (400, 409, 429):
        return False
    return "operation" in str(exc).lower()


def transient_error(exc):
    if isinstance(exc, cloudflare.APIConnectionError):
        return True

    status_code = getattr(exc, "status_code", None)
    return status_code == 429 or (isinstance(status_code, int) and status_code >= 500)


def submit_items(client, account_id, list_id, elements, deadline):
    while True:
        try:
            return put_result(
                client,
                items_endpoint(account_id, list_id),
                elements,
                timeout=max(deadline - time.monotonic(), 1),
            )
        except (cloudflare.APIConnectionError, cloudflare.APIStatusError) as exc:
            if (
                not (pending_operation_error(exc) or transient_error(exc))
                or deadline - time.monotonic() < OPERATION_POLL_SECONDS + 1
            ):
                raise

        time.sleep(OPERATION_POLL_SECONDS)


def wait_for_operation(module, client, account_id, operation, deadline):
    operation_id = None
    if isinstance(operation, dict):
        operation_id = operation.get("operation_id") or operation.get("id")
    if operation_id is None:
        module.fail_json(
            msg="Rules list items submission did not return an operation id",
            operation=operation,
        )

    status = {}
    while True:
        remaining = deadline - time.monotonic()
        if remaining < 1:
            module.fail_json(
                msg="Timed out waiting for the rules list items operation to complete",
                operation_id=operation_id,
                operation=status,
            )

        try:
            status = get_result(
                client,
                operation_endpoint(account_id, operation_id),
                default={},
                timeout=remaining,
            )
        except (cloudflare.APIConnectionError, cloudflare.APIStatusError) as exc:
            if not transient_error(exc) or deadline - time.monotonic() < 1:
                fail_from_cloudflare_error(
                    module,
                    "Cloudflare API request failed while waiting for the rules "
                    "list items operation",
                    exc,
                    operation_id=operation_id,
                    operation=status,
                )
            status = {}

        if status.get("status") == "completed":
            return status

        if status.get("status") == "failed":
            module.fail_json(
                msg="Rules list items operation failed",
                operation_id=operation_id,
                operation=status,
            )

        time.sleep(min(OPERATION_POLL_SECONDS, max(deadline - time.monotonic(), 0)))


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

        normalized_items[canonical_item(normalized)] = normalized

    return sorted(normalized_items.values(), key=canonical_item)


def main():
    module = AnsibleModule(
        argument_spec={
            "account_id": {"required": True, "type": "str"},
            "api_token": {"required": True, "type": "str", "no_log": True},
            "name": {"required": True, "type": "str"},
            "kind": {"type": "str", "choices": ["ip", "redirect", "hostname", "asn"]},
            "description": {"type": "str"},
            "elements": {"type": "list", "elements": "dict"},
            "operation_timeout": {"type": "int", "default": 240},
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

    if params["operation_timeout"] < 1:
        module.fail_json(msg="operation_timeout must be at least 1 second")

    with cloudflare_client(module) as client:
        current = find_by_field(
            client,
            endpoint(params["account_id"]),
            "name",
            params["name"],
            paginate=False,
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

        if state == "present":
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
                        "description": (
                            params["name"]
                            if params.get("description") is None
                            else params["description"]
                        ),
                        "kind": params["kind"],
                        "name": params["name"],
                    },
                )
                changed = True
            else:
                desired_description = params.get("description")
                if (
                    desired_description is not None
                    and current.get("description") != desired_description
                ):
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
                desired_items = normalize_items(params["elements"])
                current_count = current.get("num_items")

                if current_count is not None and current_count != len(desired_items):
                    items_changed = True
                else:
                    current_items = []
                    cursor = None

                    while True:
                        query = {"cursor": cursor, "per_page": ITEMS_PER_PAGE}
                        query = {
                            key: value
                            for key, value in query.items()
                            if value is not None
                        }
                        path = items_endpoint(params["account_id"], current["id"])
                        if query:
                            path = "%s?%s" % (path, urlencode(query))

                        result, result_info = parse_list_response(
                            serialize_resource(client.get(path, cast_to=object))
                        )

                        current_items.extend(result)

                        cursor = (result_info.get("cursors") or {}).get("after")
                        if not cursor:
                            break

                    items_changed = values_differ(
                        normalize_items(current_items),
                        desired_items,
                    )

                if module.check_mode and items_changed:
                    module.exit_json(
                        changed=True,
                        message="Rules list items would be updated",
                        rules_list=current,
                    )

                if items_changed:
                    deadline = time.monotonic() + params["operation_timeout"]
                    items_operation = wait_for_operation(
                        module,
                        client,
                        params["account_id"],
                        submit_items(
                            client,
                            params["account_id"],
                            current["id"],
                            params["elements"],
                            deadline,
                        ),
                        deadline,
                    )
                    current = get_result(
                        client,
                        item_endpoint(params["account_id"], current["id"]),
                        default=current,
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


if __name__ == "__main__":
    main()
