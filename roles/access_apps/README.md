# access\_apps

[![License](https://img.shields.io/badge/license-GPLv3-brightgreen.svg?style=flat)](https://www.gnu.org/licenses/gpl-3.0.txt)

Manage cloudflare access apps

Application programming interface -> [access](https://developers.cloudflare.com/api/resources/zero_trust/subresources/access/)

## Requirements

* Cloudflare api `Token` with `Write` permissions to `Access: Apps and Policies`

## Role Variables

    access_apps_account_id: null
    access_apps_api_token: null
    access_apps_list: []

## Dependencies

* [linuxhq.cloudflare.access\_policies\_info](https://github.com/linuxhq/ansible-collection-cloudflare/tree/main/roles/access_policies_info)

## Example Playbook

    - hosts: cloudflare
      connection: local
      roles:
        - role: linuxhq.cloudflare.access_apps
          accounts_info_api_token: m4wxAwXmmLVWyKLwqchybVh9F3LnmTKJtsrheV77
          accounts_info_name: linuxhq

          access_apps_account_id: "{{ _accounts_info_id }}"
          access_apps_api_token: "{{ accounts_info_api_token }}"
          access_apps_list:
            - name: linuxhq.dev
              domain: linuxhq.dev
              destinations:
                - type: public
                  uri: linuxhq.dev
                - type: public
                  uri: secondary.linuxhq.dev
              policies:
                - id: "{{ _access_policies_info_dict['linuxhq.dev'].id }}"
              type: self_hosted

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
          access_policies_info_account_id: "{{ _accounts_info_id }}"
          access_policies_info_api_token: "{{ accounts_info_api_token }}"
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
