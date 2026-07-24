# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)


DOCUMENTATION = r"""
---
module: access_apps_info
short_description: Gather information about cloudflare access apps
description:
  - Gather Cloudflare Access applications for an account.
  - Secret fields under C(scim_config.authentication) are redacted from the
    results.
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
      - Cloudflare API token with permissions to read Access applications.
    required: true
    type: str
requirements:
  - python >= 3.9
  - cloudflare >= 5.6.0, < 6

"""

EXAMPLES = r"""
- name: Gather Access applications
  linuxhq.cloudflare.access_apps_info:
    account_id: "{{ account_id }}"
    api_token: "{{ cloudflare_api_token }}"
"""

RETURN = r"""
---
access_apps:
  description: Cloudflare Access applications.
  returned: always
  type: list
  elements: dict

"""

from ansible.module_utils.basic import AnsibleModule
from ansible_collections.linuxhq.cloudflare.plugins.module_utils.cloudflare_utils import (
    cloudflare_client,
    list_all,
    redact_scim_secrets,
)


def list(module, client):
    access_apps = list_all(
        client,
        "/accounts/{}/access/apps".format(module.params["account_id"]),
    )

    for access_app in access_apps:
        redact_scim_secrets(access_app)

    module.exit_json(changed=False, access_apps=access_apps)


def main():
    module = AnsibleModule(
        argument_spec={
            "account_id": {"required": True, "type": "str"},
            "api_token": {"required": True, "type": "str", "no_log": True},
        },
        supports_check_mode=True,
    )

    with cloudflare_client(module) as client:
        list(module, client)


if __name__ == "__main__":
    main()
