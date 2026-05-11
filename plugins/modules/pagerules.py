#!/usr/bin/python

# Copyright: (c) 2026, Taylor Kimball
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import absolute_import, division, print_function

__metaclass__ = type

DOCUMENTATION = r"""
---
module: pagerules
short_description: Manage Cloudflare page rules
description:
- Create, update, and delete Cloudflare page rules identified by their targets.
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
    - Actions.
  targets:
    required: true
    type: list
    elements: dict
    description:
    - Targets.
  priority:
    type: int
    description:
    - Priority.
  status:
    type: str
    choices:
    - active
    - disabled
    default: active
    description:
    - Status.
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

FIELDS = ("actions", "priority", "status", "targets")


def comparable_current(current, payload):
    return {field: current.get(field) for field in payload.keys()}


def endpoint(zone_id):
    return "/zones/%s/pagerules" % zone_id


def find_by_targets(pagerules, targets):
    for pagerule in pagerules:
        if not values_differ(pagerule.get("targets"), targets):
            return pagerule
    return None


def item_endpoint(zone_id, pagerule_id):
    return "%s/%s" % (endpoint(zone_id), pagerule_id)


def payload_from_params(params):
    payload = {"targets": params["targets"]}
    if params.get("actions") is not None:
        payload["actions"] = params["actions"]
    if params.get("priority") is not None:
        payload["priority"] = params["priority"]
    if params.get("status") is not None:
        payload["status"] = params["status"]
    return payload


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
                "default": "active",
            },
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
        pagerules = get_result(client, endpoint(params["zone_id"]), default=[])
        current = find_by_targets(pagerules, params["targets"])

        if params["state"] == "absent":
            if current is None:
                module.exit_json(changed=False, message="Page rule already absent")
            if module.check_mode:
                module.exit_json(
                    changed=True,
                    message="Page rule would be deleted",
                    pagerule=current,
                )
            delete_result(client, item_endpoint(params["zone_id"], current["id"]))
            module.exit_json(
                changed=True,
                message="Page rule deleted",
                pagerule=current,
            )

        if not params.get("actions"):
            module.fail_json(msg="actions is required when state=present")

        payload = payload_from_params(params)
        if current is None:
            if module.check_mode:
                module.exit_json(changed=True, message="Page rule would be created")
            pagerule = post_result(client, endpoint(params["zone_id"]), payload)
            module.exit_json(
                changed=True,
                message="Page rule created",
                pagerule=pagerule,
            )

        if not values_differ(comparable_current(current, payload), payload):
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

        pagerule = put_result(
            client,
            item_endpoint(params["zone_id"], current["id"]),
            payload,
        )
        module.exit_json(
            changed=True,
            message="Page rule updated",
            pagerule=pagerule,
        )


if __name__ == "__main__":
    main()
