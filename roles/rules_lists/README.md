# rules\_lists

[![License](https://img.shields.io/badge/license-GPLv3-brightgreen.svg?style=flat)](https://www.gnu.org/licenses/gpl-3.0.txt)

Manage cloudflare rules lists

Application programming interface -> [rules](https://developers.cloudflare.com/api/resources/rules/)

## Requirements

* Cloudflare api `Token` with `Edit` permissions to `Account Filter Lists`

## Role Variables

    rules_lists_account_id: null
    rules_lists_api_token: null
    rules_lists_list: []

## Dependencies

* [linuxhq.cloudflare.accounts\_info](https://github.com/linuxhq/ansible-collection-cloudflare/tree/main/roles/accounts_info)

## Example Playbook

    - hosts: cloudflare
      connection: local
      roles:
        - role: linuxhq.cloudflare.rules_lists
          accounts_info_api_token: m4wxAwXmmLVWyKLwqchybVh9F3LnmTKJtsrheV77
          accounts_info_name: linuxhq
          rules_lists_account_id: "{{ _accounts_info_id }}"
          rules_lists_api_token: "{{ accounts_info_api_token }}"
          rules_lists_list:
            - kind: ip
              name: uptime_robot
              elements:
                "{{ lookup('ansible.builtin.url',
                           'https://uptimerobot.com/inc/files/ips/IPv4.txt',
                           wantlist=true) |
                    map('community.general.dict_kv', 'ip') |
                    sort(attribute='ip') }}"
