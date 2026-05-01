# pages\_projects\_info

[![License](https://img.shields.io/badge/license-GPLv3-brightgreen.svg?style=flat)](https://www.gnu.org/licenses/gpl-3.0.txt)

Gather information about cloudflare pages projects

Application programming interface -> [projects](https://developers.cloudflare.com/api/resources/pages/subresources/projects/)

## Requirements

* Cloudflare api `Token` with `Read` permissions to `Cloudflare Pages`

## Role Variables

    pages_projects_info_account_id: null
    pages_projects_info_api_token: null

## Dependencies

* [linuxhq.cloudflare.accounts\_info](https://github.com/linuxhq/ansible-collection-cloudflare/tree/main/roles/accounts_info)

## Return Values

    _pages_projects_info_dict
    _pages_projects_info_list

## Example Playbook

    - hosts: cloudflare
      connection: local
      roles:
        - role: linuxhq.cloudflare.pages_projects_info
          accounts_info_api_token: m4wxAwXmmLVWyKLwqchybVh9F3LnmTKJtsrheV77
          accounts_info_name: linuxhq
          pages_projects_info_account_id: "{{ _accounts_info_id }}"
          pages_projects_info_api_token: "{{ accounts_info_api_token }}"
