# dns

[![License](https://img.shields.io/badge/license-GPLv3-brightgreen.svg?style=flat)](https://www.gnu.org/licenses/gpl-3.0.txt)

Manage cloudflare dns records

## Requirements

* Cloudflare api `Token` with `Write` permissions to `DNS`

## Role Variables

    dns_api_token: null
    dns_async: 300
    dns_batch: 10
    dns_delay: 3
    dns_poll: 0
    dns_records: []
    dns_retries: 100

## Dependencies

* [linuxhq.cloudflare.cfd\_tunnel\_info](https://github.com/linuxhq/ansible-collection-cloudflare/tree/main/roles/cfd_tunnel_info)
* [linuxhq.cloudflare.warp\_connector\_info](https://github.com/linuxhq/ansible-collection-cloudflare/tree/main/roles/warp_connector_info)

## Example Playbook

    - hosts: cloudflare
      connection: local
      roles:
        - role: linuxhq.cloudflare.dns
          dns_api_token: m4wxAwXmmLVWyKLwqchybVh9F3LnmTKJtsrheV77
          dns_records:
            - zone: linuxhq.dev
              records:
                - record: ansible
                  proxied: false
                  type: CNAME
                  value: ansible.com
