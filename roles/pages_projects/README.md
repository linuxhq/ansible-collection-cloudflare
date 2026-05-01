# pages\_projects

[![License](https://img.shields.io/badge/license-GPLv3-brightgreen.svg?style=flat)](https://www.gnu.org/licenses/gpl-3.0.txt)

Manage cloudflare pages projects

Application programming interface -> [projects](https://developers.cloudflare.com/api/resources/pages/subresources/projects/)

## Requirements

* Cloudflare api `Token` with `Write` permissions to `Cloudflare Pages`
* Cloudflare api `Token` with `Write` permissions to `DNS`

## Role Variables

    pages_projects_account_id: null
    pages_projects_api_token: null
    pages_projects_list: []

## Dependencies

* [linuxhq.cloudflare.accounts\_info](https://github.com/linuxhq/ansible-collection-cloudflare/tree/main/roles/accounts_info)

## Example Playbook

    - hosts: cloudflare
      connection: local
      roles:
        - role: linuxhq.cloudflare.pages_projects
          accounts_info_api_token: m4wxAwXmmLVWyKLwqchybVh9F3LnmTKJtsrheV77
          accounts_info_name: linuxhq
          pages_projects_account_id: "{{ _accounts_info_id }}"
          pages_projects_api_token: "{{ accounts_info_api_token }}"
          pages_projects_list:
            - name: linuxhq-dev
              production_branch: main
              domains:
                - name: linuxhq.dev
                  zone: linuxhq.dev
