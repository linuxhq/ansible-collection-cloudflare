# zones

[![License](https://img.shields.io/badge/license-GPLv3-brightgreen.svg?style=flat)](https://www.gnu.org/licenses/gpl-3.0.txt)

Manage cloudflare zones

## Requirements

* Cloudflare api `Token` with `Write` permissions to `Zone`

## Role Variables

    zones_account_id: null
    zones_api_token: null
    zones_async: 300
    zones_batch: 10
    zones_delay: 3
    zones_list: []
    zones_match: all
    zones_page: 1
    zones_per_page: 20
    zones_poll: 0
    zones_retries: 100

## Dependencies

* [accounts\_info](../accounts_info)

## Example Playbook

    - hosts: cloudflare
      connection: local
      roles:
        - role: linuxhq.cloudflare.zones
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
