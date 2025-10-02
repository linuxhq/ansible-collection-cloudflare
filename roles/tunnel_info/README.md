# tunnel\_info

[![License](https://img.shields.io/badge/license-GPLv3-brightgreen.svg?style=flat)](COPYING)

Gather information about cloudflare tunnels

## Requirements

* Cloudflare api `Token` with `Edit` permissions to `Cloudflare Tunnel`

## Role Variables

    tunnel_info_account_id: null
    tunnel_info_api_token: null

## Dependencies

* [linuxhq.cloudflare.account\_info](https://github.com/linuxhq/ansible-collection-cloudflare/tree/main/roles/account_info)

## Return Values

    _tunnel_info_dict
    _tunnel_info_list

## Example Playbook

    - hosts: cloudflare
      connection: local
      roles:
        - role: linuxhq.cloudflare.tunnel_info
          tunnel_info_account_id: "{{ _cf_account_id }}"
          tunnel_info_api_token: LYwUWCwe33KWgtRbXUgi9M3EysNixqscjLpbuUfx

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
