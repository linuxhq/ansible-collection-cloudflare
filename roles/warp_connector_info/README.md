# warp\_connector\_info

[![License](https://img.shields.io/badge/license-GPLv3-brightgreen.svg?style=flat)](https://www.gnu.org/licenses/gpl-3.0.txt)

Gather information about cloudflare warp connectors

## Requirements

| Type    | Permission                     | Value |
| ------- | ------------------------------ | ----- |
| Account | Account Settings               | Read  |
| Account | Cloudflare One Connector: WARP | Read  |
| Account | Cloudflare One Connectors      | Write |

## Role Variables

    warp_connector_info_account_id: null
    warp_connector_info_api_token: null
    warp_connector_info_include_token: false
    warp_connector_info_no_log: false

## Dependencies

* [accounts\_info](../accounts_info)

## Return Values

    _warp_connector_info_dict
    _warp_connector_info_list

## Example Playbook

    - hosts: cloudflare
      connection: local
      roles:
        - role: linuxhq.cloudflare.warp_connector_info
          accounts_info_api_token: "{{ lookup('env', 'CLOUDFLARE_API_TOKEN') }}"
          accounts_info_name: "{{ lookup('env', 'CLOUDFLARE_ACCOUNT_NAME') }}"
          warp_connector_info_account_id: '{{ _accounts_info_id }}'
          warp_connector_info_api_token: '{{ accounts_info_api_token }}'
          warp_connector_info_include_token: false
