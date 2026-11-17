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
    compared exactly, including their nested fields, except that the C(id)
    Cloudflare adds to a C(github-organization) selector matches a selector
    that omits it.
  - A selector of a known type accepts only the nested fields Cloudflare
    stores for it, such as C(email) of an C(email) selector. Cloudflare
    accepts any other field but does not store it, so the module fails before
    making changes.
  - Each selector is a mapping that sets one rule, such as C(email) or
    C(everyone). Cloudflare drops an empty selector V({}) and splits a
    selector with several rules into separate selectors, so such a selector
    fails before any change.
  - Cloudflare stores a null C(any_valid_service_token) selector value as
    V({}), so such a selector fails before any change; use V({}) instead.
  - The C(account_id) of a C(cloudflare_account_member) or C(device_posture)
    selector and the C(identity_provider_id) of a C(saml) selector must not
    be V(""). Cloudflare does not store the empty value, so such a selector
    fails before any change; omit the field instead.
version_added: '2.0.0'
author:
  - Taylor Kimball (@tkimball83)
notes:
  - Cloudflare may store a requested value in a canonical form that differs from the request. The module then
    fails after the write, naming the requested and stored value of each differing field in the message and in
    C(differences), so the stored form can be requested instead.
extends_documentation_fragment:
  - linuxhq.cloudflare.cloudflare
  - linuxhq.cloudflare.cloudflare.account
  - linuxhq.cloudflare.cloudflare.create
options:
  name:
    required: true
    type: str
    description:
      - Access group name.
      - Cloudflare trims surrounding whitespace from the name, and group names
        are unique, so a name with leading or trailing whitespace never
        converges. The first run creates the group with the trimmed name and
        then fails because Cloudflare returns the wrong Access group; later
        runs fail because Cloudflare rejects the name as already in use.
      - An empty or whitespace-only name fails before any change, because
        Cloudflare does not store it.
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
    description:
      - Whether this is the account's default Access group.
      - An existing group's default status is preserved when omitted.
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
    comparable_access_rules,
    ensure_resource_absent,
    ensure_resource_present,
    find_resource,
    matching_resources,
    payload_from_params,
    validate_access_selectors,
    without_retries,
)

FIELDS = ("exclude", "include", "is_default", "name", "require")
PRESERVED_FIELDS = ("exclude", "is_default", "require")


def run(module, client):
    params = module.params
    account_id = params["account_id"]
    groups = client.zero_trust.access.groups
    if params["state"] == "present":
        # Cloudflare stores an empty name as null, so the resource is never found again.
        if not params["name"].strip():
            module.fail_json(msg="name must not be empty or only whitespace")

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
        create=lambda payload: without_retries(client).zero_trust.access.groups.create(
            account_id=account_id, **payload
        ),
        update=lambda group_id, payload: groups.update(group_id, account_id=account_id, **payload),
        find_created=lambda: matching_resources(
            groups.list(account_id=account_id, name=params["name"]), "name", params["name"]
        ),
        expected_name=params["name"],
        defaults={"is_default": False},
        preserved_fields=PRESERVED_FIELDS,
        exact_values=ACCESS_SELECTOR_FIELDS,
        comparable=lambda resource: comparable_access_rules(resource, params),
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
            "is_default": {"type": "bool"},
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
