# rulesets

[![License](https://img.shields.io/badge/license-GPLv3-brightgreen.svg?style=flat)](https://www.gnu.org/licenses/gpl-3.0.txt)

Manage cloudflare rulesets

See the [Cloudflare API reference](https://developers.cloudflare.com/api/resources/rulesets/).

## Requirements

| Type    | Permission  | Value |
| ------- | ----------- | ----- |
| Account | Account WAF | Write |
| Zone    | Zone        | Read  |

## Role Variables

| Variable             | Default                        | Description                                        |
| -------------------- | ------------------------------ | -------------------------------------------------- |
| `rulesets_api_token` | `null`                         | Cloudflare API token; null skips the role          |
| `rulesets_async`     | `300`                          | Seconds each async job may run                     |
| `rulesets_batch`     | `10`                           | Items submitted per batch                          |
| `rulesets_delay`     | `3`                            | Seconds between job status checks                  |
| `rulesets_list`      | `[]`                           | Zone rulesets to manage                            |
| `rulesets_phase`     | `http_request_firewall_custom` | Ruleset phase to manage                            |
| `rulesets_poll`      | `0`                            | Async poll interval; 0 runs jobs in the background |
| `rulesets_retries`   | `100`                          | Job status checks before failing                   |

## Dependencies

* [zones\_info](../zones_info)

## Example Playbook

    - hosts: cloudflare
      connection: local
      roles:
        - role: linuxhq.cloudflare.rulesets
          zones_info_api_token: "{{ lookup('env', 'CLOUDFLARE_API_TOKEN') }}"
          rulesets_api_token: '{{ zones_info_api_token }}'
          rulesets_list:
            - zone_id: "{{ _zones_info_dict['molecule.com'].id }}"
              name: default
              rules:
                - action: block
                  description: US
                  enabled: true
                  expression: (ip.geoip.country ne "US")
                - action: block
                  description: Known Bots
                  enabled: true
                  expression: (cf.client.bot)
