# zerotrust\_connectivity\_settings

[![License](https://img.shields.io/badge/license-GPLv3-brightgreen.svg?style=flat)](COPYING)

Manage cloudflare zerotrust connectivity settings

Application programming interface -> [zero\_trust](https://developers.cloudflare.com/api/resources/zero_trust/)

## Requirements

* Cloudflare api `Token` with `Edit` permissions to `Zero Trust`

## Role Variables

    zerotrust_connectivity_settings_account_id: null
    zerotrust_connectivity_settings_api_token: null
    zerotrust_connectivity_settings_icmp_proxy_enabled: false
    zerotrust_connectivity_settings_offramp_warp_enabled: false

## Dependencies

* [linuxhq.cloudflare.accounts\_info](https://github.com/linuxhq/ansible-collection-cloudflare/tree/main/roles/accounts_info)

## Example Playbook

    - hosts: cloudflare
      connection: local
      roles:
        - role: linuxhq.cloudflare.zerotrust_connectivity_settings
          accounts_info_api_token: m4wxAwXmmLVWyKLwqchybVh9F3LnmTKJtsrheV77
          accounts_info_name: linuxhq
          zerotrust_connectivity_settings_account_id: "{{ _accounts_info_id }}"
          zerotrust_connectivity_settings_api_token: "{{ accounts_info_api_token }}"
          zerotrust_connectivity_settings_icmp_proxy_enabled: true
          zerotrust_connectivity_settings_offramp_warp_enabled: true

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
