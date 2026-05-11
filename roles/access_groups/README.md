# access\_groups

[![License](https://img.shields.io/badge/license-GPLv3-brightgreen.svg?style=flat)](https://www.gnu.org/licenses/gpl-3.0.txt)

Manage cloudflare access groups

## Requirements

* Cloudflare api `Token` with `Write` permissions to `Access: Organizations, Identity Providers, and Groups`

## Role Variables

    access_groups_account_id: null
    access_groups_api_token: null
    access_groups_async: 300
    access_groups_batch: 10
    access_groups_delay: 3
    access_groups_list: []
    access_groups_poll: 0
    access_groups_retries: 100

## Dependencies

* [access\_service\_tokens\_info](../access_service_tokens_info)

## Example Playbook

    - hosts: cloudflare
      connection: local
      roles:
        - role: linuxhq.cloudflare.access_groups
          access_groups_account_id: '{{ _accounts_info_id }}'
          access_groups_api_token: '{{ accounts_info_api_token }}'
          access_groups_list:
            - name: molecule-00
              include:
                - service_token:
                    token_id: "{{ _access_service_tokens_info_dict['molecule-00'].id }}"
              is_default: false
            - name: molecule-01
              include:
                - service_token:
                    token_id: "{{ _access_service_tokens_info_dict['molecule-01'].id }}"
              is_default: false
            - name: molecule-02
              include:
                - service_token:
                    token_id: "{{ _access_service_tokens_info_dict['molecule-02'].id }}"
              is_default: false
