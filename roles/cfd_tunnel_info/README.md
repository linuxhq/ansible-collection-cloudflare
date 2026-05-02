# cfd\_tunnel\_info

[![License](https://img.shields.io/badge/license-GPLv3-brightgreen.svg?style=flat)](https://www.gnu.org/licenses/gpl-3.0.txt)

Gather information about cloudflare cfd tunnels

## Requirements

* Cloudflare api `Token` with `Read` permissions to `Cloudflare Tunnel`

## Role Variables

    cfd_tunnel_info_account_id: null
    cfd_tunnel_info_api_token: null

## Dependencies

* [linuxhq.cloudflare.accounts\_info](https://github.com/linuxhq/ansible-collection-cloudflare/tree/main/roles/accounts_info)

## Return Values

    _cfd_tunnel_info_dict
    _cfd_tunnel_info_list

## Example Playbook

    - hosts: cloudflare
      connection: local
      roles:
        - role: linuxhq.cloudflare.cfd_tunnel_info
          accounts_info_api_token: m4wxAwXmmLVWyKLwqchybVh9F3LnmTKJtsrheV77
          accounts_info_name: linuxhq
          cfd_tunnel_info_account_id: "{{ _accounts_info_id }}"
          cfd_tunnel_info_api_token: "{{ accounts_info_api_token }}"
