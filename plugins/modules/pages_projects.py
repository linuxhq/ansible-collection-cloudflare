#!/usr/bin/python
# Copyright: Ansible Project
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)


DOCUMENTATION = r"""
---
module: pages_projects
short_description: Manage Cloudflare Pages projects
description:
  - Create, update, and delete Cloudflare Pages projects by name.
  - Optionally ensures listed custom domains are attached to the project.
  - Results include sensitive values returned by Cloudflare, such as the web analytics
    token; protect registered results and task output, for example with C(no_log).
  - O(build_config) and O(deployment_configs) are C(no_log) options, so Ansible may
    mask any of their values that also appear elsewhere in the returned project.
version_added: '2.0.0'
author:
  - Taylor Kimball (@tkimball83)
extends_documentation_fragment:
  - linuxhq.cloudflare.cloudflare
  - linuxhq.cloudflare.cloudflare.account
options:
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
      - An empty mapping leaves the existing build configuration unchanged.
      - Set C(web_analytics_tag) or C(web_analytics_token) to null to clear it.
        Cloudflare keeps the value of any other build setting set to null, so the
        module fails before making changes.
      - C(web_analytics_token) is treated as write-only; use O(rotate_secrets) to
        apply a new value to an existing project.
      - Only C(build_caching), C(build_command), C(destination_dir), C(root_dir),
        C(web_analytics_tag), and C(web_analytics_token) are supported. Cloudflare
        accepts any other key, such as C(build_image_major_version), but does not
        store it, so the module fails before making changes.
  deployment_configs:
    type: dict
    description:
      - Environment variables and compatibility settings by environment.
      - Values of C(secret_text) variables are write-only; changes to them are not
        detected and they are only resent when another change triggers an update.
      - Use O(rotate_secrets) to force an update that resends secret values.
      - Environment variables removed from C(env_vars) are deleted from the
        project.
      - Environment variables and bindings, such as C(kv_namespaces) entries, set
        to null are deleted from the project. An empty binding map changes nothing.
      - Cloudflare keeps the value of any other setting set to null, such as
        C(compatibility_date), a whole C(env_vars) or binding map, or a field
        inside an entry other than C(services) C(entrypoint) and C(r2_buckets)
        C(jurisdiction), so the module fails before making changes.
      - Keys under C(preview) and C(production) must be Pages deployment
        settings, such as C(compatibility_date), C(env_vars), or
        C(build_image_major_version). Cloudflare accepts any other key but does
        not store it, so the module fails before making changes.
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
      - An empty mapping leaves the existing source unchanged.
  domains:
    type: list
    elements: dict
    description:
      - Custom domains that must exist on the project.
      - With O(state=absent), domains are not deleted separately; Cloudflare
        detaches every custom domain when it deletes the project.
    suboptions:
      name:
        description:
          - Fully qualified custom domain name.
          - Compared case-insensitively; Cloudflare stores domain names in lowercase.
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
  description: Custom domains added to the project during this run.
  returned: when O(state=present) changed the project or its domains, outside check mode
  type: list
  elements: dict
  contains:
    name:
      description: Added custom domain name.
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
    cloudflare_error_context,
    differs,
    get_or_none,
    payload_from_params,
    require_applied,
    resource_field,
    resource_list,
    serialize_resource,
    values_differ,
)

FIELDS = ("build_config", "deployment_configs", "name", "production_branch", "source")

# Cloudflare accepts other keys in build_config and in a preview or production
# deployment config but does not store them. These match the cloudflare SDK
# BuildConfig and DeploymentConfigsPreview/DeploymentConfigsProduction types.
BUILD_SETTINGS = (
    "build_caching",
    "build_command",
    "destination_dir",
    "root_dir",
    "web_analytics_tag",
    "web_analytics_token",
)
DEPLOYMENT_SETTINGS = (
    "ai_bindings",
    "always_use_latest_compatibility_date",
    "analytics_engine_datasets",
    "browsers",
    "build_image_major_version",
    "compatibility_date",
    "compatibility_flags",
    "d1_databases",
    "durable_object_namespaces",
    "env_vars",
    "fail_open",
    "hyperdrive_bindings",
    "kv_namespaces",
    "limits",
    "mtls_certificates",
    "placement",
    "queue_producers",
    "r2_buckets",
    "services",
    "usage_model",
    "vectorize_bindings",
    "wrangler_config_hash",
)

# Cloudflare clears these settings when they are set to null, but keeps the
# current value of any other setting set to null.
NULLABLE_BUILD_SETTINGS = ("web_analytics_tag", "web_analytics_token")
NULLABLE_DEPLOYMENT_SETTINGS = (
    "ai_bindings",
    "analytics_engine_datasets",
    "browsers",
    "d1_databases",
    "durable_object_namespaces",
    "env_vars",
    "hyperdrive_bindings",
    "kv_namespaces",
    "mtls_certificates",
    "queue_producers",
    "r2_buckets",
    "services",
    "vectorize_bindings",
)
# Cloudflare clears these fields of a binding entry when they are set to null.
NULLABLE_BINDING_FIELDS = {"r2_buckets": ("jurisdiction",), "services": ("entrypoint",)}


def contains_null(value):
    if isinstance(value, dict):
        return any(contains_null(item) for item in value.values())

    if isinstance(value, list):
        return any(contains_null(item) for item in value)

    return value is None


def validate_setting_names(module):
    """Fail when a setting Cloudflare accepts but never stores is requested."""
    params = module.params
    unknown = [f"build_config.{key}" for key in params.get("build_config") or {} if key not in BUILD_SETTINGS]
    for environment in ("preview", "production"):
        config = (params.get("deployment_configs") or {}).get(environment)
        for key in config if isinstance(config, dict) else ():
            if key not in DEPLOYMENT_SETTINGS:
                unknown.append(f"deployment_configs.{environment}.{key}")

    if unknown:
        module.fail_json(
            msg=f"Cloudflare does not store these Pages project settings: {', '.join(unknown)}",
            unsupported_settings=unknown,
        )


def validate_null_settings(module):
    """Fail when null is requested for a setting Cloudflare does not clear."""
    params = module.params
    unsupported = [
        f"build_config.{key}"
        for key, value in (params.get("build_config") or {}).items()
        if key not in NULLABLE_BUILD_SETTINGS and contains_null(value)
    ]
    for environment, config in (params.get("deployment_configs") or {}).items():
        if not isinstance(config, dict):
            if config is None:
                unsupported.append(f"deployment_configs.{environment}")

            continue

        for key, value in config.items():
            path = f"deployment_configs.{environment}.{key}"
            if key not in NULLABLE_DEPLOYMENT_SETTINGS or value is None:
                if contains_null(value):
                    unsupported.append(path)

                continue

            # Entries may be null, which deletes them, but not most of their fields.
            for name, entry in value.items() if isinstance(value, dict) else ():
                for field, item in entry.items() if isinstance(entry, dict) else ():
                    if field not in NULLABLE_BINDING_FIELDS.get(key, ()) and contains_null(item):
                        unsupported.append(f"{path}.{name}.{field}")

    if unsupported:
        module.fail_json(
            msg=f"Cloudflare does not clear Pages project settings set to null: {', '.join(unsupported)}",
            unsupported_settings=unsupported,
        )


def without_secret_values(resource):
    """Return a serialized copy without write-only secrets, which are never compared.

    Only build_config.web_analytics_token and the values of secret_text
    environment variables are write-only.
    """
    resource = serialize_resource(resource)
    build_config = resource.get("build_config")
    if isinstance(build_config, dict):
        build_config.pop("web_analytics_token", None)

    for config in (resource.get("deployment_configs") or {}).values():
        env_vars = config.get("env_vars") if isinstance(config, dict) else None
        for variable in (env_vars or {}).values() if isinstance(env_vars, dict) else ():
            if isinstance(variable, dict) and variable.get("type") == "secret_text":
                variable.pop("value", None)

    return resource


def comparable_pages_payload(payload):
    """Return the payload fields to compare.

    A requested mapping that holds only deletions or write-only secrets manages
    nothing else, so it is dropped rather than compared as empty; deletions are
    verified separately. An explicitly empty mapping, such as env_vars: {}, is
    kept.
    """
    comparable = without_secret_values(payload)

    def prune(requested, compared):
        for key in list(compared):
            requested_value, compared_value = requested.get(key), compared[key]
            if isinstance(requested_value, dict) and isinstance(compared_value, dict):
                prune(requested_value, compared_value)
                if requested_value and not compared_value:
                    compared.pop(key)

    prune(payload, comparable)
    return comparable


def comparable_project(project, comparable_payload):
    """Return the comparable project, treating a null map as the empty map requested.

    Cloudflare may return an empty environment-variable or binding collection,
    such as kv_namespaces, as null or omit it.
    """
    project = without_secret_values(project)
    for environment, config in (comparable_payload.get("deployment_configs") or {}).items():
        for key, value in config.items() if isinstance(config, dict) else ():
            if value == {}:
                current_config = project.setdefault("deployment_configs", {}).setdefault(environment, {})
                if isinstance(current_config, dict) and current_config.get(key) is None:
                    current_config[key] = {}

    return project


def cleared(value):
    # Cloudflare reports some cleared settings, such as build_config
    # web_analytics_tag, as an empty string.
    return value is None or value == ""


def payload_with_removals(payload, current):
    """Return payload with deletions marked as None, and the deleted entries' key paths.

    Cloudflare clears build settings, environment variables, bindings such as
    kv_namespaces entries, and nested binding fields that are set to null.
    Environment variables omitted from env_vars are deleted too.
    """
    merged = deepcopy(payload)
    removed = []

    def mark(desired, existing, path):
        if not isinstance(desired, dict) or not isinstance(existing, dict):
            return

        if path[-1:] == ("env_vars",):
            for name in existing:
                desired.setdefault(name, None)

        for key, value in desired.items():
            if value is None:
                if not cleared(existing.get(key)):
                    removed.append(path + (key,))
            else:
                mark(value, existing.get(key), path + (key,))

    for field in ("build_config", "deployment_configs"):
        mark(merged.get(field), current.get(field), (field,))

    return merged, removed


def removals_remain(project, removed):
    """Return whether any removed key path is still set in the project."""
    for path in removed:
        value = project
        for key in path:
            value = value.get(key) if isinstance(value, dict) else None

        if not cleared(value):
            return True

    return False


def current_domain_names(module, project, domains):
    project_domains = project.get("domains")
    if project_domains is None:
        project_domains = []
    elif not isinstance(project_domains, list):
        module.fail_json(msg="Cloudflare API returned malformed Pages domain data")

    for name in project_domains:
        if not isinstance(name, str) or not name.strip() or name != name.strip():
            module.fail_json(msg="Cloudflare API returned malformed Pages domain data")

    domain_names = [domain["name"] for domain in resource_list(module, domains, "Pages domain", ("name",))]
    # Domain names are case-insensitive, and Cloudflare stores them lowercased.
    return {name.lower() for name in project_domains + domain_names}


def desired_domain_names(module):
    names = []
    for domain in module.params.get("domains") or []:
        domain_name = domain["name"]
        if not domain_name.strip() or domain_name != domain_name.strip():
            module.fail_json(msg="Each Pages project domain requires a valid name")

        domain_name = domain_name.lower()

        if domain_name not in names:
            names.append(domain_name)

    return names


def checked_project(module, project):
    project = serialize_resource(project)
    resource_field(module, project, "name", "Pages project", expected=module.params["name"])
    return project


def get_project(module, client):
    params = module.params
    with cloudflare_error_context(
        "Cloudflare API request failed while gathering the Pages project",
        account_id=params["account_id"],
        name=params["name"],
    ):
        project = get_or_none(client.pages.projects.get, project_name=params["name"], account_id=params["account_id"])

    return None if project is None else checked_project(module, project)


def existing_domain_names(module, client, project):
    params = module.params
    with cloudflare_error_context(
        "Cloudflare API request failed while gathering Pages project domains",
        account_id=params["account_id"],
        name=params["name"],
    ):
        domains = client.pages.projects.domains.list(project_name=params["name"], account_id=params["account_id"])
        return current_domain_names(module, project, domains)


def update_project(module, client, current, payload, secrets_requested):
    params = module.params
    payload, removed = payload_with_removals(payload, current)
    comparable_payload = comparable_pages_payload(payload)
    if (
        not secrets_requested
        and not removed
        and not differs(comparable_project(current, comparable_payload), comparable_payload)
    ):
        return current, False

    if module.check_mode:
        module.exit_json(
            changed=True,
            message="Pages project would be updated",
            pages_project=current,
        )

    with cloudflare_error_context(
        "Cloudflare API request failed while updating the Pages project",
        account_id=params["account_id"],
        name=params["name"],
    ):
        project = checked_project(
            module,
            client.pages.projects.edit(project_name=params["name"], account_id=params["account_id"], **payload),
        )

    require_applied(module, comparable_project(project, comparable_payload), comparable_payload, "Pages project")
    if removals_remain(project, removed):
        module.fail_json(msg="Cloudflare did not apply the requested Pages project")

    return project, True


def add_domains(module, client, project, domain_names):
    params = module.params
    existing_names = existing_domain_names(module, client, project)
    missing_domains = [domain_name for domain_name in domain_names if domain_name not in existing_names]
    if module.check_mode and missing_domains:
        module.exit_json(
            changed=True,
            message="Pages project domains would be updated",
            pages_project=project,
        )

    added_domains = []
    for domain_name in missing_domains:
        with cloudflare_error_context(
            "Cloudflare API request failed while adding the Pages project domain",
            account_id=params["account_id"],
            name=params["name"],
            domain=domain_name,
        ):
            domain = serialize_resource(
                client.pages.projects.domains.create(
                    project_name=params["name"], account_id=params["account_id"], name=domain_name
                )
            )

        resource_field(module, domain, "name", "Pages domain", expected=domain_name)
        added_domains.append(domain)

    return added_domains


def ensure_present(module, client, domain_names):
    params = module.params
    payload = payload_from_params(params, FIELDS)
    # Cloudflare merges build_config and deployment_configs updates, so empty
    # mappings change nothing.
    for field in ("build_config", "source"):
        if payload.get(field) == {}:
            payload.pop(field)

    # Binding maps merge like the rest of deployment_configs, so an empty one
    # changes nothing. An empty env_vars still deletes every variable.
    configs = {}
    for environment, config in (payload.get("deployment_configs") or {}).items():
        if isinstance(config, dict):
            config = {key: value for key, value in config.items() if value != {} or key == "env_vars"}

        if config != {}:
            configs[environment] = config

    if configs:
        payload["deployment_configs"] = configs
    else:
        payload.pop("deployment_configs", None)

    secrets_requested = params["rotate_secrets"] and values_differ(
        without_secret_values(payload), serialize_resource(payload)
    )
    if params["rotate_secrets"] and not secrets_requested:
        module.fail_json(msg="rotate_secrets requires a secret_text value or build_config.web_analytics_token")

    current = get_project(module, client)
    created = current is None
    if created:
        if params.get("production_branch") is None:
            module.fail_json(msg="production_branch is required when creating a Pages project")

        if module.check_mode:
            module.exit_json(changed=True, message="Pages project would be created")

        with cloudflare_error_context(
            "Cloudflare API request failed while creating the Pages project",
            account_id=params["account_id"],
            name=params["name"],
        ):
            current = checked_project(module, client.pages.projects.create(account_id=params["account_id"], **payload))

        comparable_payload = comparable_pages_payload(payload)
        require_applied(module, comparable_project(current, comparable_payload), comparable_payload, "Pages project")
        changed = True
    else:
        current, changed = update_project(module, client, current, payload, secrets_requested)

    added_domains = add_domains(module, client, current, domain_names) if domain_names else []
    if added_domains:
        current = get_project(module, client)
        if current is None:
            module.fail_json(msg="Cloudflare API returned malformed Pages project data")

    if not changed and not added_domains:
        module.exit_json(
            changed=False,
            message="Pages project already present",
            pages_project=current,
        )

    module.exit_json(
        changed=True,
        message="Pages project created" if created else "Pages project updated",
        pages_project=current,
        domains=added_domains,
    )


def ensure_absent(module, client):
    params = module.params
    current = get_project(module, client)
    if current is None:
        module.exit_json(changed=False, message="Pages project already absent")

    if module.check_mode:
        module.exit_json(
            changed=True,
            message="Pages project would be deleted",
            pages_project=current,
        )

    with cloudflare_error_context(
        "Cloudflare API request failed while deleting the Pages project",
        account_id=params["account_id"],
        name=params["name"],
    ):
        client.pages.projects.delete(project_name=params["name"], account_id=params["account_id"])

    module.exit_json(
        changed=True,
        message="Pages project deleted",
        pages_project=current,
    )


def run(module, client):
    domain_names = desired_domain_names(module)
    if module.params["state"] == "present":
        validate_setting_names(module)
        validate_null_settings(module)
        ensure_present(module, client, domain_names)

    ensure_absent(module, client)


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
        run(module, client)


if __name__ == "__main__":
    main()
