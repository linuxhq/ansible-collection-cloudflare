#!/usr/bin/python
# Copyright: Contributors to the Ansible project
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)


DOCUMENTATION = r"""
---
module: access_groups
short_description: Manage Cloudflare Access groups
description:
  - Create, update, and delete Cloudflare Access groups by name.
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
      - Access group name.
  include:
    type: list
    elements: dict
    description:
      - Access selectors that include users in the group.
      - Required when O(state=present).
  exclude:
    type: list
    elements: dict
    description:
      - Access selectors that exclude users from the group.
  require:
    type: list
    elements: dict
    description:
      - Additional Access selectors every included user must satisfy.
  is_default:
    type: bool
    default: false
    description:
      - Whether this is the account's default Access group.
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
- name: Ensure Access group exists
  linuxhq.cloudflare.access_groups:
    account_id: "{{ account_id }}"
    api_token: "{{ cloudflare_api_token }}"
    name: admins
    include:
      - email:
          email: admin@example.com
"""

RETURN = r"""
---
access_group:
  description: Cloudflare Access group.
  returned: when available
  type: dict
  contains:
    id:
      description: Access group identifier.
      returned: always
      type: str
    name:
      description: Access group name.
      returned: always
      type: str
message:
  returned: always
  type: str
  description:
  - Operation summary.

"""

from ansible.module_utils.basic import AnsibleModule
from ansible_collections.linuxhq.cloudflare.plugins.module_utils.cloudflare_utils import (
    cloudflare_client,
    cloudflare_path,
    delete_result,
    find_by_name,
    normalize_current_by_desired_fields,
    payload_from_params,
    post_result,
    put_result,
    resource_id,
    select_fields,
    values_differ,
)

FIELDS = ("exclude", "include", "is_default", "name", "require")


def endpoint(account_id):
    return cloudflare_path("accounts", account_id, "access", "groups")


def ensure_present(module, client):
    params = module.params

    current = find_by_name(
        client,
        endpoint(params["account_id"]),
        params["name"],
    )

    payload = payload_from_params(params, FIELDS)

    if current is None:
        if module.check_mode:
            module.exit_json(changed=True, message="Access group would be created")

        access_group = post_result(client, endpoint(params["account_id"]), payload)
        resource_id(module, access_group, "Access group")
        module.exit_json(
            changed=True,
            message="Access group created",
            access_group=access_group,
        )

    current_id = resource_id(module, current, "Access group")
    comparable_current = current.copy()
    comparable_current.setdefault("is_default", False)

    if not values_differ(
        normalize_current_by_desired_fields(
            select_fields(comparable_current, payload.keys()),
            payload,
        ),
        payload,
    ):
        module.exit_json(
            changed=False,
            message="Access group already present",
            access_group=current,
        )

    if module.check_mode:
        module.exit_json(
            changed=True,
            message="Access group would be updated",
            access_group=current,
        )

    access_group = put_result(
        client,
        cloudflare_path(
            "accounts", params["account_id"], "access", "groups", current_id
        ),
        payload,
    )
    resource_id(module, access_group, "Access group")
    module.exit_json(
        changed=True,
        message="Access group updated",
        access_group=access_group,
    )


def ensure_absent(module, client):
    params = module.params

    current = find_by_name(
        client,
        endpoint(params["account_id"]),
        params["name"],
    )

    if current is None:
        module.exit_json(changed=False, message="Access group already absent")

    current_id = resource_id(module, current, "Access group")

    if module.check_mode:
        module.exit_json(
            changed=True,
            message="Access group would be deleted",
            access_group=current,
        )

    delete_result(
        client,
        cloudflare_path(
            "accounts", params["account_id"], "access", "groups", current_id
        ),
    )
    module.exit_json(
        changed=True,
        message="Access group deleted",
        access_group=current,
    )


def main():
    module = AnsibleModule(
        argument_spec={
            "account_id": {"required": True, "type": "str"},
            "api_token": {"required": True, "type": "str", "no_log": True},
            "name": {"required": True, "type": "str"},
            "include": {"type": "list", "elements": "dict"},
            "exclude": {"type": "list", "elements": "dict"},
            "require": {"type": "list", "elements": "dict"},
            "is_default": {"type": "bool", "default": False},
            "state": {
                "type": "str",
                "choices": ["present", "absent"],
                "default": "present",
            },
        },
        required_if=[("state", "present", ["include"])],
        supports_check_mode=True,
    )

    with cloudflare_client(module) as client:
        if module.params["state"] == "present":
            ensure_present(module, client)
        else:
            ensure_absent(module, client)


if __name__ == "__main__":
    main()
