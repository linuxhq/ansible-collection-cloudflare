#!/usr/bin/python
# Copyright: Ansible Project
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)


DOCUMENTATION = r"""
---
module: pagerules_info
short_description: Gather information about Cloudflare Page Rules
description:
  - Gather page rules for all accessible zones.
  - Zones deleted while the module runs are skipped.
version_added: '2.0.0'
author:
  - Taylor Kimball (@tkimball83)
extends_documentation_fragment:
  - linuxhq.cloudflare.cloudflare
options: {}
"""

EXAMPLES = r"""
- name: Gather page rules
  linuxhq.cloudflare.pagerules_info:
    api_token: "{{ cloudflare_api_token }}"
"""

RETURN = r"""
---
pagerules:
  description: Page rules grouped by zone.
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
    pagerules:
      description: Page rules configured for the zone.
      returned: always
      type: list
      elements: dict
      contains:
        id:
          description: Page rule identifier.
          returned: always
          type: str
        actions:
          description: Actions applied by the page rule.
          returned: always
          type: list
          elements: dict
        targets:
          description: Target constraints identifying the page rule.
          returned: always
          type: list
          elements: dict

"""

from ansible.module_utils.basic import AnsibleModule

from ansible_collections.linuxhq.cloudflare.plugins.module_utils.cloudflare_utils import (
    cloudflare,
    cloudflare_client,
    cloudflare_error_context,
    error_response_body,
    require_mapping,
    resource_list,
)

# Cloudflare answers a request for a deleted zone with this error code.
INVALID_ZONE_CODE = 1001


def zone_missing(exc):
    """Return whether an API error means the zone no longer exists."""
    if exc.status_code == 404:
        return True

    body = error_response_body(exc)
    errors = body.get("errors") if isinstance(body, dict) else None
    return exc.status_code == 400 and any(
        isinstance(error, dict) and error.get("code") == INVALID_ZONE_CODE for error in errors or ()
    )


def run(module, client):
    pagerules = []
    with cloudflare_error_context("Cloudflare API request failed while gathering zones"):
        zones = resource_list(module, client.zones.list(), "zone", ("id", "name"))

    for zone in zones:
        try:
            with cloudflare_error_context(
                "Cloudflare API request failed while gathering page rules",
                zone_id=zone["id"],
            ):
                rules = resource_list(module, client.page_rules.list(zone_id=zone["id"]) or [], "page rule")
        except cloudflare.APIStatusError as exc:
            # Skip a zone deleted after it was listed.
            if not zone_missing(exc):
                raise

            continue

        for rule in rules:
            for field in ("actions", "targets"):
                values = rule.get(field)
                if not isinstance(values, list):
                    module.fail_json(msg="Cloudflare API returned malformed page rule data")

                for value in values:
                    require_mapping(module, value, f"page rule {field[:-1]}")

        pagerules.append({"id": zone["id"], "name": zone["name"], "pagerules": rules})

    module.exit_json(changed=False, pagerules=pagerules)


def main():
    module = AnsibleModule(
        argument_spec={
            "api_token": {"required": True, "type": "str", "no_log": True},
        },
        supports_check_mode=True,
    )

    with cloudflare_client(module) as client:
        run(module, client)


if __name__ == "__main__":
    main()
