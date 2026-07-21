#!/usr/bin/python
# -*- coding: utf-8 -*-
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import absolute_import, division, print_function

__metaclass__ = type

DOCUMENTATION = r"""
---
module: access_groups
short_description: Manage cloudflare access groups
description:
  - Create, update, and delete Cloudflare Access groups by name.
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
  include:
    type: list
    elements: dict
    description:
      - Include.
      - Required when state is C(present).
  exclude:
    type: list
    elements: dict
    description:
      - Exclude.
  require:
    type: list
    elements: dict
    description:
      - Require.
  is_default:
    type: bool
    default: false
    description:
      - Is default.
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
message:
  returned: always
  type: str
  description:
  - Operation summary.

"""

from ansible.module_utils.basic import AnsibleModule

from ansible_collections.linuxhq.cloudflare.plugins.module_utils.cloudflare_utils import (
    cloudflare_client,
    delete_result,
    find_by_name,
    payload_from_params,
    post_result,
    put_result,
    select_fields,
    values_differ,
)

FIELDS = ("exclude", "include", "is_default", "name", "require")


def endpoint(account_id):
    return "/accounts/%s/access/groups" % account_id


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
        module.exit_json(
            changed=True,
            message="Access group created",
            access_group=access_group,
        )

    comparable_current = current.copy()
    comparable_current.setdefault("is_default", False)

    if not values_differ(
        select_fields(comparable_current, payload.keys()),
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
        "%s/%s" % (endpoint(params["account_id"]), current["id"]),
        payload,
    )
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

    if module.check_mode:
        module.exit_json(
            changed=True,
            message="Access group would be deleted",
            access_group=current,
        )

    delete_result(client, "%s/%s" % (endpoint(params["account_id"]), current["id"]))
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
