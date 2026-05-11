# warp\_connector

[![License](https://img.shields.io/badge/license-GPLv3-brightgreen.svg?style=flat)](https://www.gnu.org/licenses/gpl-3.0.txt)

Manage cloudflare warp connectors

## Requirements

* Cloudflare api `Token` with `Write` permissions to `Cloudflare One Connector: WARP`

## Role Variables

    warp_connector_account_id: null
    warp_connector_api_token: null
    warp_connector_async: 300
    warp_connector_batch: 10
    warp_connector_delay: 3
    warp_connector_list: []
    warp_connector_poll: 0
    warp_connector_retries: 100

## Dependencies

* [accounts\_info](../accounts_info)

## Example Playbook

    - hosts: cloudflare
      connection: local
      roles:
        - role: linuxhq.cloudflare.warp_connector
          warp_connector_account_id: '{{ _accounts_info_id }}'
          warp_connector_api_token: '{{ accounts_info_api_token }}'
          warp_connector_list:
            - name: molecule-00
            - name: molecule-01
            - name: molecule-02
            - name: molecule-03
            - name: molecule-04
