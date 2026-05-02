# access\_policies

[![License](https://img.shields.io/badge/license-GPLv3-brightgreen.svg?style=flat)](https://www.gnu.org/licenses/gpl-3.0.txt)

Manage cloudflare access policies

## Requirements

* Cloudflare api `Token` with `Write` permissions to `Access: Apps and Policies`

## Role Variables

    access_policies_account_id: null
    access_policies_api_token: null
    access_policies_list: []

## Dependencies

* [linuxhq.cloudflare.access\_groups\_info](https://github.com/linuxhq/ansible-collection-cloudflare/tree/main/roles/access_groups_info)

## Example Playbook

    - hosts: cloudflare
      connection: local
      roles:
        - role: linuxhq.cloudflare.access_policies
          accounts_info_api_token: m4wxAwXmmLVWyKLwqchybVh9F3LnmTKJtsrheV77
          accounts_info_name: linuxhq

          access_groups_account_id: "{{ _accounts_info_id }}"
          access_groups_api_token: "{{ accounts_info_api_token }}"
          access_groups_info_account_id: "{{ _accounts_info_id }}"
          access_groups_info_api_token: "{{ accounts_info_api_token }}"
          access_groups_list:
            - name: linuxhq.dev
              include:
                - service_token:
                    token_id: "{{ _access_service_tokens_info_dict['linuxhq.dev'].id }}"
              is_default: false

          access_policies_account_id: "{{ _accounts_info_id }}"
          access_policies_api_token: "{{ accounts_info_api_token }}"
          access_policies_list:
            - name: linuxhq.dev
              decision: non_identity
              include:
                - group:
                    id: "{{ _access_groups_info_dict['linuxhq.dev'].id }}"

          access_service_tokens_account_id: "{{ _accounts_info_id }}"
          access_service_tokens_api_token: "{{ accounts_info_api_token }}"
          access_service_tokens_info_account_id: "{{ _accounts_info_id }}"
          access_service_tokens_info_api_token: "{{ accounts_info_api_token }}"
          access_service_tokens_list:
            - name: linuxhq.dev
              duration: forever
