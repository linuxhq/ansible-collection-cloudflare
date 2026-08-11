#!/usr/bin/python
# Copyright: Contributors to the Ansible project
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
    require_mapping,
    resource_field,
    serialize_resource,
)


def normalized_status(status):
    return {"pending": "active", "pending-disabled": "disabled"}.get(status, status)


def ensure_present(module, client):
    with cloudflare_error_context(
        "Cloudflare API request failed while gathering DNSSEC settings",
        zone_id=module.params["zone_id"],
    ):
        current = serialize_resource(
            client.dns.dnssec.get(zone_id=module.params["zone_id"])
        )
    require_mapping(module, current, "DNSSEC settings")
    current_status = normalized_status(
        resource_field(module, current, "status", "DNSSEC settings")
    )

    comparisons = (
        (current_status, module.params["status"]),
        (
            current.get("dnssec_multi_signer"),
            module.params.get("dnssec_multi_signer"),
        ),
        (
            current.get("dnssec_presigned"),
            module.params.get("dnssec_presigned"),
        ),
        (
            current.get("dnssec_use_nsec3"),
            module.params.get("dnssec_use_nsec3"),
        ),
    )

    needs_update = any(
        desired is not None and current_value != desired
        for current_value, desired in comparisons
    )

    if not needs_update:
        module.exit_json(
            changed=False,
            message="DNSSEC settings already present",
            dnssec=current,
        )

    if module.check_mode:
        module.exit_json(
            changed=True,
            message="DNSSEC settings would be updated",
            dnssec=current,
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

    with cloudflare_error_context(
        "Cloudflare API request failed while updating DNSSEC settings",
        zone_id=module.params["zone_id"],
    ):
        dnssec = serialize_resource(client.dns.dnssec.edit(**payload))
    require_mapping(module, dnssec, "DNSSEC settings")
    response_status = normalized_status(
        resource_field(module, dnssec, "status", "DNSSEC settings")
    )
    if any(
        desired is not None and actual != desired
        for actual, desired in (
            (response_status, module.params["status"]),
            (dnssec.get("dnssec_multi_signer"), module.params["dnssec_multi_signer"]),
            (dnssec.get("dnssec_presigned"), module.params["dnssec_presigned"]),
            (dnssec.get("dnssec_use_nsec3"), module.params["dnssec_use_nsec3"]),
        )
    ):
        module.fail_json(msg="Cloudflare did not apply the requested DNSSEC settings")
    module.exit_json(
        changed=True,
        message="DNSSEC settings updated",
        dnssec=dnssec,
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
        ensure_present(module, client)


if __name__ == "__main__":
    main()
