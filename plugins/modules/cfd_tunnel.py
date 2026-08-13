#!/usr/bin/python
# Copyright: Ansible Project
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)


DOCUMENTATION = r"""
---
module: cfd_tunnel
short_description: Manage Cloudflare cloudflared tunnels
description:
  - Create and delete Cloudflare cloudflared tunnels by name.
  - Tunnel secrets are sent when creating a tunnel, or when O(rotate_secrets) is
    enabled, because Cloudflare does not return the current secret for idempotent
    comparison.
version_added: '2.0.0'
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
      - Cloudflared tunnel name.
  config_src:
    type: str
    choices:
      - local
      - cloudflare
    description:
      - Location from which the tunnel receives its configuration.
      - Required when creating a cloudflared tunnel.
  tunnel_secret:
    type: str
    description:
      - Tunnel secret for locally-managed tunnels.
      - Must be base64-encoded and decode to at least 32 bytes.
      - Applied when creating a tunnel. Cloudflare does not return the current
        secret, so changes are not detected; use O(rotate_secrets) to apply the
        secret to an existing tunnel.
  rotate_secrets:
    type: bool
    default: false
    description:
      - Apply O(tunnel_secret) to an existing tunnel, rotating its secret.
      - The module always reports C(changed) when enabled and a secret is given.
      - Requires O(tunnel_secret).
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
  - cloudflare >= 5.6.0, < 6
attributes:
  check_mode:
    description: Supports predicting changes without applying them.
    support: full
  diff_mode:
    description: Determines whether the module returns change details in diff format.
    support: none

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
  contains:
    id:
      description: Cloudflared tunnel identifier.
      returned: always
      type: str
    name:
      description: Cloudflared tunnel name.
      returned: always
      type: str
    config_src:
      description: Tunnel configuration source.
      returned: when available
      type: str
message:
  returned: always
  type: str
  description:
  - Operation summary.

"""

from ansible.module_utils.basic import AnsibleModule

from ansible_collections.linuxhq.cloudflare.plugins.module_utils.cloudflare_utils import (
    cloudflare_client,
    cloudflare_path,
    delete_result,
    find_by_name,
    patch_result,
    payload_from_params,
    post_result,
    resource_field,
    resource_id,
    validate_tunnel_secret,
)

FIELDS = ("config_src", "name", "tunnel_secret")


def endpoint(account_id):
    return cloudflare_path("accounts", account_id, "cfd_tunnel")


def ensure_present(module, client):
    params = module.params
    validate_tunnel_secret(module, params.get("tunnel_secret"))

    current = find_by_name(
        client,
        endpoint(params["account_id"]),
        params["name"],
        extra_query={"is_deleted": "false"},
    )

    if current is not None:
        current_id = resource_id(module, current, "cloudflared tunnel")
        if params["rotate_secrets"] and params.get("tunnel_secret") is not None:
            local = current.get("config_src") == "local" or current.get("remote_config") is False
            remote = current.get("config_src") == "cloudflare" or current.get("remote_config") is True
            if not local or remote:
                module.fail_json(msg="tunnel_secret is only valid for locally-managed tunnels")
            if module.check_mode:
                module.exit_json(
                    changed=True,
                    message="Cloudflared tunnel would be updated",
                    cfd_tunnel=current,
                )

            cfd_tunnel = patch_result(
                client,
                cloudflare_path("accounts", params["account_id"], "cfd_tunnel", current_id),
                {"tunnel_secret": params["tunnel_secret"]},
            )
            resource_id(module, cfd_tunnel, "cloudflared tunnel", expected=current_id)
            resource_field(
                module,
                cfd_tunnel,
                "name",
                "cloudflared tunnel",
                expected=params["name"],
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
        module.fail_json(msg="config_src is required when creating a cloudflared tunnel")
    if params["config_src"] != "local" and params.get("tunnel_secret") is not None:
        module.fail_json(msg="tunnel_secret is only valid for locally-managed tunnels")

    if module.check_mode:
        module.exit_json(changed=True, message="Cloudflared tunnel would be created")

    cfd_tunnel = post_result(
        client,
        endpoint(params["account_id"]),
        payload_from_params(params, FIELDS),
    )
    resource_id(module, cfd_tunnel, "cloudflared tunnel")
    resource_field(module, cfd_tunnel, "name", "cloudflared tunnel", expected=params["name"])
    resource_field(
        module,
        cfd_tunnel,
        "config_src",
        "cloudflared tunnel",
        expected=params["config_src"],
    )
    module.exit_json(
        changed=True,
        message="Cloudflared tunnel created",
        cfd_tunnel=cfd_tunnel,
    )


def ensure_absent(module, client):
    params = module.params

    current = find_by_name(
        client,
        endpoint(params["account_id"]),
        params["name"],
        extra_query={"is_deleted": "false"},
    )

    if current is None:
        module.exit_json(changed=False, message="Cloudflared tunnel already absent")

    current_id = resource_id(module, current, "cloudflared tunnel")

    if module.check_mode:
        module.exit_json(
            changed=True,
            message="Cloudflared tunnel would be deleted",
            cfd_tunnel=current,
        )

    delete_result(
        client,
        cloudflare_path("accounts", params["account_id"], "cfd_tunnel", current_id),
        expected_id=current_id,
    )
    module.exit_json(
        changed=True,
        message="Cloudflared tunnel deleted",
        cfd_tunnel=current,
    )


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
        required_if=[("rotate_secrets", True, ["tunnel_secret"])],
        supports_check_mode=True,
    )

    with cloudflare_client(module) as client:
        if module.params["state"] == "present":
            ensure_present(module, client)
        else:
            ensure_absent(module, client)


if __name__ == "__main__":
    main()
