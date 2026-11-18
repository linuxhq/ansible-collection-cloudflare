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
notes:
  - Cloudflare may store a requested value in a canonical form that differs from the request. The module then
    fails after the write, naming the requested and stored value of each differing field in the message and in
    C(differences), so the stored form can be requested instead.
extends_documentation_fragment:
  - linuxhq.cloudflare.cloudflare
  - linuxhq.cloudflare.cloudflare.account
  - linuxhq.cloudflare.cloudflare.create
options:
  name:
    required: true
    type: str
    description:
      - Pages project name.
      - V(""), V(.), and V(..) fail before any request.
  production_branch:
    type: str
    description:
      - Git branch deployed to the production environment.
      - Required when creating a new Pages project.
      - V("") fails before any change, because Cloudflare keeps the current
        branch.
  build_config:
    type: dict
    description:
      - Pages build command, output directory, and related settings.
      - An empty mapping leaves the existing build configuration unchanged.
      - Set C(web_analytics_tag) or C(web_analytics_token) to null to clear it.
        Cloudflare keeps the value of any other build setting set to null, so the
        module fails before making changes.
      - Only C(build_caching), C(build_command), C(destination_dir), C(root_dir),
        C(web_analytics_tag), and C(web_analytics_token) are supported. Cloudflare
        accepts any other key, such as C(build_image_major_version), but does not
        store it, so the module fails before making changes. Any other key set
        to null counts as omitted and is not rejected, because Cloudflare drops
        it.
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
        to null are deleted from the project. An empty binding map, C(limits), or
        C(placement) changes nothing.
        C(wrangler_config_hash), C(placement.mode), and C(limits.cpu_ms) set to
        null are cleared, and an environment variable C(value) or a C(services)
        entry's C(environment) set to null is stored as V(""), which matches the
        null on later runs.
      - Any other C(wrangler_config_hash) fails before making changes, because
        Cloudflare does not store it when it creates or updates a project.
      - Cloudflare keeps the current value of a whole C(preview) or
        C(production) configuration, C(always_use_latest_compatibility_date),
        C(build_image_major_version), C(compatibility_date),
        C(compatibility_flags), C(fail_open),
        C(usage_model), a whole C(env_vars), C(limits), C(placement), or
        binding map, such as C(browsers), C(d1_databases), or C(kv_namespaces),
        and the C(type) of an environment variable set to null, so the module
        fails before making changes.
      - Keys under C(preview) and C(production) must be Pages deployment
        settings, such as C(compatibility_date), C(env_vars), or
        C(build_image_major_version). Cloudflare accepts any other key but does
        not store it, so the module fails before making changes. Any other key
        set to null counts as omitted and is not rejected, because Cloudflare
        drops it.
      - The same applies to fields of C(limits), C(placement), and each
        C(browsers), C(env_vars), C(kv_namespaces), or C(vectorize_bindings)
        entry, such as C(type) and C(value) of an environment variable or
        C(namespace_id) of a C(kv_namespaces) entry. Any other field fails
        before making changes, and any other field set to null counts as
        omitted and is not rejected.
      - An empty C(compatibility_date), C(usage_model), or C(placement.mode)
        fails before making changes, because Cloudflare does not store it; omit
        it instead.
  rotate_secrets:
    type: bool
    default: false
    description:
      - Force an update that resends provided C(secret_text) values or
        C(web_analytics_token), even when no other change is detected.
      - Cloudflare returns C(web_analytics_token), so a changed token is
        detected and applied without O(rotate_secrets).
      - The module reports C(changed) when enabled with either credential input.
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
      - A domain counts as present once it is attached to the project, whatever
        its status. Cloudflare reports a new domain as C(pending) or
        C(initializing) until it is verified; the module does not detect a
        domain whose status is C(error), C(blocked), or C(deactivated).
      - With O(state=absent), domains are not deleted separately; Cloudflare
        detaches every custom domain when it deletes the project.
    suboptions:
      name:
        description:
          - Fully qualified custom domain name.
          - Compared case-insensitively; Cloudflare stores domain names in lowercase.
          - Must contain only ASCII letters, digits, C(.), and C(-), with no
            trailing C(.); write internationalized names in their C(xn--) form.
          - Each label must have 1 to 63 characters and must not start or end
            with C(-), and the name must have at most 253 characters.
          - The name must have at least two labels, its last label must not be
            all digits, so IPv4 addresses are rejected, and it must not be
            C(pages.dev) or C(workers.dev) or end in C(.pages.dev) or
            C(.workers.dev).
          - Its last label must have at least two characters and must not be a
            special-use top-level domain, C(example), C(invalid), C(local),
            C(localhost), or C(test).
          - A label that starts with C(xn--) must be the punycode form of a
            non-ASCII label, such as C(xn--bcher-kva), that encodes back to
            the same text, is unchanged by NFKC normalization, and has no
            control, format, unassigned, or separator characters, so
            C(xn--zz) and C(xn--a) are not supported.
          - These checks run before any request, because Cloudflare rejects
            such names only after the project is created or updated.
          - Cloudflare also rejects other unregistered top-level domains, which
            the module does not check, when it adds the domain after the
            project is created or updated.
          - When a name is not yet attached to this project, the module lists
            the account's Pages projects and their domains before any change,
            and fails, naming the other project, when one of them already has
            the domain.
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

- name: Ensure Pages project has custom domains
  linuxhq.cloudflare.pages_projects:
    account_id: "{{ account_id }}"
    api_token: "{{ cloudflare_api_token }}"
    name: docs
    domains:
      - name: docs.example.com

- name: Ensure Pages production environment variables
  linuxhq.cloudflare.pages_projects:
    account_id: "{{ account_id }}"
    api_token: "{{ cloudflare_api_token }}"
    name: docs
    deployment_configs:
      production:
        env_vars:
          API_URL:
            type: plain_text
            value: https://api.example.com
          API_KEY:
            type: secret_text
            value: "{{ docs_api_key }}"
          OLD_SETTING: null
  no_log: true

# env_vars lists every variable to keep; omitted variables are deleted.
- name: Resend Pages secret values
  linuxhq.cloudflare.pages_projects:
    account_id: "{{ account_id }}"
    api_token: "{{ cloudflare_api_token }}"
    name: docs
    rotate_secrets: true
    deployment_configs:
      production:
        env_vars:
          API_URL:
            type: plain_text
            value: https://api.example.com
          API_KEY:
            type: secret_text
            value: "{{ docs_api_key }}"
  no_log: true

- name: Ensure Pages project is absent
  linuxhq.cloudflare.pages_projects:
    account_id: "{{ account_id }}"
    api_token: "{{ cloudflare_api_token }}"
    name: docs
    state: absent
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
      description:
        - Domains assigned to the project.
        - Cloudflare omits a custom domain that is not active yet, such as one added during this run; the top-level
          RV(domains) lists the custom domains added during this run.
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

import string
import unicodedata
from copy import deepcopy

from ansible.module_utils.basic import AnsibleModule

from ansible_collections.linuxhq.cloudflare.plugins.module_utils.cloudflare_utils import (
    DOT_SEGMENTS,
    cloudflare_client,
    cloudflare_error_context,
    create_once,
    differs,
    fail_not_applied,
    get_or_none,
    list_all_pages,
    path_segment,
    payload_from_params,
    require_applied,
    resource_field,
    resource_list,
    serialize_resource,
    unique_match,
    unsupported_fields,
    valid_dns_labels,
    values_differ,
    without_retries,
)

FIELDS = ("build_config", "deployment_configs", "name", "production_branch", "source")

# Characters Cloudflare accepts in a Pages custom domain name.
DOMAIN_CHARACTERS = frozenset(string.ascii_letters + string.digits + ".-")
# Domains Cloudflare reserves for its own Pages and Workers hostnames.
RESERVED_DOMAINS = ("pages.dev", "workers.dev")
# Special-use top-level domains (RFC 2606, RFC 6761, and RFC 6762) that
# Cloudflare rejects as invalid.
SPECIAL_USE_TLDS = frozenset(("example", "invalid", "local", "localhost", "test"))

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
# Fields of each entry in the deployment env_vars and binding maps whose other
# fields Cloudflare drops, and of each deployment setting object, from the
# same cloudflare SDK types.
DEPLOYMENT_ENTRY_FIELDS = {
    "browsers": (),
    "env_vars": ("type", "value"),
    "kv_namespaces": ("namespace_id",),
    "vectorize_bindings": ("index_name",),
}
DEPLOYMENT_OBJECT_FIELDS = {"limits": ("cpu_ms",), "placement": ("mode",)}

# Cloudflare clears these build settings when they are set to null, but keeps
# the current value of any other build setting set to null.
NULLABLE_BUILD_SETTINGS = ("web_analytics_tag", "web_analytics_token")
# Cloudflare keeps the current value of these deployment settings, and of an
# environment variable's type or value, when they are set to null.
NON_NULLABLE_DEPLOYMENT_SETTINGS = (
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
)


def contains_null(value):
    if isinstance(value, dict):
        return any(contains_null(item) for item in value.values())

    if isinstance(value, list):
        return any(contains_null(item) for item in value)

    return value is None


def validate_setting_names(module):
    """Fail when a setting Cloudflare accepts but never stores is requested.

    Null values are ignored, as Cloudflare drops an unknown setting set to
    null; validate_null_settings checks known settings set to null.
    """
    params = module.params
    unknown = unsupported_fields(params.get("build_config"), BUILD_SETTINGS, "build_config")
    for environment in ("preview", "production"):
        config = (params.get("deployment_configs") or {}).get(environment)
        for key, value in config.items() if isinstance(config, dict) else ():
            if value is None:
                continue

            path = f"deployment_configs.{environment}.{key}"
            # Cloudflare drops wrangler_config_hash on create and update.
            if key not in DEPLOYMENT_SETTINGS or key == "wrangler_config_hash":
                unknown.append(path)

            if key in DEPLOYMENT_OBJECT_FIELDS:
                unknown.extend(unsupported_fields(value, DEPLOYMENT_OBJECT_FIELDS[key], path))

            # Entries may be null, which deletes them.
            for name, entry in value.items() if key in DEPLOYMENT_ENTRY_FIELDS and isinstance(value, dict) else ():
                unknown.extend(unsupported_fields(entry, DEPLOYMENT_ENTRY_FIELDS[key], f"{path}.{name}"))

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
        if key in BUILD_SETTINGS and key not in NULLABLE_BUILD_SETTINGS and contains_null(value)
    ]
    for environment, config in (params.get("deployment_configs") or {}).items():
        path = f"deployment_configs.{environment}"
        if config is None:
            unsupported.append(path)

        if not isinstance(config, dict):
            continue

        unsupported.extend(
            f"{path}.{key}" for key in NON_NULLABLE_DEPLOYMENT_SETTINGS if key in config and config[key] is None
        )
        # Variables may be null, which deletes them, but not their type.
        env_vars = config.get("env_vars")
        for name, variable in env_vars.items() if isinstance(env_vars, dict) else ():
            if isinstance(variable, dict) and "type" in variable and variable["type"] is None:
                unsupported.append(f"{path}.env_vars.{name}.type")

    if unsupported:
        module.fail_json(
            msg=f"Cloudflare does not clear Pages project settings set to null: {', '.join(unsupported)}",
            unsupported_settings=unsupported,
        )


def validate_empty_settings(module):
    """Fail when a deployment setting Cloudflare does not store when empty is requested empty.

    Cloudflare keeps the previous compatibility_date and usage_model, and stores
    an empty placement mode as an empty placement, so none would match the
    request.
    """
    empty = []
    for environment, config in (module.params.get("deployment_configs") or {}).items():
        if not isinstance(config, dict):
            continue

        path = f"deployment_configs.{environment}"
        for setting in ("compatibility_date", "usage_model"):
            if config.get(setting) == "":
                empty.append(f"{path}.{setting}")

        placement = config.get("placement")
        if isinstance(placement, dict) and placement.get("mode") == "":
            empty.append(f"{path}.placement.mode")

    if empty:
        module.fail_json(
            msg=f"Cloudflare does not store an empty value for these Pages project settings: {', '.join(empty)}; "
            "omit them instead",
            empty_settings=empty,
        )


def without_secret_values(resource):
    """Return a serialized copy without write-only secrets, which are never compared.

    Only the values of secret_text environment variables are write-only.
    """
    resource = serialize_resource(resource)
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

        # Only deployment_configs.<environment>.env_vars holds environment
        # variables; a binding can also be named env_vars.
        if len(path) == 3 and path[0] == "deployment_configs" and path[2] == "env_vars":
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


def remaining_removals(project, removed):
    """List each removed key path that is still set in the project, with its stored value."""
    remaining = []
    for path in removed:
        value = project
        for key in path:
            value = value.get(key) if isinstance(value, dict) else None

        if not cleared(value):
            remaining.append({"field": ".".join(path), "requested": None, "stored": value})

    return remaining


def project_context(module):
    """Return the project's account_id and name, which a failure reports."""
    return {"account_id": module.params["account_id"], "name": module.params["name"]}


def project_domain_names(module, project, context):
    """Return the lowercased domain names of project; context adds result fields to a failure."""
    project_domains = project.get("domains")
    if project_domains is None:
        return set()

    if not isinstance(project_domains, list):
        module.fail_json(msg="Cloudflare API returned malformed Pages domain data", **context)

    for name in project_domains:
        if not isinstance(name, str) or not name.strip() or name != name.strip():
            module.fail_json(msg="Cloudflare API returned malformed Pages domain data", **context)

    # Domain names are case-insensitive, and Cloudflare stores them lowercased.
    return {name.lower() for name in project_domains}


def current_domain_names(module, project, domains, context):
    """Return the domain names of project and domains; context adds result fields to a failure."""
    domain_names = [domain["name"] for domain in resource_list(module, domains, "Pages domain", ("name",), context)]
    return project_domain_names(module, project, context) | {name.lower() for name in domain_names}


def valid_ace_label(label):
    """Return whether label, a lowercase label that starts with xn--, encodes an internationalized label.

    The text after xn-- must be punycode that encodes back to the same text,
    and the label it encodes must be non-ASCII, unchanged by NFKC
    normalization, and free of control, format, unassigned, and separator
    characters. Cloudflare rejects other such labels only after the project is
    created or updated.
    """
    try:
        decoded = label[4:].encode("ascii").decode("punycode")
    except UnicodeError:
        return False

    return (
        not decoded.isascii()
        and decoded.encode("punycode") == label[4:].encode("ascii")
        and unicodedata.normalize("NFKC", decoded) == decoded
        and not any(unicodedata.category(character)[0] in "CZ" for character in decoded)
    )


def desired_domain_names(module):
    names = []
    for domain in module.params.get("domains") or []:
        domain_name = domain["name"]
        if not set(domain_name) <= DOMAIN_CHARACTERS or not valid_dns_labels(domain_name):
            module.fail_json(
                msg=(
                    "Each Pages project domain name may contain only ASCII letters, digits, '.', and '-', "
                    "each label must have 1 to 63 characters and must not start or end with '-', "
                    "and the name must have at most 253 characters with no trailing '.'"
                ),
                domain=domain_name,
            )

        domain_name = domain_name.lower()
        labels = domain_name.split(".")
        if (
            len(labels) < 2
            or labels[-1].isdigit()
            or len(labels[-1]) == 1
            or labels[-1] in SPECIAL_USE_TLDS
            or any(domain_name == reserved or domain_name.endswith("." + reserved) for reserved in RESERVED_DOMAINS)
        ):
            module.fail_json(
                msg=(
                    "Each Pages project domain name must have at least two labels, must not end in an all-numeric "
                    "label such as an IPv4 address, a one-character label, or a special-use top-level domain "
                    "(example, invalid, local, localhost, or test), and must not be or end in 'pages.dev' or "
                    "'workers.dev'"
                ),
                domain=domain["name"],
            )

        if any(label.startswith("xn--") and not valid_ace_label(label) for label in labels):
            module.fail_json(
                msg=(
                    "Each label of a Pages project domain name that starts with 'xn--' must be the valid punycode "
                    "form of an internationalized label, such as 'xn--bcher-kva'"
                ),
                domain=domain["name"],
            )

        if domain_name not in names:
            names.append(domain_name)

    return names


def checked_project(module, project, written=None):
    """Serialize and validate a project response.

    written holds the result fields a failure reports after a write in this
    run, such as changed=True; the failure then also returns the project.
    """
    project = serialize_resource(project)
    context = project_context(module) if written is None else {**written, "pages_project": project}
    resource_field(module, project, "name", "Pages project", expected=module.params["name"], context=context)
    return project


def get_project(module, client, written=None):
    """Return the project, or None; written is passed to checked_project and to a request failure."""
    params = module.params
    with cloudflare_error_context(
        "Cloudflare API request failed while gathering the Pages project",
        **{"account_id": params["account_id"], "name": params["name"], **(written or {})},
    ):
        project = get_or_none(client.pages.projects.get, project_name=params["name"], account_id=params["account_id"])

    return None if project is None else checked_project(module, project, written)


def list_domains(module, client, project_name, context):
    """Return every custom domain of the project; context adds result fields to a failure.

    The generated SDK method reads only the first page of domains.
    """
    path = f"/accounts/{path_segment(module.params['account_id'])}/pages/projects/{path_segment(project_name)}/domains"
    return list_all_pages(module, client, path, "Pages domain", context)


def existing_domain_names(module, client, project):
    context = project_context(module)
    with cloudflare_error_context("Cloudflare API request failed while gathering Pages project domains", **context):
        domains = list_domains(module, client, module.params["name"], context)
        return current_domain_names(module, project, domains, context)


def check_domain_owners(module, client, existing_names, domain_names):
    """Fail when another project in the account has a domain to be added.

    Cloudflare rejects such a domain only after the project is created or
    updated.
    """
    params = module.params
    requested = [domain_name for domain_name in domain_names if domain_name not in existing_names]
    if not requested:
        return

    with cloudflare_error_context(
        "Cloudflare API request failed while gathering Pages projects",
        account_id=params["account_id"],
        name=params["name"],
    ):
        projects = resource_list(
            module,
            client.pages.projects.list(account_id=params["account_id"]),
            "Pages project",
            ("name",),
            project_context(module),
        )

    for other in projects:
        if other["name"] == params["name"]:
            continue

        # A project's domains field omits custom domains that are not active yet.
        context = {**project_context(module), "project": other["name"]}
        with cloudflare_error_context(
            "Cloudflare API request failed while gathering Pages project domains",
            account_id=params["account_id"],
            name=other["name"],
        ):
            domains = get_or_none(list_domains, module, client, other["name"], context)

        # A project deleted since it was listed has no domains.
        if domains is None:
            continue

        other_domains = current_domain_names(module, other, domains, context)

        for domain_name in requested:
            if domain_name in other_domains:
                module.fail_json(
                    msg="Pages project domain is already attached to another Pages project",
                    account_id=params["account_id"],
                    name=params["name"],
                    domain=domain_name,
                    project=other["name"],
                )


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
        project = client.pages.projects.edit(project_name=params["name"], account_id=params["account_id"], **payload)

    written = {"changed": True, "account_id": params["account_id"], "name": params["name"]}
    project = checked_project(module, project, written)
    context = {**written, "pages_project": project}
    require_applied(
        module,
        comparable_project(project, comparable_payload),
        comparable_payload,
        "Pages project",
        context=context,
    )
    remaining = remaining_removals(project, removed)
    if remaining:
        fail_not_applied(module, "Pages project", remaining, **context)

    return project, True


def add_domains(module, client, project, existing_names, domain_names, changed):
    """Add the missing domains and return them.

    changed tells whether this run already wrote the project. A failure
    reports the project and the domains added before it, and changed=True
    after any write.
    """
    missing_domains = [domain_name for domain_name in domain_names if domain_name not in existing_names]
    if module.check_mode and missing_domains:
        module.exit_json(
            changed=True,
            message="Pages project domains would be updated",
            pages_project=project,
        )

    added_domains = []
    for domain_name in missing_domains:
        context = {"pages_project": project, "domains": list(added_domains)}
        if changed or added_domains:
            context["changed"] = True

        added_domains.append(add_domain(module, client, domain_name, context))

    return added_domains


def add_domain(module, client, domain_name, context):
    """Add the domain; context adds result fields to a failure."""
    params = module.params
    query = {"project_name": params["name"], "account_id": params["account_id"]}
    context = {"account_id": params["account_id"], "name": params["name"], **context, "domain": domain_name}
    with cloudflare_error_context("Cloudflare API request failed while adding the Pages project domain", **context):
        domain = serialize_resource(
            create_once(
                lambda: without_retries(client).pages.projects.domains.create(**query, name=domain_name),
                lambda: unique_match(get_or_none(client.pages.projects.domains.get, domain_name, **query)),
            )
        )

    context = {**context, "changed": True, "domains": [*context["domains"], domain]}
    resource_field(module, domain, "name", "Pages domain", expected=domain_name, context=context)
    return domain


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

    secrets_requested = params["rotate_secrets"] and (
        (payload.get("build_config") or {}).get("web_analytics_token") is not None
        or values_differ(without_secret_values(payload), serialize_resource(payload))
    )
    current = get_project(module, client)
    created = current is None
    if created and params.get("production_branch") is None:
        module.fail_json(msg="production_branch is required when creating a Pages project", **project_context(module))

    existing_names = existing_domain_names(module, client, current) if current is not None and domain_names else set()
    check_domain_owners(module, client, existing_names, domain_names)
    if created:
        if module.check_mode:
            module.exit_json(changed=True, message="Pages project would be created")

        with cloudflare_error_context(
            "Cloudflare API request failed while creating the Pages project",
            account_id=params["account_id"],
            name=params["name"],
        ):
            current = create_once(
                lambda: without_retries(client).pages.projects.create(account_id=params["account_id"], **payload),
                lambda: unique_match(get_project(module, client)),
            )

        written = {"changed": True, "account_id": params["account_id"], "name": params["name"]}
        current = checked_project(module, current, written)
        comparable_payload = comparable_pages_payload(payload)
        require_applied(
            module,
            comparable_project(current, comparable_payload),
            comparable_payload,
            "Pages project",
            context={**written, "pages_project": current},
        )
        changed = True
    else:
        current, changed = update_project(module, client, current, payload, secrets_requested)

    added_domains = add_domains(module, client, current, existing_names, domain_names, changed) if domain_names else []
    if added_domains:
        written = {"changed": True, "account_id": params["account_id"], "name": params["name"]}
        written_project = current
        # A failed re-read still reports the project this run wrote.
        current = get_project(module, client, {**written, "pages_project": written_project, "domains": added_domains})
        if current is None:
            module.fail_json(
                msg="Pages project was deleted while its domains were being added",
                **written,
                pages_project=written_project,
                domains=added_domains,
            )

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
        # As in ensure_resource_absent, a 404 status counts as deleted: the SDK
        # retries a delete whose response was lost, and Cloudflare answers the
        # retry with 404.
        get_or_none(client.pages.projects.delete, project_name=params["name"], account_id=params["account_id"])

    module.exit_json(
        changed=True,
        message="Pages project deleted",
        pages_project=current,
    )


def run(module, client):
    # The SDK refuses to build a request path with an empty or dot segment.
    if module.params["name"] == "":
        module.fail_json(msg="name must not be empty")

    if module.params["name"] in DOT_SEGMENTS:
        module.fail_json(msg="name must not be '.' or '..'")

    if module.params["state"] == "present":
        # Cloudflare keeps the current branch when it is set to "".
        if module.params.get("production_branch") == "":
            module.fail_json(msg="production_branch must not be empty")

        domain_names = desired_domain_names(module)
        validate_setting_names(module)
        validate_null_settings(module)
        validate_empty_settings(module)
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
