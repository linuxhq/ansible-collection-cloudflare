# access\_policies

[![License](https://img.shields.io/badge/license-GPLv3-brightgreen.svg?style=flat)](https://www.gnu.org/licenses/gpl-3.0.txt)

Manage cloudflare access policies

## Requirements

* Cloudflare api `Token` with `Write` permissions to `Access: Apps and Policies`

## Role Variables

    access_policies_account_id: null
    access_policies_api_token: null
    access_policies_async: 300
    access_policies_batch: 10
    access_policies_delay: 3
    access_policies_list: []
    access_policies_poll: 0
    access_policies_retries: 100

## Dependencies

* [access\_groups\_info](../access_groups_info)
* [access\_identity\_providers\_info](../access_identity_providers_info)

## Example Playbook

    - hosts: cloudflare
      connection: local
      roles:
        - role: linuxhq.cloudflare.access_policies
          access_policies_account_id: "{{ _accounts_info_id }}"
          access_policies_api_token: "{{ accounts_info_api_token }}"
          access_policies_list:
            - name: molecule-00-email
              decision: allow
              include:
                - email:
                    email: email@molecule.org
              require:
                - login_method:
                    id: "{{ _access_identity_providers_info_dict['onetimepin'].id }}"

            - name: molecule-00-group
              decision: non_identity
              include:
                - group:
                    id: "{{ _access_groups_info_dict['molecule-00'].id }}"
