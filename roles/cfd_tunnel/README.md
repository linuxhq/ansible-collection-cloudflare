# cfd\_tunnel

[![License](https://img.shields.io/badge/license-GPLv3-brightgreen.svg?style=flat)](https://www.gnu.org/licenses/gpl-3.0.txt)

Manage cloudflare cfd tunnels

Application programming interface -> [tunnels](https://developers.cloudflare.com/api/resources/zero_trust/subresources/tunnels/)

## Requirements

* Cloudflare api `Token` with `Write` permissions to `Cloudflare Tunnel`

## Role Variables

    cfd_tunnel_account_id: null
    cfd_tunnel_api_token: null
    cfd_tunnel_list: []

## Dependencies

* [linuxhq.cloudflare.accounts\_info](https://github.com/linuxhq/ansible-collection-cloudflare/tree/main/roles/accounts_info)

## Example Playbook

    - hosts: cloudflare
      connection: local
      roles:
        - role: linuxhq.cloudflare.cfd_tunnel
          accounts_info_api_token: m4wxAwXmmLVWyKLwqchybVh9F3LnmTKJtsrheV77
          accounts_info_name: linuxhq
          cfd_tunnel_account_id: "{{ _accounts_info_id }}"
          cfd_tunnel_api_token: "{{ accounts_info_api_token }}"
          cfd_tunnel_list:
            - name: linuxhq.dev-local
              config_src: local
              tunnel_secret: YjNhS3ZzQ0puNzNxdFljY0VmbkpGdWlOb3M3dWNxUlJ5YmhVUkx6S2NUNFBZN3k3bUZUb21McnUzd1BhTkh2aQo=

            - name: linuxhq.dev-remote
              config_src: cloudflare
