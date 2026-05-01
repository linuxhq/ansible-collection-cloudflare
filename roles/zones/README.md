# zones

[![License](https://img.shields.io/badge/license-GPLv3-brightgreen.svg?style=flat)](https://www.gnu.org/licenses/gpl-3.0.txt)

Manage cloudflare zones

Application programming interface -> [zones](https://developers.cloudflare.com/api/resources/zones/)

## Requirements

* Cloudflare api `Token` with `Write` permissions to `Zone`

## Role Variables

    zones_account_id: null
    zones_api_token: null
    zones_list: []
    zones_match: all
    zones_page: 1
    zones_per_page: 20

## Dependencies

* [linuxhq.cloudflare.accounts\_info](https://github.com/linuxhq/ansible-collection-cloudflare/tree/main/roles/accounts_info)

## Example Playbook

    - hosts: cloudflare
      connection: local
      roles:
        - role: linuxhq.cloudflare.zones
          accounts_info_api_token: m4wxAwXmmLVWyKLwqchybVh9F3LnmTKJtsrheV77
          accounts_info_name: linuxhq
          zones_account_id: "{{ _accounts_info_id }}"
          zones_api_token: "{{ accounts_info_api_token }}"
          zones_list:
            - name: linuxhq.dev
              type: full
              settings:
                - id: always_use_https
                  value: 'on'
                - id: development_mode
                  value: 'on'
                - id: ipv6
                  value: 'off'
                - id: min_tls_version
                  value: 1.3
                - id: ssl
                  value: strict
