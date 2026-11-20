# access\_apps\_info

[![License](https://img.shields.io/badge/license-GPLv3-brightgreen.svg?style=flat)](https://www.gnu.org/licenses/gpl-3.0.txt)

Gather information about cloudflare access apps

## Requirements

| Type    | Permission                | Value |
| ------- | ------------------------- | ----- |
| Account | Access: Apps and Policies | Read  |
| Account | Account Settings          | Read  |

## Role Variables

    access_apps_info_account_id: null
    access_apps_info_api_token: null

## Dependencies

* [accounts\_info](../accounts_info)

## Return Values

    _access_apps_info_dict
    _access_apps_info_list

## Example Playbook

    - hosts: cloudflare
      connection: local
      roles:
        - role: linuxhq.cloudflare.access_apps_info
          accounts_info_api_token: "{{ lookup('env', 'CLOUDFLARE_API_TOKEN') }}"
          accounts_info_name: "{{ lookup('env', 'CLOUDFLARE_ACCOUNT_NAME') }}"
          access_apps_info_account_id: '{{ _accounts_info_id }}'
          access_apps_info_api_token: '{{ accounts_info_api_token }}'
