# access\_apps

[![License](https://img.shields.io/badge/license-GPLv3-brightgreen.svg?style=flat)](https://www.gnu.org/licenses/gpl-3.0.txt)

Manage cloudflare access apps

## Requirements

| Type    | Permission                | Value |
| ------- | ------------------------- | ----- |
| Account | Access: Apps and Policies | Write |
| Account | Account Settings          | Read  |

## Role Variables

    access_apps_account_id: null
    access_apps_api_token: null
    access_apps_async: 300
    access_apps_batch: 10
    access_apps_delay: 3
    access_apps_list: []
    access_apps_poll: 0
    access_apps_retries: 100

## Dependencies

* [access\_policies\_info](../access_policies_info)

## Example Playbook

    - hosts: cloudflare
      connection: local
      roles:
        - role: linuxhq.cloudflare.access_apps
          accounts_info_api_token: "{{ lookup('env', 'CLOUDFLARE_API_TOKEN') }}"
          accounts_info_name: "{{ lookup('env', 'CLOUDFLARE_ACCOUNT_NAME') }}"
          access_policies_info_account_id: '{{ _accounts_info_id }}'
          access_policies_info_api_token: '{{ accounts_info_api_token }}'
          access_apps_account_id: '{{ _accounts_info_id }}'
          access_apps_api_token: '{{ accounts_info_api_token }}'
          access_apps_list:
            - name: linuxhq.dev
              domain: linuxhq.dev
              destinations:
                - type: public
                  uri: linuxhq.dev
                - type: public
                  uri: molecule-00.linuxhq.dev
                - type: public
                  uri: molecule-01.linuxhq.dev
              policies:
                - id: "{{ _access_policies_info_dict['molecule-00-email'].id }}"
              type: self_hosted
