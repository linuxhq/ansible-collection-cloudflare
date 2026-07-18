#!/usr/bin/python
# -*- coding: utf-8 -*-
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import absolute_import, division, print_function

__metaclass__ = type

DOCUMENTATION = r"""
---
module: dnssec
short_description: Manage cloudflare dnssec settings
description:
  - Manage Cloudflare DNSSEC settings for a zone.
author:
  - Taylor Kimball (@tkimball83)
options:
  api_token:
    description:
      - Cloudflare API token with permissions to manage DNS settings.
    required: true
    type: str
  zone_id:
    description:
      - Cloudflare zone identifier.
    required: true
    type: str
  dnssec_multi_signer:
    description:
      - Whether multi-signer DNSSEC is enabled.
    type: bool
  dnssec_presigned:
    description:
      - Whether presigned DNSSEC is enabled.
    type: bool
  dnssec_use_nsec3:
    description:
      - Whether NSEC3 is enabled.
    type: bool
  status:
    description:
      - Desired DNSSEC status.
      - Only changed when explicitly provided.
    type: str
    choices:
      - active
      - disabled
requirements:
  - python >= 3.9
  - cloudflare >= 5.5.0, < 6

"""

EXAMPLES = r"""
- name: Enable DNSSEC
  linuxhq.cloudflare.dnssec:
    api_token: "{{ dnssec_api_token }}"
    zone_id: "{{ _zones_info_dict['example.com'].id }}"
    status: active

- name: Disable DNSSEC
  linuxhq.cloudflare.dnssec:
    api_token: "{{ dnssec_api_token }}"
    zone_id: "{{ _zones_info_dict['example.com'].id }}"
    status: disabled
"""

RETURN = r"""
---
dnssec:
  description: Cloudflare DNSSEC settings after the requested operation.
  returned: always
  type: dict
message:
  description: Summary of the action taken.
  returned: always
  type: str

"""

from ansible.module_utils.basic import AnsibleModule

from ansible_collections.linuxhq.cloudflare.plugins.module_utils.cloudflare_utils import (
    cloudflare_client,
    serialize_resource,
)


def main():
    module = AnsibleModule(
        argument_spec={
            "api_token": {"required": True, "type": "str", "no_log": True},
            "zone_id": {"required": True, "type": "str"},
            "dnssec_multi_signer": {"type": "bool"},
            "dnssec_presigned": {"type": "bool"},
            "dnssec_use_nsec3": {"type": "bool"},
            "status": {
                "type": "str",
                "choices": ["active", "disabled"],
            },
        },
        supports_check_mode=True,
    )

    with cloudflare_client(module) as client:
        current = client.dns.dnssec.get(zone_id=module.params["zone_id"])

        current_dict = serialize_resource(current)

        current_status = getattr(current, "status", None)
        if current_status == "pending":
            current_status = "active"
        elif current_status == "pending-disabled":
            current_status = "disabled"

        needs_update = False
        comparisons = (
            ("status", current_status, module.params["status"]),
            (
                "dnssec_multi_signer",
                getattr(current, "dnssec_multi_signer", None),
                module.params.get("dnssec_multi_signer"),
            ),
            (
                "dnssec_presigned",
                getattr(current, "dnssec_presigned", None),
                module.params.get("dnssec_presigned"),
            ),
            (
                "dnssec_use_nsec3",
                getattr(current, "dnssec_use_nsec3", None),
                module.params.get("dnssec_use_nsec3"),
            ),
        )

        for field, current_value, desired in comparisons:
            if desired is None:
                continue

            if current_value != desired:
                needs_update = True
                break

        if not needs_update:
            module.exit_json(
                changed=False,
                message="DNSSEC settings already present",
                dnssec=current_dict,
            )

        if module.check_mode:
            module.exit_json(
                changed=True,
                message="DNSSEC settings would be updated",
                dnssec=current_dict,
            )

        payload = {"zone_id": module.params["zone_id"]}
        for field in (
            "dnssec_multi_signer",
            "dnssec_presigned",
            "dnssec_use_nsec3",
            "status",
        ):
            if module.params.get(field) is not None:
                payload[field] = module.params[field]

        dnssec = client.dns.dnssec.edit(**payload)

    module.exit_json(
        changed=True,
        message="DNSSEC settings updated",
        dnssec=serialize_resource(dnssec),
    )


if __name__ == "__main__":
    main()
