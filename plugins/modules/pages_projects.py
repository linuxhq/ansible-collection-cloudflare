#!/usr/bin/python

# Copyright: (c) 2026, Taylor Kimball
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import absolute_import, division, print_function

__metaclass__ = type

DOCUMENTATION = r"""
---
module: pages_projects
short_description: Manage Cloudflare Pages projects
description:
- Create, update, and delete Cloudflare Pages projects by name.
- Optionally ensures listed custom domains are attached to the project.
author:
- Taylor Kimball (@tkimball83)
options:
  account_id:
    required: true
    type: str
    description:
    - Cloudflare account identifier.
  api_token:
    required: true
    type: str
    description:
    - Cloudflare API token.
  name:
    required: true
    type: str
    description:
    - Resource name.
  production_branch:
    type: str
    description:
    - Production branch.
  build_config:
    type: dict
    description:
    - Build config.
  deployment_configs:
    type: dict
    description:
    - Deployment configs.
  source:
    type: dict
    description:
    - Source.
  domains:
    type: list
    elements: dict
    description:
    - Domains.
  state:
    type: str
    choices:
    - present
    - absent
    default: present
    description:
    - Desired state of the resource.
requirements:
- python >= 3.9
- cloudflare >= 4.3.1, < 5

"""

EXAMPLES = r"""
- name: Ensure Pages project exists
  linuxhq.cloudflare.pages_projects:
    account_id: "{{ account_id }}"
    api_token: "{{ cloudflare_api_token }}"
    name: docs
    production_branch: main
"""

RETURN = r"""
---
pages_project:
  description: Cloudflare Pages project.
  returned: when available
  type: dict
domains:
  description: Managed custom domains.
  returned: when domains were requested
  type: list
  elements: dict
message:
  returned: always
  type: str
  description:
  - Operation summary.

"""

from ansible.module_utils.basic import AnsibleModule

from ansible_collections.linuxhq.cloudflare.plugins.module_utils.cloudflare_utils import (
    cloudflare_client,
    delete_result,
    find_by_field,
    get_result,
    patch_result,
    payload_from_params,
    post_result,
    values_differ,
)

FIELDS = ("build_config", "deployment_configs", "name", "production_branch", "source")


def comparable_current(current, payload):
    return {field: current.get(field) for field in payload.keys()}


def current_domain_names(project, domains):
    names = set(project.get("domains") or [])
    for domain in domains:
        if isinstance(domain, dict) and domain.get("name") is not None:
            names.add(domain["name"])
    return names


def desired_domain_names(domains):
    return [
        domain["name"]
        for domain in domains or []
        if isinstance(domain, dict) and domain.get("name") is not None
    ]


def domain_item_endpoint(account_id, project_name, domain_name):
    return "%s/%s" % (domains_endpoint(account_id, project_name), domain_name)


def domains_endpoint(account_id, project_name):
    return "%s/domains" % item_endpoint(account_id, project_name)


def endpoint(account_id):
    return "/accounts/%s/pages/projects" % account_id


def item_endpoint(account_id, project_name):
    return "%s/%s" % (endpoint(account_id), project_name)


def main():
    module = AnsibleModule(
        argument_spec={
            "account_id": {"required": True, "type": "str"},
            "api_token": {"required": True, "type": "str", "no_log": True},
            "name": {"required": True, "type": "str"},
            "production_branch": {"type": "str"},
            "build_config": {"type": "dict"},
            "deployment_configs": {"type": "dict"},
            "source": {"type": "dict"},
            "domains": {"type": "list", "elements": "dict"},
            "state": {
                "type": "str",
                "choices": ["present", "absent"],
                "default": "present",
            },
        },
        supports_check_mode=True,
    )

    params = module.params
    with cloudflare_client(module) as client:
        current = find_by_field(
            client, endpoint(params["account_id"]), "name", params["name"]
        )
        domain_names = desired_domain_names(params.get("domains"))

        if params["state"] == "absent":
            if current is None:
                module.exit_json(changed=False, message="Pages project already absent")
            if module.check_mode:
                module.exit_json(
                    changed=True,
                    message="Pages project would be deleted",
                    pages_project=current,
                )
            existing_domains = get_result(
                client,
                domains_endpoint(params["account_id"], params["name"]),
                default=[],
            )
            existing_names = current_domain_names(current, existing_domains)
            for domain_name in domain_names:
                if domain_name in existing_names:
                    delete_result(
                        client,
                        domain_item_endpoint(
                            params["account_id"], params["name"], domain_name
                        ),
                    )
            delete_result(client, item_endpoint(params["account_id"], params["name"]))
            module.exit_json(
                changed=True,
                message="Pages project deleted",
                pages_project=current,
            )

        if current is None and not params.get("production_branch"):
            module.fail_json(
                msg="production_branch is required when creating a Pages project"
            )

        payload = payload_from_params(params, FIELDS)
        changed = False
        domains_changed = False
        managed_domains = []

        if current is None:
            if module.check_mode:
                module.exit_json(changed=True, message="Pages project would be created")
            current = post_result(client, endpoint(params["account_id"]), payload)
            changed = True
        elif values_differ(comparable_current(current, payload), payload):
            if module.check_mode:
                module.exit_json(
                    changed=True,
                    message="Pages project would be updated",
                    pages_project=current,
                )
            current = patch_result(
                client, item_endpoint(params["account_id"], params["name"]), payload
            )
            changed = True

        if domain_names:
            existing_domains = get_result(
                client,
                domains_endpoint(params["account_id"], params["name"]),
                default=[],
            )
            existing_names = current_domain_names(current, existing_domains)
            missing_domains = [
                domain_name
                for domain_name in domain_names
                if domain_name not in existing_names
            ]
            domains_changed = bool(missing_domains)
            if module.check_mode and domains_changed:
                module.exit_json(
                    changed=True,
                    message="Pages project domains would be updated",
                    pages_project=current,
                )
            for domain_name in missing_domains:
                managed_domains.append(
                    post_result(
                        client,
                        domains_endpoint(params["account_id"], params["name"]),
                        {"name": domain_name},
                    )
                )

        if not changed and not domains_changed:
            module.exit_json(
                changed=False,
                message="Pages project already present",
                pages_project=current,
            )

        module.exit_json(
            changed=True,
            message="Pages project updated",
            pages_project=current,
            domains=managed_domains,
        )


if __name__ == "__main__":
    main()
