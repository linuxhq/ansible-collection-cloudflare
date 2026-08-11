#!/usr/bin/python
# Copyright: Contributors to the Ansible project
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)


DOCUMENTATION = r"""
---
module: access_policies
short_description: Manage Cloudflare Access policies
description:
  - Create, update, and delete Cloudflare Access policies by name.
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
      - Access policy name.
  decision:
    type: str
    choices:
      - allow
      - deny
      - non_identity
      - bypass
    description:
      - Action applied when the policy matches.
      - Required when O(state=present).
  include:
    type: list
    elements: dict
    description:
      - Access selectors that identify candidate users.
      - Required when O(state=present).
  exclude:
    type: list
    elements: dict
    description:
      - Access selectors that remove users from the policy.
  require:
    type: list
    elements: dict
    description:
      - Additional Access selectors every included user must satisfy.
  approval_groups:
    type: list
    elements: dict
    description:
      - Approval groups authorized to approve access requests.
  approval_required:
    type: bool
    default: false
    description:
      - Whether users must obtain approval before access is granted.
  isolation_required:
    type: bool
    default: false
    description:
      - Whether matching sessions require browser isolation.
  purpose_justification_prompt:
    type: str
    description:
      - Prompt shown when requesting an access justification.
  purpose_justification_required:
    type: bool
    default: false
    description:
      - Whether users must provide a justification for access.
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
  contains:
    id:
      description: Access policy identifier.
      returned: always
      type: str
    name:
      description: Access policy name.
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
    find_by_field,
    normalize_current_by_desired_fields,
    payload_from_params,
    post_result,
    put_result,
    resource_field,
    resource_id,
    select_fields,
    validate_requested_values,
    values_differ,
)

FIELDS = (
    "approval_groups",
    "approval_required",
    "decision",
    "exclude",
    "include",
    "isolation_required",
    "name",
    "purpose_justification_prompt",
    "purpose_justification_required",
    "require",
)

FALSE_FIELDS = (
    "approval_required",
    "isolation_required",
    "purpose_justification_required",
)


def endpoint(account_id):
    return cloudflare_path("accounts", account_id, "access", "policies")


def ensure_present(module, client):
    params = module.params

    current = find_by_field(
        client, endpoint(params["account_id"]), "name", params["name"]
    )

    payload = payload_from_params(params, FIELDS)

    if current is None:
        if module.check_mode:
            module.exit_json(changed=True, message="Access policy would be created")

        access_policy = post_result(client, endpoint(params["account_id"]), payload)
        resource_id(module, access_policy, "Access policy")
        resource_field(
            module, access_policy, "name", "Access policy", expected=params["name"]
        )
        validate_requested_values(
            module,
            {**dict.fromkeys(FALSE_FIELDS, False), **access_policy},
            payload,
            "Access policy",
        )
        module.exit_json(
            changed=True,
            message="Access policy created",
            access_policy=access_policy,
        )

    current_id = resource_id(module, current, "Access policy")
    comparable_current = {**dict.fromkeys(FALSE_FIELDS, False), **current}

    if not values_differ(
        normalize_current_by_desired_fields(
            select_fields(comparable_current, payload.keys()),
            payload,
        ),
        payload,
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
        cloudflare_path(
            "accounts", params["account_id"], "access", "policies", current_id
        ),
        payload,
    )
    resource_id(module, access_policy, "Access policy", expected=current_id)
    resource_field(
        module, access_policy, "name", "Access policy", expected=params["name"]
    )
    validate_requested_values(
        module,
        {**dict.fromkeys(FALSE_FIELDS, False), **access_policy},
        payload,
        "Access policy",
    )
    module.exit_json(
        changed=True,
        message="Access policy updated",
        access_policy=access_policy,
    )


def ensure_absent(module, client):
    params = module.params

    current = find_by_field(
        client, endpoint(params["account_id"]), "name", params["name"]
    )

    if current is None:
        module.exit_json(changed=False, message="Access policy already absent")

    current_id = resource_id(module, current, "Access policy")

    if module.check_mode:
        module.exit_json(
            changed=True,
            message="Access policy would be deleted",
            access_policy=current,
        )

    delete_result(
        client,
        cloudflare_path(
            "accounts", params["account_id"], "access", "policies", current_id
        ),
        expected_id=current_id,
    )
    module.exit_json(
        changed=True,
        message="Access policy deleted",
        access_policy=current,
    )


def main():
    module = AnsibleModule(
        argument_spec={
            "account_id": {"required": True, "type": "str"},
            "api_token": {"required": True, "type": "str", "no_log": True},
            "name": {"required": True, "type": "str"},
            "approval_groups": {"type": "list", "elements": "dict"},
            "approval_required": {"type": "bool", "default": False},
            "decision": {
                "type": "str",
                "choices": ["allow", "deny", "non_identity", "bypass"],
            },
            "exclude": {"type": "list", "elements": "dict"},
            "include": {"type": "list", "elements": "dict"},
            "isolation_required": {"type": "bool", "default": False},
            "purpose_justification_prompt": {"type": "str"},
            "purpose_justification_required": {"type": "bool", "default": False},
            "require": {"type": "list", "elements": "dict"},
            "state": {
                "type": "str",
                "choices": ["present", "absent"],
                "default": "present",
            },
        },
        required_if=[("state", "present", ["decision", "include"])],
        supports_check_mode=True,
    )

    with cloudflare_client(module) as client:
        if module.params["state"] == "present":
            ensure_present(module, client)
        else:
            ensure_absent(module, client)


if __name__ == "__main__":
    main()
