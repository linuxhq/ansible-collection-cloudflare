# linuxhq.cloudflare

This document outlines the steps to execute the example playbooks

# Playbooks

* `build.yml`
* `destroy.yml`
* `info.yml`

# Environment

Define and export the following environment variables

* `CLOUDFLARE_ACCOUNT_NAME`
* `CLOUDFLARE_API_TOKEN`
* `CLOUDFLARE_DOMAIN`

Command-line examples

    export CLOUDFLARE_ACCOUNT_NAME=linuxhq
    export CLOUDFLARE_API_TOKEN=7f15527b20d04645e27dd16eb8e350c0
    export CLOUDFLARE_DOMAIN=linuxhq.dev

# Inventory

Ansible inventory variables can be found [here](group_vars/cdn)

# Execute

## Build

To configure all services supported by this collection

    ansible-playbook playbooks/build.yml

To configure individual services (tag: role\_name)

    ansible-playbook playbooks/build.yml -t cfd_tunnel

## Destroy

To destroy all service configurations supported by this collection

    ansible-playbook playbooks/destroy.yml

To destroy all service configurations while keeping the zone

    ansible-playbook playbooks/destroy.yml --skip-tags zones

## Info

To gather information for all services supported by this collection

    ansible-playbook playbooks/info.yml

To gather information for individual services (tag: role\_name)

    ansible-playbook playbooks/info.yml -t cfd_tunnel_info
