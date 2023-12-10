# access\_group

[![License](https://img.shields.io/badge/license-GPLv3-brightgreen.svg?style=flat)](COPYING)

Create and update cloudflare access groups

## Requirements

* Cloudflare api `Token` with `Edit` permissions to `Access: Organizations, Identity Providers, and Groups`

## Role Variables

Available variables are listed below, along with default values:

    cf_account_id: null
    cf_auth_token: null
    cf_access_groups: []

## Dependencies

* [linuxhq.cloudflare.account_info](https://github.com/linuxhq/ansible-collection-cloudflare/tree/main/roles/account_info)
* [linuxhq.cloudflare.service_token_info](https://github.com/linuxhq/ansible-collection-cloudflare/tree/main/roles/service_token_info)

## Return Values

None

## Example Playbook

    - hosts: cloudflare
      connection: local
      roles:
        - role: linuxhq.cloudflare.access_group
          cf_account_id: "{{ _cf_account_id }}"
          cf_auth_token: LYwUWCwe33KWgtRbXUgi9M3EysNixqscjLpbuUfx
          cf_access_group:
            -

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
