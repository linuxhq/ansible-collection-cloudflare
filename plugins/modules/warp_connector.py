#!/usr/bin/python
# Copyright: Ansible Project
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)


DOCUMENTATION = r"""
---
module: warp_connector
short_description: Manage Cloudflare WARP Connectors
description:
  - Create and delete Cloudflare WARP Connector tunnels by name.
  - Tunnel secrets are sent when creating a connector, or when O(rotate_secrets) is
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
      - WARP Connector name.
  tunnel_secret:
    type: str
    description:
      - Secret used to authenticate the WARP Connector tunnel.
      - Must be base64-encoded and decode to at least 32 bytes.
      - Applied when creating a connector. Cloudflare does not return the current
        secret, so changes are not detected; use O(rotate_secrets) to apply the
        secret to an existing connector.
  rotate_secrets:
    type: bool
    default: false
    description:
      - Apply O(tunnel_secret) to an existing connector, rotating its secret.
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
  contains:
    id:
      description: WARP Connector identifier.
      returned: always
      type: str
    name:
      description: WARP Connector name.
      returned: always
      type: str
message:
  returned: always
  type: str
  description:
  - Operation summary.

"""

from ansible.module_utils.basic import AnsibleModule

from ansible_collections.linuxhq.cloudflare.plugins.module_utils.cloudflare_utils import (
    CloudflareResponseError,
    cloudflare,
    cloudflare_client,
    cloudflare_error_context,
    ensure_resource_absent,
    find_resource,
    resource_field,
    resource_id,
    serialize_resource,
    validate_tunnel_secret,
)


def checked_connector(module, connector, expected_id=None):
    connector = serialize_resource(connector)
    resource_id(module, connector, "WARP Connector", expected=expected_id)
    resource_field(module, connector, "name", "WARP Connector", expected=module.params["name"])
    return connector


def apply_secret_or_roll_back(module, connectors, connector_id):
    params = module.params
    account_id = params["account_id"]
    try:
        with cloudflare_error_context(
            "Cloudflare API request failed while applying the WARP Connector tunnel_secret",
            account_id=account_id,
            resource_id=connector_id,
        ):
            connector = serialize_resource(
                connectors.edit(connector_id, account_id=account_id, tunnel_secret=params["tunnel_secret"])
            )

        if (
            not isinstance(connector, dict)
            or connector.get("id") != connector_id
            or connector.get("name") != params["name"]
        ):
            raise CloudflareResponseError("Cloudflare API returned the wrong WARP Connector")
    except (cloudflare.APIError, CloudflareResponseError):
        try:
            deleted = serialize_resource(connectors.delete(connector_id, account_id=account_id))
            if isinstance(deleted, dict) and "id" in deleted and deleted["id"] != connector_id:
                raise CloudflareResponseError("Cloudflare API returned the wrong WARP Connector")
        except (cloudflare.APIError, CloudflareResponseError):
            module.fail_json(
                msg="Failed to apply tunnel_secret and to roll back the created WARP Connector; "
                "delete it manually and retry",
                warp_connector_id=connector_id,
            )

        raise

    return connector


def ensure_present(module, connectors, current):
    params = module.params
    account_id = params["account_id"]

    if current is not None:
        current_id = resource_id(module, current, "WARP Connector")
        if not params["rotate_secrets"]:
            module.exit_json(changed=False, message="WARP Connector already present", warp_connector=current)

        if module.check_mode:
            module.exit_json(changed=True, message="WARP Connector would be updated", warp_connector=current)

        with cloudflare_error_context(
            "Cloudflare API request failed while updating the WARP Connector",
            account_id=account_id,
            resource_id=current_id,
        ):
            warp_connector = connectors.edit(current_id, account_id=account_id, tunnel_secret=params["tunnel_secret"])

        warp_connector = checked_connector(module, warp_connector, expected_id=current_id)
        module.exit_json(changed=True, message="WARP Connector updated", warp_connector=warp_connector)

    if module.check_mode:
        module.exit_json(changed=True, message="WARP Connector would be created")

    with cloudflare_error_context(
        "Cloudflare API request failed while creating the WARP Connector",
        account_id=account_id,
        name=params["name"],
    ):
        warp_connector = connectors.create(account_id=account_id, name=params["name"])

    warp_connector = checked_connector(module, warp_connector)
    if params.get("tunnel_secret") is not None:
        warp_connector = apply_secret_or_roll_back(module, connectors, warp_connector["id"])

    module.exit_json(changed=True, message="WARP Connector created", warp_connector=warp_connector)


def run(module, client):
    params = module.params
    account_id = params["account_id"]
    connectors = client.zero_trust.tunnels.warp_connector
    if params["state"] == "present":
        validate_tunnel_secret(module, params.get("tunnel_secret"))

    with cloudflare_error_context(
        "Cloudflare API request failed while finding the WARP Connector",
        account_id=account_id,
        name=params["name"],
    ):
        current = find_resource(
            module,
            connectors.list(account_id=account_id, name=params["name"], is_deleted=False),
            "WARP Connector",
            "name",
            params["name"],
        )

    if params["state"] == "absent":
        ensure_resource_absent(
            module,
            "warp_connector",
            "WARP Connector",
            current,
            delete=lambda connector_id: connectors.delete(connector_id, account_id=account_id),
            context={"account_id": account_id},
        )

    ensure_present(module, connectors, current)


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
        required_if=[("rotate_secrets", True, ["tunnel_secret"])],
        supports_check_mode=True,
    )

    with cloudflare_client(module) as client:
        run(module, client)


if __name__ == "__main__":
    main()
