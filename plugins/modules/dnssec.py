#!/usr/bin/python

# Copyright: (c) 2026, Taylor Kimball
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import absolute_import, division, print_function

__metaclass__ = type


DOCUMENTATION = r"""
---
module: dnssec
short_description: Manage Cloudflare DNSSEC settings
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
    no_log: true
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
    type: str
    choices:
      - active
      - disabled
    default: active
requirements:
  - python >= 3.9
  - cloudflare >= 4.3.1, < 5
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

try:
    import cloudflare
    from cloudflare import Cloudflare
except ImportError:
    cloudflare = None
    Cloudflare = None


def serialize_resource(resource):
    if resource is None:
        return None

    if hasattr(resource, "to_dict"):
        return resource.to_dict()

    return resource


def fail_from_cloudflare_error(module, message, exc):
    response = getattr(exc, "response", None)
    status_code = getattr(exc, "status_code", None)
    response_body = None

    if response is not None:
        if hasattr(response, "json"):
            try:
                response_body = response.json()
            except Exception:
                response_body = None
        if response_body is None and hasattr(response, "text"):
            response_body = response.text

    module.fail_json(
        msg=message,
        error=str(exc),
        status_code=status_code,
        response=response_body,
    )


def get_dnssec(client, zone_id):
    return client.dns.dnssec.get(zone_id=zone_id)


def normalize_status(status):
    if status == "pending":
        return "active"

    if status == "pending-disabled":
        return "disabled"

    return status


def needs_update(current, params):
    comparisons = (
        (
            "status",
            normalize_status(getattr(current, "status", None)),
            params["status"],
        ),
        (
            "dnssec_multi_signer",
            getattr(current, "dnssec_multi_signer", None),
            params.get("dnssec_multi_signer"),
        ),
        (
            "dnssec_presigned",
            getattr(current, "dnssec_presigned", None),
            params.get("dnssec_presigned"),
        ),
        (
            "dnssec_use_nsec3",
            getattr(current, "dnssec_use_nsec3", None),
            params.get("dnssec_use_nsec3"),
        ),
    )

    for field, current_value, desired in comparisons:
        if desired is None:
            continue
        if current_value != desired:
            return True

    return False


def edit_dnssec(client, params):
    payload = {
        "zone_id": params["zone_id"],
        "status": params["status"],
    }

    for field in ("dnssec_multi_signer", "dnssec_presigned", "dnssec_use_nsec3"):
        if params.get(field) is not None:
            payload[field] = params[field]

    return client.dns.dnssec.edit(**payload)


def run_module():
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
                "default": "active",
            },
        },
        supports_check_mode=True,
    )

    if Cloudflare is None:
        module.fail_json(
            msg="The official Cloudflare Python SDK is required for this module",
            missing_python_package="cloudflare",
        )

    try:
        with Cloudflare(api_token=module.params["api_token"]) as client:
            current = get_dnssec(client, module.params["zone_id"])
            current_dict = serialize_resource(current)

            if not needs_update(current, module.params):
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

            dnssec = edit_dnssec(client, module.params)
    except cloudflare.APIConnectionError as exc:
        fail_from_cloudflare_error(module, "Cloudflare API connection failed", exc)
    except cloudflare.APIStatusError as exc:
        fail_from_cloudflare_error(module, "Cloudflare API request failed", exc)

    module.exit_json(
        changed=True,
        message="DNSSEC settings updated",
        dnssec=serialize_resource(dnssec),
    )


def main():
    run_module()


if __name__ == "__main__":
    main()
