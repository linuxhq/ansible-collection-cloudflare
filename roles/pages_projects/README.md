# pages\_projects

[![License](https://img.shields.io/badge/license-GPLv3-brightgreen.svg?style=flat)](https://www.gnu.org/licenses/gpl-3.0.txt)

Manage cloudflare pages projects

See the [Cloudflare API reference](https://developers.cloudflare.com/api/resources/pages/subresources/projects/).

## Requirements

| Type    | Permission       | Value |
| ------- | ---------------- | ----- |
| Account | Account Settings | Read  |
| Account | Cloudflare Pages | Write |

## Role Variables

| Variable                    | Default | Description                                        |
| --------------------------- | ------- | -------------------------------------------------- |
| `pages_projects_account_id` | `null`  | Cloudflare account ID; null skips the role         |
| `pages_projects_api_token`  | `null`  | Cloudflare API token; null skips the role          |
| `pages_projects_async`      | `300`   | Seconds each async job may run                     |
| `pages_projects_batch`      | `10`    | Items submitted per batch                          |
| `pages_projects_delay`      | `3`     | Seconds between job status checks                  |
| `pages_projects_list`       | `[]`    | Pages projects to manage                           |
| `pages_projects_poll`       | `0`     | Async poll interval; 0 runs jobs in the background |
| `pages_projects_retries`    | `100`   | Job status checks before failing                   |

## Dependencies

* [accounts\_info](../accounts_info)

## Example Playbook

    - hosts: cloudflare
      connection: local
      roles:
        - role: linuxhq.cloudflare.pages_projects
          accounts_info_api_token: "{{ lookup('env', 'CLOUDFLARE_API_TOKEN') }}"
          accounts_info_name: "{{ lookup('env', 'CLOUDFLARE_ACCOUNT_NAME') }}"
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
