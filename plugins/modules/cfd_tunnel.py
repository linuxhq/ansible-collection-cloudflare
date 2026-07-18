#!/usr/bin/python
# -*- coding: utf-8 -*-
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import absolute_import, division, print_function

__metaclass__ = type

DOCUMENTATION = r"""
---
module: cfd_tunnel
short_description: Manage cloudflare cfd tunnels
description:
  - Create and delete Cloudflare cloudflared tunnels by name.
  - Tunnel secrets are sent when creating a tunnel, or when C(rotate_secrets) is
    enabled, because Cloudflare does not return the current secret for idempotent
    comparison.
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
      - Required when creating a cloudflared tunnel.
  tunnel_secret:
    type: str
    description:
      - Tunnel secret for locally-managed tunnels.
      - Applied when creating a tunnel. Cloudflare does not return the current
        secret, so changes are not detected; use C(rotate_secrets) to apply the
        secret to an existing tunnel.
  rotate_secrets:
    type: bool
    default: false
    description:
      - Apply C(tunnel_secret) to an existing tunnel, rotating its secret.
      - The module always reports C(changed) when enabled and a secret is given.
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
  - cloudflare >= 5.5.0, < 6

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
    find_by_name,
    patch_result,
    payload_from_params,
    post_result,
)

FIELDS = ("config_src", "name", "tunnel_secret")


def endpoint(account_id):
    return "/accounts/%s/cfd_tunnel" % account_id


def main():
    module = AnsibleModule(
        argument_spec={
            "account_id": {"required": True, "type": "str"},
            "api_token": {"required": True, "type": "str", "no_log": True},
            "name": {"required": True, "type": "str"},
            "config_src": {"type": "str", "choices": ["local", "cloudflare"]},
            "tunnel_secret": {"type": "str", "no_log": True},
            "rotate_secrets": {"type": "bool", "default": False},
            "state": {
                "type": "str",
                "choices": ["present", "absent"],
                "default": "present",
            },
        },
        supports_check_mode=True,
    )

    params = module.params
    state = params["state"]

    with cloudflare_client(module) as client:
        current = find_by_name(
            client,
            endpoint(params["account_id"]),
            params["name"],
            extra_query={"is_deleted": "false"},
        )

        if state == "absent":
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

        if state == "present":
            if current is not None:
                if params["rotate_secrets"] and params.get("tunnel_secret") is not None:
                    if module.check_mode:
                        module.exit_json(
                            changed=True,
                            message="Cloudflared tunnel would be updated",
                            cfd_tunnel=current,
                        )

                    cfd_tunnel = patch_result(
                        client,
                        "%s/%s" % (endpoint(params["account_id"]), current["id"]),
                        {"tunnel_secret": params["tunnel_secret"]},
                    )
                    module.exit_json(
                        changed=True,
                        message="Cloudflared tunnel updated",
                        cfd_tunnel=cfd_tunnel,
                    )

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
