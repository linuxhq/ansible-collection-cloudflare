# dnssec\_info

[![License](https://img.shields.io/badge/license-GPLv3-brightgreen.svg?style=flat)](https://www.gnu.org/licenses/gpl-3.0.txt)

Gather information about cloudflare dnssec settings

## Requirements

* Cloudflare api `Token` with `Read` permissions to `Zone`
* Cloudflare api `Token` with `Read` permissions to `DNS`

## Role Variables

    dnssec_info_api_token: null

## Return Values

    _dnssec_info_dict
    _dnssec_info_list

## Example Playbook

    - hosts: cloudflare
      connection: local
      roles:
        - linuxhq.cloudflare.dnssec_info
