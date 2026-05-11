# access\_service\_tokens\_info

[![License](https://img.shields.io/badge/license-GPLv3-brightgreen.svg?style=flat)](https://www.gnu.org/licenses/gpl-3.0.txt)

Gather information about cloudflare access service tokens

## Requirements

* Cloudflare api `Token` with `Read` permissions to `Access: Service Tokens`

## Role Variables

    access_service_tokens_info_account_id: null
    access_service_tokens_info_api_token: null

## Dependencies

* [accounts\_info](../accounts_info)

## Return Values

    _access_service_tokens_info_dict
    _access_service_tokens_info_list

## Example Playbook

    - hosts: cloudflare
      connection: local
      roles:
        - role: linuxhq.cloudflare.access_service_tokens_info
          access_service_tokens_info_account_id: '{{ _accounts_info_id }}'
          access_service_tokens_info_api_token: '{{ accounts_info_api_token }}'
