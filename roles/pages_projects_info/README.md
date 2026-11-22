# pages\_projects\_info

[![License](https://img.shields.io/badge/license-GPLv3-brightgreen.svg?style=flat)](https://www.gnu.org/licenses/gpl-3.0.txt)

Gather information about cloudflare pages projects

See the [Cloudflare API reference](https://developers.cloudflare.com/api/resources/pages/subresources/projects/).

## Requirements

| Type    | Permission       | Value |
| ------- | ---------------- | ----- |
| Account | Account Settings | Read  |
| Account | Cloudflare Pages | Read  |

## Role Variables

| Variable                         | Default | Description                                |
| -------------------------------- | ------- | ------------------------------------------ |
| `pages_projects_info_account_id` | `null`  | Cloudflare account ID; null skips the role |
| `pages_projects_info_api_token`  | `null`  | Cloudflare API token; null skips the role  |

## Dependencies

* [accounts\_info](../accounts_info)

## Return Values

    _pages_projects_info_dict
    _pages_projects_info_list

## Example Playbook

    - hosts: cloudflare
      connection: local
      roles:
        - role: linuxhq.cloudflare.pages_projects_info
          accounts_info_api_token: "{{ lookup('env', 'CLOUDFLARE_API_TOKEN') }}"
          accounts_info_name: "{{ lookup('env', 'CLOUDFLARE_ACCOUNT_NAME') }}"
          pages_projects_info_account_id: '{{ _accounts_info_id }}'
          pages_projects_info_api_token: '{{ accounts_info_api_token }}'
