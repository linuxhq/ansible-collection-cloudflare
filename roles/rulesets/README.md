# rulesets

[![License](https://img.shields.io/badge/license-GPLv3-brightgreen.svg?style=flat)](https://www.gnu.org/licenses/gpl-3.0.txt)

Manage cloudflare rulesets

## Requirements

* Cloudflare api `Token` with `Write` permissions to `Account WAF`

## Role Variables

    rulesets_api_token: null
    rulesets_list: []
    rulesets_phase: http_request_firewall_custom

## Dependencies

* [linuxhq.cloudflare.zones\_info](https://github.com/linuxhq/ansible-collection-cloudflare/tree/main/roles/zones_info)

## Example Playbook

    - hosts: cloudflare
      connection: local
      roles:
        - role: linuxhq.cloudflare.rulesets
          zones_info_api_token: m4wxAwXmmLVWyKLwqchybVh9F3LnmTKJtsrheV77
          rulesets_api_token: "{{ zones_info_api_token }}"
          rulesets_list:
            - zone_id: "{{ _zones_info_dict['linuxhq.dev'].id }}"
              name: default
              rules:
                - action: block
                  description: US
                  enabled: true
                  expression: >-
                    (ip.geoip.country ne "US")

                - action: block
                  description: Known Bots
                  enabled: true
                  expression: >-
                    (cf.client.bot)
