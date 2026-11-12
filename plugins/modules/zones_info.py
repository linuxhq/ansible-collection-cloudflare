#!/usr/bin/python
# Copyright: Ansible Project
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)


DOCUMENTATION = r"""
---
module: zones_info
short_description: Gather information about Cloudflare zones
description:
  - Gather Cloudflare zones visible to the supplied API token, including internal
    zones.
version_added: '2.0.0'
author:
  - Taylor Kimball (@tkimball83)
extends_documentation_fragment:
  - linuxhq.cloudflare.cloudflare
options:
  match:
    type: str
    choices:
      - any
      - all
    default: all
    description:
      - Whether all or any supplied filters must match.
      - This module exposes no zone filters, so this option currently has no
        effect on the returned zones.
"""

EXAMPLES = r"""
- name: Gather zones
  linuxhq.cloudflare.zones_info:
    api_token: "{{ cloudflare_api_token }}"
"""

RETURN = r"""
---
zones:
  description: Cloudflare zones.
  returned: always
  type: list
  elements: dict
  contains:
    id:
      description: Cloudflare zone identifier.
      returned: always
      type: str
    name:
      description: Fully qualified domain name of the zone.
      returned: always
      type: str
    status:
      description: Current zone activation status.
      returned: when available
      type: str

"""

from ansible.module_utils.basic import AnsibleModule

from ansible_collections.linuxhq.cloudflare.plugins.module_utils.cloudflare_utils import (
    cloudflare_client,
    cloudflare_error_context,
    exit_resource_list,
)

# Cloudflare omits internal zones unless a type filter names them. The API reads
# a comma-separated value; the SDK's list encoding repeats the parameter instead,
# which Cloudflare treats as matching no zones.
ZONE_TYPES = "full,partial,secondary,internal"


def run(module, client):
    with cloudflare_error_context("Cloudflare API request failed while gathering zones"):
        exit_resource_list(
            module,
            "zones",
            client.zones.list(match=module.params["match"], type=ZONE_TYPES),
            "zone",
        )


def main():
    module = AnsibleModule(
        argument_spec={
            "api_token": {"required": True, "type": "str", "no_log": True},
            "match": {"type": "str", "choices": ["any", "all"], "default": "all"},
        },
        supports_check_mode=True,
    )

    with cloudflare_client(module) as client:
        run(module, client)


if __name__ == "__main__":
    main()
