# zone\_info

[![License](https://img.shields.io/badge/license-GPLv3-brightgreen.svg?style=flat)](COPYING)

Gather information about cloudflare zones

## Requirements

* Cloudflare api `token` with `read` permissions to `zone settings`

## Role Variables

Available variables are listed below, along with default values:

    cf_auth_token: null

## Dependencies

None

## Return Values

    _cf_zone_id
    _cf_zone_list
    _cf_zone_name_servers

## Example Playbook

    - hosts: localhost
      connection: local
      roles:
        - role: linuxhq.cloudflare.zone_info
          cf_auth_token: d41d8cd98f00b204e9800998ecf8427e

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
