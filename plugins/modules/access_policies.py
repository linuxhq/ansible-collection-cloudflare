#!/usr/bin/python

# Copyright: (c) 2026, Taylor Kimball
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import absolute_import, division, print_function

__metaclass__ = type

DOCUMENTATION = r"""
---
module: access_policies
short_description: Manage Cloudflare Access policies
description:
- Create, update, and delete Cloudflare Access policies by name.
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
  decision:
    type: str
    description:
    - Decision.
  include:
    type: list
    elements: dict
    description:
    - Include.
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
  approval_groups:
    type: list
    elements: dict
    description:
    - Approval groups.
  approval_required:
    type: bool
    default: false
    description:
    - Approval required.
  isolation_required:
    type: bool
    default: false
    description:
    - Isolation required.
  precedence:
    type: int
    description:
    - Precedence.
  purpose_justification_prompt:
    type: str
    description:
    - Purpose justification prompt.
  purpose_justification_required:
    type: bool
    default: false
    description:
    - Purpose justification required.
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
- name: Ensure Access policy exists
  linuxhq.cloudflare.access_policies:
    account_id: "{{ account_id }}"
    api_token: "{{ cloudflare_api_token }}"
    name: allow-admins
    decision: allow
    include:
      - email:
          email: admin@example.com
"""

RETURN = r"""
---
access_policy:
  description: Cloudflare Access policy.
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
    find_by_field,
    payload_from_params,
    post_result,
    put_result,
    selected_values_differ,
)

FIELDS = (
    "approval_groups",
    "approval_required",
    "decision",
    "exclude",
    "include",
    "isolation_required",
    "name",
    "precedence",
    "purpose_justification_prompt",
    "purpose_justification_required",
    "require",
)

FALSE_FIELDS = (
    "approval_required",
    "isolation_required",
    "purpose_justification_required",
)


def comparable_current(current):
    current = current.copy()
    for field in FALSE_FIELDS:
        current.setdefault(field, False)

    return current


def endpoint(account_id):
    return "/accounts/%s/access/policies" % account_id


def main():
    run_module()


def run_module():
    module = AnsibleModule(
        argument_spec={
            "account_id": {"required": True, "type": "str"},
            "api_token": {"required": True, "type": "str", "no_log": True},
            "name": {"required": True, "type": "str"},
            "approval_groups": {"type": "list", "elements": "dict"},
            "approval_required": {"type": "bool", "default": False},
            "decision": {"type": "str"},
            "exclude": {"type": "list", "elements": "dict"},
            "include": {"type": "list", "elements": "dict"},
            "isolation_required": {"type": "bool", "default": False},
            "precedence": {"type": "int"},
            "purpose_justification_prompt": {"type": "str"},
            "purpose_justification_required": {"type": "bool", "default": False},
            "require": {"type": "list", "elements": "dict"},
            "state": {
                "type": "str",
                "choices": ["present", "absent"],
                "default": "present",
            },
        },
        supports_check_mode=True,
    )

    params = module.params
    if params["state"] == "present":
        validate_present(module)

    with cloudflare_client(module) as client:
        current = find_by_field(
            client, endpoint(params["account_id"]), "name", params["name"]
        )

        if params["state"] == "absent":
            if current is None:
                module.exit_json(changed=False, message="Access policy already absent")
            if module.check_mode:
                module.exit_json(
                    changed=True,
                    message="Access policy would be deleted",
                    access_policy=current,
                )
            delete_result(
                client, "%s/%s" % (endpoint(params["account_id"]), current["id"])
            )
            module.exit_json(
                changed=True,
                message="Access policy deleted",
                access_policy=current,
            )

        payload = payload_from_params(params, FIELDS)
        if current is None:
            if module.check_mode:
                module.exit_json(changed=True, message="Access policy would be created")
            access_policy = post_result(client, endpoint(params["account_id"]), payload)
            module.exit_json(
                changed=True,
                message="Access policy created",
                access_policy=access_policy,
            )

        if not selected_values_differ(
            comparable_current(current),
            payload,
            tuple(payload.keys()),
        ):
            module.exit_json(
                changed=False,
                message="Access policy already present",
                access_policy=current,
            )

        if module.check_mode:
            module.exit_json(
                changed=True,
                message="Access policy would be updated",
                access_policy=current,
            )

        access_policy = put_result(
            client,
            "%s/%s" % (endpoint(params["account_id"]), current["id"]),
            payload,
        )
        module.exit_json(
            changed=True,
            message="Access policy updated",
            access_policy=access_policy,
        )


def validate_present(module):
    missing = [
        field
        for field in ("decision", "include")
        if module.params.get(field) in (None, [], "")
    ]
    if missing:
        module.fail_json(
            msg="decision and include are required when state=present",
            missing=missing,
        )


if __name__ == "__main__":
    main()
