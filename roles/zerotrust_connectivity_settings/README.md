# zerotrust\_connectivity\_settings

[![License](https://img.shields.io/badge/license-GPLv3-brightgreen.svg?style=flat)](https://www.gnu.org/licenses/gpl-3.0.txt)

Manage cloudflare zerotrust connectivity settings

See the [Cloudflare API reference](https://developers.cloudflare.com/api/resources/zero_trust/subresources/connectivity_settings/).

## Requirements

| Type    | Permission       | Value |
| ------- | ---------------- | ----- |
| Account | Account Settings | Read  |
| Account | Zero Trust       | Write |

## Role Variables

| Variable                                               | Default | Description                                           |
| ------------------------------------------------------ | ------- | ----------------------------------------------------- |
| `zerotrust_connectivity_settings_account_id`           | `null`  | Cloudflare account ID; null skips the role            |
| `zerotrust_connectivity_settings_api_token`            | `null`  | Cloudflare API token; null skips the role             |
| `zerotrust_connectivity_settings_icmp_proxy_enabled`   | `null`  | Proxy ICMP traffic; null leaves it unchanged          |
| `zerotrust_connectivity_settings_offramp_warp_enabled` | `null`  | Enable WARP-to-WARP traffic; null leaves it unchanged |

A setting left at `null` is not sent, so Cloudflare leaves its current value unchanged.

## Dependencies

* [accounts\_info](../accounts_info)

## Example Playbook

    - hosts: cloudflare
      connection: local
      roles:
        - role: linuxhq.cloudflare.zerotrust_connectivity_settings
          accounts_info_api_token: "{{ lookup('env', 'CLOUDFLARE_API_TOKEN') }}"
          accounts_info_name: "{{ lookup('env', 'CLOUDFLARE_ACCOUNT_NAME') }}"
          zerotrust_connectivity_settings_account_id: '{{ _accounts_info_id }}'
          zerotrust_connectivity_settings_api_token: '{{ accounts_info_api_token }}'
          zerotrust_connectivity_settings_icmp_proxy_enabled: true
          zerotrust_connectivity_settings_offramp_warp_enabled: true
