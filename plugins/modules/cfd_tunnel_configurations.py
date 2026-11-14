#!/usr/bin/python
# Copyright: Ansible Project
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)


DOCUMENTATION = r"""
---
module: cfd_tunnel_configurations
short_description: Manage Cloudflare cloudflared tunnel configurations
description:
  - Update the remotely managed configuration for a cloudflared tunnel.
version_added: '2.0.0'
author:
  - Taylor Kimball (@tkimball83)
extends_documentation_fragment:
  - linuxhq.cloudflare.cloudflare
  - linuxhq.cloudflare.cloudflare.account
options:
  tunnel_id:
    required: true
    type: str
    description:
      - Cloudflared tunnel identifier.
      - The module fails before any change when the tunnel was deleted.
  config:
    required: true
    type: dict
    description:
      - Complete remotely managed tunnel configuration.
      - Omitted optional settings are reset to their defaults.
      - Use the Cloudflare API field names, such as C(originRequest) and C(noTLSVerify).
        The module fails before any change when the configuration or an ingress
        rule uses C(origin_request).
      - C(warp-routing) is not compared. Cloudflare manages WARP routing at the
        account level and ignores it in tunnel configurations.
"""

EXAMPLES = r"""
- name: Configure a cloudflared tunnel
  linuxhq.cloudflare.cfd_tunnel_configurations:
    account_id: "{{ account_id }}"
    api_token: "{{ cloudflare_api_token }}"
    tunnel_id: "{{ tunnel_id }}"
    config:
      ingress:
        - service: http_status:404
"""

RETURN = r"""
---
configuration:
  description: Cloudflare tunnel configuration.
  returned: always
  type: dict
  contains:
    config:
      description: Remotely managed tunnel configuration.
      returned: when the tunnel has a configuration
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
    cloudflare_error_context,
    normalize_current_by_desired_fields,
    require_mapping,
    resource_id,
    serialize_resource,
    values_differ,
)

# https://developers.cloudflare.com/tunnel/reference/origin-parameters/
ORIGIN_DEFAULTS = {
    "access": {"audTag": [], "teamName": "", "required": False},
    "bastionMode": False,
    "caPool": "",
    "connectTimeout": 30,
    "disableChunkedEncoding": False,
    "http2Origin": False,
    "httpHostHeader": "",
    "keepAliveConnections": 100,
    "keepAliveTimeout": 90,
    "matchSNItoHost": False,
    "noHappyEyeballs": False,
    "noTLSVerify": False,
    "originServerName": "",
    "proxyAddress": "127.0.0.1",
    "proxyPort": 0,
    "proxyType": "",
    "tcpKeepAlive": 30,
    "tlsTimeout": 10,
}

ORIGIN_FIELDS = {
    **dict.fromkeys(ORIGIN_DEFAULTS),
    "access": {"audTag": None, "teamName": None, "required": None},
}
CONFIG_FIELDS = {
    "ingress": [{"hostname": None, "service": None, "path": None, "originRequest": ORIGIN_FIELDS}],
    "originRequest": ORIGIN_FIELDS,
}


def managed_config_fields(current, desired, fields):
    # Compare known configurable fields even when omitted, but tolerate extra
    # response metadata. Explicit user fields are always compared, including
    # fields added by newer API versions.
    if isinstance(current, dict) and isinstance(fields, dict):
        desired = desired if isinstance(desired, dict) else {}
        return {
            key: managed_config_fields(value, desired.get(key), fields.get(key))
            for key, value in current.items()
            if key in fields or key in desired
        }

    if isinstance(current, list) and isinstance(fields, list):
        desired = desired if isinstance(desired, list) else []
        return [
            managed_config_fields(value, desired[index] if index < len(desired) else None, fields[0])
            for index, value in enumerate(current)
        ]

    return normalize_current_by_desired_fields(current, desired)


def normalize_origin(origin, defaults):
    if not isinstance(origin, dict):
        return origin

    normalized = {}
    for key, value in origin.items():
        if isinstance(value, dict) and isinstance(defaults.get(key), dict):
            value = normalize_origin(value, defaults[key])
            if not value:
                continue

        elif key in defaults and value == defaults[key]:
            continue

        normalized[key] = value

    return normalized


def comparable_config(config, desired=None):
    config = managed_config_fields(
        serialize_resource(config), desired if desired is not None else config, CONFIG_FIELDS
    )
    origin = config.get("originRequest", {})
    inherited = {**ORIGIN_DEFAULTS, **origin} if isinstance(origin, dict) else ORIGIN_DEFAULTS
    # cloudflared builds the JWT validator from the ingress Access object,
    # not the global one. Its omitted fields use Access defaults.
    inherited = {**inherited, "access": ORIGIN_DEFAULTS["access"]}
    normalized_origin = normalize_origin(origin, ORIGIN_DEFAULTS)
    if normalized_origin != {}:
        config["originRequest"] = normalized_origin
    else:
        config.pop("originRequest", None)

    ingress_rules = config.get("ingress", [])
    if not isinstance(ingress_rules, list):
        return config

    for ingress in ingress_rules:
        if not isinstance(ingress, dict):
            continue

        for field in ("hostname", "path"):
            if ingress.get(field) == "":
                ingress.pop(field)

        normalized_origin = normalize_origin(ingress.get("originRequest", {}), inherited)
        if normalized_origin != {}:
            ingress["originRequest"] = normalized_origin
        else:
            ingress.pop("originRequest", None)

    # Cloudflare ignores warp-routing here and returns its own value.
    config.pop("warp-routing", None)

    return config


def validate_config(module, config):
    """Fail when the configuration uses the SDK spelling of originRequest."""
    ingress_rules = config.get("ingress")
    rules = ingress_rules if isinstance(ingress_rules, list) else []
    for item in [config, *rules]:
        if isinstance(item, dict) and "origin_request" in item:
            module.fail_json(msg="config key 'origin_request' must use the Cloudflare API key 'originRequest'")


def run(module, client):
    params = module.params
    validate_config(module, params["config"])
    tunnels = client.zero_trust.tunnels.cloudflared
    configurations = tunnels.configurations
    identifiers = {"account_id": params["account_id"], "tunnel_id": params["tunnel_id"]}

    with cloudflare_error_context(
        "Cloudflare API request failed while gathering the cloudflared tunnel",
        **identifiers,
    ):
        tunnel = serialize_resource(tunnels.get(params["tunnel_id"], account_id=params["account_id"]))

    resource_id(module, tunnel, "cloudflared tunnel", expected=params["tunnel_id"])
    # Cloudflare still returns a deleted tunnel, with deleted_at set.
    if tunnel.get("deleted_at") is not None:
        module.fail_json(msg=f"Cloudflared tunnel {params['tunnel_id']} was deleted", **identifiers)

    # Cloudflare accepts a configuration for a locally managed tunnel and
    # silently converts the tunnel to remote management, which is irreversible.
    if tunnel.get("config_src") == "local" or tunnel.get("remote_config") is False:
        module.fail_json(
            msg=f"Cloudflared tunnel {params['tunnel_id']} is locally managed and cannot use a remote configuration",
            **identifiers,
        )

    with cloudflare_error_context(
        "Cloudflare API request failed while gathering the tunnel configuration",
        **identifiers,
    ):
        current = serialize_resource(configurations.get(params["tunnel_id"], account_id=params["account_id"])) or {}

    require_mapping(module, current, "tunnel configuration")
    current_config = current.get("config")
    if current_config is None:
        current_config = {}
    else:
        require_mapping(module, current_config, "tunnel configuration")

    if not values_differ(
        comparable_config(current_config, params["config"]),
        comparable_config(params["config"]),
    ):
        module.exit_json(
            changed=False,
            message="Tunnel configuration already present",
            configuration=current,
        )

    if module.check_mode:
        module.exit_json(
            changed=True,
            message="Tunnel configuration would be updated",
            configuration=current,
        )

    with cloudflare_error_context(
        "Cloudflare API request failed while updating the tunnel configuration",
        **identifiers,
    ):
        configuration = serialize_resource(
            configurations.update(params["tunnel_id"], account_id=params["account_id"], config=params["config"])
        )

    require_mapping(module, configuration, "tunnel configuration")
    returned_config = configuration.get("config")
    require_mapping(module, returned_config, "tunnel configuration")
    if values_differ(
        comparable_config(returned_config, params["config"]),
        comparable_config(params["config"]),
    ):
        module.fail_json(msg="Cloudflare did not apply the tunnel configuration")

    module.exit_json(
        changed=True,
        message="Tunnel configuration updated",
        configuration=configuration,
    )


def main():
    module = AnsibleModule(
        argument_spec={
            "account_id": {"required": True, "type": "str"},
            "api_token": {"required": True, "type": "str", "no_log": True},
            "tunnel_id": {"required": True, "type": "str"},
            "config": {"required": True, "type": "dict"},
        },
        supports_check_mode=True,
    )

    with cloudflare_client(module) as client:
        run(module, client)


if __name__ == "__main__":
    main()
