# rules\_lists\_info

[![License](https://img.shields.io/badge/license-GPLv3-brightgreen.svg?style=flat)](https://www.gnu.org/licenses/gpl-3.0.txt)

Gather information about cloudflare rules lists

See the [Cloudflare API reference](https://developers.cloudflare.com/api/resources/rules/subresources/lists/).

## Requirements

| Type    | Permission           | Value |
| ------- | -------------------- | ----- |
| Account | Account Filter Lists | Read  |
| Account | Account Settings     | Read  |

## Role Variables

| Variable                      | Default | Description                                |
| ----------------------------- | ------- | ------------------------------------------ |
| `rules_lists_info_account_id` | `null`  | Cloudflare account ID; null skips the role |
| `rules_lists_info_api_token`  | `null`  | Cloudflare API token; null skips the role  |

## Dependencies

* [accounts\_info](../accounts_info)

## Return Values

    _rules_lists_info_dict
    _rules_lists_info_list

## Example Playbook

    - hosts: cloudflare
      connection: local
      roles:
        - role: linuxhq.cloudflare.rules_lists_info
          accounts_info_api_token: "{{ lookup('env', 'CLOUDFLARE_API_TOKEN') }}"
          accounts_info_name: "{{ lookup('env', 'CLOUDFLARE_ACCOUNT_NAME') }}"
          rules_lists_info_account_id: '{{ _accounts_info_id }}'
          rules_lists_info_api_token: '{{ accounts_info_api_token }}'
