# cfd\_tunnel\_configurations\_info

[![License](https://img.shields.io/badge/license-GPLv3-brightgreen.svg?style=flat)](https://www.gnu.org/licenses/gpl-3.0.txt)

Gather information cloudflare cfd tunnel configurations

## Requirements

* Cloudflare api `Token` with `Read` permissions to `Cloudflare Tunnel`

## Role Variables

    cfd_tunnel_configurations_info_account_id: null
    cfd_tunnel_configurations_info_api_token: null

## Dependencies

* [linuxhq.cloudflare.accounts\_info](https://github.com/linuxhq/ansible-collection-cloudflare/tree/main/roles/accounts_info)

## Example Playbook

    - hosts: cloudflare
      connection: local
      roles:
        - role: linuxhq.cloudflare.cfd_tunnel_configurations_info
          accounts_info_api_token: m4wxAwXmmLVWyKLwqchybVh9F3LnmTKJtsrheV77
          accounts_info_name: linuxhq
          cfd_tunnel_configurations_info_account_id: "{{ _accounts_info_id }}"
          cfd_tunnel_configurations_info_api_token: "{{ accounts_info_api_token }}"
