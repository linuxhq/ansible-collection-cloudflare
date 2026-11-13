# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

import json
from contextlib import contextmanager
from unittest.mock import patch

import cloudflare
import httpx

from ansible.module_utils import basic

REQUEST = httpx.Request("GET", "https://api.cloudflare.com/client/v4/")


class ModuleResult(Exception):
    def __init__(self, values):
        super().__init__(values)
        self.values = values


class ModuleExit(ModuleResult):
    pass


class ModuleFail(ModuleResult):
    pass


class FakeModule:
    def __init__(self, params, check_mode=False):
        self.check_mode = check_mode
        self.params = params

    def exit_json(self, **values):
        raise ModuleExit(values)

    def fail_json(self, **values):
        raise ModuleFail(values)


def status_error(status_code, body=None):
    """Return the SDK exception Cloudflare raises for an HTTP error status."""
    body = body if body is not None else {"success": False, "errors": [], "messages": []}
    response = httpx.Response(status_code, json=body, request=REQUEST)
    error_class = {
        400: cloudflare.BadRequestError,
        401: cloudflare.AuthenticationError,
        403: cloudflare.PermissionDeniedError,
        404: cloudflare.NotFoundError,
        409: cloudflare.ConflictError,
        422: cloudflare.UnprocessableEntityError,
        429: cloudflare.RateLimitError,
    }.get(status_code, cloudflare.InternalServerError if status_code >= 500 else cloudflare.APIStatusError)
    return error_class(f"Error code: {status_code}", response=response, body=body)


def connection_error():
    return cloudflare.APIConnectionError(request=REQUEST)


def timeout_error():
    return cloudflare.APITimeoutError(request=REQUEST)


@contextmanager
def patch_module_args(args):
    """Expose module args to AnsibleModule on every supported ansible-core.

    ansible.module_utils.testing exists only in ansible-core 2.19 and later.
    """
    try:
        from ansible.module_utils.testing import patch_module_args as core_patch_module_args
    except ImportError:
        with patch.object(basic, "_ANSIBLE_ARGS", json.dumps({"ANSIBLE_MODULE_ARGS": args}).encode()):
            yield
    else:
        with core_patch_module_args(args):
            yield
