# pages\_projects

[![License](https://img.shields.io/badge/license-GPLv3-brightgreen.svg?style=flat)](https://www.gnu.org/licenses/gpl-3.0.txt)

Manage cloudflare pages projects

## Requirements

* Cloudflare api `Token` with `Write` permissions to `Cloudflare Pages`

## Role Variables

    pages_projects_account_id: null
    pages_projects_api_token: null
    pages_projects_async: 300
    pages_projects_batch: 10
    pages_projects_delay: 3
    pages_projects_list: []
    pages_projects_poll: 0
    pages_projects_retries: 100

## Dependencies

* [accounts\_info](../accounts_info)

## Example Playbook

    - hosts: cloudflare
      connection: local
      roles:
        - role: linuxhq.cloudflare.pages_projects
          pages_projects_account_id: '{{ _accounts_info_id }}'
          pages_projects_api_token: '{{ accounts_info_api_token }}'
          pages_projects_list:
            - name: molecule-com
              production_branch: main
              domains:
                - name: molecule.com
            - name: molecule-net
              production_branch: main
              domains:
                - name: molecule.net
            - name: molecule-org
              production_branch: main
              domains:
                - name: molecule.org
