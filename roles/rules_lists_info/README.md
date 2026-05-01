# rules\_lists\_info

[![License](https://img.shields.io/badge/license-GPLv3-brightgreen.svg?style=flat)](https://www.gnu.org/licenses/gpl-3.0.txt)

Gather information about cloudflare rules lists

Application programming interface -> [rules](https://developers.cloudflare.com/api/resources/rules/)

## Requirements

* Cloudflare api `Token` with `Read` permissions to `Account Filter Lists`

## Role Variables

    rules_lists_info_account_id: null
    rules_lists_info_api_token: null

## Dependencies

* [linuxhq.cloudflare.accounts\_info](https://github.com/linuxhq/ansible-collection-cloudflare/tree/main/roles/accounts_info)

## Return Values

    _rules_lists_info_dict
    _rules_lists_info_list

## Example Playbook

    - hosts: cloudflare
      connection: local
      roles:
        - role: linuxhq.cloudflare.rules_lists_info
          accounts_info_api_token: m4wxAwXmmLVWyKLwqchybVh9F3LnmTKJtsrheV77
          accounts_info_name: linuxhq
          rules_lists_info_account_id: "{{ _accounts_info_id }}"
          rules_lists_info_api_token: "{{ accounts_info_api_token }}"
