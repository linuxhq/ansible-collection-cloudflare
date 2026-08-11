#!/usr/bin/python
# Copyright: Contributors to the Ansible project
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)


DOCUMENTATION = r"""
---
module: pages_projects
short_description: Manage Cloudflare Pages projects
description:
  - Create, update, and delete Cloudflare Pages projects by name.
  - Optionally ensures listed custom domains are attached to the project.
  - Secret environment variable values and the web analytics token are redacted
    from returned projects.
version_added: '2.0.0'
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
      - Pages project name.
  production_branch:
    type: str
    description:
      - Git branch deployed to the production environment.
      - Required when creating a new Pages project.
  build_config:
    type: dict
    description:
      - Pages build command, output directory, and related settings.
      - C(web_analytics_token) is treated as write-only; use O(rotate_secrets) to
        apply a new value to an existing project.
  deployment_configs:
    type: dict
    description:
      - Environment variables and compatibility settings by environment.
      - Values of C(secret_text) variables are write-only; changes to them are not
        detected and they are only resent when another change triggers an update.
      - Use O(rotate_secrets) to force an update that resends secret values.
      - Environment variables removed from C(env_vars) are deleted from the
        project.
  rotate_secrets:
    type: bool
    default: false
    description:
      - Force an update that resends provided C(secret_text) values or
        C(web_analytics_token), even when no other change is detected.
      - The module reports C(changed) when enabled with either credential input.
      - Requires a C(secret_text) value under O(deployment_configs) or
        C(build_config.web_analytics_token).
  source:
    type: dict
    description:
      - Git provider and repository configuration.
  domains:
    type: list
    elements: dict
    description:
      - Custom domains that must exist on the project.
    suboptions:
      name:
        description:
          - Fully qualified custom domain name.
        required: true
        type: str
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
  - cloudflare >= 5.6.0, < 6
attributes:
  check_mode:
    description: Supports predicting changes without applying them.
    support: full
  diff_mode:
    description: Determines whether the module returns change details in diff format.
    support: none

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
  description: Cloudflare Pages project with credential values redacted.
  returned: when available
  type: dict
  contains:
    name:
      description: Pages project name.
      returned: always
      type: str
    production_branch:
      description: Branch deployed to production.
      returned: when available
      type: str
    domains:
      description: Domains assigned to the project.
      returned: when available
      type: list
      elements: str
domains:
  description: Managed custom domains.
  returned: when the project or its domains changed
  type: list
  elements: dict
  contains:
    name:
      description: Managed custom domain name.
      returned: always
      type: str
message:
  returned: always
  type: str
  description:
  - Operation summary.

"""

from copy import deepcopy

from ansible.module_utils.basic import AnsibleModule
from ansible_collections.linuxhq.cloudflare.plugins.module_utils.cloudflare_utils import (
    cloudflare_client,
    cloudflare_path,
    delete_result,
    get_result,
    list_all,
    normalize_current_by_desired_fields,
    patch_result,
    payload_from_params,
    post_result,
    redact_pages_secrets,
    resource_field,
    select_fields,
    validate_requested_values,
    values_differ,
)

FIELDS = ("build_config", "deployment_configs", "name", "production_branch", "source")


def comparable_pages_payload(payload):
    comparable = redact_pages_secrets(payload)
    build_config = payload.get("build_config")
    if isinstance(build_config, dict) and set(build_config) == {"web_analytics_token"}:
        comparable.pop("build_config")
    return comparable


def payload_with_removed_env_vars(payload, current):
    merged = deepcopy(payload)
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


def current_domain_names(module, project, domains):
    names = set()
    project_domains = project.get("domains")
    if project_domains is None:
        project_domains = []
    elif not isinstance(project_domains, list):
        module.fail_json(msg="Cloudflare API returned malformed Pages domain data")

    for name in project_domains:
        if not isinstance(name, str) or not name.strip() or name != name.strip():
            module.fail_json(msg="Cloudflare API returned malformed Pages domain data")
        names.add(name)

    for domain in domains:
        names.add(resource_field(module, domain, "name", "Pages domain"))
    return names


def desired_domain_names(module):
    names = []
    for domain in module.params.get("domains") or []:
        domain_name = domain.get("name") if isinstance(domain, dict) else None
        if (
            not isinstance(domain_name, str)
            or not domain_name.strip()
            or domain_name != domain_name.strip()
        ):
            module.fail_json(msg="Each Pages project domain requires a valid name")
        if domain_name not in names:
            names.append(domain_name)
    return names


def domains_endpoint(account_id, project_name):
    return cloudflare_path(
        "accounts", account_id, "pages", "projects", project_name, "domains"
    )


def endpoint(account_id):
    return cloudflare_path("accounts", account_id, "pages", "projects")


def item_endpoint(account_id, project_name):
    return cloudflare_path("accounts", account_id, "pages", "projects", project_name)


def ensure_present(module, client):
    params = module.params
    domain_names = desired_domain_names(module)
    production_branch = params.get("production_branch")
    payload = payload_from_params(params, FIELDS)
    credential_payload = payload_from_params(
        params, ("build_config", "deployment_configs")
    )
    secrets_requested = params["rotate_secrets"] and values_differ(
        redact_pages_secrets(credential_payload), credential_payload
    )
    if params["rotate_secrets"] and not secrets_requested:
        module.fail_json(
            msg=(
                "rotate_secrets requires a secret_text value or "
                "build_config.web_analytics_token"
            )
        )

    current = get_result(
        client,
        item_endpoint(params["account_id"], params["name"]),
        ok_statuses=[404],
    )

    if current is None and production_branch is None:
        module.fail_json(
            msg="production_branch is required when creating a Pages project"
        )

    changed = False
    created = False
    domains_changed = False
    managed_domains = []

    if current is None:
        if module.check_mode:
            module.exit_json(changed=True, message="Pages project would be created")

        current = post_result(client, endpoint(params["account_id"]), payload)
        resource_field(
            module, current, "name", "Pages project", expected=params["name"]
        )
        validate_requested_values(
            module,
            redact_pages_secrets(current),
            comparable_pages_payload(payload),
            "Pages project",
        )
        changed = True
        created = True
    else:
        resource_field(
            module, current, "name", "Pages project", expected=params["name"]
        )
        payload = payload_with_removed_env_vars(payload, current)

        comparable_payload = comparable_pages_payload(payload)
        if secrets_requested or values_differ(
            normalize_current_by_desired_fields(
                select_fields(current, payload.keys()),
                comparable_payload,
            ),
            comparable_payload,
        ):
            if module.check_mode:
                module.exit_json(
                    changed=True,
                    message="Pages project would be updated",
                    pages_project=redact_pages_secrets(current),
                )

            current = patch_result(
                client,
                item_endpoint(params["account_id"], params["name"]),
                payload,
            )
            resource_field(
                module, current, "name", "Pages project", expected=params["name"]
            )
            validate_requested_values(
                module,
                redact_pages_secrets(current),
                comparable_payload,
                "Pages project",
            )
            changed = True

    if domain_names:
        existing_domains = list_all(
            client,
            domains_endpoint(params["account_id"], params["name"]),
            paginate=False,
        )
        existing_names = current_domain_names(module, current, existing_domains)
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
                pages_project=redact_pages_secrets(current),
            )

        for domain_name in missing_domains:
            domain = post_result(
                client,
                domains_endpoint(params["account_id"], params["name"]),
                {"name": domain_name},
            )
            resource_field(module, domain, "name", "Pages domain", expected=domain_name)
            managed_domains.append(domain)

    if not changed and not domains_changed:
        module.exit_json(
            changed=False,
            message="Pages project already present",
            pages_project=redact_pages_secrets(current),
        )

    module.exit_json(
        changed=True,
        message="Pages project created" if created else "Pages project updated",
        pages_project=redact_pages_secrets(current),
        domains=managed_domains,
    )


def ensure_absent(module, client):
    params = module.params
    domain_names = desired_domain_names(module)

    current = get_result(
        client,
        item_endpoint(params["account_id"], params["name"]),
        ok_statuses=[404],
    )

    if current is None:
        module.exit_json(changed=False, message="Pages project already absent")

    resource_field(module, current, "name", "Pages project", expected=params["name"])

    if module.check_mode:
        module.exit_json(
            changed=True,
            message="Pages project would be deleted",
            pages_project=redact_pages_secrets(current),
        )

    if domain_names:
        existing_domains = list_all(
            client,
            domains_endpoint(params["account_id"], params["name"]),
            paginate=False,
        )
        existing_names = current_domain_names(module, current, existing_domains)

        for domain_name in domain_names:
            if domain_name in existing_names:
                delete_result(
                    client,
                    cloudflare_path(
                        "accounts",
                        params["account_id"],
                        "pages",
                        "projects",
                        params["name"],
                        "domains",
                        domain_name,
                    ),
                )

    delete_result(client, item_endpoint(params["account_id"], params["name"]))
    module.exit_json(
        changed=True,
        message="Pages project deleted",
        pages_project=redact_pages_secrets(current),
    )


def main():
    module = AnsibleModule(
        argument_spec={
            "account_id": {"required": True, "type": "str"},
            "api_token": {"required": True, "type": "str", "no_log": True},
            "name": {"required": True, "type": "str"},
            "production_branch": {"type": "str"},
            "build_config": {"type": "dict", "no_log": True},
            "deployment_configs": {"type": "dict", "no_log": True},
            "rotate_secrets": {"type": "bool", "default": False},
            "source": {"type": "dict"},
            "domains": {
                "type": "list",
                "elements": "dict",
                "options": {"name": {"required": True, "type": "str"}},
            },
            "state": {
                "type": "str",
                "choices": ["present", "absent"],
                "default": "present",
            },
        },
        supports_check_mode=True,
    )

    with cloudflare_client(module) as client:
        if module.params["state"] == "present":
            ensure_present(module, client)
        else:
            ensure_absent(module, client)


if __name__ == "__main__":
    main()
