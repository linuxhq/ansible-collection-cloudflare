#!/usr/bin/python

# Copyright: (c) 2026, Taylor Kimball
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import absolute_import, division, print_function

__metaclass__ = type

DOCUMENTATION = r"""
---
module: warp_connector
short_description: Manage Cloudflare WARP Connector tunnels
description:
- Create and delete Cloudflare WARP Connector tunnels by name.
- Tunnel secrets are only sent when creating a connector because Cloudflare does not return the current secret for idempotent comparison.
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
  name:
    required: true
    type: str
    description:
    - Resource name.
  tunnel_secret:
    type: str
    description:
    - Tunnel secret.
  state:
    type: str
    choices:
    - present
    - absent
    default: present
    description:
    - Desired state of the resource.
requirements:
- python >= 3.9
- cloudflare >= 4.3.1, < 5

"""

EXAMPLES = r"""
- name: Ensure WARP Connector exists
  linuxhq.cloudflare.warp_connector:
    account_id: "{{ account_id }}"
    api_token: "{{ cloudflare_api_token }}"
    name: example
"""

RETURN = r"""
---
warp_connector:
  description: Cloudflare WARP Connector tunnel.
  returned: when available
  type: dict
message:
  returned: always
  type: str
  description:
  - Operation summary.

"""

from ansible.module_utils.basic import AnsibleModule

from ansible_collections.linuxhq.cloudflare.plugins.module_utils.cloudflare_utils import (
    cloudflare_client,
    delete_result,
    find_by_field,
    payload_from_params,
    post_result,
)

FIELDS = ("name", "tunnel_secret")


def endpoint(account_id):
    return "/accounts/%s/warp_connector" % account_id


def list_endpoint(account_id):
    return "%s?is_deleted=false" % endpoint(account_id)


def main():
    module = AnsibleModule(
        argument_spec={
            "account_id": {"required": True, "type": "str"},
            "api_token": {"required": True, "type": "str", "no_log": True},
            "name": {"required": True, "type": "str"},
            "tunnel_secret": {"type": "str", "no_log": True},
            "state": {
                "type": "str",
                "choices": ["present", "absent"],
                "default": "present",
            },
        },
        supports_check_mode=True,
    )

    params = module.params
    with cloudflare_client(module) as client:
        current = find_by_field(
            client, list_endpoint(params["account_id"]), "name", params["name"]
        )

        if params["state"] == "absent":
            if current is None:
                module.exit_json(changed=False, message="WARP Connector already absent")
            if module.check_mode:
                module.exit_json(
                    changed=True,
                    message="WARP Connector would be deleted",
                    warp_connector=current,
                )
            delete_result(
                client, "%s/%s" % (endpoint(params["account_id"]), current["id"])
            )
            module.exit_json(
                changed=True,
                message="WARP Connector deleted",
                warp_connector=current,
            )

        if current is not None:
            module.exit_json(
                changed=False,
                message="WARP Connector already present",
                warp_connector=current,
            )

        if module.check_mode:
            module.exit_json(changed=True, message="WARP Connector would be created")

        warp_connector = post_result(
            client,
            endpoint(params["account_id"]),
            payload_from_params(params, FIELDS),
        )
        module.exit_json(
            changed=True,
            message="WARP Connector created",
            warp_connector=warp_connector,
        )


if __name__ == "__main__":
    main()
