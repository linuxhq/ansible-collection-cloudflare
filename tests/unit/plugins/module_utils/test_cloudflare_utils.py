# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

import os
from datetime import datetime, timezone
from unittest import TestCase
from unittest.mock import Mock, patch

import cloudflare
import httpx

from ansible_collections.linuxhq.cloudflare.plugins.module_utils import cloudflare_utils
from ansible_collections.linuxhq.cloudflare.plugins.module_utils.cloudflare_utils import (
    cloudflare_client,
    cloudflare_error_context,
    differs,
    ensure_resource_absent,
    ensure_resource_present,
    ensure_settings,
    exit_resource_list,
    exit_settings,
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
    validate_tunnel_secret,
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

        for name in ("account_id", "domain", "name", "phase", "production_branch", "tunnel_id", "zone_id"):
            with (
                self.subTest(name=name),
                patch.object(cloudflare_utils, "Cloudflare", constructor),
                self.assertRaises(ModuleFail) as raised,
                cloudflare_client(FakeModule({"api_token": "secret", name: " \t"})),
            ):
                pass

            self.assertEqual(raised.exception.values["msg"], f"{name} must not be empty")

        with (
            patch.object(cloudflare_utils, "Cloudflare", constructor),
            self.assertRaises(ModuleFail) as raised,
            cloudflare_client(FakeModule({"api_token": "secret", "account_id": " account"})),
        ):
            pass

        self.assertEqual(
            raised.exception.values["msg"],
            "account_id must not contain leading or trailing whitespace",
        )

    def test_client_rejects_empty_or_control_character_tokens(self):
        for token, message in (
            (" ", "api_token must not be empty"),
            ("secret\nvalue", "api_token must not contain control characters"),
        ):
            with (
                self.subTest(token=token),
                patch.object(cloudflare_utils, "Cloudflare", Mock()),
                self.assertRaises(ModuleFail) as raised,
                cloudflare_client(FakeModule({"api_token": token})),
            ):
                pass

            self.assertEqual(raised.exception.values["msg"], message)

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
    def test_validates_tunnel_secrets(self):
        validate_tunnel_secret(FakeModule({}), None)
        validate_tunnel_secret(FakeModule({}), "MDEyMzQ1Njc4OWFiY2RlZjAxMjM0NTY3ODlhYmNkZWY=")

        for secret in ("not-base64", "c2hvcnQ="):
            with self.subTest(secret=secret), self.assertRaises(ModuleFail):
                validate_tunnel_secret(FakeModule({}), secret)

    def test_serializes_sdk_models_to_json_values(self):
        expires_at = datetime(2026, 8, 11, 12, 30, tzinfo=timezone.utc)

        with patch.object(cloudflare_utils, "BaseModel", SdkModel):
            self.assertEqual(
                serialize_resource([SdkModel("token", expires_at), {"name": None}]),
                [{"id": "token", "expires_at": "2026-08-11T12:30:00Z"}, {}],
            )

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

    def test_require_applied_rejects_nested_mismatch(self):
        require_applied(FakeModule({}), {"a": {"b": 1, "c": 2}}, {"a": {"b": 1}}, "resource")

        with self.assertRaises(ModuleFail) as raised:
            require_applied(FakeModule({}), {"a": {"b": 2}}, {"a": {"b": 1}}, "resource")

        self.assertEqual(raised.exception.values["msg"], "Cloudflare did not apply the requested resource")

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
            find_resource(module, [{"id": "one"}], "resource", "name", "One")

    def test_get_or_none_maps_only_not_found(self):
        self.assertIsNone(get_or_none(Mock(side_effect=status_error(404))))
        self.assertEqual(get_or_none(Mock(return_value={"id": "one"}), "one", zone_id="z"), {"id": "one"})

        with self.assertRaises(cloudflare.PermissionDeniedError):
            get_or_none(Mock(side_effect=status_error(403)))

    def test_find_resource_stops_at_first_match(self):
        def items():
            yield {"id": "one", "name": "One"}
            raise AssertionError("iterated past the match")

        self.assertEqual(find_resource(FakeModule({}), items(), "resource", "name", "One")["id"], "one")


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
    def run_settings(self, current, payload, edited=None, check_mode=False, comparable=None):
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
            )

        return raised.exception, edit

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
