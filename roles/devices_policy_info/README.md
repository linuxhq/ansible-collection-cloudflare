# devices\_policy\_info

[![License](https://img.shields.io/badge/license-GPLv3-brightgreen.svg?style=flat)](https://www.gnu.org/licenses/gpl-3.0.txt)

Gather information about cloudflare devices policy

See the [Cloudflare API reference](https://developers.cloudflare.com/api/resources/zero_trust/subresources/devices/subresources/policies/subresources/default/).

## Requirements

| Type    | Permission       | Value |
| ------- | ---------------- | ----- |
| Account | Account Settings | Read  |
| Account | Zero Trust       | Read  |

## Role Variables

| Variable                         | Default | Description                                |
| -------------------------------- | ------- | ------------------------------------------ |
| `devices_policy_info_account_id` | `null`  | Cloudflare account ID; null skips the role |
| `devices_policy_info_api_token`  | `null`  | Cloudflare API token; null skips the role  |

## Return Values

    _devices_policy_info_dict

## Dependencies

* [accounts\_info](../accounts_info)

## Example Playbook

    - hosts: cloudflare
      connection: local
      roles:
        - role: linuxhq.cloudflare.devices_policy_info
          accounts_info_api_token: "{{ lookup('env', 'CLOUDFLARE_API_TOKEN') }}"
          accounts_info_name: "{{ lookup('env', 'CLOUDFLARE_ACCOUNT_NAME') }}"
          devices_policy_info_account_id: '{{ _accounts_info_id }}'
          devices_policy_info_api_token: '{{ accounts_info_api_token }}'
