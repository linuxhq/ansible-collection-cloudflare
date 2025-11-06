# zones

[![License](https://img.shields.io/badge/license-GPLv3-brightgreen.svg?style=flat)](COPYING)

Manage cloudflare zones

Application programming interface -> [zones](https://developers.cloudflare.com/api/resources/zones/)

## Requirements

* Cloudflare api `Token` with `Edit` permissions to `Zone`

## Role Variables

    zones_account_id: null
    zones_api_token: null
    zones_list: []
    zones_match: all
    zones_page: 1
    zones_per_page: 20

## Dependencies

* [linuxhq.cloudflare.accounts\_info](https://github.com/linuxhq/ansible-collection-cloudflare/tree/main/roles/accounts_info)

## Example Playbook

    - hosts: cloudflare
      connection: local
      roles:
        - role: linuxhq.cloudflare.zones
          accounts_info_api_token: "{{ lookup('env', 'CLOUDFLARE_API_TOKEN') }}"
          accounts_info_name: "{{ lookup('env', 'CLOUDFLARE_ACCOUNT_NAME') }}"

          zones_account_id: "{{ _accounts_info_id }}"
          zones_api_token: "{{ accounts_info_api_token }}"
          zones_list:
            - name: linuxhq.dev
              type: full
              settings:
                - id: always_use_https
                  value: 'on'
                - id: development_mode
                  value: 'on'
                - id: ipv6
                  value: 'off'
                - id: min_tls_version
                  value: 1.3
                - id: ssl
                  value: strict

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
