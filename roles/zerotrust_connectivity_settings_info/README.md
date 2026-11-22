# zerotrust\_connectivity\_settings\_info

[![License](https://img.shields.io/badge/license-GPLv3-brightgreen.svg?style=flat)](https://www.gnu.org/licenses/gpl-3.0.txt)

Gather information about cloudflare zerotrust connectivity settings

See the [Cloudflare API reference](https://developers.cloudflare.com/api/resources/zero_trust/subresources/connectivity_settings/).

## Requirements

| Type    | Permission       | Value |
| ------- | ---------------- | ----- |
| Account | Account Settings | Read  |
| Account | Zero Trust       | Read  |

## Role Variables

| Variable                                          | Default | Description                                |
| ------------------------------------------------- | ------- | ------------------------------------------ |
| `zerotrust_connectivity_settings_info_account_id` | `null`  | Cloudflare account ID; null skips the role |
| `zerotrust_connectivity_settings_info_api_token`  | `null`  | Cloudflare API token; null skips the role  |

## Return Values

    _zerotrust_connectivity_settings_info_dict

## Dependencies

* [accounts\_info](../accounts_info)

## Example Playbook

    - hosts: cloudflare
      connection: local
      roles:
        - role: linuxhq.cloudflare.zerotrust_connectivity_settings_info
          accounts_info_api_token: "{{ lookup('env', 'CLOUDFLARE_API_TOKEN') }}"
          accounts_info_name: "{{ lookup('env', 'CLOUDFLARE_ACCOUNT_NAME') }}"
          zerotrust_connectivity_settings_info_account_id: '{{ _accounts_info_id }}'
          zerotrust_connectivity_settings_info_api_token: '{{ accounts_info_api_token }}'
