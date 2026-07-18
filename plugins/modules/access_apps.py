#!/usr/bin/python
# -*- coding: utf-8 -*-
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import absolute_import, division, print_function

__metaclass__ = type

DOCUMENTATION = r"""
---
module: access_apps
short_description: Manage cloudflare access apps
description:
  - Create, update, and delete Cloudflare Access applications by name.
  - Secret fields under C(scim_config.authentication) are redacted from returned
    applications.
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
      - Required when state is C(present).
    type: str
  type:
    description:
      - Access application type.
      - Required when state is C(present).
    type: str
  allowed_idps:
    type: list
    elements: str
    description:
      - Allowed idps.
  app_launcher_visible:
    type: bool
    default: true
    description:
      - App launcher visible.
  auto_redirect_to_identity:
    type: bool
    default: false
    description:
      - Auto redirect to identity.
  cors_headers:
    type: dict
    description:
      - Cors headers.
  custom_deny_message:
    type: str
    description:
      - Custom deny message.
  custom_deny_url:
    type: str
    description:
      - Custom deny url.
  destinations:
    type: list
    elements: dict
    description:
      - Destinations.
  enable_binding_cookie:
    type: bool
    default: false
    description:
      - Enable binding cookie.
  http_only_cookie_attribute:
    type: bool
    default: true
    description:
      - Http only cookie attribute.
  logo_url:
    type: str
    description:
      - Logo url.
  policies:
    type: list
    elements: dict
    description:
      - Policies.
  same_site_cookie_attribute:
    type: str
    description:
      - Same site cookie attribute.
  service_auth_401_redirect:
    type: bool
    description:
      - Service auth 401 redirect.
  session_duration:
    type: str
    default: 24h
    description:
      - Session duration.
  skip_interstitial:
    type: bool
    description:
      - Skip interstitial.
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
  - cloudflare >= 5.5.0, < 6

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
message:
  description: Operation summary.
  returned: always
  type: str

"""

from ansible.module_utils.basic import AnsibleModule

from ansible_collections.linuxhq.cloudflare.plugins.module_utils.cloudflare_utils import (
    cloudflare_client,
    delete_result,
    find_by_name,
    normalize_current_by_desired_fields,
    payload_from_params,
    post_result,
    put_result,
    redact_scim_secrets,
    select_fields,
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
    return "/accounts/%s/access/apps" % account_id


def item_endpoint(account_id, app_id):
    return "%s/%s" % (endpoint(account_id), app_id)


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

    params = module.params
    state = params["state"]

    with cloudflare_client(module) as client:
        current = redact_scim_secrets(
            find_by_name(
                client,
                endpoint(params["account_id"]),
                params["name"],
                extra_query={"exact": "true"},
                paginate=False,
            )
        )

        if state == "absent":
            if current is None:
                module.exit_json(
                    changed=False, message="Access application already absent"
                )

            if module.check_mode:
                module.exit_json(
                    changed=True,
                    message="Access application would be deleted",
                    access_app=current,
                )

            delete_result(client, item_endpoint(params["account_id"], current["id"]))
            module.exit_json(
                changed=True,
                message="Access application deleted",
                access_app=current,
            )

        if state == "present":
            payload = payload_from_params(params, FIELDS)
            if current is None:
                if module.check_mode:
                    module.exit_json(
                        changed=True, message="Access application would be created"
                    )

                access_app = post_result(
                    client, endpoint(params["account_id"]), payload
                )
                module.exit_json(
                    changed=True,
                    message="Access application created",
                    access_app=redact_scim_secrets(access_app),
                )

            comparable_current = current.copy()
            for field, value in DEFAULT_FIELDS.items():
                comparable_current.setdefault(field, value)

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
                item_endpoint(params["account_id"], current["id"]),
                payload,
            )
            module.exit_json(
                changed=True,
                message="Access application updated",
                access_app=redact_scim_secrets(access_app),
            )


if __name__ == "__main__":
    main()
