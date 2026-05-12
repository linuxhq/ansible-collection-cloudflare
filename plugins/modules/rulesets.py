#!/usr/bin/python

# Copyright: (c) 2026, Taylor Kimball
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import absolute_import, division, print_function

__metaclass__ = type

DOCUMENTATION = r"""
---
module: rulesets
short_description: Manage cloudflare rulesets
description:
- Create, update, and delete a Cloudflare zone ruleset entrypoint for a phase.
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
  name:
    required: true
    type: str
    description:
    - Resource name.
  rules:
    type: list
    elements: dict
    description:
    - Ruleset rules.
  phase:
    type: str
    default: http_request_firewall_custom
    description:
    - Ruleset phase.
  kind:
    type: str
    default: zone
    description:
    - Resource kind.
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
- name: Ensure custom firewall ruleset exists
  linuxhq.cloudflare.rulesets:
    api_token: "{{ cloudflare_api_token }}"
    zone_id: "{{ zone_id }}"
    name: default
    rules:
      - action: block
        expression: (ip.geoip.country ne "US")
"""

RETURN = r"""
---
ruleset:
  description: Cloudflare ruleset.
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
    get_result,
    post_result,
    put_result,
    values_differ,
)


def entrypoint_endpoint(zone_id, phase):
    return "/zones/%s/rulesets/phases/%s/entrypoint" % (zone_id, phase)


def item_endpoint(zone_id, ruleset_id):
    return "%s/%s" % (rulesets_endpoint(zone_id), ruleset_id)


def normalize_current_by_desired_fields(current, desired):
    if isinstance(current, dict) and isinstance(desired, dict):
        return {
            key: normalize_current_by_desired_fields(current.get(key), value)
            for key, value in desired.items()
        }

    if isinstance(current, list) and isinstance(desired, list):
        if len(current) != len(desired):
            return current
        return [
            normalize_current_by_desired_fields(current_item, desired_item)
            for current_item, desired_item in zip(current, desired)
        ]

    return current


def payload_from_params(params, include_kind_phase):
    payload = {
        "name": params["name"],
        "rules": params.get("rules") or [],
    }
    if include_kind_phase:
        payload["kind"] = params["kind"]
        payload["phase"] = params["phase"]
    return payload


def rulesets_endpoint(zone_id):
    return "/zones/%s/rulesets" % zone_id


def selected_current(current, payload):
    return {key: current.get(key) for key in payload.keys()}


def main():
    module = AnsibleModule(
        argument_spec={
            "api_token": {"required": True, "type": "str", "no_log": True},
            "zone_id": {"required": True, "type": "str"},
            "name": {"required": True, "type": "str"},
            "rules": {"type": "list", "elements": "dict"},
            "phase": {"type": "str", "default": "http_request_firewall_custom"},
            "kind": {"type": "str", "default": "zone"},
            "state": {
                "type": "str",
                "choices": ["present", "absent"],
                "default": "present",
            },
        },
        supports_check_mode=True,
    )

    params = module.params
    with cloudflare_client(module) as client:
        current = get_result(
            client,
            entrypoint_endpoint(params["zone_id"], params["phase"]),
            default=None,
            ok_statuses=[404],
        )

        if params["state"] == "absent":
            if not current or current.get("id") is None:
                module.exit_json(changed=False, message="Ruleset already absent")
            if module.check_mode:
                module.exit_json(
                    changed=True,
                    message="Ruleset would be deleted",
                    ruleset=current,
                )
            delete_result(client, item_endpoint(params["zone_id"], current["id"]))
            module.exit_json(
                changed=True,
                message="Ruleset deleted",
                ruleset=current,
            )

        payload = payload_from_params(params, current is None)
        if current is None:
            if module.check_mode:
                module.exit_json(changed=True, message="Ruleset would be created")
            ruleset = post_result(client, rulesets_endpoint(params["zone_id"]), payload)
            module.exit_json(changed=True, message="Ruleset created", ruleset=ruleset)

        if not values_differ(
            normalize_current_by_desired_fields(
                selected_current(current, payload),
                payload,
            ),
            payload,
        ):
            module.exit_json(
                changed=False,
                message="Ruleset already present",
                ruleset=current,
            )

        if module.check_mode:
            module.exit_json(
                changed=True,
                message="Ruleset would be updated",
                ruleset=current,
            )

        ruleset = put_result(
            client,
            entrypoint_endpoint(params["zone_id"], params["phase"]),
            payload,
        )
        module.exit_json(changed=True, message="Ruleset updated", ruleset=ruleset)


if __name__ == "__main__":
    main()
