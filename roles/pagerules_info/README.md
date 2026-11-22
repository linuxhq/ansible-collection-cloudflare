# pagerules\_info

[![License](https://img.shields.io/badge/license-GPLv3-brightgreen.svg?style=flat)](https://www.gnu.org/licenses/gpl-3.0.txt)

Gather information about cloudflare pagerules

See the [Cloudflare API reference](https://developers.cloudflare.com/api/resources/page_rules/).

## Requirements

| Type | Permission | Value |
| ---- | ---------- | ----- |
| Zone | Page Rules | Read  |
| Zone | Zone       | Read  |

## Role Variables

| Variable                   | Default | Description                                                          |
| -------------------------- | ------- | -------------------------------------------------------------------- |
| `pagerules_info_api_token` | `null`  | Cloudflare API token; null skips the query and publishes empty facts |

## Dependencies

None

## Return Values

    _pagerules_info_dict
    _pagerules_info_list

## Example Playbook

    - hosts: cloudflare
      connection: local
      roles:
        - role: linuxhq.cloudflare.pagerules_info
          pagerules_info_api_token: "{{ lookup('env', 'CLOUDFLARE_API_TOKEN') }}"
