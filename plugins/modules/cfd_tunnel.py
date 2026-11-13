#!/usr/bin/python
# Copyright: Ansible Project
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)


DOCUMENTATION = r"""
---
module: cfd_tunnel
short_description: Manage Cloudflare cloudflared tunnels
description:
  - Create and delete Cloudflare cloudflared tunnels by name.
  - Results include sensitive values returned by Cloudflare, such as connector tokens and tunnel credentials; protect registered
    results and task output, for example with C(no_log).
  - Tunnel secrets are sent when creating a tunnel, or when O(rotate_secrets) is
    enabled, because Cloudflare does not return the current secret for idempotent
    comparison.
version_added: '2.0.0'
author:
  - Taylor Kimball (@tkimball83)
extends_documentation_fragment:
  - linuxhq.cloudflare.cloudflare
  - linuxhq.cloudflare.cloudflare.account
options:
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
      - An existing tunnel's configuration source is not changed; the module
        fails before making changes when it differs from the requested value.
  tunnel_secret:
    type: str
    description:
      - Tunnel secret, which locally-managed tunnels need to run.
      - Must be base64-encoded and decode to at least 32 bytes.
      - Applied when creating a tunnel. Cloudflare does not return the current
        secret, so changes are not detected; use O(rotate_secrets) to apply the
        secret to an existing tunnel.
  rotate_secrets:
    type: bool
    default: false
    description:
      - Apply O(tunnel_secret) to an existing tunnel, rotating its secret and
        connector token. Applies to locally and remotely managed tunnels.
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
    cloudflare_error_context,
    ensure_resource_absent,
    find_resource,
    payload_from_params,
    resource_field,
    resource_id,
    serialize_resource,
    validate_tunnel_secret,
)

FIELDS = ("config_src", "name", "tunnel_secret")


def checked_tunnel(module, tunnel, expected_id=None):
    tunnel = serialize_resource(tunnel)
    resource_id(module, tunnel, "cloudflared tunnel", expected=expected_id)
    resource_field(module, tunnel, "name", "cloudflared tunnel", expected=module.params["name"])
    return tunnel


def ensure_present(module, tunnels, current):
    params = module.params
    account_id = params["account_id"]

    if current is not None:
        current_id = resource_id(module, current, "cloudflared tunnel")
        current_config_src = current.get("config_src")
        if params.get("config_src") is not None and current_config_src not in (None, params["config_src"]):
            module.fail_json(
                msg=f"Cannot change config_src of the existing cloudflared tunnel from "
                f"{current_config_src} to {params['config_src']}",
                cfd_tunnel_id=current_id,
                current_config_src=current_config_src,
                requested_config_src=params["config_src"],
            )

        if not params["rotate_secrets"]:
            module.exit_json(changed=False, message="Cloudflared tunnel already present", cfd_tunnel=current)

        if module.check_mode:
            module.exit_json(changed=True, message="Cloudflared tunnel would be updated", cfd_tunnel=current)

        with cloudflare_error_context(
            "Cloudflare API request failed while updating the cloudflared tunnel",
            account_id=account_id,
            resource_id=current_id,
        ):
            cfd_tunnel = tunnels.edit(current_id, account_id=account_id, tunnel_secret=params["tunnel_secret"])

        cfd_tunnel = checked_tunnel(module, cfd_tunnel, expected_id=current_id)
        module.exit_json(changed=True, message="Cloudflared tunnel updated", cfd_tunnel=cfd_tunnel)

    if not params.get("config_src"):
        module.fail_json(msg="config_src is required when creating a cloudflared tunnel")

    if module.check_mode:
        module.exit_json(changed=True, message="Cloudflared tunnel would be created")

    with cloudflare_error_context(
        "Cloudflare API request failed while creating the cloudflared tunnel",
        account_id=account_id,
        name=params["name"],
    ):
        cfd_tunnel = tunnels.create(account_id=account_id, **payload_from_params(params, FIELDS))

    cfd_tunnel = checked_tunnel(module, cfd_tunnel)
    resource_field(module, cfd_tunnel, "config_src", "cloudflared tunnel", expected=params["config_src"])
    module.exit_json(changed=True, message="Cloudflared tunnel created", cfd_tunnel=cfd_tunnel)


def run(module, client):
    params = module.params
    account_id = params["account_id"]
    tunnels = client.zero_trust.tunnels.cloudflared
    if params["state"] == "present":
        validate_tunnel_secret(module, params.get("tunnel_secret"))

    with cloudflare_error_context(
        "Cloudflare API request failed while finding the cloudflared tunnel",
        account_id=account_id,
        name=params["name"],
    ):
        current = find_resource(
            module,
            tunnels.list(account_id=account_id, name=params["name"], is_deleted=False),
            "cloudflared tunnel",
            "name",
            params["name"],
        )

    if params["state"] == "absent":
        ensure_resource_absent(
            module,
            "cfd_tunnel",
            "cloudflared tunnel",
            current,
            delete=lambda tunnel_id: tunnels.delete(tunnel_id, account_id=account_id),
            context={"account_id": account_id},
        )

    ensure_present(module, tunnels, current)


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
        run(module, client)


if __name__ == "__main__":
    main()
