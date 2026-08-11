# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from datetime import datetime, timezone
from types import SimpleNamespace
from unittest import TestCase
from unittest.mock import Mock, patch

from ansible_collections.linuxhq.cloudflare.plugins.module_utils import cloudflare_utils
from ansible_collections.linuxhq.cloudflare.plugins.module_utils.cloudflare_utils import (
    CloudflareResponseError,
    api_request,
    cloudflare_client,
    cloudflare_error_context,
    cloudflare_path,
    cloudflare_query,
    delete_result,
    find_by_field,
    find_by_name,
    iter_items,
    normalize_current_by_desired_fields,
    parse_list_response,
    payload_from_params,
    redact_access_app_secrets,
    redact_sensitive_values,
    require_mapping,
    resource_field,
    resource_id,
    response_result,
    serialize_resource,
    validate_requested_values,
    validate_resource_fields,
    validate_tunnel_secret,
    values_differ,
)
from ansible_collections.linuxhq.cloudflare.tests.unit.plugins.modules.utils import (
    FakeModule,
    ModuleFail,
)
from cloudflare.types.zero_trust.access.service_token import ServiceToken


class ApiConnectionError(Exception):
    pass


class ApiStatusError(Exception):
    def __init__(self, message, status_code=None, response=None):
        super().__init__(message)
        self.response = response
        self.status_code = status_code


class ApiError(Exception):
    pass


ERRORS = SimpleNamespace(
    APIConnectionError=ApiConnectionError,
    APIStatusError=ApiStatusError,
    APIError=ApiError,
)


class Model:
    def __init__(self, value):
        self.value = value

    def to_dict(self):
        return self.value


class CloudflareUtilsTests(TestCase):
    def test_delete_result_verifies_expected_resource(self):
        with patch.object(
            cloudflare_utils,
            "api_request",
            return_value={"result": {"id": "one"}},
        ):
            self.assertEqual(
                delete_result(Mock(), "/resources/one", expected_id="one"),
                {"id": "one"},
            )

        with (
            patch.object(
                cloudflare_utils,
                "api_request",
                return_value={"result": {"id": "two"}},
            ),
            self.assertRaisesRegex(CloudflareResponseError, "wrong deleted resource"),
        ):
            delete_result(Mock(), "/resources/one", expected_id="one")

    def test_validates_tunnel_secrets(self):
        validate_tunnel_secret(
            FakeModule({}), "eHh4eHh4eHh4eHh4eHh4eHh4eHh4eHh4eHh4eHh4eHg="
        )

        for secret in ("not-base64", "c2hvcnQ="):
            with self.subTest(secret=secret), self.assertRaises(ModuleFail):
                validate_tunnel_secret(FakeModule({}), secret)

    def test_api_request_passes_body_and_bounded_options(self):
        client = Mock()
        client.patch.return_value = {"result": {"id": "one"}}

        result = api_request(
            client,
            "patch",
            "/resources/one",
            body={"enabled": True},
            timeout=12,
        )

        client.patch.assert_called_once_with(
            "/resources/one",
            cast_to=object,
            body={"enabled": True},
            options={"timeout": 12, "max_retries": 0},
        )
        self.assertEqual(result, {"result": {"id": "one"}})

    def test_api_request_accepts_expected_status(self):
        client = Mock()
        client.get.side_effect = ApiStatusError("missing", status_code=404)

        with patch.object(cloudflare_utils, "cloudflare", ERRORS):
            result = api_request(client, "get", "/missing", ok_statuses=[404])

        self.assertIsNone(result)

    def test_api_request_adds_failure_context(self):
        client = Mock()
        error = ApiStatusError("rejected", status_code=400)
        client.put.side_effect = error

        with (
            patch.object(cloudflare_utils, "cloudflare", ERRORS),
            self.assertRaises(ApiStatusError),
        ):
            api_request(client, "put", "/resources/one", body={})

        self.assertEqual(error._cloudflare_message, "Cloudflare API PUT request failed")
        self.assertEqual(
            error._cloudflare_context,
            {"method": "PUT", "path": "/resources/one"},
        )

    def test_sdk_error_context_adds_failure_context(self):
        error = ApiError("rejected")

        with (
            patch.object(cloudflare_utils, "cloudflare", ERRORS),
            self.assertRaises(ApiError),
            cloudflare_error_context("Creating resource failed", resource_id="one"),
        ):
            raise error

        self.assertEqual(error._cloudflare_message, "Creating resource failed")
        self.assertEqual(error._cloudflare_context, {"resource_id": "one"})

    def test_client_reports_missing_sdk(self):
        module = FakeModule({"api_token": "secret"})

        with (
            patch.object(cloudflare_utils, "Cloudflare", None),
            self.assertRaises(ModuleFail) as raised,
            cloudflare_client(module),
        ):
            pass

        self.assertEqual(
            raised.exception.values["missing_python_package"],
            "cloudflare",
        )

    def test_client_closes_sdk_context(self):
        module = FakeModule({"api_token": "secret"})
        client = Mock()
        context = Mock()
        context.__enter__ = Mock(return_value=client)
        context.__exit__ = Mock(return_value=False)
        constructor = Mock(return_value=context)

        with (
            patch.object(cloudflare_utils, "Cloudflare", constructor),
            patch.object(cloudflare_utils, "cloudflare", ERRORS),
            cloudflare_client(module) as result,
        ):
            self.assertIs(result, client)

        constructor.assert_called_once_with(api_token="secret")
        context.__exit__.assert_called_once()

    def test_client_normalizes_token_and_rejects_empty_identifiers(self):
        context = Mock()
        context.__enter__ = Mock(return_value=Mock())
        context.__exit__ = Mock(return_value=False)
        constructor = Mock(return_value=context)

        with (
            patch.object(cloudflare_utils, "Cloudflare", constructor),
            patch.object(cloudflare_utils, "cloudflare", ERRORS),
            cloudflare_client(FakeModule({"api_token": "  secret  ", "name": "app"})),
        ):
            pass

        constructor.assert_called_once_with(api_token="secret")

        for name in (
            "account_id",
            "domain",
            "name",
            "phase",
            "production_branch",
            "tunnel_id",
            "zone_id",
        ):
            with (
                self.subTest(name=name),
                patch.object(cloudflare_utils, "Cloudflare", constructor),
                self.assertRaises(ModuleFail) as raised,
                cloudflare_client(FakeModule({"api_token": "secret", name: " \t"})),
            ):
                pass

            self.assertEqual(
                raised.exception.values["msg"], f"{name} must not be empty"
            )

        with (
            patch.object(cloudflare_utils, "Cloudflare", constructor),
            self.assertRaises(ModuleFail) as raised,
            cloudflare_client(
                FakeModule({"api_token": "secret", "account_id": " account"})
            ),
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

    def test_client_sanitizes_sdk_failure(self):
        module = FakeModule({"api_token": "secret"})
        context = Mock()
        context.__enter__ = Mock(side_effect=ApiConnectionError("offline"))
        context.__exit__ = Mock(return_value=False)

        with (
            patch.object(cloudflare_utils, "Cloudflare", return_value=context),
            patch.object(cloudflare_utils, "cloudflare", ERRORS),
            self.assertRaises(ModuleFail) as raised,
            cloudflare_client(module),
        ):
            pass

        self.assertEqual(
            raised.exception.values["msg"],
            "Cloudflare API connection failed",
        )
        self.assertEqual(raised.exception.values["error"], "offline")

    def test_find_by_name_encodes_query_values(self):
        client = Mock()

        with patch.object(
            cloudflare_utils,
            "iter_items",
            return_value=[{"name": "one & two"}],
        ) as items:
            result = find_by_name(
                client,
                "/resources?active=true",
                "one & two",
                extra_query={"scope": "a/b"},
            )

        self.assertEqual(result, {"name": "one & two"})
        items.assert_called_once_with(
            client,
            "/resources?active=true&scope=a%2Fb&name=one+%26+two",
            paginate=True,
        )

    def test_find_by_field_rejects_malformed_resources(self):
        for resource in (
            "invalid",
            {},
            {"name": 1},
            {"name": " "},
            {"name": " padded"},
        ):
            with (
                self.subTest(resource=resource),
                patch.object(
                    cloudflare_utils,
                    "iter_items",
                    return_value=[resource],
                ),
                self.assertRaisesRegex(CloudflareResponseError, "malformed resource"),
            ):
                find_by_field(Mock(), "/resources", "name", "resource")

    def test_builds_encoded_paths_and_queries(self):
        path = cloudflare_path("accounts", "account/id", "projects", "docs site")

        self.assertEqual(path, "/accounts/account%2Fid/projects/docs%20site")
        self.assertEqual(
            cloudflare_query(path, {"name": "one & two", "cursor": None}),
            "/accounts/account%2Fid/projects/docs%20site?name=one+%26+two",
        )

    def test_iter_items_follows_result_info_pages(self):
        client = Mock()
        responses = [
            {"result": [{"id": "one"}], "result_info": {"total_pages": 2}},
            {"result": [{"id": "two"}], "result_info": {"total_pages": 2}},
        ]

        with patch.object(cloudflare_utils, "api_request", side_effect=responses):
            result = list(iter_items(client, "/resources", per_page=1))

        self.assertEqual(result, [{"id": "one"}, {"id": "two"}])

    def test_iter_items_follows_full_bare_list_pages(self):
        client = Mock()

        with patch.object(
            cloudflare_utils,
            "api_request",
            side_effect=[[{"id": "one"}], [{"id": "two"}], []],
        ):
            result = list(iter_items(client, "/resources", per_page=1))

        self.assertEqual(result, [{"id": "one"}, {"id": "two"}])

    def test_iter_items_rejects_malformed_pagination_data(self):
        for result_info in (
            {"page": True},
            {"count": -1},
            {"total_pages": -1},
            {"total_pages": True},
            {"total_count": -1},
            {"total_count": 1.5},
        ):
            with (
                self.subTest(result_info=result_info),
                patch.object(
                    cloudflare_utils,
                    "api_request",
                    return_value={"result": [], "result_info": result_info},
                ),
                self.assertRaisesRegex(CloudflareResponseError, "malformed pagination"),
            ):
                list(iter_items(Mock(), "/resources"))

    def test_iter_items_rejects_inconsistent_pagination_data(self):
        for response in (
            {"result": [{"id": "one"}], "result_info": {"page": 2}},
            {"result": [{"id": "one"}], "result_info": {"count": 0}},
            {"result": [{"id": "one"}], "result_info": {"total_pages": 0}},
            {"result": [{"id": "one"}], "result_info": {"total_count": 0}},
            {"result": [], "result_info": {"total_count": 1}},
            {
                "result": [{"id": "one"}],
                "result_info": {"total_pages": 1, "total_count": 2},
            },
        ):
            with (
                self.subTest(response=response),
                patch.object(cloudflare_utils, "api_request", return_value=response),
                self.assertRaisesRegex(CloudflareResponseError, "malformed pagination"),
            ):
                list(iter_items(Mock(), "/resources", per_page=1))

    def test_iter_items_validates_page_metadata_before_yielding(self):
        with (
            patch.object(
                cloudflare_utils,
                "api_request",
                return_value={
                    "result": [{"id": "one"}],
                    "result_info": {"page": 2},
                },
            ),
            self.assertRaisesRegex(CloudflareResponseError, "malformed pagination"),
        ):
            next(iter_items(Mock(), "/resources"))

    def test_response_helpers_handle_envelopes_and_models(self):
        self.assertEqual(
            response_result(Model({"result": Model({"id": "one"})})),
            {"id": "one"},
        )
        self.assertIsNone(response_result({"result": None, "success": True}))
        self.assertEqual(
            parse_list_response({"result": [{"id": "one"}]})[0], [{"id": "one"}]
        )
        self.assertEqual(
            serialize_resource({"items": [Model({"id": "one", "empty": None})]}),
            {"items": [{"id": "one"}]},
        )

        for response in (
            {"success": False, "result": []},
            {"success": True},
            {"success": "true", "result": []},
            {"result": {}},
            {},
        ):
            with (
                self.subTest(response=response),
                self.assertRaises(CloudflareResponseError),
            ):
                parse_list_response(response)

        for response in ({"success": True}, {"success": "true", "result": {}}):
            with self.assertRaisesRegex(CloudflareResponseError, "malformed data"):
                response_result(response)

    def test_validate_requested_values_rejects_nested_mismatch(self):
        module = FakeModule({})

        with self.assertRaises(ModuleFail) as raised:
            validate_requested_values(
                module,
                {"config": {"enabled": False, "ignored": True}},
                {"config": {"enabled": True}},
                "settings",
            )

        self.assertIn("did not apply", raised.exception.values["msg"])

    def test_serializes_sdk_models_to_json_values(self):
        expires_at = datetime(2026, 8, 11, 12, 30, tzinfo=timezone.utc)

        self.assertEqual(
            serialize_resource(ServiceToken(id="token", expires_at=expires_at)),
            {"id": "token", "expires_at": "2026-08-11T12:30:00Z"},
        )

    def test_payload_and_comparison_helpers_manage_only_desired_fields(self):
        desired = {"nested": {"enabled": True}, "items": [{"id": "one"}]}
        current = {
            "ignored": "value",
            "nested": {"enabled": True, "provider": "value"},
            "items": [{"id": "one", "provider": "value"}],
        }

        self.assertEqual(
            normalize_current_by_desired_fields(current, desired),
            desired,
        )
        self.assertFalse(values_differ(desired, desired.copy()))
        self.assertTrue(values_differ(desired, {"nested": {"enabled": False}}))
        self.assertEqual(
            payload_from_params(
                {"enabled": False, "name": None},
                ("enabled", "name", "count"),
            ),
            {"enabled": False},
        )

    def test_redacts_access_app_secrets_recursively(self):
        resource = {
            "saas_app": {"client_secret": "secret", "name": "example"},
            "scim_config": {
                "authentication": [
                    {"client_secret": "secret", "method": "oauth"},
                    {"nested": [{"password": "secret", "token": "secret"}]},
                ]
            },
        }

        self.assertEqual(
            redact_access_app_secrets(resource),
            {
                "saas_app": {"name": "example"},
                "scim_config": {
                    "authentication": [
                        {"method": "oauth"},
                        {"nested": [{}]},
                    ],
                },
            },
        )

    def test_redacts_sensitive_error_response_fields(self):
        self.assertEqual(
            redact_sensitive_values(
                {
                    "client_secret": "secret",
                    "nested": [{"api_token": "token", "message": "safe"}],
                }
            ),
            {
                "client_secret": "********",
                "nested": [{"api_token": "********", "message": "safe"}],
            },
        )

    def test_validates_required_resource_fields(self):
        module = FakeModule({})

        self.assertEqual(resource_id(module, {"id": "one"}, "resource"), "one")
        self.assertEqual(
            resource_field(module, {"name": "example"}, "name", "resource"),
            "example",
        )
        resources = [{"id": "one", "name": "One"}, {"id": "two", "name": "Two"}]
        validate_resource_fields(module, resources, ("id", "name"), "resource")
        require_mapping(module, {"id": "one"}, "resource")

        with self.assertRaises(ModuleFail) as raised:
            resource_id(module, {"id": "one"}, "resource", expected="two")

        self.assertEqual(
            raised.exception.values["msg"],
            "Cloudflare API returned the wrong resource",
        )

        for resource in (
            None,
            {},
            {"id": None},
            {"id": " "},
            {"id": " one"},
            {"id": 1},
        ):
            with (
                self.subTest(resource=resource),
                self.assertRaises(ModuleFail) as raised,
            ):
                resource_id(module, resource, "resource")

            self.assertEqual(
                raised.exception.values["msg"],
                "Cloudflare API returned malformed resource data",
            )
