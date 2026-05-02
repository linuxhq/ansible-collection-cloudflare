# access\_policies\_info

[![License](https://img.shields.io/badge/license-GPLv3-brightgreen.svg?style=flat)](https://www.gnu.org/licenses/gpl-3.0.txt)

Gather information about cloudflare access policies

## Requirements

* Cloudflare api `Token` with `Read` permissions to `Access: Apps and Policies`

## Role Variables

    access_policies_info_account_id: null
    access_policies_info_api_token: null

## Dependencies

* [linuxhq.cloudflare.accounts\_info](https://github.com/linuxhq/ansible-collection-cloudflare/tree/main/roles/accounts_info)

## Return Values

    _access_policies_info_dict
    _access_policies_info_list

## Example Playbook

    - hosts: cloudflare
      connection: local
      roles:
        - role: linuxhq.cloudflare.access_policies_info
          accounts_info_api_token: m4wxAwXmmLVWyKLwqchybVh9F3LnmTKJtsrheV77
          accounts_info_name: linuxhq
          access_policies_info_account_id: "{{ _accounts_info_id }}"
          access_policies_info_api_token: "{{ accounts_info_api_token }}"
