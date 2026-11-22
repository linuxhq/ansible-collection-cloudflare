# zones

[![License](https://img.shields.io/badge/license-GPLv3-brightgreen.svg?style=flat)](https://www.gnu.org/licenses/gpl-3.0.txt)

Manage cloudflare zones

See the [Cloudflare API reference](https://developers.cloudflare.com/api/resources/zones/).

## Requirements

| Type    | Permission       | Value |
| ------- | ---------------- | ----- |
| Account | Account Settings | Read  |
| Zone    | Zone             | Write |
| Zone    | Zone Settings    | Write |

## Role Variables

| Variable           | Default | Description                                           |
| ------------------ | ------- | ----------------------------------------------------- |
| `zones_account_id` | `null`  | Account to create and look up zones in; null omits it |
| `zones_api_token`  | `null`  | Cloudflare API token; null skips the role             |
| `zones_async`      | `300`   | Seconds each async job may run                        |
| `zones_batch`      | `10`    | Items submitted per batch                             |
| `zones_delay`      | `3`     | Seconds between job status checks                     |
| `zones_list`       | `[]`    | Zones to manage                                       |
| `zones_poll`       | `0`     | Async poll interval; 0 runs jobs in the background    |
| `zones_retries`    | `100`   | Job status checks before failing                      |

## Dependencies

* [accounts\_info](../accounts_info)

## Example Playbook

    - hosts: cloudflare
      connection: local
      roles:
        - role: linuxhq.cloudflare.zones
          accounts_info_api_token: "{{ lookup('env', 'CLOUDFLARE_API_TOKEN') }}"
          accounts_info_name: "{{ lookup('env', 'CLOUDFLARE_ACCOUNT_NAME') }}"
          zones_account_id: '{{ _accounts_info_id }}'
          zones_api_token: '{{ accounts_info_api_token }}'
          zones_list:
            - name: molecule.com
              type: full
              settings:
                - id: always_use_https
                  value: "on"
                - id: development_mode
                  value: "on"
                - id: ipv6
                  value: "off"
                - id: min_tls_version
                  value: 1.3
                - id: ssl
                  value: strict
            - name: molecule.net
              type: full
              settings:
                - id: always_use_https
                  value: "on"
                - id: development_mode
                  value: "on"
                - id: ipv6
                  value: "off"
                - id: min_tls_version
                  value: 1.3
                - id: ssl
                  value: strict
            - name: molecule.org
              type: full
              settings:
                - id: always_use_https
                  value: "on"
                - id: development_mode
                  value: "on"
                - id: ipv6
                  value: "off"
                - id: min_tls_version
                  value: 1.3
                - id: ssl
                  value: strict
