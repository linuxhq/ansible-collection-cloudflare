#!/usr/bin/python

# Copyright: (c) 2026, Taylor Kimball
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import absolute_import, division, print_function

__metaclass__ = type


DOCUMENTATION = r"""
---
module: dnssec_info
short_description: Gather Cloudflare DNSSEC information
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
    no_log: true
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


def fail_from_cloudflare_error(module, message, exc, **context):
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
        **context,
    )


def build_error_details(exc):
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

    details = {
        "status_code": status_code,
    }

    if isinstance(response_body, dict):
        details["errors"] = response_body.get("errors", [])
        details["messages"] = response_body.get("messages", [])
    else:
        details["error"] = str(exc)

    return details


def iter_zones(page):
    if page is None:
        return []

    result = getattr(page, "result", None)
    if result is not None:
        return result or []

    return page or []


def list_zones(client):
    page = client.zones.list(per_page=1000)
    zones = []

    for zone in iter_zones(page):
        zone_dict = serialize_resource(zone)
        if zone_dict.get("id") is not None and zone_dict.get("name") is not None:
            zones.append({"id": zone_dict["id"], "name": zone_dict["name"]})

    return zones


def list_dnssec(client):
    dnssec = []
    skipped_zones = []

    for zone in list_zones(client):
        try:
            dnssec_settings = client.dns.dnssec.get(zone_id=zone["id"])
        except cloudflare.APIStatusError as exc:
            skipped_zone = {
                "zone_id": zone["id"],
                "zone_name": zone["name"],
            }
            skipped_zone.update(build_error_details(exc))
            skipped_zones.append(skipped_zone)
            continue
        except cloudflare.APIConnectionError as exc:
            raise_zone_error(
                exc,
                zone,
                "Cloudflare API connection failed while gathering DNSSEC information",
            )
        dnssec.append(
            {
                "name": zone["name"],
                "id": zone["id"],
                "dnssec": serialize_resource(dnssec_settings),
            }
        )

    return dnssec, skipped_zones


def raise_zone_error(exc, zone, message):
    setattr(exc, "_dnssec_info_message", message)
    setattr(exc, "_dnssec_info_context", {"zone": zone})
    raise exc


def run_module():
    module = AnsibleModule(
        argument_spec={
            "api_token": {"required": True, "type": "str", "no_log": True},
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
            dnssec, skipped_zones = list_dnssec(client)
    except cloudflare.APIConnectionError as exc:
        fail_from_cloudflare_error(
            module,
            getattr(exc, "_dnssec_info_message", "Cloudflare API connection failed"),
            exc,
            **getattr(exc, "_dnssec_info_context", {}),
        )
    except cloudflare.APIStatusError as exc:
        fail_from_cloudflare_error(
            module,
            getattr(exc, "_dnssec_info_message", "Cloudflare API request failed"),
            exc,
            **getattr(exc, "_dnssec_info_context", {}),
        )

    module.exit_json(
        changed=False,
        dnssec=dnssec,
        skipped_zones=skipped_zones,
    )


def main():
    run_module()


if __name__ == "__main__":
    main()
