# page\_rule

[![License](https://img.shields.io/badge/license-GPLv3-brightgreen.svg?style=flat)](COPYING)

Create and update cloudflare page rules

## Requirements

* Cloudflare api `Token` with `View` permissions to `Account Filter Lists`

## Role Variables

Available variables are ruleed below, along with default values:

    cf_auth_token: null
    cf_page_rules: []

## Dependencies

* [linuxhq.cloudflare.zone_info](https://github.com/linuxhq/ansible-collection-cloudflare/tree/main/roles/zone_info)

## Return Values

None

## Example Playbook

    - hosts: cloudflare
      connection: local
      roles:
        - role: linuxhq.cloudflare.page_rule
          cf_auth_token: LYwUWCwe33KWgtRbXUgi9M3EysNixqscjLpbuUfx
          cf_page_rules:
            - zone_id: "{{ _cf_zone_id['linuxhq.org'] }}"
              rules:
                - actions:
                    - id: forwarding_url
                      value:
                        status_code: 301
                        url: https://github.com/linuxhq
                  priority: 1
                  targets:
                    - constraint:
                        operator: matches
                        value: '*linuxhq.org/*'
                      target: url

## License

Copyright (C) 2023 Linux HeadQuarters

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
