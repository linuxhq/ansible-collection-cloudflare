# access\_policies\_info

[![License](https://img.shields.io/badge/license-GPLv3-brightgreen.svg?style=flat)](https://www.gnu.org/licenses/gpl-3.0.txt)

Gather information about cloudflare access policies

See the [Cloudflare API reference](https://developers.cloudflare.com/api/resources/zero_trust/subresources/access/subresources/policies/).

## Requirements

| Type    | Permission                | Value |
| ------- | ------------------------- | ----- |
| Account | Access: Apps and Policies | Read  |
| Account | Account Settings          | Read  |

## Role Variables

| Variable                          | Default | Description                                                           |
| --------------------------------- | ------- | --------------------------------------------------------------------- |
| `access_policies_info_account_id` | `null`  | Cloudflare account ID; null skips the query and publishes empty facts |
| `access_policies_info_api_token`  | `null`  | Cloudflare API token; null skips the query and publishes empty facts  |

## Dependencies

* [accounts\_info](../accounts_info)

## Return Values

    _access_policies_info_dict
    _access_policies_info_list

## Example Playbook

    - hosts: cloudflare
      connection: local
      roles:
        - role: linuxhq.cloudflare.access_policies_info
          accounts_info_api_token: "{{ lookup('env', 'CLOUDFLARE_API_TOKEN') }}"
          accounts_info_name: "{{ lookup('env', 'CLOUDFLARE_ACCOUNT_NAME') }}"
          access_policies_info_account_id: '{{ _accounts_info_id }}'
          access_policies_info_api_token: '{{ accounts_info_api_token }}'
