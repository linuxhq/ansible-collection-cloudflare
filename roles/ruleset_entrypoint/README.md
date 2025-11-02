# ruleset\_entrypoint

[![License](https://img.shields.io/badge/license-GPLv3-brightgreen.svg?style=flat)](COPYING)

Create and update cloudflare entrypoint rule sets

## Requirements

* Cloudflare api `Token` with `Edit` permissions to `Zone: Zone WAF`

## Role Variables

Available variables are listed below, along with default values:

    cf_auth_token: null
    cf_ruleset_description: null
    cf_ruleset_kind: zone
    cf_ruleset_name: default
    cf_ruleset_phase: http_request_firewall_custom
    cf_ruleset_rules: []
    cf_zone_id: null

## Dependencies

* [linuxhq.cloudflare.zone_info](https://github.com/linuxhq/ansible-collection-cloudflare/tree/main/roles/zone_info)

## Example Playbook

    - hosts: cloudflare
      connection: local
      roles:
        - role: linuxhq.cloudflare.rule_list_info
          cf_auth_token: LYwUWCwe33KWgtRbXUgi9M3EysNixqscjLpbuUfx
          cf_zone_id: "{{ _cf_zone_id['linuxhq.net'] }}"
          cf_ruleset_rules:
            - action: skip
              action_parameters:
                ruleset: current
              description: UptimeRobot
              enabled: true
              expression: >-
                (ip.src in $uptime_robot)
              logging:
                enabled: true

            - action: block
              description: US
              enabled: true
              expression: >-
                (ip.geoip.country ne "US")

            - action: block
              description: Amazon ASN
              enabled: true
              expression: >-
                (ip.geoip.asnum eq 7224) or
                (ip.geoip.asnum eq 14618) or
                (ip.geoip.asnum eq 16509)

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
