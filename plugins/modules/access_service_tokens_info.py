#!/usr/bin/python

# Copyright: (c) 2026, Taylor Kimball
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import absolute_import, division, print_function

__metaclass__ = type


DOCUMENTATION = r"""
---
module: access_service_tokens_info
short_description: Gather Cloudflare Access service token information
description:
  - Gather Cloudflare Access service tokens for an account.
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
      - Cloudflare API token with permissions to read Access service tokens.
    required: true
    type: str
    no_log: true
requirements:
  - python >= 3.9
  - cloudflare >= 4.3.1, < 5
"""

EXAMPLES = r"""
- name: Gather service token information
  linuxhq.cloudflare.access_service_tokens_info:
    account_id: "{{ access_service_tokens_info_account_id }}"
    api_token: "{{ access_service_tokens_info_api_token }}"
"""

RETURN = r"""
service_tokens:
  description: List of Cloudflare Access service tokens.
  returned: always
  type: list
  elements: dict
"""

from ansible.module_utils.basic import AnsibleModule

try:
    import cloudflare
    from cloudflare import Cloudflare
except ImportError:
    cloudflare = None
    Cloudflare = None


def serialize_resource(resource):
    if resource is None:
        return None

    if hasattr(resource, "to_dict"):
        return resource.to_dict()

    return resource


def fail_from_cloudflare_error(module, message, exc):
    response = getattr(exc, "response", None)
    status_code = getattr(exc, "status_code", None)
    response_body = None

    if response is not None:
        if hasattr(response, "json"):
            try:
                response_body = response.json()
            except Exception:
                response_body = None
        if response_body is None and hasattr(response, "text"):
            response_body = response.text

    module.fail_json(
        msg=message,
        error=str(exc),
        status_code=status_code,
        response=response_body,
    )


def iter_service_tokens(page):
    result = getattr(page, "result", None)
    if result is not None:
        return result

    return page


def list_service_tokens(client, account_id):
    page = client.zero_trust.access.service_tokens.list(
        account_id=account_id,
        per_page=1000,
    )
    return [serialize_resource(item) for item in iter_service_tokens(page)]


def run_module():
    module = AnsibleModule(
        argument_spec={
            "account_id": {"required": True, "type": "str"},
            "api_token": {"required": True, "type": "str", "no_log": True},
        },
        supports_check_mode=True,
    )

    if Cloudflare is None:
        module.fail_json(
            msg="The official Cloudflare Python SDK is required for this module",
            missing_python_package="cloudflare",
        )

    try:
        with Cloudflare(api_token=module.params["api_token"]) as client:
            service_tokens = list_service_tokens(client, module.params["account_id"])
    except cloudflare.APIConnectionError as exc:
        fail_from_cloudflare_error(module, "Cloudflare API connection failed", exc)
    except cloudflare.APIStatusError as exc:
        fail_from_cloudflare_error(module, "Cloudflare API request failed", exc)

    module.exit_json(
        changed=False,
        service_tokens=service_tokens,
    )


def main():
    run_module()


if __name__ == "__main__":
    main()
