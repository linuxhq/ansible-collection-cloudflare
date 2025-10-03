# tunnel\_info

[![License](https://img.shields.io/badge/license-GPLv3-brightgreen.svg?style=flat)](COPYING)

Gather information about cloudflare tunnels

## Requirements

* For basic tunnel details, you need Cloudflare api `Token` with `Read` permissions to `Cloudflare Tunnel`
* To fetch tunnel tokens (`cf_fetch_tunnel_token: true`), you need Cloudflare api `Token` with `Edit` permissions to `Cloudflare Tunnel`

## Role Variables

Available variables are listed below, along with default values:

    cf_account_id: null
    cf_auth_token: null
    cf_fetch_tunnel_token: false
    cf_tunnel_names: []
    # If the dict above is empty (default), all tunnel tokens will be fetched

## Dependencies

* [linuxhq.cloudflare.account_info](https://github.com/linuxhq/ansible-collection-cloudflare/tree/main/roles/account_info)

## Return Values

    _cf_tunnel_account_tag
    _cf_tunnel_connections
    _cf_tunnel_id
    _cf_tunnel_remote_config
    _cf_tunnel_status
    _cf_tunnel_token
    _cf_tunnel_type

## Example Playbook

    - hosts: cloudflare
      connection: local
      
      vars:
        my_tunnel: "name-of-your-specific-tunnel"

      roles:
        - role: linuxhq.cloudflare.tunnel_info
          cf_account_id: "{{ _cf_account_id }}"
          cf_auth_token: LYwUWCwe33KWgtRbXUgi9M3EysNixqscjLpbuUfx
          cf_fetch_tunnel_token: true
          # prefilter tunnel token fetching based on names
          cf_tunnel_names:
            - "{{ cf_tunnel_names }}"

## License

Copyright (c) Linux HeadQuarters

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program. If not, see <http://www.gnu.org/licenses/>.
