# dns

[![License](https://img.shields.io/badge/license-GPLv3-brightgreen.svg?style=flat)](COPYING)

Manage cloudflare dns records

Application programming interface -> [dns](https://developers.cloudflare.com/api/resources/dns/)

## Requirements

* Cloudflare api `Token` with `Edit` permissions to `DNS`

## Role Variables

    dns_api_token: null
    dns_async: 300
    dns_batch: 10
    dns_delay: 3
    dns_poll: 0
    dns_records: []
    dns_retries: 100

## Dependencies

* [linuxhq.cloudflare.cfd\_tunnel\_info](https://github.com/linuxhq/ansible-collection-cloudflare/tree/main/roles/cfd_tunnel_info)

## Example Playbook

    - hosts: cloudflare
      connection: local
      roles:
        - role: linuxhq.cloudflare.dns
          dns_api_token: m4wxAwXmmLVWyKLwqchybVh9F3LnmTKJtsrheV77
          dns_records:
            - zone: linuxhq.dev
              records:
                - record: ansible
                  proxied: false
                  type: CNAME
                  value: ansible.com

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
