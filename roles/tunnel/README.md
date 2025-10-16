# tunnel

[![License](https://img.shields.io/badge/license-GPLv3-brightgreen.svg?style=flat)](COPYING)

Manage cloudflare tunnels

## Requirements

* Cloudflare api `Token` with `Edit` permissions to `Cloudflare Tunnel`

## Role Variables

    tunnel_account_id: null
    tunnel_api_token: null
    tunnel_list: []

## Dependencies

* [linuxhq.cloudflare.account\_info](https://github.com/linuxhq/ansible-collection-cloudflare/tree/main/roles/account_info)

## Return Values

None

## Example Playbook

    - hosts: cloudflare
      connection: local
      roles:
        - role: linuxhq.cloudflare.tunnel
          account_info_api_token: m4wxAwXmmLVWyKLwqchybVh9F3LnmTKJtsrheV77
          account_info_name: linuxhq
          tunnel_account_id: "{{ _account_info_id }}"
          tunnel_api_token: "{{ account_info_api_token }}"
          tunnel_list:
            - name: taylorkimball.org
              tunnel_secret: YjNhS3ZzQ0puNzNxdFljY0VmbkpGdWlOb3M3dWNxUlJ5YmhVUkx6S2NUNFBZN3k3bUZUb21McnUzd1BhTkh2aQo=

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
