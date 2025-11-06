# rulesets\_info

[![License](https://img.shields.io/badge/license-GPLv3-brightgreen.svg?style=flat)](COPYING)

Gather information about cloudflare rulesets

Application programming interface -> [rulesets](https://developers.cloudflare.com/api/resources/rulesets/)

## Requirements

* Cloudflare api `Token` with `Read` permissions to `Zone: Zone WAF`

## Role Variables

    rulesets_info_async: 300
    rulesets_info_api_token: null
    rulesets_info_delay: 3
    rulesets_info_phase: http_request_firewall_custom
    rulesets_info_poll: 0
    rulesets_info_retries: 100

## Return Values

    _rulesets_info_dict
    _rulesets_info_list

## Example Playbook

    - hosts: cloudflare
      connection: local
      roles:
        - role: linuxhq.cloudflare.rulesets_info
          rulesets_info_api_token: m4wxAwXmmLVWyKLwqchybVh9F3LnmTKJtsrheV77

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
