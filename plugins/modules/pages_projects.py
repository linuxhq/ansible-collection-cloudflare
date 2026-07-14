#!/usr/bin/python

# Copyright: (c) 2026, Taylor Kimball
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import absolute_import, division, print_function

__metaclass__ = type

DOCUMENTATION = r"""
---
module: pages_projects
short_description: Manage cloudflare pages projects
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
    - Required when creating a new Pages project.
  build_config:
    type: dict
    description:
    - Build config.
  deployment_configs:
    type: dict
    description:
    - Deployment configs.
    - Values of C(secret_text) variables are write-only; changes to them are not
      detected and they are only resent when another change triggers an update.
    - Use C(rotate_secrets) to force an update that resends secret values.
    - Environment variables removed from C(env_vars) are deleted from the
      project.
  rotate_secrets:
    type: bool
    default: false
    description:
    - Force an update that resends C(deployment_configs), including C(secret_text)
      values, even when no other change is detected.
    - Use to rotate secrets; the module always reports C(changed) when enabled.
  source:
    type: dict
    description:
    - Source.
  domains:
    type: list
    elements: dict
    description:
    - Domains.
    - Each entry requires a C(name).
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

import copy

from ansible.module_utils.basic import AnsibleModule

from ansible_collections.linuxhq.cloudflare.plugins.module_utils.cloudflare_utils import (
    cloudflare_client,
    delete_result,
    get_result,
    list_all,
    normalize_current_by_desired_fields,
    patch_result,
    payload_from_params,
    post_result,
    select_fields,
    values_differ,
)

FIELDS = ("build_config", "deployment_configs", "name", "production_branch", "source")


def comparable_payload(payload):
    comparable = copy.deepcopy(payload)
    configs = comparable.get("deployment_configs")
    if not isinstance(configs, dict):
        return comparable

    for environment in configs.values():
        if not isinstance(environment, dict):
            continue

        env_vars = environment.get("env_vars")
        if not isinstance(env_vars, dict):
            continue

        for variable in env_vars.values():
            if isinstance(variable, dict) and variable.get("type") == "secret_text":
                variable.pop("value", None)

    return comparable


def payload_with_removed_env_vars(payload, current):
    merged = copy.deepcopy(payload)
    configs = merged.get("deployment_configs")
    current_configs = (
        current.get("deployment_configs") if isinstance(current, dict) else None
    )
    if not isinstance(configs, dict) or not isinstance(current_configs, dict):
        return merged

    for environment, desired_env in configs.items():
        if not isinstance(desired_env, dict):
            continue

        desired_vars = desired_env.get("env_vars")
        current_env = current_configs.get(environment)
        current_vars = (
            current_env.get("env_vars") if isinstance(current_env, dict) else None
        )
        if not isinstance(desired_vars, dict) or not isinstance(current_vars, dict):
            continue

        for name in current_vars:
            if name not in desired_vars:
                desired_vars[name] = None

    return merged


def current_domain_names(project, domains):
    names = set(project.get("domains") or [])
    for domain in domains:
        if isinstance(domain, dict) and domain.get("name") is not None:
            names.add(domain["name"])
    return names


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
            "rotate_secrets": {"type": "bool", "default": False},
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
    state = params["state"]

    with cloudflare_client(module) as client:
        current = get_result(
            client,
            item_endpoint(params["account_id"], params["name"]),
            ok_statuses=[404],
        )
        domain_names = []
        for domain in params.get("domains") or []:
            domain_name = domain.get("name") if isinstance(domain, dict) else None
            if not domain_name:
                module.fail_json(msg="Each Pages project domain requires a name")
            if domain_name not in domain_names:
                domain_names.append(domain_name)

        if state == "absent":
            if current is None:
                module.exit_json(changed=False, message="Pages project already absent")
            if module.check_mode:
                module.exit_json(
                    changed=True,
                    message="Pages project would be deleted",
                    pages_project=current,
                )
            existing_domains = list_all(
                client,
                domains_endpoint(params["account_id"], params["name"]),
                paginate=False,
            )
            existing_names = current_domain_names(current, existing_domains)
            for domain_name in domain_names:
                if domain_name in existing_names:
                    delete_result(
                        client,
                        "%s/%s"
                        % (
                            domains_endpoint(params["account_id"], params["name"]),
                            domain_name,
                        ),
                    )
            delete_result(client, item_endpoint(params["account_id"], params["name"]))
            module.exit_json(
                changed=True,
                message="Pages project deleted",
                pages_project=current,
            )

        elif state == "present":
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
                    module.exit_json(
                        changed=True, message="Pages project would be created"
                    )
                current = post_result(client, endpoint(params["account_id"]), payload)
                changed = True
            else:
                payload = payload_with_removed_env_vars(payload, current)
                if (
                    params["rotate_secrets"]
                    and params.get("deployment_configs") is not None
                ) or values_differ(
                    normalize_current_by_desired_fields(
                        select_fields(current, payload.keys()),
                        comparable_payload(payload),
                    ),
                    comparable_payload(payload),
                ):
                    if module.check_mode:
                        module.exit_json(
                            changed=True,
                            message="Pages project would be updated",
                            pages_project=current,
                        )
                    current = patch_result(
                        client,
                        item_endpoint(params["account_id"], params["name"]),
                        payload,
                    )
                    changed = True

            if domain_names:
                existing_domains = list_all(
                    client,
                    domains_endpoint(params["account_id"], params["name"]),
                    paginate=False,
                )
                existing_names = current_domain_names(current, existing_domains)
                missing_domains = []
                for domain_name in domain_names:
                    if domain_name not in existing_names:
                        missing_domains.append(domain_name)

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

        else:
            module.fail_json(msg=f"Unsupported state: {state}")


if __name__ == "__main__":
    main()
