# cfd\_tunnel

[![License](https://img.shields.io/badge/license-GPLv3-brightgreen.svg?style=flat)](COPYING)

Manage cloudflare cfd tunnels

Application programming interface -> [tunnels](https://developers.cloudflare.com/api/resources/zero_trust/subresources/tunnels/)

## Requirements

* Cloudflare api `Token` with `Edit` permissions to `Cloudflare Tunnel`

## Role Variables

    cfd_tunnel_account_id: null
    cfd_tunnel_api_token: null
    cfd_tunnel_list: []

## Dependencies

* [linuxhq.cloudflare.accounts\_info](https://github.com/linuxhq/ansible-collection-cloudflare/tree/main/roles/accounts_info)

## Example Playbook

    - hosts: cloudflare
      connection: local
      roles:
        - role: linuxhq.cloudflare.cfd_tunnel
          accounts_info_api_token: m4wxAwXmmLVWyKLwqchybVh9F3LnmTKJtsrheV77
          accounts_info_name: linuxhq
          cfd_tunnel_account_id: "{{ _accounts_info_id }}"
          cfd_tunnel_api_token: "{{ accounts_info_api_token }}"
          cfd_tunnel_list:
            - name: linuxhq.dev
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
