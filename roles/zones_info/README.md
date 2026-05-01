# zones\_info

[![License](https://img.shields.io/badge/license-GPLv3-brightgreen.svg?style=flat)](https://www.gnu.org/licenses/gpl-3.0.txt)

Gather information about cloudflare zones

Application programming interface -> [zones](https://developers.cloudflare.com/api/resources/zones/)

## Requirements

* Cloudflare api `Token` with `Read` permissions to `Zone`

## Role Variables

    zones_info_api_token: null
    zones_info_match: all
    zones_info_page: 1
    zones_info_per_page: 20

## Return Values

    _zones_info_dict
    _zones_info_list

## Example Playbook

    - hosts: cloudflare
      connection: local
      roles:
        - role: linuxhq.cloudflare.zones_info
          zones_info_api_token: m4wxAwXmmLVWyKLwqchybVh9F3LnmTKJtsrheV77
