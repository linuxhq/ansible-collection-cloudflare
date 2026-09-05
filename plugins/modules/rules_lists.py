#!/usr/bin/python
# Copyright: Ansible Project
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)


DOCUMENTATION = r"""
---
module: rules_lists
short_description: Manage Cloudflare Rules Lists
description:
  - Create, update, populate, and delete Cloudflare Rules lists by name.
  - Item updates wait for the resulting bulk operation to complete and fail when
    Cloudflare reports the operation failed.
version_added: '2.0.0'
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
      - Rules list name.
  kind:
    type: str
    choices:
      - ip
      - redirect
      - hostname
      - asn
    description:
      - Data type stored by the Rules list.
      - Required when creating a Rules list.
      - Existing list kinds cannot be changed.
  description:
    type: str
    description:
      - Human-readable purpose of the Rules list.
  elements:
    type: list
    elements: dict
    description:
      - Complete set of entries that the Rules list must contain.
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
  - cloudflare >= 5.6.0, < 6
attributes:
  check_mode:
    description: Supports predicting changes without applying them.
    support: full
  diff_mode:
    description: Determines whether the module returns change details in diff format.
    support: none

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
  contains:
    id:
      description: Rules list identifier.
      returned: always
      type: str
    name:
      description: Rules list name.
      returned: always
      type: str
    kind:
      description: Data type stored by the Rules list.
      returned: always
      type: str
    num_items:
      description: Number of entries in the Rules list.
      returned: when available
      type: float
items_operation:
  description: Bulk operation returned when list items were updated.
  returned: when list items changed
  type: dict
  contains:
    id:
      description: Bulk operation identifier.
      returned: when provided by Cloudflare
      type: str
    operation_id:
      description: Bulk operation identifier.
      returned: when provided by Cloudflare
      type: str
    status:
      description: Final bulk operation status.
      returned: always
      type: str
message:
  returned: always
  type: str
  description:
  - Operation summary.

"""

import json
import time

from ansible.module_utils.basic import AnsibleModule

from ansible_collections.linuxhq.cloudflare.plugins.module_utils.cloudflare_utils import (
    CloudflareResponseError,
    cloudflare,
    cloudflare_client,
    cloudflare_error_context,
    cloudflare_path,
    delete_result,
    fail_from_cloudflare_error,
    find_by_field,
    get_result,
    post_result,
    put_result,
    require_mapping,
    resource_field,
    resource_id,
    serialize_resource,
    validate_requested_values,
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
    return cloudflare_path("accounts", account_id, "rules", "lists")


def item_endpoint(account_id, list_id):
    return cloudflare_path("accounts", account_id, "rules", "lists", list_id)


def items_endpoint(account_id, list_id):
    return cloudflare_path("accounts", account_id, "rules", "lists", list_id, "items")


def list_items(module, client, account_id, list_id):
    with cloudflare_error_context(
        "Cloudflare API request failed while gathering Rules list items",
        account_id=account_id,
        rules_list_id=list_id,
    ):
        items = [
            serialize_resource(item)
            for item in client.rules.lists.items.list(
                list_id,
                account_id=account_id,
                per_page=ITEMS_PER_PAGE,
            )
        ]

    for item in items:
        require_mapping(module, item, "Rules list item")

    return items


def operation_endpoint(account_id, operation_id):
    return cloudflare_path(
        "accounts",
        account_id,
        "rules",
        "lists",
        "bulk_operations",
        operation_id,
    )


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
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            raise CloudflareResponseError("Timed out submitting the Rules list items operation")

        try:
            return put_result(
                client,
                items_endpoint(account_id, list_id),
                elements,
                timeout=remaining,
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

    if not isinstance(operation_id, str) or not operation_id.strip() or operation_id != operation_id.strip():
        module.fail_json(
            msg="Rules list items submission did not return an operation id",
            operation=operation,
        )

    status = {}
    while True:
        remaining = deadline - time.monotonic()
        if remaining <= 0:
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
            if not transient_error(exc) or deadline - time.monotonic() <= 0:
                fail_from_cloudflare_error(
                    module,
                    "Cloudflare API request failed while waiting for the rules list items operation",
                    exc,
                    operation_id=operation_id,
                    operation=status,
                )

            status = {}
            time.sleep(min(OPERATION_POLL_SECONDS, max(deadline - time.monotonic(), 0)))
            continue

        if not isinstance(status, dict) or not isinstance(status.get("status"), str):
            module.fail_json(
                msg="Cloudflare API returned malformed Rules list operation data",
                operation_id=operation_id,
            )

        status_id = resource_id(module, status, "Rules list operation")
        if status_id != operation_id:
            module.fail_json(
                msg="Cloudflare API returned the wrong Rules list operation",
                operation_id=operation_id,
            )

        operation_status = status["status"]
        if operation_status == "completed":
            return status

        if operation_status == "failed":
            module.fail_json(
                msg="Rules list items operation failed",
                operation_id=operation_id,
                operation=status,
            )

        if operation_status not in ("pending", "running"):
            module.fail_json(
                msg="Cloudflare API returned an unknown Rules list operation status",
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

            normalized_value = value
            if key == "hostname" and isinstance(normalized_value, dict):
                hostname = {
                    hostname_key: hostname_value
                    for hostname_key, hostname_value in normalized_value.items()
                    if hostname_value is not None
                }

                if hostname.get("exclude_exact_hostname") is True:
                    hostname.pop("exclude_exact_hostname")

                normalized_value = hostname

            if key == "redirect" and isinstance(normalized_value, dict):
                normalized_value = {
                    redirect_key: redirect_value
                    for redirect_key, redirect_value in normalized_value.items()
                    if redirect_value is not None and redirect_value != REDIRECT_DEFAULTS.get(redirect_key)
                }

            normalized[key] = normalized_value

        normalized_items[canonical_item(normalized)] = normalized

    return sorted(normalized_items.values(), key=canonical_item)


def ensure_present(module, client):
    params = module.params

    current = find_by_field(
        client,
        endpoint(params["account_id"]),
        "name",
        params["name"],
        paginate=False,
    )

    if current is None and params.get("kind") is None:
        module.fail_json(msg="kind is required when creating a Rules list")

    changed = False
    created = False
    items_changed = False
    items_operation = None

    if current is None:
        if module.check_mode:
            module.exit_json(changed=True, message="Rules list would be created")

        payload = {
            "description": (params["name"] if params.get("description") is None else params["description"]),
            "kind": params["kind"],
            "name": params["name"],
        }
        current = post_result(
            client,
            endpoint(params["account_id"]),
            payload,
        )
        resource_id(module, current, "Rules list")
        resource_field(module, current, "name", "Rules list", expected=params["name"])
        resource_field(module, current, "kind", "Rules list", expected=params["kind"])
        validate_requested_values(module, current, payload, "Rules list")
        current_kind = params["kind"]
        changed = True
        created = True
    else:
        current_id = resource_id(module, current, "Rules list")
        current_kind = resource_field(module, current, "kind", "Rules list")
        if params.get("kind") is not None and params["kind"] != current_kind:
            module.fail_json(
                msg="An existing Rules list kind cannot be changed",
                rules_list=current,
            )

        desired_description = params.get("description")
        if desired_description is not None and current.get("description") != desired_description:
            if module.check_mode:
                module.exit_json(
                    changed=True,
                    message="Rules list would be updated",
                    rules_list=current,
                )

            current = put_result(
                client,
                item_endpoint(params["account_id"], current_id),
                {"description": desired_description},
            )
            resource_id(module, current, "Rules list", expected=current_id)
            resource_field(module, current, "name", "Rules list", expected=params["name"])
            resource_field(module, current, "kind", "Rules list", expected=current_kind)
            validate_requested_values(
                module,
                current,
                {"description": desired_description},
                "Rules list",
            )
            changed = True

    current_id = resource_id(module, current, "Rules list")

    if params.get("elements") is not None:
        desired_items = normalize_items(params["elements"])
        current_count = current.get("num_items")

        if current_count is not None and (
            isinstance(current_count, bool)
            or not isinstance(current_count, (int, float))
            or current_count < 0
            or int(current_count) != current_count
        ):
            module.fail_json(msg="Cloudflare API returned malformed Rules list data")

        if current_count is not None and current_count != len(desired_items):
            items_changed = True
        else:
            items_changed = values_differ(
                normalize_items(list_items(module, client, params["account_id"], current_id)),
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
                    current_id,
                    desired_items,
                    deadline,
                ),
                deadline,
            )
            current = get_result(
                client,
                item_endpoint(params["account_id"], current_id),
                default=current,
            )
            resource_id(module, current, "Rules list", expected=current_id)
            resource_field(module, current, "name", "Rules list", expected=params["name"])
            resource_field(module, current, "kind", "Rules list", expected=current_kind)
            if values_differ(
                normalize_items(list_items(module, client, params["account_id"], current_id)),
                desired_items,
            ):
                module.fail_json(msg="Cloudflare did not apply the requested Rules list items")

    if not changed and not items_changed:
        module.exit_json(
            changed=False,
            message="Rules list already present",
            rules_list=current,
        )

    result = {
        "changed": True,
        "message": "Rules list created" if created else "Rules list updated",
        "rules_list": current,
    }
    if items_operation is not None:
        result["items_operation"] = items_operation

    module.exit_json(**result)


def ensure_absent(module, client):
    params = module.params

    current = find_by_field(
        client,
        endpoint(params["account_id"]),
        "name",
        params["name"],
        paginate=False,
    )

    if current is None:
        module.exit_json(changed=False, message="Rules list already absent")

    if module.check_mode:
        module.exit_json(
            changed=True,
            message="Rules list would be deleted",
            rules_list=current,
        )

    current_id = resource_id(module, current, "Rules list")
    delete_result(client, item_endpoint(params["account_id"], current_id), expected_id=current_id)
    module.exit_json(
        changed=True,
        message="Rules list deleted",
        rules_list=current,
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
            "operation_timeout": {"type": "int", "default": 240},
            "state": {
                "type": "str",
                "choices": ["present", "absent"],
                "default": "present",
            },
        },
        supports_check_mode=True,
    )

    if module.params["operation_timeout"] < 1:
        module.fail_json(msg="operation_timeout must be at least 1 second")

    with cloudflare_client(module) as client:
        if module.params["state"] == "present":
            ensure_present(module, client)
        else:
            ensure_absent(module, client)


if __name__ == "__main__":
    main()
