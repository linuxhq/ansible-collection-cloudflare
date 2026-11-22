# devices\_settings

[![License](https://img.shields.io/badge/license-GPLv3-brightgreen.svg?style=flat)](https://www.gnu.org/licenses/gpl-3.0.txt)

Manage cloudflare devices settings

See the [Cloudflare API reference](https://developers.cloudflare.com/api/resources/zero_trust/subresources/devices/subresources/settings/).

## Requirements

| Type    | Permission       | Value |
| ------- | ---------------- | ----- |
| Account | Account Settings | Read  |
| Account | Zero Trust       | Write |

## Role Variables

| Variable                                                 | Default | Description                                                 |
| -------------------------------------------------------- | ------- | ----------------------------------------------------------- |
| `devices_settings_account_id`                            | `null`  | Cloudflare account ID; null skips the role                  |
| `devices_settings_api_token`                             | `null`  | Cloudflare API token; null skips the role                   |
| `devices_settings_disable_for_time`                      | `null`  | Override code duration in seconds; null leaves it unchanged |
| `devices_settings_gateway_proxy_enabled`                 | `null`  | Proxy TCP through Gateway; null leaves it unchanged         |
| `devices_settings_gateway_udp_proxy_enabled`             | `null`  | Proxy UDP through Gateway; null leaves it unchanged         |
| `devices_settings_root_certificate_installation_enabled` | `null`  | Install the root certificate; null leaves it unchanged      |
| `devices_settings_use_zt_virtual_ip`                     | `null`  | Assign Zero Trust virtual IPs; null leaves it unchanged     |

A setting left at `null` is not sent, so Cloudflare leaves its current value unchanged.

## Dependencies

* [accounts\_info](../accounts_info)

## Example Playbook

    - hosts: cloudflare
      connection: local
      roles:
        - role: linuxhq.cloudflare.devices_settings
          accounts_info_api_token: "{{ lookup('env', 'CLOUDFLARE_API_TOKEN') }}"
          accounts_info_name: "{{ lookup('env', 'CLOUDFLARE_ACCOUNT_NAME') }}"
          devices_settings_account_id: '{{ _accounts_info_id }}'
          devices_settings_api_token: '{{ accounts_info_api_token }}'
          devices_settings_gateway_proxy_enabled: true
          devices_settings_gateway_udp_proxy_enabled: true
          devices_settings_use_zt_virtual_ip: true
