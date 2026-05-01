# access\_groups

[![License](https://img.shields.io/badge/license-GPLv3-brightgreen.svg?style=flat)](https://www.gnu.org/licenses/gpl-3.0.txt)

Manage cloudflare access groups

Application programming interface -> [access](https://developers.cloudflare.com/api/resources/zero_trust/subresources/access/)

## Requirements

* Cloudflare api `Token` with `Write` permissions to `Access: Organizations, Identity Providers, and Groups`

## Role Variables

    access_groups_account_id: null
    access_groups_api_token: null
    access_groups_list: []

## Dependencies

* [linuxhq.cloudflare.access\_service\_tokens\_info](https://github.com/linuxhq/ansible-collection-cloudflare/tree/main/roles/access_service_tokens_info)

## Example Playbook

    - hosts: cloudflare
      connection: local
      roles:
        - role: linuxhq.cloudflare.access_groups
          accounts_info_api_token: m4wxAwXmmLVWyKLwqchybVh9F3LnmTKJtsrheV77
          accounts_info_name: linuxhq

          access_groups_account_id: "{{ _accounts_info_id }}"
          access_groups_api_token: "{{ accounts_info_api_token }}"
          access_groups_list:
            - name: linuxhq.dev
              include:
                - service_token:
                    token_id: "{{ _access_service_token_info_dict['linuxhq.dev'].id }}"
              is_default: false

          access_service_tokens_account_id: "{{ _accounts_info_id }}"
          access_service_tokens_api_token: "{{ accounts_info_api_token }}"
          access_service_tokens_info_account_id: "{{ _accounts_info_id }}"
          access_service_tokens_info_api_token: "{{ accounts_info_api_token }}"
          access_service_tokens_list:
            - name: linuxhq.dev
              duration: forever
