# dns

[![License](https://img.shields.io/badge/license-GPLv3-brightgreen.svg?style=flat)](https://www.gnu.org/licenses/gpl-3.0.txt)

Manage cloudflare dns records

See the [Cloudflare API reference](https://developers.cloudflare.com/api/resources/dns/subresources/records/).

## Requirements

| Type    | Permission                     | Value |
| ------- | ------------------------------ | ----- |
| Account | Account Settings               | Read  |
| Account | Cloudflare One Connector: WARP | Read  |
| Account | Cloudflare One Connectors      | Write |
| Account | Cloudflare Tunnel              | Read  |
| Account | Cloudflare Tunnel              | Write |
| Zone    | DNS                            | Write |
| Zone    | Zone                           | Read  |

## Role Variables

| Variable        | Default | Description                                        |
| --------------- | ------- | -------------------------------------------------- |
| `dns_api_token` | `null`  | Cloudflare API token; null skips the role          |
| `dns_async`     | `300`   | Seconds each async job may run                     |
| `dns_batch`     | `10`    | Items submitted per batch                          |
| `dns_delay`     | `3`     | Seconds between job status checks                  |
| `dns_poll`      | `0`     | Async poll interval; 0 runs jobs in the background |
| `dns_records`   | `[]`    | Zones and their DNS records to manage              |
| `dns_retries`   | `100`   | Job status checks before failing                   |

## Dependencies

* [cfd\_tunnel\_info](../cfd_tunnel_info)
* [warp\_connector\_info](../warp_connector_info)

## Example Playbook

    - hosts: cloudflare
      connection: local
      roles:
        - role: linuxhq.cloudflare.dns
          dns_api_token: "{{ lookup('env', 'CLOUDFLARE_API_TOKEN') }}"
          dns_records:
            - zone: molecule.com
              records:
                - record: one
                  comment: Managed by Ansible
                  proxied: true
                  type: A
                  value: 8.8.8.1
                - record: two
                  proxied: false
                  type: A
                  value: 8.8.8.2
                - record: three
                  proxied: true
                  type: A
                  value: 8.8.8.3
                - record: four
                  proxied: false
                  type: A
                  value: 8.8.8.4
                - record: five
                  proxied: true
                  type: A
                  value: 8.8.8.5
                - record: six
                  proxied: false
                  type: A
                  value: 8.8.8.6
                - record: seven
                  proxied: true
                  type: A
                  value: 8.8.8.7
                - record: eight
                  proxied: false
                  type: A
                  value: 8.8.8.8
                - record: nine
                  proxied: true
                  type: A
                  value: 8.8.8.9
                - record: ten
                  proxied: false
                  type: A
                  value: 8.8.8.10
                - record: eleven
                  proxied: true
                  type: A
                  value: 8.8.8.11
                - record: twelve
                  proxied: false
                  type: A
                  value: 8.8.8.12
                - record: thirteen
                  proxied: true
                  type: A
                  value: 8.8.8.13
