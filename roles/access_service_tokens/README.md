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

* [accounts\_info](../accounts_info)

## Example Playbook

    - hosts: cloudflare
      connection: local
      roles:
        - role: linuxhq.cloudflare.access_service_tokens
          access_service_tokens_list:
            - name: molecule-00
              duration: forever
            - name: molecule-01
              duration: forever
            - name: molecule-02
              duration: forever
            - name: molecule-03
              duration: forever
            - name: molecule-04
              duration: forever
            - name: molecule-05
              duration: forever
            - name: molecule-06
              duration: forever
            - name: molecule-07
              duration: forever
            - name: molecule-08
              duration: forever
            - name: molecule-09
              duration: forever
            - name: molecule-10
              duration: forever
            - name: molecule-11
              duration: forever
