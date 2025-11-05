# rulesets

[![License](https://img.shields.io/badge/license-GPLv3-brightgreen.svg?style=flat)](COPYING)

Manage cloudflare rulesets

Application programming interface -> [rulesets](https://developers.cloudflare.com/api/resources/rulesets/)

## Requirements

* Cloudflare api `Token` with `Edit` permissions to `Zone: Zone WAF`

## Role Variables

    rulesets_api_token: null
    rulesets_list: []
    rulesets_phase: http_request_firewall_custom

## Dependencies

* [linuxhq.cloudflare.zones\_info](https://github.com/linuxhq/ansible-collection-cloudflare/tree/main/roles/zones_info)

## Example Playbook

    - hosts: cloudflare
      connection: local
      roles:
        - role: linuxhq.cloudflare.rulesets
          zones_info_api_token: "{{ lookup('env', 'CLOUDFLARE_API_TOKEN') }}"
          rulesets_api_token: "{{ zones_info_api_token }}"
          rulesets_list:
            - zone_id: "{{ _zones_info_dict['linuxhq.dev'].id }}"
              name: default
              rules:
                - action: block
                  description: US
                  enabled: true
                  expression: >-
                    (ip.geoip.country ne "US")

                - action: block
                  description: Known Bots
                  enabled: true
                  expression: >-
                    (cf.client.bot)

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
