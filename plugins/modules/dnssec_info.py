#!/usr/bin/python
# Copyright: Ansible Project
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)


DOCUMENTATION = r"""
---
module: dnssec_info
short_description: Gather information about Cloudflare DNSSEC settings
description:
  - Gather Cloudflare DNSSEC information for all accessible zones.
version_added: '2.0.0'
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
  contains:
    id:
      description: Cloudflare zone identifier.
      returned: always
      type: str
    name:
      description: Cloudflare zone name.
      returned: always
      type: str
    dnssec:
      description: DNSSEC settings for the zone.
      returned: always
      type: dict
      contains:
        status:
          description: Current DNSSEC activation status.
          returned: always
          type: str
        algorithm:
          description: DNSSEC signing algorithm identifier.
          returned: when provided by Cloudflare
          type: str
        digest:
          description: Delegation signer digest.
          returned: when provided by Cloudflare
          type: str
        digest_algorithm:
          description: Delegation signer digest algorithm.
          returned: when provided by Cloudflare
          type: str
        digest_type:
          description: Delegation signer digest type.
          returned: when provided by Cloudflare
          type: str
        ds:
          description: Delegation signer record content.
          returned: when provided by Cloudflare
          type: str
        dnssec_multi_signer:
          description: Whether multi-signer DNSSEC is enabled.
          returned: when provided by Cloudflare
          type: bool
        dnssec_presigned:
          description: Whether presigned DNSSEC is enabled.
          returned: when provided by Cloudflare
          type: bool
        dnssec_use_nsec3:
          description: Whether NSEC3 is enabled.
          returned: when provided by Cloudflare
          type: bool
        flags:
          description: DNSKEY flags value.
          returned: when provided by Cloudflare
          type: float
        key_tag:
          description: DNSKEY key tag.
          returned: when provided by Cloudflare
          type: float
        key_type:
          description: DNSKEY type.
          returned: when provided by Cloudflare
          type: str
        modified_on:
          description: Time the DNSSEC settings were last modified.
          returned: when provided by Cloudflare
          type: str
        public_key:
          description: Public DNSSEC key.
          returned: when provided by Cloudflare
          type: str
skipped_zones:
  description: Zones skipped because DNSSEC information could not be retrieved.
  returned: always
  type: list
  elements: dict
  contains:
    zone_id:
      description: Identifier of the skipped zone.
      returned: always
      type: str
    zone_name:
      description: Name of the skipped zone.
      returned: always
      type: str
    status_code:
      description: HTTP status returned by Cloudflare.
      returned: always
      type: int
    errors:
      description: Structured Cloudflare API errors.
      returned: when structured details are available
      type: list
      elements: dict
    messages:
      description: Structured Cloudflare API messages.
      returned: when structured details are available
      type: list
      elements: dict
    error:
      description: Fallback error when Cloudflare returns no structured details.
      returned: when structured details are unavailable
      type: str

"""

from ansible.module_utils.basic import AnsibleModule

from ansible_collections.linuxhq.cloudflare.plugins.module_utils.cloudflare_utils import (
    cloudflare,
    cloudflare_client,
    cloudflare_error_context,
    fail_from_cloudflare_error,
    redact_sensitive_values,
    require_mapping,
    resource_field,
    resource_id,
    serialize_resource,
)

SKIP_STATUSES = (400, 404)


def list_resources(module, client):
    dnssec = []
    skipped_zones = []
    zones = []

    with cloudflare_error_context("Cloudflare API request failed while gathering zones for DNSSEC information"):
        for zone in client.zones.list():
            zone_dict = serialize_resource(zone)
            zones.append(
                {
                    "id": resource_id(module, zone_dict, "zone"),
                    "name": resource_field(module, zone_dict, "name", "zone"),
                }
            )

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

            if response is not None and hasattr(response, "json"):
                try:
                    response_body = redact_sensitive_values(response.json())
                except ValueError:
                    response_body = None

            skipped_zone = {
                "zone_id": zone["id"],
                "zone_name": zone["name"],
                "status_code": status_code,
            }

            if isinstance(response_body, dict):
                for field in ("errors", "messages"):
                    value = response_body.get(field, [])
                    skipped_zone[field] = (
                        value if isinstance(value, list) and all(isinstance(item, dict) for item in value) else []
                    )
            else:
                skipped_zone["error"] = "Cloudflare API did not return structured error details"

            skipped_zones.append(skipped_zone)
            continue
        except cloudflare.APIConnectionError as exc:
            exc._cloudflare_message = "Cloudflare API connection failed while gathering DNSSEC information"
            exc._cloudflare_context = {"zone": zone}
            raise
        except cloudflare.APIError as exc:
            exc._cloudflare_message = "Cloudflare API error while gathering DNSSEC information"
            exc._cloudflare_context = {"zone": zone}
            raise

        dnssec_settings = serialize_resource(dnssec_settings)
        require_mapping(module, dnssec_settings, "DNSSEC settings")
        resource_field(module, dnssec_settings, "status", "DNSSEC settings")

        dnssec.append(
            {
                "name": zone["name"],
                "id": zone["id"],
                "dnssec": dnssec_settings,
            }
        )

    module.exit_json(
        changed=False,
        dnssec=dnssec,
        skipped_zones=skipped_zones,
    )


def main():
    module = AnsibleModule(
        argument_spec={
            "api_token": {"required": True, "type": "str", "no_log": True},
        },
        supports_check_mode=True,
    )

    with cloudflare_client(module) as client:
        list_resources(module, client)


if __name__ == "__main__":
    main()
