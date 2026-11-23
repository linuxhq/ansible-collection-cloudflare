# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

import os
from datetime import datetime, timezone
from unittest import TestCase
from unittest.mock import ANY, Mock, patch

import cloudflare
import httpx

from ansible_collections.linuxhq.cloudflare.plugins.module_utils import cloudflare_utils
from ansible_collections.linuxhq.cloudflare.plugins.module_utils.cloudflare_utils import (
    access_rules_payload,
    applied_differences,
    checked_written,
    cloudflare_client,
    cloudflare_error_context,
    cloudflare_error_details,
    create_once,
    differs,
    ensure_resource_absent,
    ensure_resource_present,
    ensure_settings,
    exit_resource_list,
    exit_settings,
    fail_not_applied,
    find_resource,
    get_or_none,
    list_all_pages,
    matching_resources,
    normalize_current_by_desired_fields,
    payload_from_params,
    require_applied,
    require_mapping,
    resource_field,
    resource_id,
    resource_list,
    serialize_resource,
    unsupported_fields,
    valid_dns_labels,
    validate_access_selectors,
    values_differ,
    without_nested_nulls,
    without_retries,
    zone_missing,
)
from ansible_collections.linuxhq.cloudflare.tests.unit.plugins.modules.utils import (
    FALSY_PAGE_RESULTS,
    FakeModule,
    ModuleExit,
    ModuleFail,
    connection_error,
    list_response,
    malformed_response,
    sdk_client,
    status_error,
    timeout_error,
)


class SdkModel:
    def __init__(self, resource_id, expires_at):
        self.resource_id = resource_id
        self.expires_at = expires_at

    def to_dict(self, mode=None, warnings=True):
        if mode != "json":
            raise ValueError("expected JSON serialization")

        return {
            "id": self.resource_id,
            "expires_at": self.expires_at.isoformat().replace("+00:00", "Z"),
        }


EXPECTED_HEADERS = {
    "Authorization": "Bearer secret",
    "X-Auth-Email": cloudflare.omit,
    "X-Auth-Key": cloudflare.omit,
    "X-Auth-User-Service-Key": cloudflare.omit,
}


def sdk_constructor(respond, **options):
    """Return a Cloudflare constructor whose client sends each request to respond.

    The HTTP client keeps the event hooks cloudflare_client gives it.
    """

    def build(http_client, **kwargs):
        transport = httpx.MockTransport(respond)
        return cloudflare.Cloudflare(
            **kwargs, **options, http_client=httpx.Client(transport=transport, event_hooks=http_client.event_hooks)
        )

    return build


def sdk_context(client):
    context = Mock()
    context.__enter__ = Mock(return_value=client)
    context.__exit__ = Mock(return_value=False)
    return context


class ClientTests(TestCase):
    def test_client_uses_only_explicit_token_with_environment_credentials(self):
        environments = (
            {},
            {"CLOUDFLARE_EMAIL": "EXAMPLE@example.com"},
            {"CLOUDFLARE_API_KEY": "EXAMPLE-key"},
            {"CLOUDFLARE_API_USER_SERVICE_KEY": "EXAMPLE-service-key"},
            {
                "CLOUDFLARE_EMAIL": "EXAMPLE@example.com",
                "CLOUDFLARE_API_KEY": "EXAMPLE-key",
                "CLOUDFLARE_API_USER_SERVICE_KEY": "EXAMPLE-service-key",
                "CLOUDFLARE_API_TOKEN": "EXAMPLE-environment-token",
            },
            {"CLOUDFLARE_CUSTOM_HEADERS": "Authorization: Bearer EXAMPLE-ambient"},
            {"CLOUDFLARE_CUSTOM_HEADERS": "authorization: Bearer EXAMPLE-ambient"},
            {
                "CLOUDFLARE_EMAIL": "EXAMPLE@example.com",
                "CLOUDFLARE_API_KEY": "EXAMPLE-key",
                "CLOUDFLARE_API_USER_SERVICE_KEY": "EXAMPLE-service-key",
                "CLOUDFLARE_CUSTOM_HEADERS": (
                    " Authorization : Bearer EXAMPLE-ambient\n"
                    "aUtHoRiZaTiOn: Bearer EXAMPLE-other\n"
                    "X-Auth-Email: EXAMPLE@example.com\n"
                    "x-auth-email: EXAMPLE-other@example.com\n"
                    "X-Auth-Key: EXAMPLE-key\n"
                    "x-AUTH-key: EXAMPLE-other-key\n"
                    "X-Auth-User-Service-Key: EXAMPLE-service-key\n"
                    "x-auth-user-service-key: EXAMPLE-other-service-key\n"
                    "X-Example-Trace: preserve-me"
                ),
            },
        )
        for environment in environments:
            with self.subTest(environment=environment):
                requests = []

                def respond(request, record=requests.append):
                    record(request)
                    return httpx.Response(200, json={"success": True, "result": {"id": "zone"}})

                with (
                    patch.dict(os.environ, environment, clear=True),
                    patch.object(cloudflare_utils, "Cloudflare", side_effect=sdk_constructor(respond)),
                    cloudflare_client(FakeModule({"api_token": "  EXAMPLE-explicit-token  "})) as client,
                ):
                    client.zones.get(zone_id="zone")
                    client.with_options(timeout=5, max_retries=0).zones.get(zone_id="zone")
                    self.assertEqual(dict(os.environ), environment)

                self.assertEqual(len(requests), 2)
                for request in requests:
                    self.assertEqual(request.headers["Authorization"], "Bearer EXAMPLE-explicit-token")
                    if "X-Example-Trace" in environment.get("CLOUDFLARE_CUSTOM_HEADERS", ""):
                        self.assertEqual(request.headers["X-Example-Trace"], "preserve-me")

                    for header in ("X-Auth-Email", "X-Auth-Key", "X-Auth-User-Service-Key"):
                        self.assertNotIn(header, request.headers)

    def test_client_reports_missing_sdk(self):
        with (
            patch.object(cloudflare_utils, "Cloudflare", None),
            self.assertRaises(ModuleFail) as raised,
            cloudflare_client(FakeModule({"api_token": "secret"})),
        ):
            pass

        self.assertEqual(raised.exception.values["missing_python_package"], "cloudflare")

    def test_client_closes_sdk_context(self):
        client = Mock()
        context = sdk_context(client)
        constructor = Mock(return_value=context)

        with (
            patch.object(cloudflare_utils, "Cloudflare", constructor),
            cloudflare_client(FakeModule({"api_token": "secret"})) as result,
        ):
            self.assertIs(result, client)

        constructor.assert_called_once_with(api_token="secret", default_headers=EXPECTED_HEADERS, http_client=ANY)
        context.__exit__.assert_called_once()

    def test_client_normalizes_token_and_rejects_empty_identifiers(self):
        constructor = Mock(return_value=sdk_context(Mock()))

        with (
            patch.object(cloudflare_utils, "Cloudflare", constructor),
            cloudflare_client(FakeModule({"api_token": "  secret  ", "name": "app"})),
        ):
            pass

        constructor.assert_called_once_with(api_token="secret", default_headers=EXPECTED_HEADERS, http_client=ANY)

        # The SDK raises ValueError for an empty path parameter.
        for name in ("account_id", "phase", "tunnel_id", "zone_id"):
            with (
                self.subTest(name=name),
                patch.object(cloudflare_utils, "Cloudflare", constructor),
                self.assertRaises(ModuleFail) as raised,
                cloudflare_client(FakeModule({"api_token": "secret", name: ""})),
            ):
                pass

            self.assertEqual(raised.exception.values["msg"], f"{name} must not be empty")

        # Cloudflare rejects these on the first request, or the module checks them.
        for name, value in (("zone_id", " \t"), ("domain", ""), ("name", ""), ("production_branch", "")):
            with (
                self.subTest(name=name, value=value),
                patch.object(cloudflare_utils, "Cloudflare", constructor),
                cloudflare_client(FakeModule({"api_token": "secret", name: value})),
            ):
                pass

    def test_client_passes_padded_values_to_cloudflare(self):
        # Cloudflare trims, rejects, or stores these as sent.
        constructor = Mock(return_value=sdk_context(Mock()))
        for name in ("account_id", "domain", "name", "phase", "production_branch", "zone_id"):
            with (
                self.subTest(name=name),
                patch.object(cloudflare_utils, "Cloudflare", constructor),
                cloudflare_client(FakeModule({"api_token": "secret", name: " value "})),
            ):
                pass

    def test_client_rejects_dot_segment_path_parameters(self):
        constructor = Mock(return_value=sdk_context(Mock()))
        for name in ("account_id", "phase", "tunnel_id", "zone_id"):
            for value in (".", ".."):
                with (
                    self.subTest(name=name, value=value),
                    patch.object(cloudflare_utils, "Cloudflare", constructor),
                    self.assertRaises(ModuleFail) as raised,
                    cloudflare_client(FakeModule({"api_token": "secret", name: value})),
                ):
                    pass

                self.assertEqual(raised.exception.values["msg"], f"{name} must not be '.' or '..'")

        constructor.assert_not_called()

        # A dot is a valid value of a parameter that is not a request path segment.
        for name in ("domain", "name", "production_branch"):
            with (
                self.subTest(name=name),
                patch.object(cloudflare_utils, "Cloudflare", constructor),
                cloudflare_client(FakeModule({"api_token": "secret", name: ".."})),
            ):
                pass

    def test_client_rejects_non_ascii_tokens(self):
        # HTTPX raises UnicodeEncodeError for the header.
        with (
            patch.object(cloudflare_utils, "Cloudflare", Mock()),
            self.assertRaises(ModuleFail) as raised,
            cloudflare_client(FakeModule({"api_token": "secr\u00e9t"})),
        ):
            pass

        self.assertEqual(raised.exception.values["msg"], "api_token must contain only ASCII characters")

    def test_client_leaves_empty_and_control_character_tokens_to_the_sdk(self):
        # The SDK fails these with a connection error before sending a request.
        for token in (" ", "secret\nvalue"):
            constructor = Mock(return_value=sdk_context(Mock()))
            with (
                self.subTest(token=token),
                patch.object(cloudflare_utils, "Cloudflare", constructor),
                cloudflare_client(FakeModule({"api_token": token})),
            ):
                pass

            constructor.assert_called_once()

    def test_client_reports_sdk_failures_with_context(self):
        cases = (
            (connection_error(), None),
            (status_error(403, {"errors": [{"message": "denied"}], "api_token": "x"}), 403),
        )
        for error, status_code in cases:
            with (
                self.subTest(error=type(error).__name__),
                patch.object(cloudflare_utils, "Cloudflare", return_value=sdk_context(Mock())),
                self.assertRaises(ModuleFail) as raised,
                cloudflare_client(FakeModule({"api_token": "secret"})),
                cloudflare_error_context("Reading the resource failed", resource_id="one"),
            ):
                raise error

            values = raised.exception.values
            self.assertEqual(values["msg"], "Reading the resource failed")
            self.assertEqual(values["resource_id"], "one")
            if status_code:
                self.assertEqual(values["status_code"], status_code)
                self.assertEqual(values["response"]["api_token"], "x")
            else:
                self.assertIn("error", values)

        with (
            patch.object(cloudflare_utils, "Cloudflare", return_value=sdk_context(Mock())),
            self.assertRaises(ModuleFail) as raised,
            cloudflare_client(FakeModule({"api_token": "secret"})),
        ):
            raise connection_error()

        self.assertEqual(raised.exception.values["msg"], "Cloudflare API connection failed")

    def test_client_reports_the_cause_of_a_connection_failure(self):
        def refuse(request):
            raise httpx.ConnectError("[Errno 8] nodename nor servname provided")

        def time_out(request):
            raise httpx.ReadTimeout("The read operation timed out")

        def reject_header(request):
            # HTTPX quotes the invalid header value, including the token.
            raise httpx.LocalProtocolError(f"Illegal header value {request.headers['Authorization'].encode()!r}")

        cases = (
            ("EXAMPLE-token", refuse, "Connection error. ConnectError: [Errno 8] nodename nor servname provided"),
            ("EXAMPLE-token", time_out, "Request timed out. ReadTimeout: The read operation timed out"),
            ("EXAMPLE-token\x7f", reject_header, "Connection error. LocalProtocolError"),
        )
        for token, respond, error in cases:
            with (
                self.subTest(error=error),
                patch.object(cloudflare_utils, "Cloudflare", side_effect=sdk_constructor(respond, max_retries=0)),
                self.assertRaises(ModuleFail) as raised,
                cloudflare_client(FakeModule({"api_token": token})) as client,
            ):
                client.zones.get(zone_id="zone")

            values = raised.exception.values
            self.assertEqual(values["msg"], "Cloudflare API connection failed")
            self.assertEqual(values["error"], error)
            self.assertNotIn("EXAMPLE", str(values))

    def test_client_reports_non_json_error_response_text(self):
        def respond(request):
            return httpx.Response(502, text="<html>502 Bad Gateway</html>")

        with (
            patch.object(cloudflare_utils, "Cloudflare", side_effect=sdk_constructor(respond, max_retries=0)),
            self.assertRaises(ModuleFail) as raised,
            cloudflare_client(FakeModule({"api_token": "secret"})) as client,
            cloudflare_error_context("Reading the zone failed", zone_id="zone"),
        ):
            client.zones.get(zone_id="zone")

        values = raised.exception.values
        self.assertEqual(values["msg"], "Reading the zone failed")
        self.assertEqual(values["zone_id"], "zone")
        self.assertEqual(values["status_code"], 502)
        self.assertEqual(values["response"], "<html>502 Bad Gateway</html>")

    def test_client_fails_cleanly_on_sdk_errors(self):
        def make_client(body):
            def respond(request):
                return httpx.Response(200, content=body, headers={"content-type": "application/json"})

            return sdk_constructor(respond, max_retries=0)

        def create_zone(client):
            return client.zones.create(account={"id": "account"}, name="example.com")

        def edit_policy(client):
            # The SDK cannot encode the value, so it sends nothing.
            return client.zero_trust.devices.policies.default.edit(account_id="account", auto_connect=float("inf"))

        cases = (
            # The body is not JSON.
            ("JSONDecodeError", b"<html>OK</html>", lambda client: client.zones.get(zone_id="zone"), False),
            # The envelope is not an object.
            ("AttributeError", b'["zone"]', lambda client: client.zones.get(zone_id="zone"), False),
            # A list page's result is not a list.
            ("TypeError", b'{"success": true, "result": 5}', lambda client: list(client.zones.list()), False),
            # Cloudflare answered the write with a 2xx status, so it was applied.
            ("JSONDecodeError", b"<html>OK</html>", create_zone, True),
            ("ValueError", b"{}", edit_policy, False),
        )
        for error, body, request, changed in cases:
            with (
                self.subTest(error=error, request=request),
                patch.object(cloudflare_utils, "Cloudflare", side_effect=make_client(body)),
                self.assertRaises(ModuleFail) as raised,
                cloudflare_client(FakeModule({"api_token": "secret"})) as client,
                cloudflare_error_context("Reading the zone failed", zone_id="zone"),
            ):
                request(client)

            values = raised.exception.values
            self.assertEqual(values["msg"], "Reading the zone failed")
            self.assertEqual(values["zone_id"], "zone")
            self.assertTrue(values["error"].startswith(f"{error}: "))
            self.assertEqual(values.get("changed"), True if changed else None)
            if error == "JSONDecodeError":
                self.assertEqual(values["status_code"], 200)
                self.assertEqual(values["response"], "<html>OK</html>")
            else:
                self.assertNotIn("response", values)

        with (
            patch.object(cloudflare_utils, "Cloudflare", side_effect=make_client(b"<html>OK</html>")),
            self.assertRaises(ModuleFail) as raised,
            cloudflare_client(FakeModule({"api_token": "secret"})) as client,
        ):
            client.zones.get(zone_id="zone")

        self.assertEqual(raised.exception.values["msg"], "Cloudflare API request failed")

    def test_client_fails_cleanly_on_retry_and_decoding_errors(self):
        # An out-of-range Retry-After date the SDK reads before retrying a 429,
        # and a 2xx body nested too deeply to decode.
        rate_limited = httpx.Response(
            429,
            headers={"Retry-After": "Mon, 01 Jan 99999999999999999999 00:00:00 GMT"},
            json={"success": False, "errors": [], "messages": []},
        )
        depth = 100000
        nested = httpx.Response(
            200,
            content=b'{"success": true, "result": ' + b"[" * depth + b"]" * depth + b"}",
            headers={"content-type": "application/json"},
        )
        for error, answer in (("OverflowError", rate_limited), ("RecursionError", nested)):
            for write in (False, True):

                def respond(request, answer=answer):
                    if request.method == "PATCH":
                        return httpx.Response(200, json={"success": True, "result": {"id": "zone"}})

                    return answer

                with self.subTest(error=error, write=write):
                    with (
                        patch.object(cloudflare_utils, "Cloudflare", side_effect=sdk_constructor(respond)),
                        self.assertRaises(ModuleFail) as raised,
                        cloudflare_client(FakeModule({"api_token": "secret"})) as client,
                        cloudflare_error_context("Reading the zone failed", zone_id="zone"),
                    ):
                        if write:
                            client.zones.edit(zone_id="zone", paused=True)

                        client.zones.get(zone_id="zone")

                    values = raised.exception.values
                    self.assertEqual(values["msg"], "Reading the zone failed")
                    self.assertEqual(values["zone_id"], "zone")
                    self.assertTrue(values["error"].startswith(f"{error}: "))
                    self.assertEqual(values.get("changed"), True if write else None)

    def test_client_reports_the_change_of_an_answered_write_on_a_later_api_error(self):
        def respond(request):
            if request.method == "PATCH":
                return httpx.Response(200, json={"success": True, "result": {"id": "zone"}})

            return httpx.Response(500, json={"success": False, "errors": [], "messages": []})

        for write in (False, True):
            with (
                self.subTest(write=write),
                patch.object(cloudflare_utils, "Cloudflare", side_effect=sdk_constructor(respond, max_retries=0)),
                self.assertRaises(ModuleFail) as raised,
                cloudflare_client(FakeModule({"api_token": "secret"})) as client,
            ):
                if write:
                    client.zones.edit(zone_id="zone", paused=True)

                client.zones.get(zone_id="zone")

            self.assertEqual(raised.exception.values["status_code"], 500)
            self.assertEqual(raised.exception.values.get("changed"), True if write else None)

    def test_client_keeps_the_traceback_of_errors_raised_outside_the_sdk(self):
        errors = (
            AttributeError("bug"),
            OverflowError("bug"),
            RecursionError("bug"),
            TypeError("bug"),
            ValueError("bug"),
        )
        for error in errors:
            with (
                self.subTest(error=type(error).__name__),
                patch.object(cloudflare_utils, "Cloudflare", return_value=sdk_context(Mock())),
                self.assertRaises(type(error)) as raised,
                cloudflare_client(FakeModule({"api_token": "secret"})),
                cloudflare_error_context("Reading the zone failed", zone_id="zone"),
            ):
                raise error

            self.assertFalse(hasattr(raised.exception, "_cloudflare_context"))

    def test_error_context_preserves_non_sdk_errors_without_sdk(self):
        with (
            patch.object(cloudflare_utils, "cloudflare", None),
            self.assertRaisesRegex(RuntimeError, "validation failed"),
            cloudflare_error_context("Request failed"),
        ):
            raise RuntimeError("validation failed")


class ValueTests(TestCase):
    def test_serializes_sdk_models_to_json_values(self):
        expires_at = datetime(2026, 8, 11, 12, 30, tzinfo=timezone.utc)

        with patch.object(cloudflare_utils, "BaseModel", SdkModel):
            self.assertEqual(
                serialize_resource([SdkModel("token", expires_at), {"name": None}]),
                [{"id": "token", "expires_at": "2026-08-11T12:30:00Z"}, {}],
            )

    def test_serializes_without_warnings_argument_on_pydantic_v1(self):
        model = Mock(spec=["to_dict"])
        model.to_dict.return_value = {"id": "one"}

        for pydantic_v2, expected in ((True, {"mode": "json", "warnings": False}), (False, {"mode": "json"})):
            with self.subTest(pydantic_v2=pydantic_v2):
                with (
                    patch.object(cloudflare_utils, "BaseModel", Mock),
                    patch.object(cloudflare_utils, "PYDANTIC_V2", pydantic_v2),
                ):
                    self.assertEqual(serialize_resource(model), {"id": "one"})

                self.assertEqual(model.to_dict.call_args.kwargs, expected)

    def test_comparison_manages_only_desired_fields(self):
        desired = {"nested": {"enabled": True}, "items": [{"id": "one"}]}
        current = {
            "ignored": "value",
            "nested": {"enabled": True, "provider": "value"},
            "items": [{"id": "one", "provider": "value"}],
        }

        self.assertEqual(normalize_current_by_desired_fields(current, desired), desired)
        self.assertFalse(values_differ(desired, desired.copy()))
        self.assertFalse(differs(current, desired))
        self.assertTrue(differs(current, {"nested": {"enabled": False}}))
        self.assertFalse(differs(current, {}))
        self.assertFalse(differs({}, {"enabled": False}, defaults={"enabled": False}))
        self.assertTrue(differs({}, {"enabled": False}))
        self.assertTrue(differs({"include": [{"email": {}}]}, {"include": [{"everyone": {}}]}))
        headers = {"headers": {"A": {"value": 1, "extra": 2}, "B": {"value": 2}}}
        self.assertFalse(differs(headers, {"headers": {"A": {"value": 1}}}))
        self.assertEqual(
            payload_from_params({"enabled": False, "name": None}, ("enabled", "name", "count")),
            {"enabled": False},
        )

    def test_comparison_distinguishes_booleans_from_numbers(self):
        for number, boolean in ((1, True), (0, False), ({"a": [1]}, {"a": [True]})):
            with self.subTest(number=number, boolean=boolean):
                self.assertTrue(values_differ(number, boolean))
                self.assertTrue(values_differ(boolean, number))

        self.assertFalse(values_differ({"ttl": 60.0}, {"ttl": 60}))
        self.assertTrue(differs({"enabled": 1}, {"enabled": True}))

    def test_require_applied_rejects_nested_mismatch(self):
        require_applied(FakeModule({}), {"a": {"b": 1, "c": 2}}, {"a": {"b": 1}}, "resource")

        with self.assertRaises(ModuleFail) as raised:
            require_applied(FakeModule({}), {"a": {"b": 2}}, {"a": {"b": 1}}, "resource")

        self.assertEqual(
            raised.exception.values["msg"],
            'Cloudflare did not apply the requested resource: a requested {"b": 1}, stored {"b": 2}',
        )
        self.assertEqual(
            raised.exception.values["differences"], [{"field": "a", "requested": {"b": 1}, "stored": {"b": 2}}]
        )

    def test_require_applied_names_requested_and_stored_values(self):
        stored = {"id": "group", "name": "example", "include": [{"ip": {"ip": "192.0.2.1/32"}}]}
        requested = {"name": "example", "include": [{"ip": {"ip": "192.0.2.1"}}]}

        with self.assertRaises(ModuleFail) as raised:
            require_applied(FakeModule({}), stored, requested, "Access group")

        self.assertEqual(
            raised.exception.values["msg"],
            "Cloudflare did not apply the requested Access group: "
            'include requested [{"ip": {"ip": "192.0.2.1"}}], stored [{"ip": {"ip": "192.0.2.1/32"}}]',
        )
        self.assertEqual(
            raised.exception.values["differences"],
            [
                {
                    "field": "include",
                    "requested": [{"ip": {"ip": "192.0.2.1"}}],
                    "stored": [{"ip": {"ip": "192.0.2.1/32"}}],
                }
            ],
        )

    def test_require_applied_names_compared_stored_values(self):
        with self.assertRaises(ModuleFail) as raised:
            require_applied(
                FakeModule({}),
                {"a": {"b": 1, "c": 2}, "d": 1},
                {"a": {"b": 1}, "d": 1, "e": True},
                "resource",
                defaults={"e": False},
                exact_values=("a",),
            )

        self.assertEqual(
            raised.exception.values["differences"],
            [
                {"field": "a", "requested": {"b": 1}, "stored": {"b": 1, "c": 2}},
                {"field": "e", "requested": True, "stored": False},
            ],
        )

    def test_applied_differences_lists_only_differing_fields(self):
        self.assertEqual(
            applied_differences({"a": 1, "b": None, "c": 1, "e": 2}, {"a": 1, "c": True, "d": 3}),
            [
                {"field": "c", "requested": True, "stored": 1},
                {"field": "d", "requested": 3, "stored": None},
                {"field": "e", "requested": None, "stored": 2},
            ],
        )
        self.assertEqual(applied_differences({"a": [1]}, {"a": [1]}), [])

    def test_fail_not_applied_limits_the_message(self):
        differences = [{"field": f"f{index}", "requested": index, "stored": None} for index in range(12)]

        with self.assertRaises(ModuleFail) as raised:
            fail_not_applied(FakeModule({}), "resource", differences)

        self.assertTrue(
            raised.exception.values["msg"].endswith(
                "f9 requested 9, stored null; 2 more fields are listed in differences"
            )
        )
        self.assertEqual(raised.exception.values["differences"], differences)

    def test_fail_not_applied_masks_escaped_no_log_values(self):
        module = FakeModule({})
        module.no_log_values = {'se"cret', "plain"}

        with self.assertRaises(ModuleFail) as raised:
            fail_not_applied(module, "resource", [{"field": "a", "requested": 'se"cret', "stored": "plain"}])

        self.assertNotIn('se\\"cret', raised.exception.values["msg"])
        self.assertEqual(
            raised.exception.values["msg"],
            'Cloudflare did not apply the requested resource: a requested "********", stored "plain"',
        )

    def test_validates_required_resource_fields(self):
        module = FakeModule({})

        self.assertEqual(resource_id(module, {"id": "one"}, "resource"), "one")
        self.assertEqual(resource_field(module, {"name": "example"}, "name", "resource"), "example")
        require_mapping(module, {"id": "one"}, "resource")

        with self.assertRaises(ModuleFail) as raised:
            resource_id(module, {"id": "one"}, "resource", expected="two")

        self.assertEqual(raised.exception.values["msg"], "Cloudflare API returned the wrong resource")

        for resource in (None, {}, {"id": None}, {"id": " "}, {"id": " one"}, {"id": 1}):
            with self.subTest(resource=resource), self.assertRaises(ModuleFail) as raised:
                resource_id(module, resource, "resource")

            self.assertEqual(raised.exception.values["msg"], "Cloudflare API returned malformed resource data")

    def test_checked_written_reports_the_expected_id(self):
        module = FakeModule({})
        context = {"account_id": "account"}

        resource, failure = checked_written(
            module, {"id": "one", "name": "One"}, "resource", "item", context, expected_name="One", expected_id="one"
        )

        self.assertEqual(resource, {"id": "one", "name": "One"})
        self.assertEqual(
            failure,
            {"changed": True, "account_id": "account", "item": resource, "resource_id": "one"},
        )
        self.assertEqual(context, {"account_id": "account"})
        for written, msg in (
            ({"id": "two", "name": "One"}, "Cloudflare API returned the wrong resource"),
            ({"id": "one", "name": "Two"}, "Cloudflare API returned the wrong resource"),
            ({"name": "One"}, "Cloudflare API returned malformed resource data"),
        ):
            with self.subTest(written=written), self.assertRaises(ModuleFail) as raised:
                checked_written(module, written, "resource", "item", context, expected_name="One", expected_id="one")

            self.assertEqual(
                raised.exception.values,
                {"msg": msg, "changed": True, "account_id": "account", "item": written, "resource_id": "one"},
            )

    def test_lists_and_finds_resources(self):
        module = FakeModule({})
        items = [{"id": "one", "name": "One"}, {"id": "two", "name": "Two"}]

        self.assertEqual(resource_list(module, iter(items), "resource", ("id", "name")), items)
        self.assertEqual(find_resource(module, iter(items), "resource", "name", "Two"), items[1])
        self.assertIsNone(find_resource(module, iter(items), "resource", "name", "Three"))

        with self.assertRaises(ModuleFail):
            find_resource(module, [{"id": "one", "name": "One"}, "not a mapping"], "resource", "name", "One")

    def test_find_resource_skips_items_without_the_field(self):
        # Cloudflare stores an Access policy, group, or token with an empty name as null.
        items = [{"id": "nameless"}, {"id": "null", "name": None}, {"id": "one", "name": "One"}]

        self.assertEqual(find_resource(FakeModule({}), iter(items), "resource", "name", "One"), items[2])
        self.assertIsNone(find_resource(FakeModule({}), iter(items[:2]), "resource", "name", "One"))

    def test_get_or_none_maps_only_not_found(self):
        self.assertIsNone(get_or_none(Mock(side_effect=status_error(404))))
        self.assertEqual(get_or_none(Mock(return_value={"id": "one"}), "one", zone_id="z"), {"id": "one"})

        with self.assertRaises(cloudflare.PermissionDeniedError):
            get_or_none(Mock(side_effect=status_error(403)))

    def test_unrelated_names_with_whitespace_do_not_fail_lookups(self):
        module = FakeModule({})
        items = [{"id": "one", "name": "One "}, {"id": "two", "name": ""}, {"id": "three", "name": "Three"}]

        self.assertEqual(find_resource(module, iter(items), "resource", "name", "Three"), items[2])
        self.assertIsNone(find_resource(module, iter(items), "resource", "name", "One"))
        self.assertEqual(resource_list(module, iter(items), "resource", ("id", "name")), items)
        with self.assertRaises(ModuleExit) as raised:
            exit_resource_list(module, "things", iter(items), "thing")

        self.assertEqual(raised.exception.values["things"], items)

    def test_lookups_keep_strict_id_and_match_checks_and_name_the_item(self):
        module = FakeModule({})
        cases = (
            (lambda items: resource_list(module, items, "resource", ("id", "name")), {"id": " one", "name": "One"}),
            (lambda items: resource_list(module, items, "resource", ("id", "name")), {"id": "one", "name": 1}),
        )
        for lookup, item in cases:
            with self.subTest(item=item), self.assertRaises(ModuleFail) as raised:
                lookup([{"id": "other", "name": "Other"}, item])

            self.assertEqual(
                raised.exception.values,
                {"msg": "Cloudflare API returned malformed resource data", "resource_id": item["id"]},
            )

    def test_find_resource_matches_a_padded_name(self):
        item = {"id": "one", "name": " One "}

        self.assertEqual(find_resource(FakeModule({}), [item], "resource", "name", " One "), item)

    def test_find_resource_fails_on_duplicate_names(self):
        items = [{"id": "one", "name": "One"}, {"id": "two", "name": "Two"}, {"id": "three", "name": "One"}]

        with self.assertRaises(ModuleFail) as raised:
            find_resource(FakeModule({}), iter(items), "resource", "name", "One")

        self.assertEqual(raised.exception.values["msg"], "Found more than one resource with name 'One'")
        self.assertEqual(raised.exception.values["matching_ids"], ["one", "three"])

    def test_resource_field_accepts_a_padded_name_but_not_a_padded_id(self):
        resource = {"id": "one", "name": " One "}

        self.assertEqual(resource_field(FakeModule({}), resource, "name", "resource", expected=" One "), " One ")
        for value in (" one", ""):
            with self.subTest(id=value), self.assertRaises(ModuleFail):
                resource_field(FakeModule({}), {"id": value}, "id", "resource")

        # Cloudflare stores a whitespace-only Access policy name verbatim.
        self.assertEqual(resource_field(FakeModule({}), {"name": "   "}, "name", "resource"), "   ")
        with self.assertRaises(ModuleFail):
            resource_field(FakeModule({}), {"name": ""}, "name", "resource")

    def test_unsupported_fields_lists_unknown_keys_at_every_level(self):
        fields = {"a": ("b", "c"), "d": None}
        value = {"a": {"b": 1, "x": 2}, "d": {"anything": 1}, "y": 3}

        self.assertEqual(unsupported_fields(value, fields, "opt"), ["opt.a.x", "opt.y"])
        self.assertEqual(unsupported_fields({"b": 1, "z": 1}, ("b",), "opt"), ["opt.z"])
        self.assertEqual(unsupported_fields({"a": "not a mapping"}, fields, "opt"), [])
        for value in (None, "text", ["b"]):
            with self.subTest(value=value):
                self.assertEqual(unsupported_fields(value, fields, "opt"), [])

    def test_unsupported_fields_ignore_null_values(self):
        fields = {"a": ("b",)}
        value = {"a": {"b": 1, "x": None}, "y": None}

        self.assertEqual(unsupported_fields(value, fields, "opt"), [])

    def test_access_selectors_ignore_null_unknown_fields(self):
        rules = {"include": [{"email": {"email": "a@example.com", "bogus": None}}]}

        validate_access_selectors(FakeModule({}), rules, "policies[0].")

    def test_access_selectors_reject_unstored_nested_fields(self):
        rules = {
            "include": [{"email": {"email": "a@example.com", "bogus": "x"}}, {"everyone": {"bogus": 1}}],
            "require": [{"github-organization": {"identity_provider_id": "idp", "name": "org", "id": "1", "x": 1}}],
        }
        unsupported = [
            "policies[0].include[0].email.bogus",
            "policies[0].include[1].everyone.bogus",
            "policies[0].require[0].github-organization.x",
        ]

        with self.assertRaises(ModuleFail) as raised:
            validate_access_selectors(FakeModule({}), rules, "policies[0].")

        self.assertEqual(
            raised.exception.values,
            {
                "msg": f"Cloudflare does not store these Access selector fields: {', '.join(unsupported)}",
                "unsupported_fields": unsupported,
            },
        )

    def test_access_selectors_reject_several_rules_in_one_selector(self):
        for field in ("include", "exclude", "require"):
            with self.subTest(field=field):
                rules = {field: [{"everyone": {}}, {"ip": {"ip": "192.0.2.0/24"}, "unknown_type": {}}]}

                with self.assertRaises(ModuleFail) as raised:
                    validate_access_selectors(FakeModule({}), rules, "policies[0].")

                self.assertEqual(
                    raised.exception.values,
                    {
                        "msg": f"policies[0].{field}[1] sets the selectors 'ip', 'unknown_type', which Cloudflare "
                        f"splits into separate {field} entries; list each selector as its own entry"
                    },
                )

    def test_access_selectors_reject_null_any_valid_service_token(self):
        for field in ("include", "exclude", "require"):
            for value in (None,):
                with self.subTest(field=field, value=value):
                    rules = {field: [{"everyone": {}}, {"any_valid_service_token": value}]}

                    with self.assertRaises(ModuleFail) as raised:
                        validate_access_selectors(FakeModule({}), rules, "policies[0].")

                    self.assertEqual(
                        raised.exception.values,
                        {
                            "msg": f"policies[0].{field}[1].any_valid_service_token must be a mapping; use {{}} for a "
                            "selector without fields, as Cloudflare stores a null selector as {}"
                        },
                    )

    def test_access_selectors_leave_other_non_mapping_values_to_cloudflare(self):
        # Cloudflare rejects these on the first write.
        rules = {
            "exclude": ["everyone", ["everyone"], 5],
            "include": [{"email": None}, {"ip": None}, {"group": None}, {"email": "a@example.com"}],
            "require": [{"everyone": []}, {"everyone": True}, {"any_valid_service_token": ""}],
        }

        validate_access_selectors(FakeModule(rules))

    def test_access_selectors_reject_null_and_empty_selectors(self):
        cases = (
            (None, "must not be null; Cloudflare drops a null selector"),
            ({}, "must set one selector; Cloudflare drops an empty selector"),
        )
        for field in ("include", "exclude", "require"):
            for selector, message in cases:
                with self.subTest(field=field, selector=selector):
                    rules = {field: [{"everyone": {}}, selector]}

                    with self.assertRaises(ModuleFail) as raised:
                        validate_access_selectors(FakeModule({}), rules, "policies[0].")

                    self.assertEqual(raised.exception.values, {"msg": f"policies[0].{field}[1] {message}"})

    def test_access_selectors_reject_empty_string_fields_cloudflare_drops(self):
        rules = {
            "include": [
                {"device_posture": {"integration_uid": "posture", "account_id": ""}},
                {"cloudflare_account_member": {"account_id": ""}},
            ],
            "require": [{"saml": {"attribute_name": "group", "attribute_value": "x", "identity_provider_id": ""}}],
        }
        empty = [
            "include[0].device_posture.account_id",
            "include[1].cloudflare_account_member.account_id",
            "require[0].saml.identity_provider_id",
        ]

        with self.assertRaises(ModuleFail) as raised:
            validate_access_selectors(FakeModule(rules))

        self.assertEqual(
            raised.exception.values,
            {
                "msg": f"Cloudflare does not store an empty value for these Access selector fields: "
                f"{', '.join(empty)}; omit them instead",
                "empty_fields": empty,
            },
        )

    def test_access_selectors_leave_other_empty_string_fields_to_cloudflare(self):
        # Cloudflare stores an empty saml attribute_value and rejects the others on the first write.
        rules = {
            "include": [{"email": {"email": ""}}, {"device_posture": {"integration_uid": ""}}],
            "require": [{"saml": {"attribute_name": "group", "attribute_value": ""}}],
        }

        validate_access_selectors(FakeModule(rules))

    def test_access_selectors_accept_stored_fields_and_unknown_selector_types(self):
        rules = {
            "include": [
                {key: dict.fromkeys(fields, "value")} for key, fields in cloudflare_utils.ACCESS_SELECTOR_KEYS.items()
            ],
            "exclude": [{"unknown_type": {"anything": 1}}],
            "require": [{"github-organization": {"identity_provider_id": "idp", "name": "org", "id": "1"}}],
        }

        validate_access_selectors(FakeModule(rules))

    def test_valid_dns_labels(self):
        for name, expected in (
            ("example.com", True),
            ("a-b.example.com", True),
            (f"{'a' * 63}.example.com", True),
            (".".join(["a" * 63] * 3 + ["b" * 61]), True),
            (f"{'a' * 64}.example.com", False),
            (".".join(["a" * 63] * 3 + ["b" * 62]), False),
            ("", False),
            ("a..example.com", False),
            ("example.com.", False),
            ("-a.example.com", False),
            ("a-.example.com", False),
        ):
            with self.subTest(name=name):
                self.assertIs(valid_dns_labels(name), expected)

    def test_without_nested_nulls_drops_null_keys_at_every_level(self):
        value = {"a": None, "b": [{"c": None, "d": 1}, None], "e": {"f": {"g": None}}}

        self.assertEqual(without_nested_nulls(value), {"b": [{"d": 1}, None], "e": {"f": {}}})
        self.assertEqual(value["b"][0], {"c": None, "d": 1})

    def test_access_rules_payload_keeps_null_selectors(self):
        # A selector set to null keeps its key, so Cloudflare rejects it rather
        # than dropping the empty selector.
        rules = {
            "include": [{"email": {"email": "a@example.com", "x": None}}, {"email": None}],
            "exclude": None,
            "name": "admins",
        }

        self.assertEqual(
            access_rules_payload(rules),
            {"include": [{"email": {"email": "a@example.com"}}, {"email": None}], "exclude": None, "name": "admins"},
        )

    def test_access_rules_payload_sends_ip_selectors_as_stored(self):
        # Cloudflare stores an ip selector as its canonical network; other values are left for it to reject.
        for requested, sent in (
            ("192.0.2.1", "192.0.2.1/32"),
            ("2001:db8::1", "2001:db8::1/128"),
            ("2001:DB8:0:0::1", "2001:db8::1/128"),
            ("2001:DB8:0:0::1/128", "2001:db8::1/128"),
            ("192.0.2.1/24", "192.0.2.0/24"),
            ("192.0.2.0/24", "192.0.2.0/24"),
            ("192.0.2.0/024", "192.0.2.0/24"),
            (" 192.0.2.1 ", "192.0.2.1/32"),
            ("64:ff9b::192.0.2.1", "64:ff9b::c000:201/128"),
            ("not an ip", "not an ip"),
            ("192.0.2.1/33", "192.0.2.1/33"),
            ("192.0.2.1/255.255.255.0", "192.0.2.1/255.255.255.0"),
            ("fe80::1234%en0/64", "fe80::1234%en0/64"),
            ("::ffff:192.0.2.1", "::ffff:192.0.2.1"),
            ("::ffff:c000:201/128", "::ffff:c000:201/128"),
            ("::ffff:192.0.2.1/95", "::ffff:192.0.2.1/95"),
            ("192.0.002.1", "192.0.002.1"),
            ("192.0.2.01/32", "192.0.2.01/32"),
            ("64:ff9b::192.0.2.01", "64:ff9b::192.0.2.01"),
            ("2001:db8::0001", "2001:db8::1/128"),
            ("192.0.2.0/32", "192.0.2.0/32"),
            (5, 5),
        ):
            with self.subTest(requested=requested):
                rules = {"include": [{"ip": {"ip": requested}}], "require": [{"ip": {"ip": requested, "x": None}}]}

                self.assertEqual(
                    access_rules_payload(rules),
                    {"include": [{"ip": {"ip": sent}}], "require": [{"ip": {"ip": sent}}]},
                )

        self.assertEqual(access_rules_payload({"include": [{"ip": None}]}), {"include": [{"ip": None}]})

    def test_zone_missing_matches_deleted_zone_answers(self):
        invalid = {"success": False, "errors": [{"code": 1001, "message": "Invalid zone identifier"}]}
        for exc, expected in (
            (status_error(404), True),
            (status_error(400, invalid), True),
            (status_error(400), False),
            (status_error(403, invalid), False),
        ):
            with self.subTest(status=exc.status_code, body=exc.body):
                self.assertIs(zone_missing(exc), expected)


class InfoTests(TestCase):
    def test_exit_resource_list_returns_all_fields_and_validates(self):
        with self.assertRaises(ModuleExit) as raised:
            exit_resource_list(FakeModule({}), "things", [{"id": "one", "name": "One", "token": "secret"}], "thing")

        self.assertEqual(
            raised.exception.values, {"changed": False, "things": [{"id": "one", "name": "One", "token": "secret"}]}
        )

        with self.assertRaises(ModuleFail):
            exit_resource_list(FakeModule({}), "things", [{"id": "one"}], "thing")

    def test_exit_settings_treats_null_as_empty(self):
        with self.assertRaises(ModuleExit) as raised:
            exit_settings(FakeModule({}), "settings", None)

        self.assertEqual(raised.exception.values, {"changed": False, "settings": {}})

    def test_exit_settings_returns_other_values_unmodified(self):
        for settings in ({}, "", 0, False, []):
            with self.subTest(settings=settings), self.assertRaises(ModuleExit) as raised:
                exit_settings(FakeModule({}), "settings", settings)

            returned = raised.exception.values["settings"]
            self.assertEqual((type(returned), returned), (type(settings), settings))

    def test_info_failures_carry_the_owner(self):
        context = {"account_id": "account"}
        for call in (
            lambda: exit_resource_list(FakeModule({}), "things", [{"id": "one"}], "thing", context=context),
            lambda: resource_list(FakeModule({}), [{"id": ""}], "thing", context=context),
        ):
            with self.assertRaises(ModuleFail) as raised:
                call()

            self.assertEqual(raised.exception.values["account_id"], "account")

    def test_find_resource_failures_carry_the_owner_and_value(self):
        for items in (
            [{"name": "n"}, {"name": "n", "id": "two"}],
            [{"id": "one", "name": "n"}, {"id": "two", "name": "n"}],
        ):
            with self.subTest(items=items), self.assertRaises(ModuleFail) as raised:
                find_resource(FakeModule({}), items, "thing", "name", "n", context={"account_id": "account"})

            self.assertEqual(raised.exception.values["account_id"], "account")
            self.assertEqual(raised.exception.values["name"], "n")


class EnsureSettingsTests(TestCase):
    def run_settings(self, current, payload, edited=None, check_mode=False, comparable=None, exact_values=()):
        edit = Mock(return_value=edited)
        with self.assertRaises((ModuleExit, ModuleFail)) as raised:
            ensure_settings(
                FakeModule({}, check_mode=check_mode),
                "settings",
                "device settings",
                current,
                payload,
                edit,
                comparable=comparable,
                exact_values=exact_values,
            )

        return raised.exception, edit

    def test_exact_values_compare_every_nested_key(self):
        current = {"routes": [{"address": "192.0.2.0/24", "description": "old"}], "other": 1}
        payload = {"routes": [{"address": "192.0.2.0/24"}]}

        result, edit = self.run_settings(current, payload)
        edit.assert_not_called()
        self.assertFalse(result.values["changed"])

        result, edit = self.run_settings(current, payload, edited={**current, **payload}, exact_values=("routes",))
        edit.assert_called_once_with(payload)
        self.assertTrue(result.values["changed"])

        result, _ignored = self.run_settings(current, payload, edited=current, exact_values=("routes",))
        self.assertIsInstance(result, ModuleFail)

    def test_malformed_current_settings_fail_before_the_edit(self):
        for current in (["enabled"], "enabled", [], False, ""):
            edit = Mock()
            with self.subTest(current=current), self.assertRaises(ModuleFail) as raised:
                ensure_settings(
                    FakeModule({}),
                    "settings",
                    "device settings",
                    current,
                    {"enabled": True},
                    edit,
                    context={"account_id": "acc"},
                )

            edit.assert_not_called()
            self.assertEqual(
                raised.exception.values,
                {"msg": "Cloudflare API returned malformed device settings data", "account_id": "acc"},
            )

    def test_unchanged_settings_skip_edit(self):
        result, edit = self.run_settings({"enabled": True, "other": 1}, {"enabled": True})

        edit.assert_not_called()
        self.assertEqual(result.values["message"], "Device settings already present")
        self.assertFalse(result.values["changed"])

    def test_check_mode_predicts_without_edit(self):
        result, edit = self.run_settings({"enabled": False}, {"enabled": True}, check_mode=True)

        edit.assert_not_called()
        self.assertTrue(result.values["changed"])

    def test_edits_and_verifies(self):
        result, edit = self.run_settings({"enabled": False}, {"enabled": True}, edited={"enabled": True})

        edit.assert_called_once_with({"enabled": True})
        self.assertEqual(result.values["settings"], {"enabled": True})
        self.assertTrue(result.values["changed"])

        result, _ignored = self.run_settings({"enabled": False}, {"enabled": True}, edited={"enabled": False})
        self.assertIsInstance(result, ModuleFail)

    def test_not_applied_failure_names_the_settings_owner(self):
        edit = Mock(return_value={"enabled": False})
        with self.assertRaises(ModuleFail) as raised:
            ensure_settings(
                FakeModule({}),
                "settings",
                "device settings",
                {"enabled": False},
                {"enabled": True},
                edit,
                context={"account_id": "acc"},
            )

        self.assertEqual(raised.exception.values["account_id"], "acc")
        self.assertIn("did not apply", raised.exception.values["msg"])

    def test_comparable_normalizes_both_sides(self):
        def comparable(settings, failure):
            return {**settings, "status": {"pending": "active"}.get(settings.get("status"), settings.get("status"))}

        result, edit = self.run_settings({"status": "pending"}, {"status": "active"}, comparable=comparable)

        edit.assert_not_called()
        self.assertFalse(result.values["changed"])


class EnsureResourceTests(TestCase):
    def present(self, current, payload, created=None, updated=None, check_mode=False, found=(), **kwargs):
        create = Mock(return_value=created)
        update = Mock(return_value=updated)
        with self.assertRaises((ModuleExit, ModuleFail)) as raised:
            ensure_resource_present(
                FakeModule({}, check_mode=check_mode),
                "thing",
                "thing",
                current,
                payload,
                create,
                update,
                lambda: list(found),
                **kwargs,
            )

        return raised.exception, create, update

    def test_sdk_errors_of_writes_name_the_operation(self):
        writes = (
            (
                "Cloudflare API request failed while creating the thing",
                lambda module, write: ensure_resource_present(
                    module, "thing", "thing", None, {"name": "n"}, write, Mock(), list, expected_name="n"
                ),
                {"name": "n"},
            ),
            (
                "Cloudflare API request failed while updating the thing",
                lambda module, write: ensure_resource_present(
                    module, "thing", "thing", {"id": "one", "name": "old"}, {"name": "n"}, Mock(), write, list
                ),
                {"resource_id": "one"},
            ),
            (
                "Cloudflare API request failed while deleting the thing",
                lambda module, write: ensure_resource_absent(module, "thing", "thing", {"id": "one"}, write),
                {"resource_id": "one"},
            ),
            (
                "Cloudflare API request failed while updating device settings",
                lambda module, write: ensure_settings(
                    module, "settings", "device settings", {"enabled": False}, {"enabled": True}, write
                ),
                {},
            ),
        )
        for message, ensure, context in writes:
            module = FakeModule({"api_token": "secret"})
            write = Mock(side_effect=malformed_response)
            with (
                self.subTest(message=message),
                patch.object(cloudflare_utils, "Cloudflare", return_value=sdk_context(Mock())),
                self.assertRaises(ModuleFail) as raised,
                cloudflare_client(module),
            ):
                ensure(module, write)

            write.assert_called_once()
            values = raised.exception.values
            self.assertEqual(values["msg"], message)
            self.assertLessEqual(context.items(), values.items())

    def test_creates_and_verifies(self):
        created = {"id": "one", "name": "n", "enabled": True, "token": "secret"}
        result, create, _ignored = self.present(
            None, {"name": "n", "enabled": True}, created=created, expected_name="n"
        )

        create.assert_called_once_with({"name": "n", "enabled": True})
        self.assertEqual(result.values["thing"], created)
        self.assertEqual(result.values["message"], "Thing created")

        result, _ignored, _ignored = self.present(
            None, {"name": "n"}, created={"id": "one", "name": "other"}, expected_name="n"
        )
        self.assertEqual(result.values["msg"], "Cloudflare API returned the wrong thing")

    def test_not_applied_after_create_reports_the_created_resource(self):
        created = {"id": "one", "name": "n", "enabled": False, "token": "secret"}
        result, create, _ignored = self.present(
            None,
            {"name": "n", "enabled": True},
            created=created,
            expected_name="n",
            context={"account_id": "acc"},
            comparable=lambda resource, failure: {key: value for key, value in resource.items() if key != "token"},
        )

        create.assert_called_once()
        self.assertIsInstance(result, ModuleFail)
        self.assertIn("did not apply", result.values["msg"])
        self.assertTrue(result.values["changed"])
        self.assertEqual(result.values["thing"], created)
        self.assertEqual(result.values["resource_id"], "one")
        self.assertEqual(result.values["name"], "n")
        self.assertEqual(result.values["account_id"], "acc")
        self.assertEqual(result.values["differences"], [{"field": "enabled", "requested": True, "stored": False}])

    def test_not_applied_after_update_names_the_resource(self):
        current = {"id": "one", "enabled": False}
        result, _ignored, update = self.present(current, {"enabled": True}, updated=current, context={"zone_id": "z"})

        update.assert_called_once()
        self.assertIsInstance(result, ModuleFail)
        self.assertIn("did not apply", result.values["msg"])
        self.assertEqual(result.values["resource_id"], "one")
        self.assertEqual(result.values["zone_id"], "z")
        self.assertTrue(result.values["changed"])

    def test_check_mode_never_mutates(self):
        for current in (None, {"id": "one", "enabled": False}):
            result, create, update = self.present(current, {"enabled": True}, check_mode=True)

            create.assert_not_called()
            update.assert_not_called()
            self.assertTrue(result.values["changed"])

    def test_unchanged_with_defaults(self):
        result, _ignored, update = self.present({"id": "one"}, {"enabled": False}, defaults={"enabled": False})

        update.assert_not_called()
        self.assertFalse(result.values["changed"])

    def test_update_preserves_omitted_fields_and_verifies_identity(self):
        current = {"id": "one", "enabled": False, "exclude": ["x"]}
        updated = {"id": "one", "enabled": True, "exclude": ["x"]}
        result, _ignored, update = self.present(
            current, {"enabled": True}, updated=updated, preserved_fields=("exclude", "require")
        )

        update.assert_called_once_with("one", {"exclude": ["x"], "enabled": True})
        self.assertTrue(result.values["changed"])

        result, _ignored, _ignored = self.present(current, {"enabled": True}, updated={**updated, "id": "two"})
        self.assertEqual(result.values["msg"], "Cloudflare API returned the wrong thing")

    def absent(self, current, deleted=None, check_mode=False):
        delete = Mock(return_value=deleted)
        with self.assertRaises((ModuleExit, ModuleFail)) as raised:
            ensure_resource_absent(FakeModule({}, check_mode=check_mode), "thing", "thing", current, delete)

        return raised.exception, delete

    def test_absent_paths(self):
        result, delete = self.absent(None)
        delete.assert_not_called()
        self.assertFalse(result.values["changed"])

        result, delete = self.absent({"id": "one"}, check_mode=True)
        delete.assert_not_called()
        self.assertTrue(result.values["changed"])

        result, delete = self.absent({"id": "one"}, deleted={"id": "one"})
        delete.assert_called_once_with("one")
        self.assertEqual(result.values["thing"], {"id": "one"})

        result, _ignored = self.absent({"id": "one"}, deleted={"id": "two"})
        self.assertIsInstance(result, ModuleFail)

    def test_delete_answered_with_404_counts_as_deleted(self):
        # The SDK retries a delete whose response was lost; Cloudflare answers the retry with 404.
        delete = Mock(side_effect=status_error(404))
        with self.assertRaises(ModuleExit) as raised:
            ensure_resource_absent(FakeModule({}), "thing", "thing", {"id": "one"}, delete)

        delete.assert_called_once_with("one")
        self.assertEqual(raised.exception.values, {"changed": True, "message": "Thing deleted", "thing": {"id": "one"}})

    def test_retried_delete_answered_with_404_counts_as_deleted_through_the_sdk(self):
        requests = []

        def respond(request):
            requests.append(request)
            if len(requests) == 1:
                # The first delete reaches Cloudflare, but its response is lost.
                raise httpx.ConnectError("connection reset", request=request)

            return httpx.Response(404, json={"success": False, "errors": [{"code": 12152, "message": "not found"}]})

        with (
            cloudflare.Cloudflare(
                api_token="EXAMPLE-token",
                max_retries=1,
                http_client=httpx.Client(transport=httpx.MockTransport(respond)),
            ) as client,
            self.assertRaises(ModuleExit) as raised,
        ):
            ensure_resource_absent(
                FakeModule({}),
                "access_group",
                "Access group",
                {"id": "one"},
                lambda group_id: client.zero_trust.access.groups.delete(group_id, account_id="account"),
            )

        self.assertEqual([request.method for request in requests], ["DELETE", "DELETE"])
        self.assertTrue(raised.exception.values["changed"])
        self.assertEqual(raised.exception.values["message"], "Access group deleted")

    def test_delete_answered_with_a_deleted_code_counts_as_deleted(self):
        body = {"success": False, "errors": [{"code": 1001, "message": "Invalid zone identifier"}]}
        delete = Mock(side_effect=status_error(400, body))
        with self.assertRaises(ModuleExit) as raised:
            ensure_resource_absent(FakeModule({}), "thing", "thing", {"id": "one"}, delete, deleted_codes=(1001,))

        delete.assert_called_once_with("one")
        self.assertEqual(raised.exception.values, {"changed": True, "message": "Thing deleted", "thing": {"id": "one"}})

    def test_delete_answered_with_another_400_error_is_raised(self):
        for body in (
            {"success": False, "errors": [{"code": 1002, "message": "other"}]},
            {"success": False, "errors": None},
            {"success": False},
        ):
            error = status_error(400, body)
            with self.subTest(body=body), self.assertRaises(cloudflare.BadRequestError) as raised:
                ensure_resource_absent(
                    FakeModule({}),
                    "thing",
                    "thing",
                    {"id": "one"},
                    Mock(side_effect=error),
                    context={"zone_id": "z"},
                    deleted_codes=(1001,),
                )

            self.assertIs(raised.exception, error)
            self.assertEqual(error._cloudflare_context, {"resource_id": "one", "zone_id": "z"})

    def test_malformed_current_resource_carries_the_owner(self):
        with self.assertRaises(ModuleFail) as raised:
            ensure_resource_absent(FakeModule({}), "thing", "thing", {"id": ""}, Mock(), context={"zone_id": "z"})

        self.assertEqual(raised.exception.values["zone_id"], "z")

        result, create, update = self.present(
            {"id": None, "name": "n"}, {"name": "n"}, expected_name="n", context={"account_id": "acc"}
        )
        create.assert_not_called()
        update.assert_not_called()
        self.assertEqual(result.values["msg"], "Cloudflare API returned malformed thing data")
        self.assertEqual(result.values["account_id"], "acc")
        self.assertEqual(result.values["name"], "n")

    def test_delete_failures_other_than_404_are_raised(self):
        for status_code in (400, 403, 409, 500):
            with self.subTest(status_code=status_code):
                error = status_error(status_code)
                with self.assertRaises(cloudflare.APIStatusError) as raised:
                    ensure_resource_absent(FakeModule({}), "thing", "thing", {"id": "one"}, Mock(side_effect=error))

                self.assertIs(raised.exception, error)

    def test_mutation_errors_carry_context(self):
        error = status_error(400)
        create = Mock(side_effect=error)

        with self.assertRaises(cloudflare.BadRequestError):
            ensure_resource_present(FakeModule({}), "thing", "thing", None, {"a": 1}, create, Mock(), list)

        self.assertEqual(error._cloudflare_message, "Cloudflare API request failed while creating the thing")
        self.assertEqual(error._cloudflare_context, {})

        error = status_error(409)
        with self.assertRaises(cloudflare.ConflictError):
            ensure_resource_present(
                FakeModule({}),
                "thing",
                "thing",
                None,
                {"a": 1},
                Mock(side_effect=error),
                Mock(),
                list,
                expected_name="n",
                context={"account_id": "acc"},
            )

        self.assertEqual(error._cloudflare_context, {"name": "n", "account_id": "acc"})

        error = status_error(400)
        with self.assertRaises(cloudflare.BadRequestError):
            ensure_resource_absent(
                FakeModule({}), "thing", "thing", {"id": "one"}, Mock(side_effect=error), context={"zone_id": "z"}
            )

        self.assertEqual(error._cloudflare_context, {"resource_id": "one", "zone_id": "z"})

    def test_create_recovers_the_resource_after_a_lost_response(self):
        created = {"id": "one", "name": "n", "enabled": True}
        for error in (connection_error(), timeout_error(), status_error(500), status_error(503)):
            with self.subTest(error=type(error).__name__, status=getattr(error, "status_code", None)):
                create = Mock(side_effect=error)
                find = Mock(return_value=[created])
                with self.assertRaises(ModuleExit) as raised:
                    ensure_resource_present(
                        FakeModule({}),
                        "thing",
                        "thing",
                        None,
                        {"name": "n", "enabled": True},
                        create,
                        Mock(),
                        find,
                        expected_name="n",
                    )

                create.assert_called_once_with({"name": "n", "enabled": True})
                find.assert_called_once_with()
                self.assertEqual(raised.exception.values["message"], "Thing created")
                self.assertEqual(raised.exception.values["thing"], created)

    def test_recovered_resource_is_checked_like_a_created_one(self):
        with self.assertRaises(ModuleFail) as raised:
            ensure_resource_present(
                FakeModule({}),
                "thing",
                "thing",
                None,
                {"name": "n", "enabled": True},
                Mock(side_effect=timeout_error()),
                Mock(),
                lambda: [{"id": "one", "name": "n", "enabled": False}],
                expected_name="n",
            )

        self.assertIn("did not apply", raised.exception.values["msg"])


class CreateOnceTests(TestCase):
    def test_returns_the_created_resource_without_reading_it_again(self):
        find = Mock()

        self.assertEqual(create_once(lambda: {"id": "one"}, find), {"id": "one"})
        find.assert_not_called()

    def test_original_error_is_raised_unless_exactly_one_resource_matches(self):
        for matches in ([], [{"id": "one"}, {"id": "two"}]):
            with self.subTest(matches=matches):
                error = timeout_error()

                with self.assertRaises(cloudflare.APITimeoutError) as raised:
                    create_once(Mock(side_effect=error), Mock(return_value=matches))

                self.assertIs(raised.exception, error)

    def test_original_error_is_raised_when_the_lookup_fails(self):
        error = status_error(502)

        with self.assertRaises(cloudflare.InternalServerError) as raised:
            create_once(Mock(side_effect=error), Mock(side_effect=connection_error()))

        self.assertIs(raised.exception, error)

    def test_lookup_failure_keeps_the_connection_error_cause(self):
        cause = httpx.ConnectError("connection refused")
        error = connection_error()
        error.__cause__ = cause

        with self.assertRaises(cloudflare.APIConnectionError) as raised:
            create_once(Mock(side_effect=error), Mock(side_effect=status_error(500)))

        self.assertIs(raised.exception, error)
        self.assertIs(raised.exception.__cause__, cause)
        self.assertEqual(
            cloudflare_error_details(raised.exception)["error"], "Connection error. ConnectError: connection refused"
        )

    def test_malformed_lookup_response_keeps_the_create_error(self):
        # A JSON body that is not an object, and a body that is not JSON.
        for lookup in (httpx.Response(200, json=[]), httpx.Response(200, text="<html>OK</html>")):
            with self.subTest(lookup=lookup.text):

                def respond(request, lookup=lookup):
                    if request.method == "POST":
                        return httpx.Response(500, json={"success": False, "errors": [], "messages": []})

                    return lookup

                with sdk_client(respond) as client, self.assertRaises(cloudflare.InternalServerError) as raised:
                    create_once(
                        lambda: client.zero_trust.access.groups.create(
                            account_id="account", name="n", include=[{"everyone": {}}]
                        ),
                        lambda: matching_resources(
                            client.zero_trust.access.groups.list(account_id="account", name="n"), "name", "n"
                        ),
                    )

                self.assertEqual(cloudflare_error_details(raised.exception)["status_code"], 500)

    def test_collection_errors_in_the_lookup_keep_their_traceback(self):
        def find():
            raise TypeError("collection bug")

        with self.assertRaisesRegex(TypeError, "collection bug"):
            create_once(Mock(side_effect=status_error(500)), find)

    def test_rejected_create_is_not_looked_up(self):
        # Cloudflare answered, so the resource was not created.
        for status_code in (400, 409, 429):
            with self.subTest(status_code=status_code), patch.object(cloudflare_utils.time, "sleep"):
                find = Mock(return_value=[{"id": "one"}])

                with self.assertRaises(cloudflare.APIStatusError):
                    create_once(Mock(side_effect=status_error(status_code)), find)

                find.assert_not_called()

    def test_only_conflicts_and_rate_limits_are_retried(self):
        for status_code, attempts in ((400, 1), (403, 1), (404, 1), (409, 3), (429, 3)):
            with self.subTest(status_code=status_code), patch.object(cloudflare_utils.time, "sleep") as sleep:
                error = status_error(status_code)
                create = Mock(side_effect=error)

                with self.assertRaises(cloudflare.APIStatusError) as raised:
                    create_once(create, Mock())

                self.assertIs(raised.exception, error)
                self.assertEqual(create.call_count, attempts)
                self.assertEqual(sleep.call_count, attempts - 1)

    def test_retried_create_returns_the_created_resource(self):
        for status_code in (409, 429):
            with self.subTest(status_code=status_code), patch.object(cloudflare_utils.time, "sleep") as sleep:
                find = Mock()
                create = Mock(side_effect=[status_error(status_code), status_error(status_code), {"id": "one"}])

                self.assertEqual(create_once(create, find), {"id": "one"})

                self.assertEqual(create.call_count, 3)
                self.assertEqual([call.args for call in sleep.call_args_list], [(0.5,), (1.0,)])
                find.assert_not_called()

    def test_lost_response_after_a_retry_is_looked_up(self):
        find = Mock(return_value=[{"id": "one"}])
        create = Mock(side_effect=[status_error(429), timeout_error()])

        with patch.object(cloudflare_utils.time, "sleep"):
            self.assertEqual(create_once(create, find), {"id": "one"})

        self.assertEqual(create.call_count, 2)
        find.assert_called_once_with()

    def test_retry_delay_honors_retry_after(self):
        def rejected(headers):
            response = httpx.Response(429, headers=headers, json={}, request=httpx.Request("POST", "https://x"))
            return cloudflare.RateLimitError("Error code: 429", response=response, body={})

        now = datetime(2026, 11, 17, tzinfo=timezone.utc)
        cases = (
            ({"Retry-After": "3"}, 0, 3.0),
            ({"Retry-After": "1.5"}, 1, 1.5),
            ({"Retry-After-Ms": "250", "Retry-After": "9"}, 0, 0.25),
            # As in the SDK, an unparseable Retry-After-Ms falls through to Retry-After.
            ({"Retry-After-Ms": "soon", "Retry-After": "4"}, 0, 4.0),
            ({"Retry-After-Ms": "", "Retry-After": "Tue, 17 Nov 2026 00:00:05 GMT"}, 0, 5.0),
            # An HTTP date without a time zone is in UTC.
            ({"Retry-After": "Tue, 17 Nov 2026 00:00:06 -0000"}, 0, 6.0),
            ({"Retry-After": "17 Nov 2026 00:00:08"}, 0, 8.0),
            ({"Retry-After": "Tue, 17 Nov 2026 00:00:07 GMT"}, 0, 7.0),
            # A delay longer than the SDK's 60-second cap, or none, uses the backoff.
            ({"Retry-After": "61"}, 0, 0.5),
            ({"Retry-After": "0"}, 1, 1.0),
            ({"Retry-After": "-1"}, 0, 0.5),
            ({"Retry-After": "nan"}, 0, 0.5),
            ({"Retry-After": "soon"}, 0, 0.5),
            ({"Retry-After": "Tue, 17 Nov 2026 01:00:00 GMT"}, 0, 0.5),
            # Out-of-range and extreme dates use the backoff.
            ({"Retry-After": "Mon, 01 Jan 99999999999999999999 00:00:00 GMT"}, 0, 0.5),
            ({"Retry-After": "Tue, 17 Nov 2026 99999999999999999999:00:00 GMT"}, 0, 0.5),
            ({"Retry-After": "Tue, 17 Nov 2026 00:00:00 +99999999999999999999"}, 0, 0.5),
            ({"Retry-After": "Fri, 31 Dec 9999 23:59:59 -2359"}, 0, 0.5),
            ({"Retry-After": "Mon, 01 Jan 0001 00:00:00 +2359"}, 0, 0.5),
            ({}, 1, 1.0),
        )
        with patch.object(cloudflare_utils, "datetime", Mock(wraps=datetime, now=Mock(return_value=now))):
            for headers, attempt, delay in cases:
                with self.subTest(headers=headers, attempt=attempt):
                    self.assertEqual(cloudflare_utils.retry_delay(rejected(headers), attempt), delay)

    def test_rate_limited_create_is_retried_through_the_sdk(self):
        requests = []

        def respond(request):
            requests.append(request)
            if len(requests) == 1:
                return httpx.Response(429, headers={"Retry-After": "2"}, json={"success": False, "errors": []})

            return httpx.Response(200, json={"success": True, "result": {"id": "one", "name": "n"}})

        with (
            patch.object(cloudflare_utils.time, "sleep") as sleep,
            cloudflare.Cloudflare(
                api_token="EXAMPLE-token", http_client=httpx.Client(transport=httpx.MockTransport(respond))
            ) as client,
        ):
            group = create_once(
                lambda: without_retries(client).zero_trust.access.groups.create(
                    account_id="account", name="n", include=[{"everyone": {}}]
                ),
                Mock(),
            )

        self.assertEqual(serialize_resource(group)["id"], "one")
        self.assertEqual([request.method for request in requests], ["POST", "POST"])
        sleep.assert_called_once_with(2.0)

    def test_rate_limited_create_with_an_out_of_range_retry_date_uses_the_backoff(self):
        requests = []

        def respond(request):
            requests.append(request)
            if len(requests) == 1:
                return httpx.Response(
                    429,
                    headers={"Retry-After": "Mon, 01 Jan 99999999999999999999 00:00:00 GMT"},
                    json={"success": False, "errors": []},
                )

            return httpx.Response(200, json={"success": True, "result": {"id": "one", "name": "n"}})

        module = FakeModule({"api_token": "secret"})
        with (
            patch.object(cloudflare_utils.time, "sleep") as sleep,
            patch.object(cloudflare_utils, "Cloudflare", side_effect=sdk_constructor(respond)),
            self.assertRaises(ModuleExit) as raised,
            cloudflare_client(module) as client,
        ):
            ensure_resource_present(
                module,
                "group",
                "Access group",
                None,
                {"name": "n"},
                lambda payload: without_retries(client).zero_trust.access.groups.create(
                    account_id="account", include=[{"everyone": {}}], **payload
                ),
                Mock(),
                list,
                expected_name="n",
            )

        self.assertEqual([request.method for request in requests], ["POST", "POST"])
        sleep.assert_called_once_with(0.5)
        self.assertTrue(raised.exception.values["changed"])
        self.assertEqual(raised.exception.values["group"]["id"], "one")

    def test_matching_resources_compares_the_field_exactly(self):
        items = [{"id": "one", "name": "n"}, {"id": "two", "name": "N"}, {"id": "three"}, None]

        self.assertEqual(matching_resources(iter(items), "name", "n"), [{"id": "one", "name": "n"}])

    def test_create_request_is_sent_once(self):
        # The SDK would retry the 500 twice, creating up to three resources.
        requests = []

        def respond(request):
            requests.append(request)
            if request.method == "POST":
                return httpx.Response(500, json={"success": False, "errors": [], "messages": []})

            # The list paginates until a page is empty.
            result = [{"id": "one", "name": "n"}] if request.url.params.get("page", "1") == "1" else []
            return httpx.Response(200, json={"success": True, "result": result})

        with cloudflare.Cloudflare(
            api_token="EXAMPLE-token", http_client=httpx.Client(transport=httpx.MockTransport(respond))
        ) as client:
            groups = client.zero_trust.access.groups
            group = create_once(
                lambda: without_retries(client).zero_trust.access.groups.create(
                    account_id="account", name="n", include=[{"everyone": {}}]
                ),
                lambda: matching_resources(groups.list(account_id="account", name="n"), "name", "n"),
            )

        self.assertEqual(group, {"id": "one", "name": "n"})
        self.assertEqual([request.method for request in requests].count("POST"), 1)
        self.assertEqual(requests[0].method, "POST")


class ListAllPagesTests(TestCase):
    def run_pages(self, pages):
        requests = []

        def respond(request):
            requests.append(request)
            page = int(request.url.params["page"])
            return httpx.Response(200, json={"success": True, "errors": [], "messages": [], **pages[page - 1]})

        with cloudflare.Cloudflare(
            api_token="EXAMPLE-token", http_client=httpx.Client(transport=httpx.MockTransport(respond))
        ) as client:
            items = list_all_pages(FakeModule({}), client, "/accounts/a%2Fb/things", "thing")

        return items, requests

    def test_reads_every_page_until_total_pages(self):
        first = [{"name": f"item-{index}"} for index in range(20)]
        pages = [
            {"result": first, "result_info": {"page": 1, "per_page": 20, "total_pages": 2}},
            {"result": [{"name": "last"}], "result_info": {"page": 2, "per_page": 20, "total_pages": 2}},
        ]

        items, requests = self.run_pages(pages)

        self.assertEqual(items, [*first, {"name": "last"}])
        self.assertEqual(
            [dict(request.url.params) for request in requests],
            [
                {"page": "1", "per_page": "20"},
                {"page": "2", "per_page": "20"},
            ],
        )
        self.assertEqual(requests[0].url.raw_path.split(b"?")[0], b"/client/v4/accounts/a%2Fb/things")

    def test_total_pages_wins_over_a_short_page(self):
        pages = [
            {"result": [{"name": "a"}], "result_info": {"total_pages": 2}},
            {"result": [{"name": "b"}], "result_info": {"total_pages": 2}},
        ]

        items, _ignored = self.run_pages(pages)

        self.assertEqual(items, [{"name": "a"}, {"name": "b"}])

    def test_without_total_pages_stops_at_a_short_page(self):
        pages = [{"result": [{"name": str(index)} for index in range(20)]}, {"result": []}]

        items, requests = self.run_pages(pages)

        self.assertEqual(len(items), 20)
        self.assertEqual(len(requests), 2)

    def test_stops_at_an_empty_page_despite_total_pages(self):
        first = [{"name": f"item-{index}"} for index in range(20)]
        info = {"result_info": {"total_pages": 1000000000}}
        for pages in ([{"result": first, **info}, {"result": [], **info}], [{"result": [], **info}]):
            with self.subTest(pages=len(pages)):
                # Every later page is empty too.
                items, requests = self.run_pages(pages + [{"result": [], **info}] * 10)

                self.assertEqual(items, pages[0]["result"])
                self.assertEqual(len(requests), len(pages))

    def test_rejects_a_malformed_page(self):
        with self.assertRaises(ModuleFail) as raised:
            self.run_pages([{"result": {"name": "a"}}])

        self.assertEqual(raised.exception.values["msg"], "Cloudflare API returned malformed thing data")

    def test_malformed_page_carries_the_context(self):
        requests = []

        def respond(request):
            requests.append(request)
            return httpx.Response(200, json={"success": True, "errors": [], "messages": [], "result": {}})

        with (
            cloudflare.Cloudflare(
                api_token="EXAMPLE-token", http_client=httpx.Client(transport=httpx.MockTransport(respond))
            ) as client,
            self.assertRaises(ModuleFail) as raised,
        ):
            list_all_pages(FakeModule({}), client, "/things", "thing", {"account_id": "account"})

        self.assertEqual(raised.exception.values["account_id"], "account")


class ListedItemsTests(TestCase):
    """SDK list responses are read page by page; a falsy page result that is not null is malformed."""

    def listings(self, module, groups):
        context = {"account_id": "account"}
        return (
            lambda: find_resource(module, groups.list(account_id="account"), "group", "name", "n", context),
            lambda: resource_list(module, groups.list(account_id="account"), "group", context=context),
            lambda: exit_resource_list(module, "groups", groups.list(account_id="account"), "group", context=context),
        )

    def test_falsy_page_results_fail(self):
        for result in FALSY_PAGE_RESULTS:
            requests = []
            with sdk_client(list_response(result, requests)) as client:
                for index, listing in enumerate(self.listings(FakeModule({}), client.zero_trust.access.groups)):
                    with self.subTest(result=result, listing=index), self.assertRaises(ModuleFail) as raised:
                        listing()

                    self.assertEqual(raised.exception.values["msg"], "Cloudflare API returned malformed group data")
                    self.assertEqual(raised.exception.values["account_id"], "account")

    def test_null_page_result_is_empty(self):
        requests = []
        with sdk_client(list_response(None, requests)) as client:
            find, listed, exit_listed = self.listings(FakeModule({}), client.zero_trust.access.groups)

            self.assertIsNone(find())
            self.assertEqual(listed(), [])
            with self.assertRaises(ModuleExit) as raised:
                exit_listed()

        self.assertEqual(raised.exception.values, {"changed": False, "groups": []})

    def test_every_page_is_read(self):
        pages = {"1": [{"id": "one", "name": "m"}], "2": [{"id": "two", "name": "n"}], "3": []}

        def respond(request):
            result = pages[request.url.params.get("page", "1")]
            return httpx.Response(200, json={"success": True, "errors": [], "messages": [], "result": result})

        with sdk_client(respond) as client:
            find, listed, _exit_listed = self.listings(FakeModule({}), client.zero_trust.access.groups)

            self.assertEqual(find(), {"id": "two", "name": "n"})
            self.assertEqual([group["id"] for group in listed()], ["one", "two"])


class WrittenFailureTests(TestCase):
    """A failure after a write reports changed=True, the resource, and its identifiers."""

    def present(self, current, payload, created=None, updated=None, **kwargs):
        with self.assertRaises(ModuleFail) as raised:
            ensure_resource_present(
                FakeModule({}),
                "thing",
                "thing",
                current,
                payload,
                Mock(return_value=created),
                Mock(return_value=updated),
                list,
                context={"account_id": "acc"},
                **kwargs,
            )

        return raised.exception.values

    def test_created_resource_with_another_name(self):
        created = {"id": "one", "name": "n"}
        result = self.present(None, {"name": " n"}, created=created, expected_name=" n")

        self.assertEqual(result["msg"], "Cloudflare API returned the wrong thing")
        self.assertTrue(result["changed"])
        self.assertEqual(result["thing"], created)
        self.assertEqual(result["resource_id"], "one")
        self.assertEqual(result["name"], " n")
        self.assertEqual(result["account_id"], "acc")

    def test_created_resource_without_an_id(self):
        result = self.present(None, {"name": "n"}, created={"name": "n"}, expected_name="n")

        self.assertEqual(result["msg"], "Cloudflare API returned malformed thing data")
        self.assertTrue(result["changed"])
        self.assertEqual(result["thing"], {"name": "n"})
        self.assertEqual(result["account_id"], "acc")

    def test_updated_resource_with_another_id(self):
        updated = {"id": "two", "enabled": True}
        result = self.present({"id": "one", "enabled": False}, {"enabled": True}, updated=updated)

        self.assertEqual(result["msg"], "Cloudflare API returned the wrong thing")
        self.assertTrue(result["changed"])
        self.assertEqual(result["thing"], updated)
        self.assertEqual(result["resource_id"], "one")
        self.assertEqual(result["account_id"], "acc")

    def test_comparable_receives_the_failure_context(self):
        created = {"id": "one", "name": "n"}
        seen = []
        with self.assertRaises(ModuleExit):
            ensure_resource_present(
                FakeModule({}),
                "thing",
                "thing",
                None,
                {"name": "n"},
                Mock(return_value=created),
                Mock(),
                list,
                expected_name="n",
                comparable=lambda resource, failure: seen.append(failure) or resource,
            )

        self.assertEqual(seen, [{"resource_id": "one", "changed": True, "name": "n", "thing": created}])

    def test_malformed_settings_after_the_patch(self):
        with self.assertRaises(ModuleFail) as raised:
            ensure_settings(
                FakeModule({}),
                "settings",
                "device settings",
                {"enabled": False},
                {"enabled": True},
                Mock(return_value=["malformed"]),
                context={"account_id": "acc"},
            )

        result = raised.exception.values
        self.assertEqual(result["msg"], "Cloudflare API returned malformed device settings data")
        self.assertTrue(result["changed"])
        self.assertEqual(result["settings"], ["malformed"])
        self.assertEqual(result["account_id"], "acc")

    def test_deleted_resource_with_another_id(self):
        current = {"id": "one"}
        with self.assertRaises(ModuleFail) as raised:
            ensure_resource_absent(
                FakeModule({}), "thing", "thing", current, Mock(return_value={"id": "two"}), context={"zone_id": "z"}
            )

        result = raised.exception.values
        self.assertEqual(result["msg"], "Cloudflare API returned the wrong thing")
        self.assertTrue(result["changed"])
        self.assertEqual(result["thing"], current)
        self.assertEqual(result["resource_id"], "one")
        self.assertEqual(result["zone_id"], "z")
