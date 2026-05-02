# warp\_connector\_info

[![License](https://img.shields.io/badge/license-GPLv3-brightgreen.svg?style=flat)](https://www.gnu.org/licenses/gpl-3.0.txt)

Gather information about cloudflare warp connectors

## Requirements

* Cloudflare api `Token` with `Read` permissions to `Cloudflare One Connector: WARP`

## Role Variables

    warp_connector_info_account_id: null
    warp_connector_info_api_token: null

## Dependencies

* [linuxhq.cloudflare.accounts\_info](https://github.com/linuxhq/ansible-collection-cloudflare/tree/main/roles/accounts_info)

## Return Values

    _warp_connector_info_dict
    _warp_connector_info_list

## Example Playbook

    - hosts: cloudflare
      connection: local
      roles:
        - role: linuxhq.cloudflare.warp_connector_info
          accounts_info_api_token: m4wxAwXmmLVWyKLwqchybVh9F3LnmTKJtsrheV77
          accounts_info_name: linuxhq
          warp_connector_info_account_id: "{{ _accounts_info_id }}"
          warp_connector_info_api_token: "{{ accounts_info_api_token }}"
