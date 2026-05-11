# cfd\_tunnel

[![License](https://img.shields.io/badge/license-GPLv3-brightgreen.svg?style=flat)](https://www.gnu.org/licenses/gpl-3.0.txt)

Manage cloudflare cfd tunnels

## Requirements

* Cloudflare api `Token` with `Write` permissions to `Cloudflare Tunnel`

## Role Variables

    cfd_tunnel_account_id: null
    cfd_tunnel_api_token: null
    cfd_tunnel_async: 300
    cfd_tunnel_batch: 10
    cfd_tunnel_delay: 3
    cfd_tunnel_list: []
    cfd_tunnel_poll: 0
    cfd_tunnel_retries: 100

## Dependencies

* [accounts\_info](../accounts_info)

## Example Playbook

    - hosts: cloudflare
      connection: local
      roles:
        - role: linuxhq.cloudflare.cfd_tunnel
          cfd_tunnel_list:
            - name: molecule-local
              config_src: local
              tunnel_secret: >-
                YjNhS3ZzQ0puNzNxdFljY0VmbkpGdWlOb3M3dWNxUlJ5YmhVUkx6S2NUNFBZN3k3bUZUb21McnUzd1BhTkh2aQo=

            - name: molecule-remote
              config_src: cloudflare
