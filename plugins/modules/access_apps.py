#!/usr/bin/python
# Copyright: Ansible Project
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)


DOCUMENTATION = r"""
---
module: access_apps
short_description: Manage Cloudflare Access applications
description:
  - Create, update, and delete Cloudflare Access applications by name.
  - Results include sensitive values returned by Cloudflare, such as client secrets; protect registered
    results and task output, for example with C(no_log).
  - Optional settings are preserved on an existing application when omitted,
    and so are settings this module does not manage, such as C(tags) or
    C(custom_pages).
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
options:
  name:
    description:
      - Access application name.
      - Cloudflare trims surrounding whitespace from the name, so a name with
        leading or trailing whitespace is not idempotent; each run creates
        another resource and then fails because Cloudflare returns the
        trimmed name.
      - An empty or whitespace-only name fails before any change, because
        Cloudflare does not store it.
    required: true
    type: str
  domain:
    description:
      - Application domain.
      - Required when O(state=present).
    type: str
  type:
    description:
      - Access application type.
      - Only types that are reached through O(domain) and need no other required
        settings are supported.
      - Required when O(state=present).
      - Settings that Cloudflare does not store for the chosen type must be
        omitted or set to Cloudflare's default, which is V("") for settings
        that V("") clears. Type V(bookmark) does not support
        O(allowed_idps), O(auto_redirect_to_identity), O(cors_headers),
        O(custom_deny_message), O(custom_deny_url), O(destinations),
        O(enable_binding_cookie), O(http_only_cookie_attribute),
        O(same_site_cookie_attribute), O(service_auth_401_redirect),
        O(session_duration), or O(skip_interstitial). Type V(mcp_portal) does not
        support O(app_launcher_visible). Type V(proxy_endpoint) does not support
        O(app_launcher_visible), O(cors_headers), O(custom_deny_message),
        O(destinations), O(enable_binding_cookie), O(http_only_cookie_attribute),
        O(logo_url), O(same_site_cookie_attribute), O(service_auth_401_redirect),
        or O(skip_interstitial).
      - Changing an existing application to type V(bookmark) keeps only its
        O(app_launcher_visible), O(logo_url), O(policies), and tags.
      - Changing an existing application to type V(proxy_endpoint) keeps only its
        O(allowed_idps), O(auto_redirect_to_identity), O(custom_deny_url),
        O(policies), O(session_duration), C(custom_non_identity_deny_url),
        C(custom_pages), and tags.
    type: str
    choices:
      - bookmark
      - mcp_portal
      - proxy_endpoint
      - self_hosted
      - ssh
      - vnc
  allowed_idps:
    type: list
    elements: str
    description:
      - Identity provider identifiers allowed for the application.
      - Order is not significant. Cloudflare stores identity providers in its
        own order, so the same identifiers in any order match.
  app_launcher_visible:
    type: bool
    description:
      - Whether to show the application in the Access application launcher.
      - When omitted, the current value is left unchanged; Cloudflare defaults
        to V(true) on create.
  auto_redirect_to_identity:
    type: bool
    description:
      - Whether to redirect users to the identity provider automatically.
      - When omitted, the current value is left unchanged; Cloudflare defaults
        to V(false) on create.
  cors_headers:
    type: dict
    description:
      - Cross-origin resource sharing headers for the application.
      - Accepts only C(allow_all_headers), C(allow_all_methods),
        C(allow_all_origins), C(allow_credentials), C(allowed_headers),
        C(allowed_methods), C(allowed_origins), and C(max_age). Cloudflare
        accepts any other key but does not store it, so the module fails before
        making changes.
      - An empty C(allowed_headers), C(allowed_methods), or C(allowed_origins)
        list fails before making changes, because Cloudflare does not store
        it; omit the key instead.
      - Compared exactly, so omitting a key removes it. A key set to null is
        not sent and counts as omitted.
      - Cloudflare omits V(false) for C(allow_all_headers),
        C(allow_all_methods), C(allow_all_origins), and C(allow_credentials),
        and V(0) for C(max_age), so those values match an application that
        does not return the key.
  custom_deny_message:
    type: str
    description:
      - Message displayed when Access denies a request.
      - V("") clears the message; Cloudflare then omits it, so V("") matches an
        application without a message.
  custom_deny_url:
    type: str
    description:
      - URL used when Access denies a request.
      - V("") clears the URL; Cloudflare then omits it, so V("") matches an
        application without a URL.
  destinations:
    type: list
    elements: dict
    description:
      - Public destinations protected by the application.
      - Each entry must set C(type), such as C(public); Cloudflare stores an
        entry without one as a C(public) destination, so the module fails
        before making changes.
      - A C(public) or C(private) entry accepts only the fields Cloudflare
        stores for its C(type), such as C(type), C(uri), and C(overrides) of a
        C(public) destination. Each C(overrides) entry accepts only C(behavior) and C(path_pattern).
        Cloudflare accepts any other field but does not store it, so the
        module fails before making changes.
      - An empty C(overrides) list fails before making changes, because
        Cloudflare stores the destination without C(overrides); omit
        C(overrides) instead.
      - An empty list fails before making changes, because Cloudflare
        replaces it with a C(public) destination for O(domain); omit
        O(destinations) instead.
      - An empty C(hostname), C(port_range), or C(vnet_id) of a C(private)
        destination fails before making changes, because Cloudflare does not
        store it; omit the key instead.
      - Each entry is compared exactly, so keys omitted from an entry are
        removed from it.
      - A bare IP address in C(cidr) is sent with its full-length prefix,
        C(/32) for IPv4 or C(/128) for IPv6, as Cloudflare stores it.
      - When omitted, the current destinations are kept unless O(domain) changes,
        in which case Cloudflare derives them from the new O(domain).
  enable_binding_cookie:
    type: bool
    description:
      - Whether to bind the Access cookie to the user session.
      - When omitted, the current value is left unchanged; Cloudflare defaults
        to V(false) on create.
  http_only_cookie_attribute:
    type: bool
    description:
      - Whether the Access cookie uses the HTTP-only attribute.
      - When omitted, the current value is left unchanged; Cloudflare defaults
        to V(true) on create.
  logo_url:
    type: str
    description:
      - URL of the application logo.
      - V("") clears the URL; Cloudflare then omits it, so V("") matches an
        application without a logo.
  policies:
    type: list
    elements: dict
    description:
      - Access policies attached to the application.
      - A field of an entry set to null is not sent and counts as omitted,
        including a nested field of C(connection_rules), C(connection_rules.rdp),
        or C(mfa_config).
      - Each entry accepts only the fields of a reusable policy link, C(id)
        and C(precedence), or of an inline policy, such as
        C(name), C(decision), C(include), C(exclude), C(require), and
        C(approval_groups), whose entries accept only C(approvals_needed),
        C(email_addresses), and C(email_list_uuid). C(connection_rules)
        accepts only C(rdp), whose value accepts only
        C(allowed_clipboard_local_to_remote_formats) and
        C(allowed_clipboard_remote_to_local_formats). The same applies to the
        nested fields of a known inline policy selector. Cloudflare accepts
        any other field, such as C(account_id), but does not store it, so the
        module fails before making changes.
      - An empty C(approval_groups) list, an empty C(email_addresses) list or
        C(email_list_uuid) in one of its groups, an empty
        C(allowed_clipboard_local_to_remote_formats) or
        C(allowed_clipboard_remote_to_local_formats) list under
        C(connection_rules.rdp), and an empty
        C(purpose_justification_prompt) or C(session_duration) fail before
        making changes, because Cloudflare does not store them; omit them
        instead.
      - Cloudflare omits V(false) for C(approval_required),
        C(isolation_required), and C(purpose_justification_required) of an
        inline policy, so V(false) matches a policy that does not return the
        field.
      - Cloudflare returns the policies in ascending C(precedence) order, so
        entries that set C(precedence) must be listed in that order; otherwise
        the module fails before any change.
      - Inline policy selectors in C(include), C(exclude), and C(require) use
        Cloudflare API key names, such as C(github-organization) and
        C(azureAD); the SDK spellings C(github_organization) and C(azure_ad)
        fail before any change.
      - Each inline policy selector is a mapping that sets one rule, such as
        C(email) or C(everyone). Cloudflare drops an empty selector V({}) and
        splits a selector with several rules into separate selectors, so such
        a selector fails before any change.
      - Cloudflare stores a null C(any_valid_service_token) inline policy
        selector value as V({}), so such a selector fails before any change;
        use V({}) instead.
      - The C(account_id) of a C(cloudflare_account_member) or
        C(device_posture) inline policy selector and the
        C(identity_provider_id) of a C(saml) one must not be V(""). Cloudflare
        does not store the empty value, so such a selector fails before any
        change; omit the field instead.
      - Stored policies are compared with the entries at the same position.
        An entry that sets a selector or has no C(id) is an inline policy whose
        C(include), C(exclude), and C(require) are compared exactly, so a
        selector key or list removed from it is a change; an omitted or null
        selector list matches an empty one, and the
        C(id) Cloudflare adds to a
        C(github-organization) selector matches a selector that omits it.
        The C(approval_groups) and C(connection_rules) an inline policy sets
        are also compared exactly, so a key removed from one of them, such as
        the C(approvals_needed) of a group, is a change. Other entries, such as
        C(id) and C(precedence) links to reusable policies, are compared only
        on the keys they set.
  same_site_cookie_attribute:
    type: str
    description:
      - SameSite attribute for the Access cookie.
      - V("") clears the attribute; Cloudflare then omits it, so V("") matches an
        application without this setting.
  service_auth_401_redirect:
    type: bool
    description:
      - Whether to return HTTP 401 instead of redirecting to the login page when a
        Service Auth policy blocks a request.
      - Cloudflare omits V(false) from the application, so V(false) matches an
        application that does not return this setting.
  session_duration:
    type: str
    description:
      - Maximum duration of an authenticated Access session.
      - When omitted, the current value is left unchanged; Cloudflare defaults
        to V(24h) on create.
      - V("") fails before making changes, because Cloudflare then stores
        V(24h); omit it instead.
  skip_interstitial:
    type: bool
    description:
      - Whether to skip the Access interstitial page.
      - Cloudflare omits V(false) from the application, so V(false) matches an
        application that does not return this setting.
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
- name: Ensure Access application exists
  linuxhq.cloudflare.access_apps:
    account_id: "{{ account_id }}"
    api_token: "{{ cloudflare_api_token }}"
    name: app
    domain: app.example.com
    type: self_hosted
"""

RETURN = r"""
---
access_app:
  description: Cloudflare Access application.
  returned: when available
  type: dict
  contains:
    id:
      description: Access application identifier.
      returned: always
      type: str
    name:
      description: Access application name.
      returned: always
      type: str
message:
  description: Operation summary.
  returned: always
  type: str

"""

from ansible.module_utils.basic import AnsibleModule

from ansible_collections.linuxhq.cloudflare.plugins.module_utils.cloudflare_utils import (
    ACCESS_APPROVAL_GROUP_FIELDS,
    ACCESS_SELECTOR_FIELDS,
    cidr_from_address,
    cloudflare_client,
    cloudflare_error_context,
    comparable_access_rules,
    empty_approval_group_fields,
    ensure_resource_absent,
    ensure_resource_present,
    find_resource,
    normalize_current_by_desired_fields,
    payload_from_params,
    serialize_resource,
    unsupported_fields,
    validate_access_selectors,
)

FIELDS = (
    "allowed_idps",
    "app_launcher_visible",
    "auto_redirect_to_identity",
    "cors_headers",
    "custom_deny_message",
    "custom_deny_url",
    "destinations",
    "domain",
    "enable_binding_cookie",
    "http_only_cookie_attribute",
    "logo_url",
    "name",
    "policies",
    "same_site_cookie_attribute",
    "service_auth_401_redirect",
    "session_duration",
    "skip_interstitial",
    "type",
)

PRESERVED_FIELDS = (
    "allowed_idps",
    "app_launcher_visible",
    "auto_redirect_to_identity",
    "cors_headers",
    "custom_deny_message",
    "custom_deny_url",
    "destinations",
    "enable_binding_cookie",
    "http_only_cookie_attribute",
    "logo_url",
    "policies",
    "same_site_cookie_attribute",
    "service_auth_401_redirect",
    "session_duration",
    "skip_interstitial",
)

# The update replaces the application, so settings this module does not manage
# are carried over too. self_hosted_domains is omitted: it mirrors domain and
# destinations and would conflict with a changed domain.
UNMANAGED_FIELDS = (
    "allow_authenticate_via_warp",
    "allow_iframe",
    "app_launcher_logo_url",
    "bg_color",
    "custom_non_identity_deny_url",
    "custom_pages",
    "eager_redirect_cookie_setting",
    "footer_links",
    "header_bg_color",
    "landing_page_design",
    "mfa_config",
    "oauth_configuration",
    "options_preflight_bypass",
    "path_cookie_attribute",
    "read_service_tokens_from_header",
    "saas_app",
    "scim_config",
    "skip_app_launcher_login_page",
    "tags",
    "target_criteria",
    "use_clientless_isolation_app_launcher_url",
)

DEFAULT_FIELDS = {
    "app_launcher_visible": True,
    "auto_redirect_to_identity": False,
    "enable_binding_cookie": False,
    "http_only_cookie_attribute": True,
    "service_auth_401_redirect": False,
    "session_duration": "24h",
    "skip_interstitial": False,
}

# Cloudflare clears these settings when they are set to "" and then omits them,
# so an omitted setting matches "".
EMPTY_STRING_FIELDS = ("custom_deny_message", "custom_deny_url", "logo_url", "same_site_cookie_attribute")

FIELD_DEFAULTS = {**DEFAULT_FIELDS, **dict.fromkeys(EMPTY_STRING_FIELDS, "")}

# Cloudflare accepts these settings for the application types below but does
# not store them, so a requested value could never converge. Verified against
# the API; the SDK response models omit more fields for mcp_portal than
# Cloudflare drops.
UNSUPPORTED_FIELDS = {
    "bookmark": (
        "allowed_idps",
        "auto_redirect_to_identity",
        "cors_headers",
        "custom_deny_message",
        "custom_deny_url",
        "destinations",
        "enable_binding_cookie",
        "http_only_cookie_attribute",
        "same_site_cookie_attribute",
        "service_auth_401_redirect",
        "session_duration",
        "skip_interstitial",
    ),
    "mcp_portal": ("app_launcher_visible",),
    "proxy_endpoint": (
        "app_launcher_visible",
        "cors_headers",
        "custom_deny_message",
        "destinations",
        "enable_binding_cookie",
        "http_only_cookie_attribute",
        "logo_url",
        "same_site_cookie_attribute",
        "service_auth_401_redirect",
        "skip_interstitial",
    ),
}

# Cloudflare stores only these of the carried-over fields for the application
# types below, so the others are dropped from the update.
STORED_FIELDS = {
    "bookmark": ("app_launcher_visible", "logo_url", "policies", "tags"),
    "proxy_endpoint": (
        "allowed_idps",
        "auto_redirect_to_identity",
        "custom_deny_url",
        "custom_non_identity_deny_url",
        "custom_pages",
        "policies",
        "session_duration",
        "tags",
    ),
}

# Fields Cloudflare stores, from the cloudflare SDK application create types;
# it accepts any other field but drops it. Destinations are keyed by type, and
# an entry with an unknown type may use the fields of any destination type.
CORS_HEADERS_FIELDS = (
    "allow_all_headers",
    "allow_all_methods",
    "allow_all_origins",
    "allow_credentials",
    "allowed_headers",
    "allowed_methods",
    "allowed_origins",
    "max_age",
)
# Destination types whose dropped fields were verified; Cloudflare checks the others.
DESTINATION_FIELDS = {
    "private": ("cidr", "hostname", "l4_protocol", "port_range", "type", "vnet_id"),
    "public": ("overrides", "type", "uri"),
}
# DestinationOverrideParam.
DESTINATION_OVERRIDE_FIELDS = ("behavior", "path_pattern")
# A policy entry is a reusable policy link or an inline policy; the SDK inline
# policy type omits the fields shared with Access policies, such as name.
POLICY_FIELDS = (
    "approval_groups",
    "approval_required",
    "connection_rules",
    "decision",
    "exclude",
    "id",
    "include",
    "isolation_required",
    "mfa_config",
    "name",
    "precedence",
    "purpose_justification_prompt",
    "purpose_justification_required",
    "require",
    "session_duration",
)
# The inline policy ConnectionRules type.
POLICY_CONNECTION_RULES_FIELDS = {
    "rdp": ("allowed_clipboard_local_to_remote_formats", "allowed_clipboard_remote_to_local_formats"),
}
# Inline policy fields Cloudflare stores exactly as sent, so keys removed from
# them count as differences.
INLINE_POLICY_EXACT_FIELDS = ("approval_groups", "connection_rules")
# Fields Cloudflare drops when they hold an empty value.
EMPTY_CORS_HEADERS_FIELDS = ("allowed_headers", "allowed_methods", "allowed_origins")
EMPTY_DESTINATION_FIELDS = ("hostname", "port_range", "vnet_id")
EMPTY_POLICY_FIELDS = ("purpose_justification_prompt", "session_duration")
# Cloudflare omits these fields when they hold their default value.
CORS_HEADERS_DEFAULTS = {
    **dict.fromkeys(("allow_all_headers", "allow_all_methods", "allow_all_origins", "allow_credentials"), False),
    "max_age": 0,
}
POLICY_FALSE_FIELDS = ("approval_required", "isolation_required", "purpose_justification_required")


def validate_type_fields(module):
    params = module.params
    unsupported = [
        field
        for field in UNSUPPORTED_FIELDS.get(params["type"], ())
        if params.get(field) is not None and params[field] != FIELD_DEFAULTS.get(field)
    ]
    if unsupported:
        module.fail_json(
            msg=f"Access applications of type {params['type']} do not support {', '.join(unsupported)}",
            unsupported_fields=unsupported,
        )


def validate_policy_order(module):
    """Fail when policies that set precedence are not in the order Cloudflare returns them."""
    ordered = [
        policy
        for policy in module.params.get("policies") or ()
        if isinstance(policy.get("precedence"), int) and not isinstance(policy["precedence"], bool)
    ]
    expected = sorted(ordered, key=lambda policy: policy["precedence"])
    if ordered != expected:
        module.fail_json(
            msg="policies must be listed in ascending precedence order, as Cloudflare returns them",
            expected_order=[{"id": policy.get("id"), "precedence": policy["precedence"]} for policy in expected],
        )


def validate_field_names(module):
    """Fail when an application field Cloudflare accepts but never stores is requested."""
    params = module.params
    destinations = params.get("destinations") or ()
    untyped = [
        f"destinations[{index}]" for index, destination in enumerate(destinations) if destination.get("type") is None
    ]
    if untyped:
        module.fail_json(
            msg=f"{', '.join(untyped)} must set type; Cloudflare stores a destination without one as type public"
        )

    empty_overrides = [
        f"destinations[{index}].overrides"
        for index, destination in enumerate(destinations)
        if destination.get("overrides") == []
    ]
    if empty_overrides:
        module.fail_json(
            msg=f"{', '.join(empty_overrides)} must be omitted instead of an empty list; Cloudflare stores a "
            "destination with empty overrides without them"
        )

    unknown = unsupported_fields(params.get("cors_headers"), CORS_HEADERS_FIELDS, "cors_headers")
    for index, destination in enumerate(destinations):
        kind = destination["type"]
        if isinstance(kind, str) and kind in DESTINATION_FIELDS:
            unknown.extend(unsupported_fields(destination, DESTINATION_FIELDS[kind], f"destinations[{index}]"))

        overrides = destination.get("overrides")
        for position, override in enumerate(overrides if isinstance(overrides, list) else ()):
            path = f"destinations[{index}].overrides[{position}]"
            unknown.extend(unsupported_fields(override, DESTINATION_OVERRIDE_FIELDS, path))

    for index, policy in enumerate(params.get("policies") or ()):
        unknown.extend(unsupported_fields(policy, POLICY_FIELDS, f"policies[{index}]"))
        unknown.extend(
            unsupported_fields(
                policy.get("connection_rules"),
                POLICY_CONNECTION_RULES_FIELDS,
                f"policies[{index}].connection_rules",
            )
        )
        approval_groups = policy.get("approval_groups")
        for position, group in enumerate(approval_groups if isinstance(approval_groups, list) else ()):
            path = f"policies[{index}].approval_groups[{position}]"
            unknown.extend(unsupported_fields(group, ACCESS_APPROVAL_GROUP_FIELDS, path))

    if unknown:
        module.fail_json(
            msg=f"Cloudflare does not store these Access application fields: {', '.join(unknown)}",
            unsupported_fields=unknown,
        )


def validate_empty_values(module):
    """Fail when a field Cloudflare does not store when empty is requested empty.

    Cloudflare drops these empty values, or replaces empty destinations with
    one derived from the domain, so they would never match the request.
    """
    params = module.params
    cors_headers = params.get("cors_headers")
    empty = [
        f"cors_headers.{field}"
        for field in EMPTY_CORS_HEADERS_FIELDS
        if isinstance(cors_headers, dict) and cors_headers.get(field) == []
    ]
    destinations = params.get("destinations")
    if destinations == []:
        empty.append("destinations")

    for index, destination in enumerate(destinations or ()):
        empty.extend(
            f"destinations[{index}].{field}" for field in EMPTY_DESTINATION_FIELDS if destination.get(field) == ""
        )

    if params.get("session_duration") == "":
        empty.append("session_duration")

    for index, policy in enumerate(params.get("policies") or ()):
        path = f"policies[{index}]"
        approval_groups = policy.get("approval_groups")
        if approval_groups == []:
            empty.append(f"{path}.approval_groups")

        empty.extend(empty_approval_group_fields(approval_groups, f"{path}.approval_groups"))
        empty.extend(f"{path}.{field}" for field in EMPTY_POLICY_FIELDS if policy.get(field) == "")
        connection_rules = policy.get("connection_rules")
        rdp = connection_rules.get("rdp") if isinstance(connection_rules, dict) else None
        if isinstance(rdp, dict):
            empty.extend(
                f"{path}.connection_rules.rdp.{field}"
                for field in POLICY_CONNECTION_RULES_FIELDS["rdp"]
                if rdp.get(field) == []
            )

    if empty:
        module.fail_json(
            msg=f"Cloudflare does not store an empty value for these Access application fields: {', '.join(empty)}; "
            "omit them instead",
            empty_fields=empty,
        )


def without_nulls(value):
    """Return the mapping value without the keys set to null, which count as omitted."""
    return {key: item for key, item in value.items() if item is not None}


def without_nested_nulls(value):
    """Return value without the keys set to null at any level of its nested mappings."""
    if not isinstance(value, dict):
        return value

    return {key: without_nested_nulls(item) for key, item in value.items() if item is not None}


def policy_without_nulls(policy):
    """Return the policy entry without null fields, including those in its nested mappings."""
    policy = without_nulls(policy)
    for field in ("connection_rules", "mfa_config"):
        if field in policy:
            policy[field] = without_nested_nulls(policy[field])

    return policy


def comparable_policy(policy, desired):
    """Return policy projected onto the fields of desired.

    The selectors of an inline policy, one that sets a selector or has no id,
    are kept whole, apart from keys Cloudflare assigns, so removed selector
    keys and lists count as differences. Its requested approval_groups and
    connection_rules are kept whole too. An omitted selector list matches an
    empty one, and an omitted POLICY_FALSE_FIELDS field matches false.
    """
    if not isinstance(policy, dict) or not isinstance(desired, dict):
        return policy

    policy = {**dict.fromkeys(POLICY_FALSE_FIELDS, False), **policy}
    comparable = normalize_current_by_desired_fields(policy, desired)
    if "id" in desired and not any(field in desired for field in ACCESS_SELECTOR_FIELDS):
        return comparable

    policy = comparable_access_rules(policy, desired)
    for field in ACCESS_SELECTOR_FIELDS:
        comparable.pop(field, None)
        stored = policy.get(field)
        if field in desired:
            comparable[field] = [] if stored is None else stored
        elif stored:
            comparable[field] = stored

    for field in INLINE_POLICY_EXACT_FIELDS:
        if field in desired:
            comparable[field] = policy.get(field)

    return comparable


def comparable_app(app, allowed_idps, policies, cors_headers):
    """Return app in the form compared with the requested settings.

    Cloudflare ignores the order of allowed_idps and stores identity providers
    in its own order, so stored identity providers that match the request take
    its order. Stored policies are paired with the requested ones by position.
    Cloudflare omits CORS header fields that hold their default, so a requested
    one the stored CORS headers omit matches its default.
    """
    app = serialize_resource(app)
    if not isinstance(app, dict):
        return app

    stored = app.get("cors_headers")
    if isinstance(cors_headers, dict) and (stored is None or isinstance(stored, dict)):
        defaults = {key: value for key, value in CORS_HEADERS_DEFAULTS.items() if key in cors_headers}
        if defaults:
            app = {**app, "cors_headers": {**defaults, **(stored or {})}}

    stored = app.get("allowed_idps")
    if (
        isinstance(allowed_idps, list)
        and isinstance(stored, list)
        and all(isinstance(idp, str) for idp in stored)
        and sorted(stored) == sorted(allowed_idps)
    ):
        app = {**app, "allowed_idps": allowed_idps}

    stored = app.get("policies")
    if isinstance(policies, list) and isinstance(stored, list) and len(stored) == len(policies):
        app = {**app, "policies": [comparable_policy(*pair) for pair in zip(stored, policies)]}

    return app


def run(module, client):
    params = module.params
    account_id = params["account_id"]
    applications = client.zero_trust.access.applications
    if params["state"] == "present":
        # Cloudflare stores an empty name as the app's domain, so the app is never found by name again.
        if not params["name"].strip():
            module.fail_json(msg="name must not be empty or only whitespace")

        validate_type_fields(module)
        validate_policy_order(module)
        validate_field_names(module)
        validate_empty_values(module)
        for index, policy in enumerate(params.get("policies") or ()):
            validate_access_selectors(module, policy, f"policies[{index}].")

    with cloudflare_error_context(
        "Cloudflare API request failed while finding the Access application",
        account_id=account_id,
        name=params["name"],
    ):
        current = find_resource(
            module,
            applications.list(account_id=account_id, name=params["name"], exact=True),
            "Access application",
            "name",
            params["name"],
        )

    if params["state"] == "absent":
        ensure_resource_absent(
            module,
            "access_app",
            "Access application",
            current,
            delete=lambda app_id: applications.delete(app_id, account_id=account_id),
            context={"account_id": account_id},
        )

    preserved_fields = PRESERVED_FIELDS + UNMANAGED_FIELDS
    if current is not None and current.get("domain") != params["domain"]:
        # Cloudflare rejects a domain that is not among the destinations, so
        # kept destinations would block every domain change.
        preserved_fields = tuple(field for field in preserved_fields if field != "destinations")

    if params["type"] in STORED_FIELDS:
        preserved_fields = tuple(field for field in preserved_fields if field in STORED_FIELDS[params["type"]])

    # Cloudflare drops these on a change to the type, so carrying them over
    # would fail the change.
    unsupported = UNSUPPORTED_FIELDS.get(params["type"], ())
    preserved_fields = tuple(field for field in preserved_fields if field not in unsupported)

    payload = payload_from_params(params, FIELDS)
    if "destinations" in payload:
        payload["destinations"] = [
            {**destination, "cidr": cidr_from_address(destination["cidr"])} if "cidr" in destination else destination
            for destination in payload["destinations"]
        ]

    if "cors_headers" in payload:
        payload["cors_headers"] = without_nulls(payload["cors_headers"])

    if "policies" in payload:
        payload["policies"] = [policy_without_nulls(policy) for policy in payload["policies"]]

    ensure_resource_present(
        module,
        "access_app",
        "Access application",
        current,
        payload,
        create=lambda payload: applications.create(account_id=account_id, **payload),
        update=lambda app_id, payload: applications.update(app_id, account_id=account_id, **payload),
        expected_name=params["name"],
        defaults=FIELD_DEFAULTS,
        preserved_fields=preserved_fields,
        exact_values=("cors_headers", "destinations", "policies"),
        context={"account_id": account_id},
        comparable=lambda app: comparable_app(
            app, params.get("allowed_idps"), payload.get("policies"), payload.get("cors_headers")
        ),
    )


def main():
    module = AnsibleModule(
        argument_spec={
            "account_id": {"required": True, "type": "str"},
            "api_token": {"required": True, "type": "str", "no_log": True},
            "name": {"required": True, "type": "str"},
            "domain": {"type": "str"},
            "type": {
                "type": "str",
                "choices": ["bookmark", "mcp_portal", "proxy_endpoint", "self_hosted", "ssh", "vnc"],
            },
            "allowed_idps": {"type": "list", "elements": "str"},
            "app_launcher_visible": {"type": "bool"},
            "auto_redirect_to_identity": {"type": "bool"},
            "cors_headers": {"type": "dict"},
            "custom_deny_message": {"type": "str"},
            "custom_deny_url": {"type": "str"},
            "destinations": {"type": "list", "elements": "dict"},
            "enable_binding_cookie": {"type": "bool"},
            "http_only_cookie_attribute": {"type": "bool"},
            "logo_url": {"type": "str"},
            "policies": {"type": "list", "elements": "dict"},
            "same_site_cookie_attribute": {"type": "str"},
            "service_auth_401_redirect": {"type": "bool"},
            "session_duration": {"type": "str"},
            "skip_interstitial": {"type": "bool"},
            "state": {
                "type": "str",
                "choices": ["present", "absent"],
                "default": "present",
            },
        },
        required_if=[("state", "present", ["domain", "type"])],
        supports_check_mode=True,
    )

    with cloudflare_client(module) as client:
        run(module, client)


if __name__ == "__main__":
    main()
