#!/usr/bin/python
# Copyright: Ansible Project
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)


DOCUMENTATION = r"""
---
module: pagerules
short_description: Manage Cloudflare Page Rules
description:
  - Create, update, and delete Cloudflare page rules identified by their targets.
version_added: '2.0.0'
author:
  - Taylor Kimball (@tkimball83)
extends_documentation_fragment:
  - linuxhq.cloudflare.cloudflare
options:
  zone_id:
    required: true
    type: str
    description:
      - Cloudflare zone identifier.
  actions:
    type: list
    elements: dict
    description:
      - Actions applied when the page rule matches.
      - Required when O(state=present).
  targets:
    required: true
    type: list
    elements: dict
    description:
      - URL matching conditions that identify the page rule.
  priority:
    type: int
    description:
      - Evaluation priority of the page rule.
      - An existing rule's priority is preserved when omitted.
  status:
    type: str
    choices:
      - active
      - disabled
    description:
      - Whether the page rule is active or disabled.
      - Defaults to C(active) when creating a page rule; an existing rule's
        status is preserved when omitted.
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
- name: Ensure page rule exists
  linuxhq.cloudflare.pagerules:
    api_token: "{{ cloudflare_api_token }}"
    zone_id: "{{ zone_id }}"
    actions:
      - id: forwarding_url
        value:
          status_code: 301
          url: https://www.example.com
    targets:
      - target: url
        constraint:
          operator: matches
          value: example.com/*
"""

RETURN = r"""
---
pagerule:
  description: Cloudflare page rule.
  returned: when available
  type: dict
  contains:
    id:
      description: Page rule identifier.
      returned: always
      type: str
    actions:
      description: Actions applied by the page rule.
      returned: always
      type: list
      elements: dict
    priority:
      description: Evaluation priority of the page rule.
      returned: when available
      type: int
    status:
      description: Current page rule status.
      returned: when available
      type: str
    targets:
      description: Target constraints identifying the page rule.
      returned: always
      type: list
      elements: dict
message:
  returned: always
  type: str
  description:
  - Operation summary.

"""

from ansible.module_utils.basic import AnsibleModule

from ansible_collections.linuxhq.cloudflare.plugins.module_utils.cloudflare_utils import (
    cloudflare_client,
    cloudflare_error_context,
    ensure_resource_absent,
    ensure_resource_present,
    normalize_current_by_desired_fields,
    payload_from_params,
    require_mapping,
    serialize_resource,
    values_differ,
)

FIELDS = ("actions", "priority", "status", "targets")
PRESERVED_FIELDS = ("priority", "status")


def pagerule_targets(module, pagerule):
    require_mapping(module, pagerule, "page rule")
    targets = pagerule.get("targets")
    if not isinstance(targets, list):
        module.fail_json(msg="Cloudflare API returned malformed page rule data")

    for target in targets:
        require_mapping(module, target, "page rule target")

    return targets


def find_pagerule(module, client):
    zone_id = module.params["zone_id"]
    targets = module.params["targets"]
    with cloudflare_error_context(
        "Cloudflare API request failed while finding the page rule",
        zone_id=zone_id,
    ):
        # The SDK types this response as optional; treat null as no rules.
        pagerules = client.page_rules.list(zone_id=zone_id) or []

    found = None
    for pagerule in pagerules:
        pagerule = serialize_resource(pagerule)
        if not values_differ(normalize_current_by_desired_fields(pagerule_targets(module, pagerule), targets), targets):
            if found is not None:
                module.fail_json(msg="Multiple page rules match the requested target constraints")

            found = pagerule

    return found


def run(module, client):
    zone_id = module.params["zone_id"]
    page_rules = client.page_rules
    current = find_pagerule(module, client)

    if module.params["state"] == "absent":
        ensure_resource_absent(
            module,
            "pagerule",
            "page rule",
            current,
            delete=lambda pagerule_id: page_rules.delete(pagerule_id=pagerule_id, zone_id=zone_id),
            context={"zone_id": zone_id},
        )

    payload = payload_from_params(module.params, FIELDS)
    if current is None:
        payload.setdefault("status", "active")

    ensure_resource_present(
        module,
        "pagerule",
        "page rule",
        current,
        payload,
        create=lambda payload: page_rules.create(zone_id=zone_id, **payload),
        update=lambda pagerule_id, payload: page_rules.update(pagerule_id=pagerule_id, zone_id=zone_id, **payload),
        preserved_fields=PRESERVED_FIELDS,
        context={"zone_id": zone_id},
    )


def main():
    module = AnsibleModule(
        argument_spec={
            "api_token": {"required": True, "type": "str", "no_log": True},
            "zone_id": {"required": True, "type": "str"},
            "actions": {"type": "list", "elements": "dict"},
            "targets": {"required": True, "type": "list", "elements": "dict"},
            "priority": {"type": "int"},
            "status": {
                "type": "str",
                "choices": ["active", "disabled"],
            },
            "state": {
                "type": "str",
                "choices": ["present", "absent"],
                "default": "present",
            },
        },
        required_if=[("state", "present", ["actions"])],
        supports_check_mode=True,
    )

    with cloudflare_client(module) as client:
        run(module, client)


if __name__ == "__main__":
    main()
