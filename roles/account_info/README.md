# account\_info

[![License](https://img.shields.io/badge/license-GPLv3-brightgreen.svg?style=flat)](COPYING)

Gather information about cloudflare account

## Requirements

* Cloudflare api `Token` with `Read` permissions to `Account Settings`

## Role Variables

Available variables are listed below, along with default values:

    account_info_api_token: null
    account_info_name: null

## Dependencies

None

## Return Values

    _account_info_id
    _account_info_name
    _account_info_settings
    _account_info_type

## Example Playbook

    - hosts: cloudflare
      connection: local
      roles:
        - role: linuxhq.cloudflare.account_info
          account_info_api_token: LYwUWCwe33KWgtRbXUgi9M3EysNixqscjLpbuUfx
          account_info_name: linuxhq

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
