#!/usr/bin/python
# -*- coding: utf-8 -*-
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import absolute_import, division, print_function

__metaclass__ = type

DOCUMENTATION = r"""
---
module: dnssec_info
short_description: Gather information about cloudflare dnssec settings
description:
  - Gather Cloudflare DNSSEC information for all accessible zones.
author:
  - Taylor Kimball (@tkimball83)
options:
  api_token:
    description:
      - Cloudflare API token with permissions to read DNS settings.
    required: true
    type: str
requirements:
  - python >= 3.9
  - cloudflare >= 4.3.1, < 5

"""

EXAMPLES = r"""
- name: Gather DNSSEC information
  linuxhq.cloudflare.dnssec_info:
    api_token: "{{ dnssec_info_api_token }}"
"""

RETURN = r"""
---
dnssec:
  description: List of DNSSEC information by zone.
  returned: always
  type: list
  elements: dict
skipped_zones:
  description: Zones skipped because DNSSEC information could not be retrieved.
  returned: always
  type: list
  elements: dict

"""

from ansible.module_utils.basic import AnsibleModule

from ansible_collections.linuxhq.cloudflare.plugins.module_utils.cloudflare_utils import (
    cloudflare,
    cloudflare_client,
    fail_from_cloudflare_error,
    serialize_resource,
)

SKIP_STATUSES = (400, 404)


def main():
    module = AnsibleModule(
        argument_spec={
            "api_token": {"required": True, "type": "str", "no_log": True},
        },
        supports_check_mode=True,
    )

    dnssec = []
    skipped_zones = []

    with cloudflare_client(module) as client:
        zones = []

        for zone in client.zones.list():
            zone_dict = serialize_resource(zone)
            if zone_dict.get("id") is not None and zone_dict.get("name") is not None:
                zones.append({"id": zone_dict["id"], "name": zone_dict["name"]})

        for zone in zones:
            try:
                dnssec_settings = client.dns.dnssec.get(zone_id=zone["id"])
            except cloudflare.APIStatusError as exc:
                status_code = getattr(exc, "status_code", None)
                if status_code not in SKIP_STATUSES:
                    fail_from_cloudflare_error(
                        module,
                        "Cloudflare API request failed while gathering DNSSEC information",
                        exc,
                        zone=zone,
                    )

                response = getattr(exc, "response", None)
                response_body = None

                if response is not None:
                    if hasattr(response, "json"):
                        try:
                            response_body = response.json()
                        except Exception:
                            response_body = None

                    if response_body is None and hasattr(response, "text"):
                        response_body = response.text

                skipped_zone = {
                    "zone_id": zone["id"],
                    "zone_name": zone["name"],
                    "status_code": status_code,
                }

                if isinstance(response_body, dict):
                    skipped_zone["errors"] = response_body.get("errors", [])
                    skipped_zone["messages"] = response_body.get("messages", [])
                else:
                    skipped_zone["error"] = str(exc)

                skipped_zones.append(skipped_zone)
                continue
            except cloudflare.APIConnectionError as exc:
                setattr(
                    exc,
                    "_cloudflare_message",
                    "Cloudflare API connection failed while gathering DNSSEC information",
                )
                setattr(exc, "_cloudflare_context", {"zone": zone})
                raise exc

            dnssec.append(
                {
                    "name": zone["name"],
                    "id": zone["id"],
                    "dnssec": serialize_resource(dnssec_settings),
                }
            )

    module.exit_json(
        changed=False,
        dnssec=dnssec,
        skipped_zones=skipped_zones,
    )


if __name__ == "__main__":
    main()
