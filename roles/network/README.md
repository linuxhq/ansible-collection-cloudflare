# network

[![License](https://img.shields.io/badge/license-GPLv3-brightgreen.svg?style=flat)](COPYING)

Configure network settings

## Requirements

* Cloudflare api `Token` with `Edit` permissions to `Zone Settings`

## Role Variables

    network_api_token: null
    network_list: []

## Dependencies

* [linuxhq.cloudflare.zone\_info](https://github.com/linuxhq/ansible-collection-cloudflare/tree/main/roles/zone_info)

## Example Playbook

    - hosts: cloudflare
      connection: local
      vars:
        account_info_api_token: m4wxAwXmmLVWyKLwqchybVh9F3LnmTKJtsrheV77
        account_info_name: linuxhq
        zone_info_api_token: "{{ account_info_api_token }}"

      roles:
        - role: linuxhq.cloudflare.zone
          zone_account_id: "{{ _account_info_id }}"
          zone_api_token: "{{ account_info_api_token }}"
          zone_list:
            - name: taylorkimball.org
              type: full

        - role: linuxhq.cloudflare.network
          network_api_token: "{{ account_info_api_token }}"
          network_list:
            - zone_id: "{{ _zone_info_dict['taylorkimball.org'].id }}"
              ip_geolocation: true
              ipv6: false
              opportunistic_onion: false
              pseudo_ipv4: false
              websockets: true

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
