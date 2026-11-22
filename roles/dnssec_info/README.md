# dnssec\_info

[![License](https://img.shields.io/badge/license-GPLv3-brightgreen.svg?style=flat)](https://www.gnu.org/licenses/gpl-3.0.txt)

Gather information about cloudflare dnssec settings

See the [Cloudflare API reference](https://developers.cloudflare.com/api/resources/dns/subresources/dnssec/).

## Requirements

| Type | Permission | Value |
| ---- | ---------- | ----- |
| Zone | DNS        | Read  |
| Zone | Zone       | Read  |

## Role Variables

| Variable                | Default | Description                               |
| ----------------------- | ------- | ----------------------------------------- |
| `dnssec_info_api_token` | `null`  | Cloudflare API token; null skips the role |

## Dependencies

None

## Return Values

    _dnssec_info_dict
    _dnssec_info_list

## Example Playbook

    - hosts: cloudflare
      connection: local
      roles:
        - role: linuxhq.cloudflare.dnssec_info
          dnssec_info_api_token: "{{ lookup('env', 'CLOUDFLARE_API_TOKEN') }}"
