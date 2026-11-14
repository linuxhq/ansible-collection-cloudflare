#!/usr/bin/python
# Copyright: Ansible Project
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)


DOCUMENTATION = r"""
---
module: access_policies
short_description: Manage Cloudflare Access policies
description:
  - Create, update, and delete Cloudflare Access policies by name.
  - Access selectors in O(include), O(exclude), and O(require) use Cloudflare
    API key names, such as C(github-organization) and C(azureAD), and are
    compared exactly, including their nested fields.
  - Settings this module does not manage, such as C(session_duration), are
    preserved on an existing policy.
version_added: '2.0.0'
author:
  - Taylor Kimball (@tkimball83)
extends_documentation_fragment:
  - linuxhq.cloudflare.cloudflare
  - linuxhq.cloudflare.cloudflare.account
options:
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
      - An existing policy's value is preserved when omitted.
  require:
    type: list
    elements: dict
    description:
      - Additional Access selectors every included user must satisfy.
      - An existing policy's value is preserved when omitted.
  approval_groups:
    type: list
    elements: dict
    description:
      - Approval groups authorized to approve access requests.
      - An existing policy's value is preserved when omitted.
  approval_required:
    type: bool
    description:
      - Whether users must obtain approval before access is granted.
      - When omitted, the current value is left unchanged; Cloudflare defaults
        to V(false) on create.
  isolation_required:
    type: bool
    description:
      - Whether matching sessions require browser isolation.
      - When omitted, the current value is left unchanged; Cloudflare defaults
        to V(false) on create.
  purpose_justification_prompt:
    type: str
    description:
      - Prompt shown when requesting an access justification.
      - An existing policy's value is preserved when omitted.
      - V("") clears the prompt; Cloudflare then omits it, so V("") matches a
        policy without a prompt.
  purpose_justification_required:
    type: bool
    description:
      - Whether users must provide a justification for access.
      - When omitted, the current value is left unchanged; Cloudflare defaults
        to V(false) on create.
  state:
    type: str
    choices:
      - present
      - absent
    default: present
    description:
      - Desired state of the resource.
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
    ACCESS_SELECTOR_FIELDS,
    cloudflare_client,
    cloudflare_error_context,
    ensure_resource_absent,
    ensure_resource_present,
    find_resource,
    payload_from_params,
    validate_access_selectors,
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

PRESERVED_FIELDS = (
    "approval_groups",
    "approval_required",
    "exclude",
    "isolation_required",
    "purpose_justification_prompt",
    "purpose_justification_required",
    "require",
)

# The update replaces the policy, so settings this module does not manage are
# carried over too.
UNMANAGED_FIELDS = ("connection_rules", "mfa_config", "policy_resolution_account_id", "session_duration")

FALSE_FIELDS = (
    "approval_required",
    "isolation_required",
    "purpose_justification_required",
)


def run(module, client):
    params = module.params
    account_id = params["account_id"]
    policies = client.zero_trust.access.policies
    if params["state"] == "present":
        validate_access_selectors(module)

    # The list endpoint has no name filter, so match the name locally.
    with cloudflare_error_context(
        "Cloudflare API request failed while finding the Access policy",
        account_id=account_id,
        name=params["name"],
    ):
        current = find_resource(
            module,
            policies.list(account_id=account_id),
            "Access policy",
            "name",
            params["name"],
        )

    if params["state"] == "absent":
        ensure_resource_absent(
            module,
            "access_policy",
            "Access policy",
            current,
            delete=lambda policy_id: policies.delete(policy_id, account_id=account_id),
            context={"account_id": account_id},
        )

    ensure_resource_present(
        module,
        "access_policy",
        "Access policy",
        current,
        payload_from_params(params, FIELDS),
        create=lambda payload: policies.create(account_id=account_id, **payload),
        update=lambda policy_id, payload: policies.update(policy_id, account_id=account_id, **payload),
        expected_name=params["name"],
        # Cloudflare omits a prompt cleared with "".
        defaults={**dict.fromkeys(FALSE_FIELDS, False), "purpose_justification_prompt": ""},
        preserved_fields=PRESERVED_FIELDS + UNMANAGED_FIELDS,
        exact_values=ACCESS_SELECTOR_FIELDS,
        context={"account_id": account_id},
    )


def main():
    module = AnsibleModule(
        argument_spec={
            "account_id": {"required": True, "type": "str"},
            "api_token": {"required": True, "type": "str", "no_log": True},
            "name": {"required": True, "type": "str"},
            "approval_groups": {"type": "list", "elements": "dict"},
            "approval_required": {"type": "bool"},
            "decision": {
                "type": "str",
                "choices": ["allow", "deny", "non_identity", "bypass"],
            },
            "exclude": {"type": "list", "elements": "dict"},
            "include": {"type": "list", "elements": "dict"},
            "isolation_required": {"type": "bool"},
            "purpose_justification_prompt": {"type": "str"},
            "purpose_justification_required": {"type": "bool"},
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
        run(module, client)


if __name__ == "__main__":
    main()
