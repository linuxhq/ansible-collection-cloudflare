#!/usr/bin/python
# -*- coding: utf-8 -*-
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import absolute_import, division, print_function

__metaclass__ = type

DOCUMENTATION = r"""
---
module: pagerules
short_description: Manage cloudflare pagerules
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
      - Required when state is C(present).
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
      - An existing rule's priority is preserved when omitted.
  status:
    type: str
    choices:
      - active
      - disabled
    description:
      - Status.
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
  - cloudflare >= 5.5.0, < 6

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
    payload_from_params,
    post_result,
    put_result,
    select_fields,
    values_differ,
)

FIELDS = ("actions", "priority", "status", "targets")


def endpoint(zone_id):
    return "/zones/%s/pagerules" % zone_id


def item_endpoint(zone_id, pagerule_id):
    return "%s/%s" % (endpoint(zone_id), pagerule_id)


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

    params = module.params
    state = params["state"]

    with cloudflare_client(module) as client:
        pagerules = get_result(client, endpoint(params["zone_id"]), default=[])
        current = None

        for pagerule in pagerules:
            if not values_differ(pagerule.get("targets"), params["targets"]):
                current = pagerule
                break

        if state == "absent":
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

        if state == "present":
            payload = payload_from_params(params, FIELDS)
            if current is None:
                payload.setdefault("status", "active")

                if module.check_mode:
                    module.exit_json(changed=True, message="Page rule would be created")

                pagerule = post_result(client, endpoint(params["zone_id"]), payload)
                module.exit_json(
                    changed=True,
                    message="Page rule created",
                    pagerule=pagerule,
                )

            for field in ("priority", "status"):
                if field not in payload and current.get(field) is not None:
                    payload[field] = current[field]

            if not values_differ(select_fields(current, payload.keys()), payload):
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
