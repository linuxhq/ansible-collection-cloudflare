# Copyright: Ansible Project
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)


class ModuleDocFragment:
    DOCUMENTATION = r"""
options:
  api_token:
    description:
      - Cloudflare API token.
    required: true
    type: str
requirements:
  - python >= 3.9
  - cloudflare >= 5.8.0, < 6
attributes:
  check_mode:
    description: Supports predicting changes without applying them.
    support: full
  diff_mode:
    description: Determines whether the module returns change details in diff format.
    support: none
"""

    ACCOUNT = r"""
options:
  account_id:
    description:
      - Cloudflare account identifier.
    required: true
    type: str
"""
