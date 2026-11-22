# devices\_policy

[![License](https://img.shields.io/badge/license-GPLv3-brightgreen.svg?style=flat)](https://www.gnu.org/licenses/gpl-3.0.txt)

Manage cloudflare devices policy

See the [Cloudflare API reference](https://developers.cloudflare.com/api/resources/zero_trust/subresources/devices/subresources/policies/subresources/default/).

## Requirements

| Type    | Permission       | Value |
| ------- | ---------------- | ----- |
| Account | Account Settings | Read  |
| Account | Zero Trust       | Write |

## Role Variables

| Variable                                        | Default | Description                                                      |
| ----------------------------------------------- | ------- | ---------------------------------------------------------------- |
| `devices_policy_account_id`                     | `null`  | Cloudflare account ID; null skips the role                       |
| `devices_policy_allow_mode_switch`              | `null`  | Allow switching WARP modes; null leaves it unchanged             |
| `devices_policy_allow_updates`                  | `null`  | Receive WARP update notifications; null leaves it unchanged      |
| `devices_policy_allowed_to_leave`               | `null`  | Allow leaving the organization; null leaves it unchanged         |
| `devices_policy_api_token`                      | `null`  | Cloudflare API token; null skips the role                        |
| `devices_policy_auto_connect`                   | `null`  | Seconds before WARP reconnects; null leaves it unchanged         |
| `devices_policy_captive_portal`                 | `null`  | Seconds before captive portal handling; null leaves it unchanged |
| `devices_policy_disable_auto_fallback`          | `null`  | Disable automatic fallback DNS; null leaves it unchanged         |
| `devices_policy_exclude`                        | `null`  | Split tunnel routes to exclude; null leaves it unchanged         |
| `devices_policy_exclude_office_ips`             | `null`  | Exclude Microsoft IPs; null leaves it unchanged                  |
| `devices_policy_include`                        | `null`  | Split tunnel routes to include; null leaves it unchanged         |
| `devices_policy_lan_allow_minutes`              | `null`  | Minutes of LAN access; null leaves it unchanged                  |
| `devices_policy_lan_allow_subnet_size`          | `null`  | Subnet size for LAN access; null leaves it unchanged             |
| `devices_policy_register_interface_ip_with_dns` | `null`  | Register WARP interface IP in DNS; null leaves it unchanged      |
| `devices_policy_sccm_vpn_boundary_support`      | `null`  | Report SCCM VPN boundary; null leaves it unchanged               |
| `devices_policy_service_mode_v2`                | `null`  | WARP service mode; null leaves it unchanged                      |
| `devices_policy_support_url`                    | `null`  | Send Feedback button URL; null leaves it unchanged               |
| `devices_policy_switch_locked`                  | `null`  | Prevent turning off WARP; null leaves it unchanged               |
| `devices_policy_tunnel_protocol`                | `null`  | Tunnel protocol; null leaves it unchanged                        |

## Dependencies

* [accounts\_info](../accounts_info)

## Example Playbook

    - hosts: cloudflare
      connection: local
      roles:
        - role: linuxhq.cloudflare.devices_policy
          accounts_info_api_token: "{{ lookup('env', 'CLOUDFLARE_API_TOKEN') }}"
          accounts_info_name: "{{ lookup('env', 'CLOUDFLARE_ACCOUNT_NAME') }}"
          devices_policy_account_id: '{{ _accounts_info_id }}'
          devices_policy_api_token: '{{ accounts_info_api_token }}'
          devices_policy_auto_connect: 60
          devices_policy_include:
            - address: 100.64.0.0/10
          devices_policy_service_mode_v2:
            mode: warp_tunnel_only
