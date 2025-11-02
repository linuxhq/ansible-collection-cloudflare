# page\_rule

[![License](https://img.shields.io/badge/license-GPLv3-brightgreen.svg?style=flat)](COPYING)

Manage cloudflare page rules

## Requirements

* Cloudflare api `Token` with `Edit` permissions to `Zone Settings`

## Role Variables

    page_rule_api_token: null
    page_rule_list: []

## Dependencies

* [linuxhq.cloudflare.zone\_info](https://github.com/linuxhq/ansible-collection-cloudflare/tree/main/roles/zone_info)

## Example Playbook

    - hosts: cloudflare
      connection: local
      roles:
        - role: linuxhq.cloudflare.page_rule
          zone_info_api_token: m4wxAwXmmLVWyKLwqchybVh9F3LnmTKJtsrheV77
          page_rule_api_token: "{{ zone_info_api_token }}"
          page_rule_list:
            - zone_id: "{{ _zone_info_dict['taylorkimball.org'].id }}"
              page_rules:
                - actions:
                    - id: forwarding_url
                      value:
                        status_code: 301
                        url: https://github.com/tkimball83
                  status: active
                  targets:
                    - constraint:
                        operator: matches
                        value: "taylorkimball.org/*"
                      target: url
                - actions:
                    - id: forwarding_url
                      value:
                        status_code: 301
                        url: https://github.com/tkimball83
                  status: active
                  targets:
                    - constraint:
                        operator: matches
                        value: "www.taylorkimball.org/*"
                      target: url

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
