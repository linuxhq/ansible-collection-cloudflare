# scrape\_shield

[![License](https://img.shields.io/badge/license-GPLv3-brightgreen.svg?style=flat)](COPYING)

Configure scrape shield settings

## Requirements

* Cloudflare api `Token` with `Edit` permissions to `Zone Settings`

## Role Variables

Available variables are listed below, along with default values:

    cf_auth_token: null
    cf_scrape_shield: []

## Dependencies

* [linuxhq.cloudflare.zone_info](https://github.com/linuxhq/ansible-collection-cloudflare/tree/main/roles/zone_info)

## Example Playbook

    - hosts: cloudflare
      connection: local
      roles:
        - role: linuxhq.cloudflare.scrape_shield
          cf_auth_token: LYwUWCwe33KWgtRbXUgi9M3EysNixqscjLpbuUfx
          cf_scrape_shield:
            - zone_id: "{{ _cf_zone_id['linuxhq.net'] }}"
              email_obfuscation: true
              hotlink_protection: true
              server_side_exclude: true

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
