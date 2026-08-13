#!/usr/bin/python
# Copyright: Ansible Project
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)


DOCUMENTATION = r"""
---
module: access_apps
short_description: Manage Cloudflare Access applications
description:
  - Create, update, and delete Cloudflare Access applications by name.
  - Secret fields are redacted from returned applications.
version_added: '2.0.0'
author:
  - Taylor Kimball (@tkimball83)
options:
  account_id:
    description:
      - Cloudflare account identifier.
    required: true
    type: str
  api_token:
    description:
      - Cloudflare API token with permissions to manage Access applications.
    required: true
    type: str
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
      - Required when O(state=present).
    type: str
  allowed_idps:
    type: list
    elements: str
    description:
      - Identity provider identifiers allowed for the application.
  app_launcher_visible:
    type: bool
    default: true
    description:
      - Whether to show the application in the Access application launcher.
  auto_redirect_to_identity:
    type: bool
    default: false
    description:
      - Whether to redirect users to the identity provider automatically.
  cors_headers:
    type: dict
    description:
      - Cross-origin resource sharing headers for the application.
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
  enable_binding_cookie:
    type: bool
    default: false
    description:
      - Whether to bind the Access cookie to the user session.
  http_only_cookie_attribute:
    type: bool
    default: true
    description:
      - Whether the Access cookie uses the HTTP-only attribute.
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
      - Whether service authentication failures redirect with HTTP 401.
  session_duration:
    type: str
    default: 24h
    description:
      - Maximum duration of an authenticated Access session.
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
    cloudflare_path,
    delete_result,
    find_by_name,
    normalize_current_by_desired_fields,
    payload_from_params,
    post_result,
    put_result,
    redact_access_app_secrets,
    resource_field,
    resource_id,
    select_fields,
    validate_requested_values,
    values_differ,
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

DEFAULT_FIELDS = {
    "app_launcher_visible": True,
    "auto_redirect_to_identity": False,
    "enable_binding_cookie": False,
    "http_only_cookie_attribute": True,
    "session_duration": "24h",
}


def endpoint(account_id):
    return cloudflare_path("accounts", account_id, "access", "apps")


def item_endpoint(account_id, app_id):
    return cloudflare_path("accounts", account_id, "access", "apps", app_id)


def ensure_present(module, client):
    params = module.params

    current = redact_access_app_secrets(
        find_by_name(
            client,
            endpoint(params["account_id"]),
            params["name"],
            extra_query={"exact": "true"},
            paginate=False,
        )
    )

    payload = payload_from_params(params, FIELDS)

    if current is None:
        if module.check_mode:
            module.exit_json(changed=True, message="Access application would be created")

        access_app = post_result(client, endpoint(params["account_id"]), payload)
        resource_id(module, access_app, "Access application")
        resource_field(module, access_app, "name", "Access application", expected=params["name"])
        validate_requested_values(
            module,
            {**DEFAULT_FIELDS, **access_app},
            payload,
            "Access application",
        )
        module.exit_json(
            changed=True,
            message="Access application created",
            access_app=redact_access_app_secrets(access_app),
        )

    current_id = resource_id(module, current, "Access application")
    comparable_current = {**DEFAULT_FIELDS, **current}

    if not values_differ(
        normalize_current_by_desired_fields(
            select_fields(comparable_current, payload.keys()),
            payload,
        ),
        payload,
    ):
        module.exit_json(
            changed=False,
            message="Access application already present",
            access_app=current,
        )

    if module.check_mode:
        module.exit_json(
            changed=True,
            message="Access application would be updated",
            access_app=current,
        )

    access_app = put_result(
        client,
        item_endpoint(params["account_id"], current_id),
        payload,
    )
    resource_id(module, access_app, "Access application", expected=current_id)
    resource_field(module, access_app, "name", "Access application", expected=params["name"])
    validate_requested_values(
        module,
        {**DEFAULT_FIELDS, **access_app},
        payload,
        "Access application",
    )
    module.exit_json(
        changed=True,
        message="Access application updated",
        access_app=redact_access_app_secrets(access_app),
    )


def ensure_absent(module, client):
    params = module.params

    current = redact_access_app_secrets(
        find_by_name(
            client,
            endpoint(params["account_id"]),
            params["name"],
            extra_query={"exact": "true"},
            paginate=False,
        )
    )

    if current is None:
        module.exit_json(changed=False, message="Access application already absent")

    current_id = resource_id(module, current, "Access application")

    if module.check_mode:
        module.exit_json(
            changed=True,
            message="Access application would be deleted",
            access_app=current,
        )

    delete_result(client, item_endpoint(params["account_id"], current_id), expected_id=current_id)
    module.exit_json(
        changed=True,
        message="Access application deleted",
        access_app=current,
    )


def main():
    module = AnsibleModule(
        argument_spec={
            "account_id": {"required": True, "type": "str"},
            "api_token": {"required": True, "type": "str", "no_log": True},
            "name": {"required": True, "type": "str"},
            "domain": {"type": "str"},
            "type": {"type": "str"},
            "allowed_idps": {"type": "list", "elements": "str"},
            "app_launcher_visible": {"type": "bool", "default": True},
            "auto_redirect_to_identity": {"type": "bool", "default": False},
            "cors_headers": {"type": "dict"},
            "custom_deny_message": {"type": "str"},
            "custom_deny_url": {"type": "str"},
            "destinations": {"type": "list", "elements": "dict"},
            "enable_binding_cookie": {"type": "bool", "default": False},
            "http_only_cookie_attribute": {"type": "bool", "default": True},
            "logo_url": {"type": "str"},
            "policies": {"type": "list", "elements": "dict"},
            "same_site_cookie_attribute": {"type": "str"},
            "service_auth_401_redirect": {"type": "bool"},
            "session_duration": {"type": "str", "default": "24h"},
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
        if module.params["state"] == "present":
            ensure_present(module, client)
        else:
            ensure_absent(module, client)


if __name__ == "__main__":
    main()
