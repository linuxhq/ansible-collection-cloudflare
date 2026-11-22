# purge\_cache

[![License](https://img.shields.io/badge/license-GPLv3-brightgreen.svg?style=flat)](https://www.gnu.org/licenses/gpl-3.0.txt)

Manage cloudflare purging of cache

See the [Cloudflare API reference](https://developers.cloudflare.com/api/resources/cache/).

## Requirements

| Type | Permission  | Value |
| ---- | ----------- | ----- |
| Zone | Cache Purge | Purge |
| Zone | Zone        | Read  |

## Role Variables

| Variable                | Default | Description                                        |
| ----------------------- | ------- | -------------------------------------------------- |
| `purge_cache_api_token` | `null`  | Cloudflare API token; null skips the role          |
| `purge_cache_async`     | `300`   | Seconds each async job may run                     |
| `purge_cache_batch`     | `10`    | Items submitted per batch                          |
| `purge_cache_delay`     | `3`     | Seconds between job status checks                  |
| `purge_cache_list`      | `[]`    | Cache purges to run                                |
| `purge_cache_poll`      | `0`     | Async poll interval; 0 runs jobs in the background |
| `purge_cache_retries`   | `100`   | Job status checks before failing                   |

## Dependencies

* [zones\_info](../zones_info)

## Example Playbook

    - hosts: cloudflare
      connection: local
      roles:
        - role: linuxhq.cloudflare.purge_cache
          zones_info_api_token: "{{ lookup('env', 'CLOUDFLARE_API_TOKEN') }}"
          purge_cache_api_token: '{{ zones_info_api_token }}'
          purge_cache_list:
            - zone_id: "{{ _zones_info_dict['molecule.com'].id }}"
              cache:
                purge_everything: true
