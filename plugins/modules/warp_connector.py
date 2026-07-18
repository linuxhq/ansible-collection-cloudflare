#!/usr/bin/python
# -*- coding: utf-8 -*-
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import absolute_import, division, print_function

__metaclass__ = type

DOCUMENTATION = r"""
---
module: warp_connector
short_description: Manage cloudflare warp connectors
description:
  - Create and delete Cloudflare WARP Connector tunnels by name.
  - Tunnel secrets are sent when creating a connector, or when C(rotate_secrets) is
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
  tunnel_secret:
    type: str
    description:
      - Tunnel secret.
      - Applied when creating a connector. Cloudflare does not return the current
        secret, so changes are not detected; use C(rotate_secrets) to apply the
        secret to an existing connector.
  rotate_secrets:
    type: bool
    default: false
    description:
      - Apply C(tunnel_secret) to an existing connector, rotating its secret.
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
    cloudflare,
    cloudflare_client,
    delete_result,
    find_by_name,
    patch_result,
    post_result,
)


def endpoint(account_id):
    return "/accounts/%s/warp_connector" % account_id


def main():
    module = AnsibleModule(
        argument_spec={
            "account_id": {"required": True, "type": "str"},
            "api_token": {"required": True, "type": "str", "no_log": True},
            "name": {"required": True, "type": "str"},
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

        if state == "present":
            if current is not None:
                if params["rotate_secrets"] and params.get("tunnel_secret") is not None:
                    if module.check_mode:
                        module.exit_json(
                            changed=True,
                            message="WARP Connector would be updated",
                            warp_connector=current,
                        )

                    warp_connector = patch_result(
                        client,
                        "%s/%s" % (endpoint(params["account_id"]), current["id"]),
                        {"tunnel_secret": params["tunnel_secret"]},
                    )
                    module.exit_json(
                        changed=True,
                        message="WARP Connector updated",
                        warp_connector=warp_connector,
                    )

                module.exit_json(
                    changed=False,
                    message="WARP Connector already present",
                    warp_connector=current,
                )

            if module.check_mode:
                module.exit_json(
                    changed=True, message="WARP Connector would be created"
                )

            warp_connector = post_result(
                client,
                endpoint(params["account_id"]),
                {"name": params["name"]},
            )

            if params.get("tunnel_secret") is not None:
                connector_path = "%s/%s" % (
                    endpoint(params["account_id"]),
                    warp_connector["id"],
                )
                try:
                    warp_connector = patch_result(
                        client,
                        connector_path,
                        {"tunnel_secret": params["tunnel_secret"]},
                    )
                except (cloudflare.APIConnectionError, cloudflare.APIStatusError):
                    try:
                        delete_result(client, connector_path)
                    except (cloudflare.APIConnectionError, cloudflare.APIStatusError):
                        module.fail_json(
                            msg=(
                                "Failed to apply tunnel_secret and to roll back "
                                "the created WARP Connector; delete it manually "
                                "and retry"
                            ),
                            warp_connector_id=warp_connector["id"],
                        )
                    raise

            module.exit_json(
                changed=True,
                message="WARP Connector created",
                warp_connector=warp_connector,
            )


if __name__ == "__main__":
    main()
