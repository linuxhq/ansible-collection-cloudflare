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
  - linuxhq.cloudflare.cloudflare.create
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
      - When omitted on create, Cloudflare creates a tunnel without a
        configuration source, which is treated as V(local).
      - An existing tunnel's configuration source is not changed; the module
        fails before making changes when it differs from the requested value.
  tunnel_secret:
    type: str
    description:
      - Tunnel secret, which locally-managed tunnels need to run.
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
    checked_written,
    cloudflare_client,
    cloudflare_error_context,
    create_once,
    ensure_resource_absent,
    find_resource,
    matching_resources,
    payload_from_params,
    resource_field,
    resource_id,
    without_retries,
)

FIELDS = ("config_src", "name", "tunnel_secret")


def list_tunnels(module, tunnels):
    """Return the tunnels that are not deleted and whose name matches the requested one."""
    params = module.params
    return tunnels.list(account_id=params["account_id"], name=params["name"], is_deleted=False)


def checked_tunnel(module, tunnel, expected_id=None):
    """Serialize and validate the tunnel a create or update returned.

    A failure reports changed=True, the tunnel, and its identifiers.
    """
    context = {"account_id": module.params["account_id"], "name": module.params["name"]}
    if expected_id is not None:
        context["resource_id"] = expected_id

    tunnel, failure = checked_written(
        module, tunnel, "cloudflared tunnel", "cfd_tunnel", context, module.params["name"], expected_id
    )
    if expected_id is None and module.params.get("config_src") is not None:
        resource_field(
            module, tunnel, "config_src", "cloudflared tunnel", expected=module.params["config_src"], context=failure
        )

    return tunnel


def ensure_present(module, client, current):
    params = module.params
    account_id = params["account_id"]
    tunnels = client.zero_trust.tunnels.cloudflared

    if current is not None:
        current_id = resource_id(
            module, current, "cloudflared tunnel", context={"account_id": account_id, "name": params["name"]}
        )
        current_config_src = current.get("config_src")
        if current_config_src is None and current.get("remote_config") is False:
            current_config_src = "local"

        if params.get("config_src") is not None and current_config_src not in (None, params["config_src"]):
            module.fail_json(
                msg=f"Cannot change config_src of the existing cloudflared tunnel from "
                f"{current_config_src} to {params['config_src']}",
                account_id=account_id,
                resource_id=current_id,
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

    if module.check_mode:
        module.exit_json(changed=True, message="Cloudflared tunnel would be created")

    with cloudflare_error_context(
        "Cloudflare API request failed while creating the cloudflared tunnel",
        account_id=account_id,
        name=params["name"],
    ):
        cfd_tunnel = create_once(
            lambda: without_retries(client).zero_trust.tunnels.cloudflared.create(
                account_id=account_id, **payload_from_params(params, FIELDS)
            ),
            lambda: matching_resources(list_tunnels(module, tunnels), "name", params["name"]),
        )

    cfd_tunnel = checked_tunnel(module, cfd_tunnel)
    module.exit_json(changed=True, message="Cloudflared tunnel created", cfd_tunnel=cfd_tunnel)


def run(module, client):
    params = module.params
    account_id = params["account_id"]
    tunnels = client.zero_trust.tunnels.cloudflared
    with cloudflare_error_context(
        "Cloudflare API request failed while finding the cloudflared tunnel",
        account_id=account_id,
        name=params["name"],
    ):
        current = find_resource(
            module,
            list_tunnels(module, tunnels),
            "cloudflared tunnel",
            "name",
            params["name"],
            context={"account_id": account_id},
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

    ensure_present(module, client, current)


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
