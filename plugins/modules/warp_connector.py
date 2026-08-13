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
    cloudflare_path,
    delete_result,
    find_by_name,
    patch_result,
    post_result,
    resource_field,
    resource_id,
    validate_tunnel_secret,
)


def endpoint(account_id):
    return cloudflare_path("accounts", account_id, "warp_connector")


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
        current_id = resource_id(module, current, "WARP Connector")
        if params["rotate_secrets"] and params.get("tunnel_secret") is not None:
            if module.check_mode:
                module.exit_json(
                    changed=True,
                    message="WARP Connector would be updated",
                    warp_connector=current,
                )

            warp_connector = patch_result(
                client,
                cloudflare_path("accounts", params["account_id"], "warp_connector", current_id),
                {"tunnel_secret": params["tunnel_secret"]},
            )
            resource_id(module, warp_connector, "WARP Connector", expected=current_id)
            resource_field(
                module,
                warp_connector,
                "name",
                "WARP Connector",
                expected=params["name"],
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
        module.exit_json(changed=True, message="WARP Connector would be created")

    warp_connector = post_result(
        client,
        endpoint(params["account_id"]),
        {"name": params["name"]},
    )
    connector_id = resource_id(module, warp_connector, "WARP Connector")
    resource_field(module, warp_connector, "name", "WARP Connector", expected=params["name"])

    if params.get("tunnel_secret") is not None:
        connector_path = cloudflare_path(
            "accounts",
            params["account_id"],
            "warp_connector",
            connector_id,
        )
        try:
            warp_connector = patch_result(
                client,
                connector_path,
                {"tunnel_secret": params["tunnel_secret"]},
            )
            if (
                not isinstance(warp_connector, dict)
                or warp_connector.get("id") != connector_id
                or warp_connector.get("name") != params["name"]
            ):
                raise CloudflareResponseError("Cloudflare API returned the wrong WARP Connector")
        except (cloudflare.APIError, CloudflareResponseError):
            try:
                delete_result(client, connector_path, expected_id=connector_id)
            except (cloudflare.APIError, CloudflareResponseError):
                module.fail_json(
                    msg=(
                        "Failed to apply tunnel_secret and to roll back "
                        "the created WARP Connector; delete it manually "
                        "and retry"
                    ),
                    warp_connector_id=connector_id,
                )
            raise

    module.exit_json(
        changed=True,
        message="WARP Connector created",
        warp_connector=warp_connector,
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
        module.exit_json(changed=False, message="WARP Connector already absent")

    current_id = resource_id(module, current, "WARP Connector")

    if module.check_mode:
        module.exit_json(
            changed=True,
            message="WARP Connector would be deleted",
            warp_connector=current,
        )

    delete_result(
        client,
        cloudflare_path("accounts", params["account_id"], "warp_connector", current_id),
        expected_id=current_id,
    )
    module.exit_json(
        changed=True,
        message="WARP Connector deleted",
        warp_connector=current,
    )


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
        if module.params["state"] == "present":
            ensure_present(module, client)
        else:
            ensure_absent(module, client)


if __name__ == "__main__":
    main()
