# accounts\_info

[![License](https://img.shields.io/badge/license-GPLv3-brightgreen.svg?style=flat)](https://www.gnu.org/licenses/gpl-3.0.txt)

Gather information about cloudflare accounts

Application programming interface -> [accounts](https://developers.cloudflare.com/api/resources/accounts/)

## Requirements

* Cloudflare api `Token` with `Read` permissions to `Account Settings`

## Role Variables

    accounts_info_api_token: null
    accounts_info_name: null

## Return Values

    _accounts_info_id
    _accounts_info_name
    _accounts_info_settings
    _accounts_info_type

## Example Playbook

    - hosts: cloudflare
      connection: local
      roles:
        - role: linuxhq.cloudflare.accounts_info
          accounts_info_api_token: m4wxAwXmmLVWyKLwqchybVh9F3LnmTKJtsrheV77
          accounts_info_name: linuxhq
