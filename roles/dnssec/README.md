# dnssec

[![License](https://img.shields.io/badge/license-GPLv3-brightgreen.svg?style=flat)](https://www.gnu.org/licenses/gpl-3.0.txt)

Manage cloudflare dnssec settings

See the [Cloudflare API reference](https://developers.cloudflare.com/api/resources/dns/subresources/dnssec/).

## Requirements

| Type | Permission | Value |
| ---- | ---------- | ----- |
| Zone | DNS        | Write |
| Zone | Zone       | Read  |

## Role Variables

| Variable           | Default | Description                                        |
| ------------------ | ------- | -------------------------------------------------- |
| `dnssec_api_token` | `null`  | Cloudflare API token; null skips the role          |
| `dnssec_async`     | `300`   | Seconds each async job may run                     |
| `dnssec_batch`     | `10`    | Items submitted per batch                          |
| `dnssec_delay`     | `3`     | Seconds between job status checks                  |
| `dnssec_list`      | `[]`    | Zone DNSSEC settings to manage                     |
| `dnssec_poll`      | `0`     | Async poll interval; 0 runs jobs in the background |
| `dnssec_retries`   | `100`   | Job status checks before failing                   |

## Dependencies

* [zones\_info](../zones_info)

## Example Playbook

    - hosts: cloudflare
      connection: local
      roles:
        - role: linuxhq.cloudflare.dnssec
          zones_info_api_token: "{{ lookup('env', 'CLOUDFLARE_API_TOKEN') }}"
          dnssec_api_token: '{{ zones_info_api_token }}'
          dnssec_list:
            - zone_id: "{{ _zones_info_dict['molecule.com'].id }}"
              status: active
            - zone_id: "{{ _zones_info_dict['molecule.net'].id }}"
              status: active
            - zone_id: "{{ _zones_info_dict['molecule.org'].id }}"
              status: active
