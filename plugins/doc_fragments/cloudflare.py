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
  - cloudflare >= 5.10.0, < 6
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

    CREATE = r"""
options: {}
notes:
  - Requests that create a resource are sent without the Cloudflare SDK's automatic retries, which could create a
    duplicate. When Cloudflare rejects one with a 409 or 429 status, it created nothing, so the request is retried up
    to twice, after the delay the response's C(Retry-After-Ms) or C(Retry-After) header asks for when that is at
    most 60 seconds, or otherwise after 0.5 and then 1 second.
  - When a create request fails without a response, such as after a timeout, or with a 5xx status, Cloudflare may
    have created the resource anyway, so the request is not retried and the module looks the resource up again as it
    did before creating it. A single match is treated as the created resource; otherwise the module fails with the
    original error.
"""
