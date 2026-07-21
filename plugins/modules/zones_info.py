#!/usr/bin/python
# -*- coding: utf-8 -*-
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import absolute_import, division, print_function

__metaclass__ = type

DOCUMENTATION = r"""
---
module: zones_info
short_description: Gather information about cloudflare zones
description:
  - Gather Cloudflare zones visible to the supplied API token.
author:
  - Taylor Kimball (@tkimball83)
options:
  api_token:
    required: true
    type: str
    description:
      - Cloudflare API token.
  match:
    type: str
    choices:
      - any
      - all
    default: all
    description:
      - Match.
requirements:
  - python >= 3.9
  - cloudflare >= 5.5.0, < 6

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

"""

from ansible.module_utils.basic import AnsibleModule

from ansible_collections.linuxhq.cloudflare.plugins.module_utils.cloudflare_utils import (
    cloudflare_client,
    list_all,
)


def list(module, client):
    zones = list_all(client, "/zones?match=%s" % module.params["match"])

    module.exit_json(changed=False, zones=zones)


def main():
    module = AnsibleModule(
        argument_spec={
            "api_token": {"required": True, "type": "str", "no_log": True},
            "match": {"type": "str", "choices": ["any", "all"], "default": "all"},
        },
        supports_check_mode=True,
    )

    with cloudflare_client(module) as client:
        list(module, client)


if __name__ == "__main__":
    main()
