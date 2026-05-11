# pagerules\_info

[![License](https://img.shields.io/badge/license-GPLv3-brightgreen.svg?style=flat)](https://www.gnu.org/licenses/gpl-3.0.txt)

Gather information about cloudflare pagerules

## Requirements

* Cloudflare api `Token` with `Read` permissions to `Page Rules`

## Role Variables

    pagerules_info_api_token: null

## Return Values

    _pagerules_info_dict
    _pagerules_info_list

## Example Playbook

    - hosts: cloudflare
      connection: local
      roles:
        - role: linuxhq.cloudflare.pagerules_info
          pagerules_info_api_token: '{{ accounts_info_api_token }}'
