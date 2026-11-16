# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

import os
from datetime import datetime, timezone
from unittest import TestCase
from unittest.mock import Mock, patch

import cloudflare
import httpx

from ansible_collections.linuxhq.cloudflare.plugins.module_utils import cloudflare_utils
from ansible_collections.linuxhq.cloudflare.plugins.module_utils.cloudflare_utils import (
    applied_differences,
    cloudflare_client,
    cloudflare_error_context,
    differs,
    ensure_resource_absent,
    ensure_resource_present,
    ensure_settings,
    exit_resource_list,
    exit_settings,
    fail_not_applied,
    find_resource,
    get_or_none,
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
)
from ansible_collections.linuxhq.cloudflare.tests.unit.plugins.modules.utils import (
    FakeModule,
    ModuleExit,
    ModuleFail,
    connection_error,
    status_error,
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

                def make_client(**kwargs):
                    return cloudflare.Cloudflare(
                        **kwargs,
                        http_client=httpx.Client(transport=httpx.MockTransport(respond)),
                    )

                with (
                    patch.dict(os.environ, environment, clear=True),
                    patch.object(cloudflare_utils, "Cloudflare", side_effect=make_client),
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

        constructor.assert_called_once_with(api_token="secret", default_headers=EXPECTED_HEADERS)
        context.__exit__.assert_called_once()

    def test_client_normalizes_token_and_rejects_empty_identifiers(self):
        constructor = Mock(return_value=sdk_context(Mock()))

        with (
            patch.object(cloudflare_utils, "Cloudflare", constructor),
            cloudflare_client(FakeModule({"api_token": "  secret  ", "name": "app"})),
        ):
            pass

        constructor.assert_called_once_with(api_token="secret", default_headers=EXPECTED_HEADERS)

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
        self.assertTrue(differs(headers, {"headers": {"A": {"value": 1}}}, exact_fields=("headers",)))
        self.assertFalse(
            differs(headers, {"headers": {"A": {"value": 1}, "B": {"value": 2}}}, exact_fields=("headers",))
        )
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
            "include": [{"email": None}, {"ip": None}, {"group": None}, {"email": "a@example.com"}],
            "require": [{"everyone": []}, {"everyone": True}, {"any_valid_service_token": ""}],
        }

        validate_access_selectors(FakeModule(rules))

    def test_access_selectors_reject_non_mapping_and_empty_selectors(self):
        cases = (
            (None, "must be a mapping that sets one selector, such as {'everyone': {}}"),
            ("azure_ad", "must be a mapping that sets one selector, such as {'everyone': {}}"),
            (["everyone"], "must be a mapping that sets one selector, such as {'everyone': {}}"),
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
            exit_settings(FakeModule({}), "settings", None, "settings")

        self.assertEqual(raised.exception.values, {"changed": False, "settings": {}})

        with self.assertRaises(ModuleFail):
            exit_settings(FakeModule({}), "settings", ["bad"], "settings")


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

    def test_comparable_normalizes_both_sides(self):
        def comparable(settings):
            return {**settings, "status": {"pending": "active"}.get(settings.get("status"), settings.get("status"))}

        result, edit = self.run_settings({"status": "pending"}, {"status": "active"}, comparable=comparable)

        edit.assert_not_called()
        self.assertFalse(result.values["changed"])


class EnsureResourceTests(TestCase):
    def present(self, current, payload, created=None, updated=None, check_mode=False, **kwargs):
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
                **kwargs,
            )

        return raised.exception, create, update

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

    def test_mutation_errors_carry_context(self):
        error = status_error(400)
        create = Mock(side_effect=error)

        with self.assertRaises(cloudflare.BadRequestError):
            ensure_resource_present(FakeModule({}), "thing", "thing", None, {"a": 1}, create, Mock())

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
