# pagerules\_info

[![License](https://img.shields.io/badge/license-GPLv3-brightgreen.svg?style=flat)](COPYING)

Gather information about cloudflare pagerules

Application programming interface -> [pagerules](https://developers.cloudflare.com/api/resources/page_rules/)

## Requirements

* Cloudflare api `Token` with `View` permissions to `Zone Settings`

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
          pagerules_info_api_token: m4wxAwXmmLVWyKLwqchybVh9F3LnmTKJtsrheV77

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
