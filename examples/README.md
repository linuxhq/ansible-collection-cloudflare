# linuxhq.cloudflare

This document outlines the steps to execute the example playbooks

# Playbooks

* build.yml
* destroy.yml
* info.yml

# Environment

Setup the following environment variables

   export ANSIBLE_INVENTORY=hosts
   export CLOUDFLARE_ACCOUNT_NAME=your.account.name
   export CLOUDFLARE_API_TOKEN=your.account.token
   export CLOUDFLARE_DOMAIN=your.domain.com

# Inventory

Inventory can be found (here)[group_vars/cdn]

## Build

To configure all services supported by this collection

    ansible-playbook playbooks/build.yml

To configure individual services (tag: role\_name)

    ansible-playbook playbooks/build.yml -t cfd_tunnel

## Destroy

To destroy all service configurations supported by this collection

    ansible-playbook playbooks/destroy.yml

## Info

To gather inforamtion for all services supported by this collection

    ansible-playbook playbooks/info.yml

To gather information for individual services (tag: role\_name)

    ansible-playbook playbooks/info.yml -t cfd_tunnel_info
