# policy

[![License](https://img.shields.io/badge/license-GPLv3-brightgreen.svg?style=flat)](COPYING)

Create cloudflare access policies

## Requirements

* Cloudflare api `Token` with `Edit` permissions to `Access: Apps and Policies`

## Role Variables

Available variables are listed below, along with default values:

    cf_auth_token: null
    cf_policies: []

## Dependencies

* [linuxhq.cloudflare.application_info](https://github.com/linuxhq/ansible-collection-cloudflare/tree/main/roles/application_info)
* [linuxhq.cloudflare.service_token_info](https://github.com/linuxhq/ansible-collection-cloudflare/tree/main/roles/service_token_info)
* [linuxhq.cloudflare.zone_info](https://github.com/linuxhq/ansible-collection-cloudflare/tree/main/roles/zone_info)

## Return Values

None

## Example Playbook

    - hosts: cloudflare
      connection: local
      roles:
        - role: linuxhq.cloudflare.application
          cf_auth_token: LYwUWCwe33KWgtRbXUgi9M3EysNixqscjLpbuUfx
          cf_policies:
            - application_id: "{{ _cf_application_id['tunnel-linuxhq-org' }}"
              zone_id: "{{ _cf_zone_id['linuxhq.org'] }}"
              name: tunnel-linuxhq-org
              type: self_hosted

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
