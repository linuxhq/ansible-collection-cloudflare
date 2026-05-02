#!/usr/bin/python

# Copyright: (c) 2026, Taylor Kimball
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import absolute_import, division, print_function

__metaclass__ = type


DOCUMENTATION = r"""
---
module: accounts_info
short_description: Gather Cloudflare account information
description:
  - Gather Cloudflare account information by name.
author:
  - Taylor Kimball (@tkimball83)
options:
  api_token:
    description:
      - Cloudflare API token with permissions to read account settings.
    required: true
    type: str
    no_log: true
  name:
    description:
      - Cloudflare account name to look up.
    required: true
    type: str
requirements:
  - python >= 3.9
  - cloudflare >= 4.3.1, < 5
"""

EXAMPLES = r"""
- name: Gather account information
  linuxhq.cloudflare.accounts_info:
    api_token: "{{ accounts_info_api_token }}"
    name: "{{ accounts_info_name }}"
"""

RETURN = r"""
account:
  description: Cloudflare account information.
  returned: always
  type: dict
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


def iter_accounts(page):
    result = getattr(page, "result", None)
    if result is not None:
        return result

    return page


def find_account(client, name):
    page = client.accounts.list(
        name=name,
        per_page=1000,
    )
    for account in iter_accounts(page):
        if getattr(account, "name", None) == name:
            return serialize_resource(account)

    return None


def run_module():
    module = AnsibleModule(
        argument_spec={
            "api_token": {"required": True, "type": "str", "no_log": True},
            "name": {"required": True, "type": "str"},
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
            account = find_account(client, module.params["name"])
    except cloudflare.APIConnectionError as exc:
        fail_from_cloudflare_error(module, "Cloudflare API connection failed", exc)
    except cloudflare.APIStatusError as exc:
        fail_from_cloudflare_error(module, "Cloudflare API request failed", exc)

    module.exit_json(
        changed=False,
        account=account,
    )


def main():
    run_module()


if __name__ == "__main__":
    main()
