# pages\_projects\_info

[![License](https://img.shields.io/badge/license-GPLv3-brightgreen.svg?style=flat)](https://www.gnu.org/licenses/gpl-3.0.txt)

Gather information about cloudflare pages projects

## Requirements

* Cloudflare api `Token` with `Read` permissions to `Cloudflare Pages`

## Role Variables

    pages_projects_info_account_id: null
    pages_projects_info_api_token: null

## Dependencies

* [accounts\_info](../accounts_info)

## Return Values

    _pages_projects_info_dict
    _pages_projects_info_list

## Example Playbook

    - hosts: cloudflare
      connection: local
      roles:
        - linuxhq.cloudflare.pages_projects_info
