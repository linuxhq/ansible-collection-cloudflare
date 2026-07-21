#!/usr/bin/python
# -*- coding: utf-8 -*-
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import absolute_import, division, print_function

__metaclass__ = type

DOCUMENTATION = r"""
---
module: warp_connector_info
short_description: Gather information about cloudflare warp connectors
description:
  - Gather active Cloudflare WARP Connectors and optionally their connector tokens.
author:
  - Taylor Kimball (@tkimball83)
options:
  account_id:
    required: true
    type: str
    description:
      - Cloudflare account identifier.
  api_token:
    required: true
    type: str
    description:
      - Cloudflare API token.
  include_token:
    type: bool
    default: true
    description:
      - Include token.
requirements:
  - python >= 3.9
  - cloudflare >= 5.5.0, < 6

"""

EXAMPLES = r"""
- name: Gather WARP Connectors
  linuxhq.cloudflare.warp_connector_info:
    account_id: "{{ account_id }}"
    api_token: "{{ cloudflare_api_token }}"
"""

RETURN = r"""
---
warp_connectors:
  description: Cloudflare WARP Connectors.
  returned: always
  type: list
  elements: dict

"""

from ansible.module_utils.basic import AnsibleModule

from ansible_collections.linuxhq.cloudflare.plugins.module_utils.cloudflare_utils import (
    cloudflare_client,
    get_result,
    list_all,
)


def list(module, client):
    account_id = module.params["account_id"]
    warp_connectors = list_all(
        client,
        "/accounts/%s/warp_connector?is_deleted=false" % account_id,
        per_page=1000,
    )

    if module.params["include_token"]:
        for connector in warp_connectors:
            if connector.get("id") is not None:
                connector["token"] = get_result(
                    client,
                    "/accounts/%s/warp_connector/%s/token"
                    % (account_id, connector["id"]),
                )

    module.exit_json(changed=False, warp_connectors=warp_connectors)


def main():
    module = AnsibleModule(
        argument_spec={
            "account_id": {"required": True, "type": "str"},
            "api_token": {"required": True, "type": "str", "no_log": True},
            "include_token": {"type": "bool", "default": True},
        },
        supports_check_mode=True,
    )

    with cloudflare_client(module) as client:
        list(module, client)


if __name__ == "__main__":
    main()
