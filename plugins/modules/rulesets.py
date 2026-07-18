#!/usr/bin/python
# -*- coding: utf-8 -*-
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
    type: str
    description:
      - Resource name.
      - Required when creating the ruleset; an existing ruleset cannot be renamed.
  rules:
    type: list
    elements: dict
    description:
      - Ruleset rules.
      - When omitted, the existing rules are preserved.
      - An explicit empty list clears the ruleset.
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
  - cloudflare >= 5.5.0, < 6

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
    normalize_current_by_desired_fields,
    post_result,
    put_result,
    values_differ,
)


def entrypoint_endpoint(zone_id, phase):
    return "/zones/%s/rulesets/phases/%s/entrypoint" % (zone_id, phase)


def rulesets_endpoint(zone_id):
    return "/zones/%s/rulesets" % zone_id


def main():
    module = AnsibleModule(
        argument_spec={
            "api_token": {"required": True, "type": "str", "no_log": True},
            "zone_id": {"required": True, "type": "str"},
            "name": {"type": "str"},
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
    state = params["state"]

    with cloudflare_client(module) as client:
        current = get_result(
            client,
            entrypoint_endpoint(params["zone_id"], params["phase"]),
            default=None,
            ok_statuses=[404],
        )

        if state == "absent":
            if not current or current.get("id") is None:
                module.exit_json(changed=False, message="Ruleset already absent")

            if module.check_mode:
                module.exit_json(
                    changed=True,
                    message="Ruleset would be deleted",
                    ruleset=current,
                )

            delete_result(
                client, "%s/%s" % (rulesets_endpoint(params["zone_id"]), current["id"])
            )
            module.exit_json(
                changed=True,
                message="Ruleset deleted",
                ruleset=current,
            )

        if state == "present":
            if current is None:
                if params.get("name") is None:
                    module.fail_json(msg="name is required when creating a ruleset")

                if module.check_mode:
                    module.exit_json(changed=True, message="Ruleset would be created")

                ruleset = post_result(
                    client,
                    rulesets_endpoint(params["zone_id"]),
                    {
                        "kind": params["kind"],
                        "name": params["name"],
                        "phase": params["phase"],
                        "rules": params.get("rules") or [],
                    },
                )
                module.exit_json(
                    changed=True, message="Ruleset created", ruleset=ruleset
                )

            if (
                params.get("name") is not None
                and current.get("name") is not None
                and params["name"] != current["name"]
            ):
                module.fail_json(
                    msg="An existing ruleset cannot be renamed",
                    ruleset=current,
                )

            payload = {
                "rules": (
                    current.get("rules") or []
                    if params.get("rules") is None
                    else params["rules"]
                ),
            }

            if not values_differ(
                normalize_current_by_desired_fields(
                    {"rules": current.get("rules") or []},
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
