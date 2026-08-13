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
options:
  api_token:
    required: true
    type: str
    description:
      - Cloudflare API token.
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
    cloudflare_path,
    delete_result,
    list_all,
    normalize_current_by_desired_fields,
    payload_from_params,
    post_result,
    put_result,
    require_mapping,
    resource_id,
    select_fields,
    validate_requested_values,
    values_differ,
)

FIELDS = ("actions", "priority", "status", "targets")


def endpoint(zone_id):
    return cloudflare_path("zones", zone_id, "pagerules")


def item_endpoint(zone_id, pagerule_id):
    return cloudflare_path("zones", zone_id, "pagerules", pagerule_id)


def pagerule_targets(module, pagerule):
    require_mapping(module, pagerule, "page rule")
    targets = pagerule.get("targets")
    if not isinstance(targets, list):
        module.fail_json(msg="Cloudflare API returned malformed page rule data")
    for target in targets:
        require_mapping(module, target, "page rule target")
    return targets


def find_pagerule(module, client):
    found = None
    for pagerule in list_all(client, endpoint(module.params["zone_id"])):
        if not values_differ(
            normalize_current_by_desired_fields(pagerule_targets(module, pagerule), module.params["targets"]),
            module.params["targets"],
        ):
            if found is not None:
                module.fail_json(msg="Multiple page rules match the requested target constraints")
            found = pagerule
    return found


def ensure_present(module, client):
    params = module.params
    current = find_pagerule(module, client)

    payload = payload_from_params(params, FIELDS)

    if current is None:
        payload.setdefault("status", "active")

        if module.check_mode:
            module.exit_json(changed=True, message="Page rule would be created")

        pagerule = post_result(client, endpoint(params["zone_id"]), payload)
        resource_id(module, pagerule, "page rule")
        validate_requested_values(module, pagerule, payload, "page rule")
        module.exit_json(
            changed=True,
            message="Page rule created",
            pagerule=pagerule,
        )

    for field in ("priority", "status"):
        if field not in payload and current.get(field) is not None:
            payload[field] = current[field]

    if not values_differ(
        normalize_current_by_desired_fields(select_fields(current, payload.keys()), payload),
        payload,
    ):
        module.exit_json(
            changed=False,
            message="Page rule already present",
            pagerule=current,
        )

    if module.check_mode:
        module.exit_json(
            changed=True,
            message="Page rule would be updated",
            pagerule=current,
        )

    current_id = resource_id(module, current, "page rule")
    pagerule = put_result(
        client,
        item_endpoint(params["zone_id"], current_id),
        payload,
    )
    resource_id(module, pagerule, "page rule", expected=current_id)
    validate_requested_values(module, pagerule, payload, "page rule")
    module.exit_json(
        changed=True,
        message="Page rule updated",
        pagerule=pagerule,
    )


def ensure_absent(module, client):
    params = module.params
    current = find_pagerule(module, client)

    if current is None:
        module.exit_json(changed=False, message="Page rule already absent")

    if module.check_mode:
        module.exit_json(
            changed=True,
            message="Page rule would be deleted",
            pagerule=current,
        )

    current_id = resource_id(module, current, "page rule")
    delete_result(client, item_endpoint(params["zone_id"], current_id), expected_id=current_id)
    module.exit_json(
        changed=True,
        message="Page rule deleted",
        pagerule=current,
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
        if module.params["state"] == "present":
            ensure_present(module, client)
        else:
            ensure_absent(module, client)


if __name__ == "__main__":
    main()
