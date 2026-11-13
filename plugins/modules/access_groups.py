#!/usr/bin/python
# Copyright: Ansible Project
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)


DOCUMENTATION = r"""
---
module: access_groups
short_description: Manage Cloudflare Access groups
description:
  - Create, update, and delete Cloudflare Access groups by name.
  - Access selectors in O(include), O(exclude), and O(require) use Cloudflare
    API key names, such as C(github-organization) and C(azureAD), and are
    compared exactly, including their nested fields.
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
      - An existing group's exclusions are preserved when omitted.
  require:
    type: list
    elements: dict
    description:
      - Additional Access selectors every included user must satisfy.
      - An existing group's requirements are preserved when omitted.
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
    ACCESS_SELECTOR_FIELDS,
    cloudflare_client,
    cloudflare_error_context,
    ensure_resource_absent,
    ensure_resource_present,
    find_resource,
    payload_from_params,
    validate_access_selectors,
)

FIELDS = ("exclude", "include", "is_default", "name", "require")
PRESERVED_FIELDS = ("exclude", "require")


def run(module, client):
    params = module.params
    account_id = params["account_id"]
    groups = client.zero_trust.access.groups
    if params["state"] == "present":
        validate_access_selectors(module)

    with cloudflare_error_context(
        "Cloudflare API request failed while finding the Access group",
        account_id=account_id,
        name=params["name"],
    ):
        current = find_resource(
            module,
            groups.list(account_id=account_id, name=params["name"]),
            "Access group",
            "name",
            params["name"],
        )

    if params["state"] == "absent":
        ensure_resource_absent(
            module,
            "access_group",
            "Access group",
            current,
            delete=lambda group_id: groups.delete(group_id, account_id=account_id),
            context={"account_id": account_id},
        )

    ensure_resource_present(
        module,
        "access_group",
        "Access group",
        current,
        payload_from_params(params, FIELDS),
        create=lambda payload: groups.create(account_id=account_id, **payload),
        update=lambda group_id, payload: groups.update(group_id, account_id=account_id, **payload),
        expected_name=params["name"],
        defaults={"is_default": False},
        preserved_fields=PRESERVED_FIELDS,
        exact_values=ACCESS_SELECTOR_FIELDS,
        context={"account_id": account_id},
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
        run(module, client)


if __name__ == "__main__":
    main()
