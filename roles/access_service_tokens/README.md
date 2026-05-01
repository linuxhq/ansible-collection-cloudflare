# access\_service\_tokens

[![License](https://img.shields.io/badge/license-GPLv3-brightgreen.svg?style=flat)](https://www.gnu.org/licenses/gpl-3.0.txt)

Manage cloudflare access service tokens

## Requirements

* Cloudflare api `Token` with `Write` permissions to `Access: Service Tokens`

## Role Variables

    access_service_tokens_account_id: null
    access_service_tokens_api_token: null
    access_service_tokens_async: 300
    access_service_tokens_batch: 10
    access_service_tokens_delay: 3
    access_service_tokens_display: true
    access_service_tokens_list: []
    access_service_tokens_poll: 0
    access_service_tokens_retries: 100

## Dependencies

* [linuxhq.cloudflare.accounts\_info](https://github.com/linuxhq/ansible-collection-cloudflare/tree/main/roles/accounts_info)

## Example Playbook

    - hosts: cloudflare
      connection: local
      roles:
        - role: linuxhq.cloudflare.access_service_tokens
          accounts_info_api_token: m4wxAwXmmLVWyKLwqchybVh9F3LnmTKJtsrheV77
          accounts_info_name: linuxhq
          access_service_tokens_account_id: "{{ _accounts_info_id }}"
          access_service_tokens_api_token: "{{ accounts_info_api_token }}"
          access_service_tokens_list:
            - name: linuxhq.dev
              duration: forever
