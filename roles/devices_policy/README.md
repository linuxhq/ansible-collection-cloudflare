# devices\_policy

[![License](https://img.shields.io/badge/license-GPLv3-brightgreen.svg?style=flat)](COPYING)

Manage cloudflare devices policy

Application programming interface -> [zero\_trust](https://developers.cloudflare.com/api/resources/zero_trust/)

## Requirements

* Cloudflare api `Token` with `Edit` permissions to `Zero Trust`

## Role Variables

    devices_policy_account_id: null
    devices_policy_api_token: null
    devices_policy_dict: {}

## Dependencies

* [linuxhq.cloudflare.accounts\_info](https://github.com/linuxhq/ansible-collection-cloudflare/tree/main/roles/accounts_info)

## Example Playbook

    - hosts: cloudflare
      connection: local
      roles:
        - role: linuxhq.cloudflare.devices_policy
          accounts_info_api_token: m4wxAwXmmLVWyKLwqchybVh9F3LnmTKJtsrheV77
          accounts_info_name: linuxhq
          devices_policy_account_id: "{{ _accounts_info_id }}"
          devices_policy_api_token: "{{ accounts_info_api_token }}"
          devices_policy_dict:
            include:
              - address: 100.64.0.0/10
            service_mode_v2:
              mode: warp_tunnel_only

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
