# access\_app

[![License](https://img.shields.io/badge/license-GPLv3-brightgreen.svg?style=flat)](COPYING)

Manage cloudflare access applications

## Requirements

* Cloudflare api `Token` with `Edit` permissions to `Access: Apps and Policies`

## Role Variables

    access_app_account_id: null
    access_app_api_token: null
    access_app_list: []

## Dependencies

* [linuxhq.cloudflare.access\_policy\_info](https://github.com/linuxhq/ansible-collection-cloudflare/tree/main/roles/access_policy_info)

## Example Playbook

    - hosts: cloudflare
      connection: local
      roles:
        - role: linuxhq.cloudflare.access_app
          accounts_info_api_token: m4wxAwXmmLVWyKLwqchybVh9F3LnmTKJtsrheV77
          accounts_info_name: linuxhq

          access_app_account_id: "{{ _accounts_info_id }}"
          access_app_api_token: "{{ accounts_info_api_token }}"
          access_app_list:
            - domain: taylorkimball.org
              name: taylorkimball.org
              policies:
                - id: "{{ _access_policy_info_dict['taylorkimball.org'].id }}"
              type: self_hosted

          access_group_account_id: "{{ _accounts_info_id }}"
          access_group_api_token: "{{ accounts_info_api_token }}"
          access_group_info_account_id: "{{ _accounts_info_id }}"
          access_group_info_api_token: "{{ accounts_info_api_token }}"
          access_group_list:
            - name: taylorkimball.org
              include:
                - service_token:
                    token_id: "{{ _access_service_token_info_dict['taylorkimball.org'].id }}"
              is_default: false

          access_policy_account_id: "{{ _accounts_info_id }}"
          access_policy_api_token: "{{ accounts_info_api_token }}"
          access_policy_info_account_id: "{{ _accounts_info_id }}"
          access_policy_info_api_token: "{{ accounts_info_api_token }}"
          access_policy_list:
            - name: taylorkimball.org
              decision: non_identity
              include:
                - group:
                    id: "{{ _access_group_info_dict['taylorkimball.org'].id }}"

          access_service_token_account_id: "{{ _accounts_info_id }}"
          access_service_token_api_token: "{{ accounts_info_api_token }}"
          access_service_token_info_account_id: "{{ _accounts_info_id }}"
          access_service_token_info_api_token: "{{ accounts_info_api_token }}"
          access_service_token_list:
            - name: taylorkimball.org
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
