#!/usr/bin/python
# Copyright: Ansible Project
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)


DOCUMENTATION = r"""
---
module: warp_connector
short_description: Manage Cloudflare WARP Connectors
description:
  - Create and delete Cloudflare WARP Connector tunnels by name.
  - Results include sensitive values returned by Cloudflare, such as connector tokens and tunnel credentials; protect registered
    results and task output, for example with C(no_log).
  - Tunnel secrets are sent when creating a connector, or when O(rotate_secrets) is
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
      - WARP Connector name.
  tunnel_secret:
    type: str
    description:
      - Secret used to authenticate the WARP Connector tunnel.
      - When creating a connector, it must be non-empty and base64-encoded, with
        or without padding, because Cloudflare rejects other values only after the
        connector is created. It is not checked when O(rotate_secrets) applies it
        to an existing connector.
      - Applied when creating a connector. Cloudflare does not return the current
        secret, so changes are not detected; use O(rotate_secrets) to apply the
        secret to an existing connector.
      - When applying the secret to a newly created connector fails, the module
        fails and names the connector ID. The connector remains without the
        requested secret, and later runs report it present, so rerun with
        O(rotate_secrets=true) to apply the secret.
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

from base64 import b64decode

from ansible.module_utils.basic import AnsibleModule

from ansible_collections.linuxhq.cloudflare.plugins.module_utils.cloudflare_utils import (
    cloudflare,
    cloudflare_client,
    cloudflare_error_context,
    cloudflare_error_details,
    create_once,
    ensure_resource_absent,
    find_resource,
    matching_resources,
    resource_field,
    resource_id,
    serialize_resource,
    without_retries,
)


def validate_created_secret(module):
    """Fail when tunnel_secret is empty or not base64, which Cloudflare rejects only after the connector is created.

    Cloudflare accepts standard base64 of any length, with or without padding.
    """
    secret = module.params.get("tunnel_secret")
    if secret is None:
        return

    try:
        b64decode(secret + "=" * (-len(secret) % 4), validate=True)
    except ValueError:
        secret = ""

    if not secret:
        module.fail_json(msg="tunnel_secret must be non-empty and base64-encoded")


def list_connectors(module, connectors):
    """Return the WARP Connectors that are not deleted and whose name matches the requested one."""
    params = module.params
    return connectors.list(account_id=params["account_id"], name=params["name"], is_deleted=False)


def checked_connector(module, connector, expected_id=None):
    """Serialize and validate the WARP Connector a create or update returned.

    A failure reports changed=True, the connector, and its identifiers.
    """
    connector = serialize_resource(connector)
    failure = {"changed": True, "account_id": module.params["account_id"], "warp_connector": connector}
    if expected_id is not None:
        failure["resource_id"] = expected_id

    failure = {
        "resource_id": resource_id(module, connector, "WARP Connector", expected=expected_id, context=failure),
        **failure,
    }
    resource_field(module, connector, "name", "WARP Connector", expected=module.params["name"], context=failure)
    return connector


def apply_created_secret(module, connectors, created):
    """Apply tunnel_secret to the created connector.

    A failure reports changed=True and the connector: the created one when the
    edit failed, or the edit response when it names another connector.
    """
    params = module.params
    account_id = params["account_id"]
    connector_id = created["id"]
    failure = {
        "changed": True,
        "account_id": account_id,
        "resource_id": connector_id,
        "warp_connector_id": connector_id,
    }
    try:
        connector = serialize_resource(
            connectors.edit(connector_id, account_id=account_id, tunnel_secret=params["tunnel_secret"])
        )
    except cloudflare.APIError as exc:
        module.fail_json(
            msg=(
                f"Failed to apply tunnel_secret to the created WARP Connector {connector_id}; it was created "
                "without the requested secret. Later runs report it present and cannot detect the secret, "
                "so rerun with rotate_secrets: true to apply it"
            ),
            warp_connector=created,
            **failure,
            **cloudflare_error_details(exc),
        )

    if (
        not isinstance(connector, dict)
        or connector.get("id") != connector_id
        or connector.get("name") != params["name"]
    ):
        module.fail_json(
            msg=(
                f"Cloudflare API returned the wrong WARP Connector after applying tunnel_secret to the created "
                f"WARP Connector {connector_id}"
            ),
            error="Cloudflare API returned the wrong WARP Connector",
            warp_connector=connector,
            **failure,
        )

    return connector


def ensure_present(module, client, current):
    params = module.params
    account_id = params["account_id"]
    connectors = client.zero_trust.tunnels.warp_connector

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

    validate_created_secret(module)
    if module.check_mode:
        module.exit_json(changed=True, message="WARP Connector would be created")

    with cloudflare_error_context(
        "Cloudflare API request failed while creating the WARP Connector",
        account_id=account_id,
        name=params["name"],
    ):
        warp_connector = create_once(
            lambda: without_retries(client).zero_trust.tunnels.warp_connector.create(
                account_id=account_id, name=params["name"]
            ),
            lambda: matching_resources(list_connectors(module, connectors), "name", params["name"]),
        )

    warp_connector = checked_connector(module, warp_connector)
    if params.get("tunnel_secret") is not None:
        warp_connector = apply_created_secret(module, connectors, warp_connector)

    module.exit_json(changed=True, message="WARP Connector created", warp_connector=warp_connector)


def run(module, client):
    params = module.params
    account_id = params["account_id"]
    connectors = client.zero_trust.tunnels.warp_connector
    with cloudflare_error_context(
        "Cloudflare API request failed while finding the WARP Connector",
        account_id=account_id,
        name=params["name"],
    ):
        current = find_resource(module, list_connectors(module, connectors), "WARP Connector", "name", params["name"])

    if params["state"] == "absent":
        ensure_resource_absent(
            module,
            "warp_connector",
            "WARP Connector",
            current,
            delete=lambda connector_id: connectors.delete(connector_id, account_id=account_id),
            context={"account_id": account_id},
        )

    ensure_present(module, client, current)


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
