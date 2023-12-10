# linuxhq.cloudflare

![License](https://img.shields.io/badge/license-GPLv3-lightgreen)
[![Ansible Galaxy](https://img.shields.io/badge/collection-linuxhq.cloudflare-blue)](https://galaxy.ansible.com/linuxhq/cloudflare)
[![Lint](https://github.com/linuxhq/ansible-collection-cloudflare/actions/workflows/linting.yml/badge.svg)](https://github.com/linuxhq/ansible-collection-cloudflare/actions/workflows/linting.yml)
[![Release](https://github.com/linuxhq/ansible-collection-cloudflare/actions/workflows/release.yml/badge.svg)](https://github.com/linuxhq/ansible-collection-cloudflare/actions/workflows/release.yml)

A collection of cloudflare roles

# Collection

## Build

    ansible-galaxy collection build

## Install

    ansible-galaxy collection install linuxhq.cloudflare

# Playbook

An example playbook utilizing roles available to create a cloudflare tunnel

    - hosts: localhost
      connection: local

      vars:
        cf_account_id: "{{ _cf_account_id }}"
        cf_account_name: linuxhq
        cf_auth_token: LYwUWCwe33KWgtRbXUgi9M3EysNixqscjLpbuUfx

      roles:
        - role: linuxhq.cloudflare.zone
          cf_zones:
            - name: linuxhq.net

        - role: linuxhq.cloudflare.tunnel
          cf_tunnels:
            - name: linuxhq-net-tunnel
              config_src: local
              tunnel_secret: ZGtjVXdzRWJramFYVVduYm0zd2VSalhVaE5IZWppNGQ=

        - role: linuxhq.cloudflare.service_token
          cf_service_tokens:
            - name: linuxhq-net-token
              duration: forever

        - role: linuxhq.cloudflare.application
          cf_applications:
            - domain: tunnel.linuxhq.net
              name: linuxhq-net-app
              type: self_hosted

        - role: linuxhq.cloudflare.policy
          cf_policies:
            - application_id: "{{ _cf_application_id['linuxhq-net-app'] }}"
              decision: non_identity
              name: linuxhq-net-policy
              include:
                - service_token:
                    token_id: "{{ _cf_service_token_id['linuxhq-net-token'] }}"

        - role: linuxhq.cloudflare.dns
          cf_dns:
            - zone: linuxhq.net
              records:
                - record: tunnel
                  proxied: true
                  type: CNAME
                  value: "{{ _cf_tunnel_id['linuxhq-net-tunnel'] ~ '.cfargotunnel.com' }}"

# Tokens

The use of these roles will require an api token which can be generated using the link below

* https://dash.cloudflare.com/profile/api-tokens

## Permissions

If you plan to utilize all the roles in this collection you'll need the following permissions

| Type    | Permission                                            | Value |
| ------- | ----------------------------------------------------- | ----- |
| Account | Access: Apps and Policies                             | Edit  |
| Account | Access: Organizations, Identity Providers, and Groups | Edit  |
| Account | Access: Service Tokens                                | Edit  |
| Account | Account Filter Lists                                  | Edit  |
| Account | Account Settings                                      | Read  |
| Account | Cloudflare Tunnel                                     | Edit  |
| Zone    | DNS                                                   | Edit  |
| Zone    | Page Rules                                            | Edit  |
| Zone    | Zone                                                  | Edit  |
| Zone    | Zone Settings                                         | Edit  |
| Zone    | Zone WAF                                              | Edit  |
