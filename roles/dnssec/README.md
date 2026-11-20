# dnssec

[![License](https://img.shields.io/badge/license-GPLv3-brightgreen.svg?style=flat)](https://www.gnu.org/licenses/gpl-3.0.txt)

Manage cloudflare dnssec settings

## Requirements

| Type | Permission | Value |
| ---- | ---------- | ----- |
| Zone | DNS        | Write |
| Zone | Zone       | Read  |

## Role Variables

    dnssec_api_token: null
    dnssec_async: 300
    dnssec_batch: 10
    dnssec_delay: 3
    dnssec_list: []
    dnssec_poll: 0
    dnssec_retries: 100

## Dependencies

* [zones\_info](../zones_info)

## Example Playbook

    - hosts: cloudflare
      connection: local
      roles:
        - role: linuxhq.cloudflare.dnssec
          zones_info_api_token: "{{ lookup('env', 'CLOUDFLARE_API_TOKEN') }}"
          dnssec_api_token: '{{ zones_info_api_token }}'
          dnssec_list:
            - zone_id: "{{ _zones_info_dict['molecule.com'].id }}"
              status: active
            - zone_id: "{{ _zones_info_dict['molecule.net'].id }}"
              status: active
            - zone_id: "{{ _zones_info_dict['molecule.org'].id }}"
              status: active
