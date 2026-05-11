# purge\_cache

[![License](https://img.shields.io/badge/license-GPLv3-brightgreen.svg?style=flat)](https://www.gnu.org/licenses/gpl-3.0.txt)

Manage cloudflare purging of cache

## Requirements

* Cloudflare api `Token` with `Purge` permissions to `Cache Purge`

## Role Variables

    purge_cache_api_token: null
    purge_cache_async: 300
    purge_cache_batch: 10
    purge_cache_delay: 3
    purge_cache_list: []
    purge_cache_poll: 0
    purge_cache_retries: 100

## Dependencies

* [zones\_info](../zones_info)

## Example Playbook

    - hosts: cloudflare
      connection: local
      roles:
        - role: linuxhq.cloudflare.purge_cache
          purge_cache_list:
            - zone_id: "{{ _zones_info_dict['linuxhq.dev'].id }}"
              cache:
                purge_everything: true
