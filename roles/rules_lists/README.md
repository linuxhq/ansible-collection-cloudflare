# rules\_lists

[![License](https://img.shields.io/badge/license-GPLv3-brightgreen.svg?style=flat)](COPYING)

Manage cloudflare rules lists

Application programming interface -> [rules](https://developers.cloudflare.com/api/resources/rules/)

## Requirements

* Cloudflare api `Token` with `Edit` permissions to `Account Filter Lists`

## Role Variables

    rules_lists_account_id: null
    rules_lists_api_token: null
    rules_lists_list: []

## Dependencies

* [linuxhq.cloudflare.accounts\_info](https://github.com/linuxhq/ansible-collection-cloudflare/tree/main/roles/accounts_info)

## Example Playbook

    - hosts: cloudflare
      connection: local
      roles:
        - role: linuxhq.cloudflare.rules_lists
          accounts_info_api_token: "{{ lookup('env', 'CLOUDFLARE_API_TOKEN') }}"
          accounts_info_name: "{{ lookup('env', 'CLOUDFLARE_ACCOUNT_NAME') }}"
          rules_lists_account_id: "{{ _accounts_info_id }}"
          rules_lists_api_token: "{{ accounts_info_api_token }}"
          rules_lists_list:
            - kind: ip
              name: uptime_robot
              elements:
                "{{ lookup('ansible.builtin.url',
                           'https://uptimerobot.com/inc/files/ips/IPv4.txt',
                           wantlist=true) |
                    map('community.general.dict_kv', 'ip') |
                    sort(attribute='ip') }}"

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
