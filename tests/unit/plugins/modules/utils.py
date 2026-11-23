# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

import json
from contextlib import contextmanager
from unittest.mock import patch

import cloudflare
import httpx

from ansible.module_utils import basic

from ansible_collections.linuxhq.cloudflare.plugins.module_utils import cloudflare_utils

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


def malformed_response(*args, **kwargs):
    """Raise the error the SDK raises when a 2xx response body is not JSON.

    Use it as a Mock side_effect for an SDK method.
    """
    transport = httpx.MockTransport(lambda request: httpx.Response(200, text="<html>OK</html>"))
    with cloudflare.Cloudflare(
        api_token="EXAMPLE-token", max_retries=0, http_client=httpx.Client(transport=transport)
    ) as client:
        client.zones.get(zone_id="zone")


# Page results the SDK reads as an empty page, which are malformed list data.
FALSY_PAGE_RESULTS = ({}, "", 0, False)


def sdk_client(respond):
    """Return a Cloudflare client that sends each request once, to respond."""
    return cloudflare.Cloudflare(
        api_token="EXAMPLE-token", max_retries=0, http_client=httpx.Client(transport=httpx.MockTransport(respond))
    )


def list_response(result, requests):
    """Return a respond function that answers each request with result, recording the request in requests."""

    def respond(request):
        requests.append(request)
        return httpx.Response(200, json={"success": True, "errors": [], "messages": [], "result": result})

    return respond


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


def failed_create(*reads):
    """Return a respond function that answers a POST with a 500 status and each other request with the next of reads."""
    reads = list(reads)

    def respond(request):
        if request.method == "POST":
            return httpx.Response(500, json={"success": False, "errors": [], "messages": []})

        return reads.pop(0)

    return respond


def run_through_client(run, module, respond):
    """Run a module's run() inside cloudflare_client, sending each request without SDK retries to respond.

    Return the values the module exited or failed with, and the method and path of each request.
    """
    requests = []

    def recorded(request):
        requests.append((request.method, request.url.path))
        return respond(request)

    def build(http_client, **kwargs):
        transport = httpx.MockTransport(recorded)
        return cloudflare.Cloudflare(
            **kwargs, max_retries=0, http_client=httpx.Client(transport=transport, event_hooks=http_client.event_hooks)
        )

    try:
        with (
            patch.object(cloudflare_utils, "Cloudflare", side_effect=build),
            cloudflare_utils.cloudflare_client(module) as client,
        ):
            run(module, client)
    except ModuleResult as exc:
        return exc.values, requests

    raise AssertionError("the module neither exited nor failed")
