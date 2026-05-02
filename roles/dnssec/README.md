# dnssec

[![License](https://img.shields.io/badge/license-GPLv3-brightgreen.svg?style=flat)](https://www.gnu.org/licenses/gpl-3.0.txt)

Manage cloudflare dnssec settings

## Requirements

* Cloudflare api `Token` with `Write` permissions to `DNS`

## Role Variables

    dnssec_api_token: null
    dnssec_async: 300
    dnssec_batch: 10
    dnssec_delay: 3
    dnssec_list: []
    dnssec_poll: 0
    dnssec_retries: 100

## Dependencies

* [linuxhq.cloudflare.zones\_info](https://github.com/linuxhq/ansible-collection-cloudflare/tree/main/roles/zones_info)

## Example Playbook

    - hosts: cloudflare
      connection: local
      roles:
        - role: linuxhq.cloudflare.dnssec
          zones_info_api_token: m4wxAwXmmLVWyKLwqchybVh9F3LnmTKJtsrheV77
          dnssec_api_token: "{{ zones_info_api_token }}"
          dnssec_list:
            - zone_id: "{{ _zones_info_dict['linuxhq.dev'].id }}"
              status: active
