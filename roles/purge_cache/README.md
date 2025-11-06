# purge\_cache

[![License](https://img.shields.io/badge/license-GPLv3-brightgreen.svg?style=flat)](COPYING)

Manage cloudflare purging of cache

Application programming interface -> [cache](https://developers.cloudflare.com/api/resources/cache/)

## Requirements

* Cloudflare api `Token` with `Purge` permissions to `Cache Purge`

## Role Variables

    purge_cache_api_token: null
    purge_cache_list: []

## Dependencies

* [linuxhq.cloudflare.zones\_info](https://github.com/linuxhq/ansible-collection-cloudflare/tree/main/roles/zones_info)

## Example Playbook

    - hosts: cloudflare
      connection: local
      roles:
        - role: linuxhq.cloudflare.purge_cache
          zones_info_api_token: m4wxAwXmmLVWyKLwqchybVh9F3LnmTKJtsrheV77
          purge_cache_api_token: "{{ zones_info_api_token }}"
          purge_cache_list:
            - zone_id: "{{ _zones_info_dict['linuxhq.dev'].id }}"
              cache:
                purge_everything: true

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
