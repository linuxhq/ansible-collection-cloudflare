# application\_info

[![License](https://img.shields.io/badge/license-GPLv3-brightgreen.svg?style=flat)](COPYING)

Gather information about cloudflare access applications

## Requirements

* Cloudflare api `Token` with `Read` permissions to `Access: Apps and Policies`

## Role Variables

Available variables are listed below, along with default values:

    cf_account_id: null
    cf_auth_token: null

## Dependencies

* [linuxhq.cloudflare.account_info](https://github.com/linuxhq/ansible-collection-cloudflare/tree/main/roles/account_info)

## Return Values

    _cf_application_id

## Example Playbook

    - hosts: cloudflare
      connection: local
      roles:
        - role: linuxhq.cloudflare.application_info
          cf_account_id: "{{ _cf_account_id }}"
          cf_auth_token: LYwUWCwe33KWgtRbXUgi9M3EysNixqscjLpbuUfx

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
