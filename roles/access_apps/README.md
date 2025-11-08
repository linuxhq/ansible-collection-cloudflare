# access\_apps

[![License](https://img.shields.io/badge/license-GPLv3-brightgreen.svg?style=flat)](COPYING)

Manage cloudflare access apps

Application programming interface -> [access](https://developers.cloudflare.com/api/resources/zero_trust/subresources/access/)

## Requirements

* Cloudflare api `Token` with `Edit` permissions to `Access: Apps and Policies`

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

## License

Copyright (c) Linux HeadQuarters

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program. If not, see <http://www.gnu.org/licenses/>.
