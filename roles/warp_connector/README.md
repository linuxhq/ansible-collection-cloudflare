# warp\_connector

[![License](https://img.shields.io/badge/license-GPLv3-brightgreen.svg?style=flat)](COPYING)

Manage cloudflare warp connectors

Application programming interface -> [tunnels](https://developers.cloudflare.com/api/resources/zero_trust/subresources/tunnels/)

## Requirements

* Cloudflare api `Token` with `Edit` permissions to `Cloudflare One Connector: WARP`

## Role Variables

    warp_connector_account_id: null
    warp_connector_api_token: null
    warp_connector_list: []

## Dependencies

* [linuxhq.cloudflare.accounts\_info](https://github.com/linuxhq/ansible-collection-cloudflare/tree/main/roles/accounts_info)

## Example Playbook

    - hosts: cloudflare
      connection: local
      roles:
        - role: linuxhq.cloudflare.warp_connector
          accounts_info_api_token: m4wxAwXmmLVWyKLwqchybVh9F3LnmTKJtsrheV77
          accounts_info_name: linuxhq
          warp_connector_account_id: "{{ _accounts_info_id }}"
          warp_connector_api_token: "{{ accounts_info_api_token }}"
          warp_connector_list:
            - name: linuxhq.dev

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
