# linuxhq.cloudflare

[![Ansible Galaxy](https://img.shields.io/badge/collection-linuxhq.cloudflare-blue)](https://galaxy.ansible.com/linuxhq/cloudflare)

A collection of cloudflare roles

# Collection

## Build

    ansible-galaxy collection build

## Install

    ansible-galaxy collection install linuxhq.cloudflare

# Playbook

An example playbook utilizing all roles available in this collection

    - hosts: localhost
      connection: local

      vars:
        cf_account_id: "{{ _cf_account_id }}"
        cf_account_name: linuxhq
        cf_auth_token: LYwUWCwe33KWgtRbXUgi9M3EysNixqscjLpbuUfx
        cf_dns:
          - zone: linuxhq.net
            records:
              - record: tkimball
                proxied: false
                type: CNAME
                value: ansible.com
        cf_ipv6:
          - zone_identifier: "{{ _cf_zone_id['linuxhq.net'] }}"
            value: off
        cf_rule_lists:
          - kind: ip
            name: cloudflare
            ips:
              - ip: 1.1.1.1/32
              - ip: 1.1.1.2/32
        cf_zones:
          - name: linuxhq.net

      roles:
        - linuxhq.cloudflare.zone
        - linuxhq.cloudflare.dns
        - linuxhq.cloudflare.ipv6
        - linuxhq.cloudflare.rule_list

# Tokens

The use of these roles will require an api token which can be generated using the link below

* https://dash.cloudflare.com/profile/api-tokens

## Permissions

If you plan to utilize all the roles in this collection you'll need the following permissions

| Type    | Permission           | Value |
| ------- | -------------------- | ----- |
| Account | Account Filter Lists | Edit  |
| Account | Account Settings     | Read  |
| Zone    | DNS                  | Edit  |
| Zone    | Zone                 | Edit  |
| Zone    | Zone Settings        | Edit  |
