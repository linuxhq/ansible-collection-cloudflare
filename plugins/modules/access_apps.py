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
extends_documentation_fragment:
  - linuxhq.cloudflare.cloudflare
  - linuxhq.cloudflare.cloudflare.account
options:
  name:
    description:
      - Access application name.
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
        omitted or set to Cloudflare's default. Type V(bookmark) does not support
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
      - Compared exactly, so omitting a key removes it.
  custom_deny_message:
    type: str
    description:
      - Message displayed when Access denies a request.
  custom_deny_url:
    type: str
    description:
      - URL used when Access denies a request.
  destinations:
    type: list
    elements: dict
    description:
      - Public destinations protected by the application.
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
  policies:
    type: list
    elements: dict
    description:
      - Access policies attached to the application.
  same_site_cookie_attribute:
    type: str
    description:
      - SameSite attribute for the Access cookie.
  service_auth_401_redirect:
    type: bool
    description:
      - Whether to return HTTP 401 instead of redirecting to the login page when a
        Service Auth policy blocks a request.
  session_duration:
    type: str
    description:
      - Maximum duration of an authenticated Access session.
      - When omitted, the current value is left unchanged; Cloudflare defaults
        to V(24h) on create.
  skip_interstitial:
    type: bool
    description:
      - Whether to skip the Access interstitial page.
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
    cloudflare_client,
    cloudflare_error_context,
    ensure_resource_absent,
    ensure_resource_present,
    find_resource,
    payload_from_params,
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
    "session_duration": "24h",
}

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
STORED_FIELDS = {"bookmark": ("app_launcher_visible", "logo_url", "policies", "tags")}


def validate_type_fields(module):
    params = module.params
    unsupported = [
        field
        for field in UNSUPPORTED_FIELDS.get(params["type"], ())
        if params.get(field) is not None and params[field] != DEFAULT_FIELDS.get(field)
    ]
    if unsupported:
        module.fail_json(
            msg=f"Access applications of type {params['type']} do not support {', '.join(unsupported)}",
            unsupported_fields=unsupported,
        )


def run(module, client):
    params = module.params
    account_id = params["account_id"]
    applications = client.zero_trust.access.applications
    if params["state"] == "present":
        validate_type_fields(module)

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

    ensure_resource_present(
        module,
        "access_app",
        "Access application",
        current,
        payload_from_params(params, FIELDS),
        create=lambda payload: applications.create(account_id=account_id, **payload),
        update=lambda app_id, payload: applications.update(app_id, account_id=account_id, **payload),
        expected_name=params["name"],
        defaults=DEFAULT_FIELDS,
        preserved_fields=preserved_fields,
        exact_values=("cors_headers",),
        context={"account_id": account_id},
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
