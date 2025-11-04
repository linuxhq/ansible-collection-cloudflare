# access\_groups

[![License](https://img.shields.io/badge/license-GPLv3-brightgreen.svg?style=flat)](COPYING)

Manage cloudflare access groups

Application programming interface -> [access](https://developers.cloudflare.com/api/resources/zero_trust/subresources/access/)

## Requirements

* Cloudflare api `Token` with `Edit` permissions to `Access: Organizations, Identity Providers, and Groups`

## Role Variables

    access_groups_account_id: null
    access_groups_api_token: null
    access_groups_list: []

## Dependencies

* [linuxhq.cloudflare.access\_service\_token\_info](https://github.com/linuxhq/ansible-collection-cloudflare/tree/main/roles/access_service_token_info)

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
