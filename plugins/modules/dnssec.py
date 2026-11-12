#!/usr/bin/python
# Copyright: Ansible Project
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)


DOCUMENTATION = r"""
---
module: dnssec
short_description: Manage Cloudflare DNSSEC settings
description:
  - Manage Cloudflare DNSSEC settings for a zone.
version_added: '2.0.0'
author:
  - Taylor Kimball (@tkimball83)
extends_documentation_fragment:
  - linuxhq.cloudflare.cloudflare
options:
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
message:
  description: Summary of the action taken.
  returned: always
  type: str

"""

from ansible.module_utils.basic import AnsibleModule

from ansible_collections.linuxhq.cloudflare.plugins.module_utils.cloudflare_utils import (
    cloudflare_client,
    cloudflare_error_context,
    ensure_settings,
    payload_from_params,
    resource_field,
)

FIELDS = ("dnssec_multi_signer", "dnssec_presigned", "dnssec_use_nsec3", "status")
PENDING_STATUSES = {"pending": "active", "pending-disabled": "disabled"}


def comparable_settings(module, settings):
    status = resource_field(module, settings, "status", "DNSSEC settings")
    return {**settings, "status": PENDING_STATUSES.get(status, status)}


def run(module, client):
    zone_id = module.params["zone_id"]
    with cloudflare_error_context(
        "Cloudflare API request failed while gathering DNSSEC settings",
        zone_id=zone_id,
    ):
        current = client.dns.dnssec.get(zone_id=zone_id)

    ensure_settings(
        module,
        "dnssec",
        "DNSSEC settings",
        current,
        payload_from_params(module.params, FIELDS),
        edit=lambda payload: client.dns.dnssec.edit(zone_id=zone_id, **payload),
        comparable=lambda settings: comparable_settings(module, settings),
        context={"zone_id": zone_id},
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
        run(module, client)


if __name__ == "__main__":
    main()
