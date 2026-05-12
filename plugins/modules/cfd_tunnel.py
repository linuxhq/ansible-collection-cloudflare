#!/usr/bin/python

# Copyright: (c) 2026, Taylor Kimball
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import absolute_import, division, print_function

__metaclass__ = type

DOCUMENTATION = r"""
---
module: cfd_tunnel
short_description: Manage cloudflare cfd tunnels
description:
- Create and delete Cloudflare cloudflared tunnels by name.
- Tunnel secrets are only sent when creating a tunnel because Cloudflare does not return the current secret for idempotent comparison.
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
  config_src:
    type: str
    choices:
    - local
    - cloudflare
    description:
    - Config src.
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
- name: Ensure cloudflared tunnel exists
  linuxhq.cloudflare.cfd_tunnel:
    account_id: "{{ account_id }}"
    api_token: "{{ cloudflare_api_token }}"
    name: example
    config_src: cloudflare
"""

RETURN = r"""
---
cfd_tunnel:
  description: Cloudflare tunnel.
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

FIELDS = ("config_src", "name", "tunnel_secret")


def endpoint(account_id):
    return "/accounts/%s/cfd_tunnel" % account_id


def list_endpoint(account_id):
    return "%s?is_deleted=false" % endpoint(account_id)


def main():
    module = AnsibleModule(
        argument_spec={
            "account_id": {"required": True, "type": "str"},
            "api_token": {"required": True, "type": "str", "no_log": True},
            "name": {"required": True, "type": "str"},
            "config_src": {"type": "str", "choices": ["local", "cloudflare"]},
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
                module.exit_json(
                    changed=False, message="Cloudflared tunnel already absent"
                )
            if module.check_mode:
                module.exit_json(
                    changed=True,
                    message="Cloudflared tunnel would be deleted",
                    cfd_tunnel=current,
                )
            delete_result(
                client, "%s/%s" % (endpoint(params["account_id"]), current["id"])
            )
            module.exit_json(
                changed=True,
                message="Cloudflared tunnel deleted",
                cfd_tunnel=current,
            )

        if current is not None:
            module.exit_json(
                changed=False,
                message="Cloudflared tunnel already present",
                cfd_tunnel=current,
            )

        if not params.get("config_src"):
            module.fail_json(
                msg="config_src is required when creating a cloudflared tunnel"
            )

        if module.check_mode:
            module.exit_json(
                changed=True, message="Cloudflared tunnel would be created"
            )

        cfd_tunnel = post_result(
            client,
            endpoint(params["account_id"]),
            payload_from_params(params, FIELDS),
        )
        module.exit_json(
            changed=True,
            message="Cloudflared tunnel created",
            cfd_tunnel=cfd_tunnel,
        )


if __name__ == "__main__":
    main()
