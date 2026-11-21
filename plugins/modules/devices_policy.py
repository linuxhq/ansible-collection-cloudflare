#!/usr/bin/python
# Copyright: Ansible Project
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)


DOCUMENTATION = r"""
---
module: devices_policy
short_description: Manage the Cloudflare device policy
description:
  - Patch the Cloudflare Zero Trust default device policy for an account.
version_added: '2.0.0'
author:
  - Taylor Kimball (@tkimball83)
notes:
  - Cloudflare may store a requested value in a canonical form that differs from the request. The module then
    fails after the write, naming the requested and stored value of each differing field in the message and in
    C(differences), so the stored form can be requested instead.
extends_documentation_fragment:
  - linuxhq.cloudflare.cloudflare
  - linuxhq.cloudflare.cloudflare.account
options:
  allow_mode_switch:
    type: bool
    description:
      - Whether to allow the user to switch WARP between modes.
      - When omitted, the current value is left unchanged.
  allow_updates:
    type: bool
    description:
      - Whether to receive WARP client update notifications.
      - When omitted, the current value is left unchanged.
  allowed_to_leave:
    type: bool
    description:
      - Whether to allow devices to leave the organization.
      - When omitted, the current value is left unchanged.
  auto_connect:
    type: float
    description:
      - Seconds before reconnecting after WARP has been disabled.
      - When omitted, the current value is left unchanged.
  captive_portal:
    type: float
    description:
      - Seconds before turning on captive portal handling.
      - When omitted, the current value is left unchanged.
  disable_auto_fallback:
    type: bool
    description:
      - Whether to disable automatic fallback DNS resolver selection.
      - When omitted, the current value is left unchanged.
  exclude:
    type: list
    elements: dict
    description:
      - Split tunnel routes excluded from the WARP tunnel.
      - Replaces the current routes; each route is compared on all of its fields.
      - Each route accepts only C(address), C(host), and C(description).
        Cloudflare accepts any other field but does not store it, so the
        module fails before making changes.
      - A route field set to null is not sent and counts as omitted.
      - A route C(description) of V("") matches a route without a description,
        since Cloudflare drops an empty description.
      - A bare IP address in a route's C(address) is compared and sent as a
        single-host CIDR, such as C(192.0.2.1/32), as Cloudflare stores it.
      - When omitted, the current value is left unchanged.
      - Mutually exclusive with O(include).
  exclude_office_ips:
    type: bool
    description:
      - Whether to add Microsoft IPs to split tunnel exclusions.
      - When omitted, the current value is left unchanged.
  include:
    type: list
    elements: dict
    description:
      - Split tunnel routes included in the WARP tunnel.
      - Replaces the current routes; each route is compared on all of its fields.
      - Each route accepts only C(address), C(host), and C(description).
        Cloudflare accepts any other field but does not store it, so the
        module fails before making changes.
      - A route field set to null is not sent and counts as omitted.
      - A route C(description) of V("") matches a route without a description,
        since Cloudflare drops an empty description.
      - A bare IP address in a route's C(address) is compared and sent as a
        single-host CIDR, such as C(192.0.2.1/32), as Cloudflare stores it.
      - Must not be empty; Cloudflare stores an empty include list as exclude
        mode with no routes, so use O(exclude=[]) instead.
      - When omitted, the current value is left unchanged.
      - Mutually exclusive with O(exclude).
  lan_allow_minutes:
    type: float
    description:
      - Minutes a user is allowed access to their LAN.
      - When omitted, the current value is left unchanged.
  lan_allow_subnet_size:
    type: float
    description:
      - Subnet size for local access.
      - When omitted, the current value is left unchanged.
  register_interface_ip_with_dns:
    type: bool
    description:
      - Whether the operating system registers WARP's local interface IP with DNS.
      - When omitted, the current value is left unchanged.
  sccm_vpn_boundary_support:
    type: bool
    description:
      - Whether the WARP client indicates to SCCM that it is inside a VPN boundary.
      - When omitted, the current value is left unchanged.
  service_mode_v2:
    type: dict
    description:
      - WARP client service mode configuration.
      - Accepts only C(mode) and C(port); a null key is ignored. Cloudflare accepts any other key but
        does not store it, so the module fails before making changes.
      - C(port) with a C(mode) other than C(proxy) fails before making
        changes, because Cloudflare does not store a port for another mode.
      - Cloudflare replaces the whole configuration on every write. When
        C(mode) equals the current mode, keys omitted here, such as C(port),
        keep their current values.
      - When omitted, the current value is left unchanged.
  support_url:
    type: str
    description:
      - URL launched by the WARP client Send Feedback button.
      - When omitted, the current value is left unchanged.
  switch_locked:
    type: bool
    description:
      - Whether to prevent users from turning off WARP and disconnecting the client.
      - When omitted, the current value is left unchanged.
  tunnel_protocol:
    type: str
    description:
      - Tunnel protocol to use.
      - When omitted, the current value is left unchanged.
"""

EXAMPLES = r"""
- name: Manage device policy
  linuxhq.cloudflare.devices_policy:
    account_id: "{{ account_id }}"
    api_token: "{{ cloudflare_api_token }}"
    allow_updates: true
    auto_connect: 60
    include:
      - address: 100.64.0.0/10
    service_mode_v2:
      mode: warp_tunnel_only
"""

RETURN = r"""
---
devices_policy:
  description: Cloudflare device policy.
  returned: always
  type: dict
  contains:
    allow_updates:
      description: Whether the WARP client receives update notifications.
      returned: when available
      type: bool
    service_mode_v2:
      description: WARP client service mode configuration.
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
    cidr_from_address,
    cloudflare_client,
    cloudflare_error_context,
    ensure_settings,
    payload_from_params,
    serialize_resource,
    unsupported_fields,
)

FIELDS = (
    "allow_mode_switch",
    "allow_updates",
    "allowed_to_leave",
    "auto_connect",
    "captive_portal",
    "disable_auto_fallback",
    "exclude",
    "exclude_office_ips",
    "include",
    "lan_allow_minutes",
    "lan_allow_subnet_size",
    "register_interface_ip_with_dns",
    "sccm_vpn_boundary_support",
    "service_mode_v2",
    "support_url",
    "switch_locked",
    "tunnel_protocol",
)
# Fields Cloudflare stores, from the cloudflare SDK split tunnel route and
# service mode types; it accepts any other field but drops it.
ROUTE_FIELDS = ("address", "description", "host")
SERVICE_MODE_FIELDS = ("mode", "port")


def validate_field_names(module):
    """Fail when a route or service mode field Cloudflare accepts but never stores is requested."""
    params = module.params
    unknown = []
    for option in ("exclude", "include"):
        for index, route in enumerate(params.get(option) or ()):
            unknown.extend(unsupported_fields(route, ROUTE_FIELDS, f"{option}[{index}]"))

    unknown.extend(unsupported_fields(params.get("service_mode_v2"), SERVICE_MODE_FIELDS, "service_mode_v2"))
    if unknown:
        module.fail_json(
            msg=f"Cloudflare does not store these device policy fields: {', '.join(unknown)}",
            unsupported_fields=unknown,
        )

    # Cloudflare does not store a port for a mode other than proxy.
    service_mode_v2 = params.get("service_mode_v2") or {}
    if service_mode_v2.get("port") is not None and service_mode_v2.get("mode") not in (None, "proxy"):
        module.fail_json(
            msg="service_mode_v2.port requires mode proxy; Cloudflare does not store a port for another mode"
        )


def split_tunnel_route(route):
    """Return route without null fields, which count as omitted, and with a bare IP address as Cloudflare stores it."""
    route = {key: value for key, value in route.items() if value is not None}
    if "address" in route:
        route["address"] = cidr_from_address(route["address"])

    return route


def comparable_policy(policy, payload):
    """Return policy with each route stored without a description matching a requested empty description.

    Cloudflare drops a split tunnel route description set to "" and returns
    the route without it.
    """
    policy = dict(policy)
    for field in ("exclude", "include"):
        requested, routes = payload.get(field), policy.get(field)
        if requested is not None and routes:
            policy[field] = [
                (
                    {**route, "description": ""}
                    if route.get("description") is None and {**route, "description": ""} in requested
                    else route
                )
                for route in routes
            ]

    return policy


def service_mode(requested, current):
    """Return requested with the keys it omits carried over from current.

    Cloudflare replaces service_mode_v2 as a whole, so a write that omits the
    port of an unchanged mode would reset it. Keys are carried over only when
    the mode is unchanged, since another mode stores different keys, and the
    port only for mode proxy, the only mode that stores one. Null keys count
    as omitted, as Cloudflare rejects a null port.
    """
    requested = {key: value for key, value in requested.items() if value is not None}
    if not isinstance(current, dict) or current.get("mode") != requested.get("mode"):
        return requested

    if requested.get("mode") != "proxy":
        current = {key: value for key, value in current.items() if key != "port"}

    return {**current, **requested}


def run(module, client):
    account_id = module.params["account_id"]
    if module.params.get("include") == []:
        module.fail_json(msg="include must not be empty; Cloudflare stores it as exclude mode, use exclude: [] instead")

    validate_field_names(module)

    payload = payload_from_params(module.params, FIELDS)
    for field in ("exclude", "include"):
        if field in payload:
            payload[field] = [split_tunnel_route(route) for route in payload[field]]

    policy = client.zero_trust.devices.policies.default
    with cloudflare_error_context(
        "Cloudflare API request failed while gathering the device policy",
        account_id=account_id,
    ):
        current = serialize_resource(policy.get(account_id=account_id)) or {}

    if "service_mode_v2" in payload:
        payload["service_mode_v2"] = service_mode(payload["service_mode_v2"], current.get("service_mode_v2"))

    ensure_settings(
        module,
        "devices_policy",
        "device policy",
        current,
        payload,
        edit=lambda payload: policy.edit(account_id=account_id, **payload),
        comparable=lambda settings, failure: comparable_policy(settings, payload),
        context={"account_id": account_id},
        exact_values=("exclude", "include"),
    )


def main():
    module = AnsibleModule(
        argument_spec={
            "account_id": {"required": True, "type": "str"},
            "allow_mode_switch": {"type": "bool"},
            "allow_updates": {"type": "bool"},
            "allowed_to_leave": {"type": "bool"},
            "api_token": {"required": True, "type": "str", "no_log": True},
            "auto_connect": {"type": "float"},
            "captive_portal": {"type": "float"},
            "disable_auto_fallback": {"type": "bool"},
            "exclude": {"type": "list", "elements": "dict"},
            "exclude_office_ips": {"type": "bool"},
            "include": {"type": "list", "elements": "dict"},
            "lan_allow_minutes": {"type": "float"},
            "lan_allow_subnet_size": {"type": "float"},
            "register_interface_ip_with_dns": {"type": "bool"},
            "sccm_vpn_boundary_support": {"type": "bool"},
            "service_mode_v2": {"type": "dict"},
            "support_url": {"type": "str"},
            "switch_locked": {"type": "bool"},
            "tunnel_protocol": {"type": "str"},
        },
        mutually_exclusive=[("exclude", "include")],
        supports_check_mode=True,
    )

    with cloudflare_client(module) as client:
        run(module, client)


if __name__ == "__main__":
    main()
