# dns

[![License](https://img.shields.io/badge/license-GPLv3-brightgreen.svg?style=flat)](https://www.gnu.org/licenses/gpl-3.0.txt)

Manage cloudflare dns records

## Requirements

* Cloudflare api `Token` with `Write` permissions to `DNS`
* Cloudflare api `Token` with `Read` permissions to `Zone`
* Cloudflare api `Token` with `Read` permissions to `Cloudflare Tunnel`
* Cloudflare api `Token` with `Write` permissions to `Cloudflare Tunnel`
* Cloudflare api `Token` with `Read` permissions to `Account Settings`
* Cloudflare api `Token` with `Read` permissions to `Cloudflare One Connector: WARP`
* Cloudflare api `Token` with `Write` permissions to `Cloudflare One Connectors`

## Role Variables

    dns_api_token: null
    dns_async: 300
    dns_batch: 10
    dns_delay: 3
    dns_poll: 0
    dns_records: []
    dns_retries: 100

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
