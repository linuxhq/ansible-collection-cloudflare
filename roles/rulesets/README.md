# rulesets

[![License](https://img.shields.io/badge/license-GPLv3-brightgreen.svg?style=flat)](https://www.gnu.org/licenses/gpl-3.0.txt)

Manage cloudflare rulesets

## Requirements

* Cloudflare api `Token` with `Write` permissions to `Account WAF`

## Role Variables

    rulesets_api_token: null
    rulesets_async: 300
    rulesets_batch: 10
    rulesets_delay: 3
    rulesets_list: []
    rulesets_phase: http_request_firewall_custom
    rulesets_poll: 0
    rulesets_retries: 100

## Dependencies

* [zones\_info](../zones_info)

## Example Playbook

    - hosts: cloudflare
      connection: local
      roles:
        - role: linuxhq.cloudflare.rulesets
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
