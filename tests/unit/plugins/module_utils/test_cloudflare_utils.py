# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from types import SimpleNamespace
from unittest import TestCase
from unittest.mock import Mock, patch

from ansible_collections.linuxhq.cloudflare.plugins.module_utils import cloudflare_utils
from ansible_collections.linuxhq.cloudflare.plugins.module_utils.cloudflare_utils import (
    api_request,
    cloudflare_client,
    find_by_name,
    iter_items,
    normalize_current_by_desired_fields,
    parse_list_response,
    payload_from_params,
    redact_scim_secrets,
    response_result,
    serialize_resource,
    values_differ,
)
from ansible_collections.linuxhq.cloudflare.tests.unit.plugins.modules.utils import (
    FakeModule,
    ModuleFail,
)


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
            "/resources?active=true&scope=a%2Fb&name=one%20%26%20two",
            paginate=True,
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

    def test_response_helpers_handle_envelopes_and_models(self):
        self.assertEqual(
            response_result(Model({"result": Model({"id": "one"})})),
            {"id": "one"},
        )
        self.assertEqual(
            parse_list_response({"result": {"id": "one"}})[0], [{"id": "one"}]
        )
        self.assertEqual(
            serialize_resource({"items": [Model({"id": "one", "empty": None})]}),
            {"items": [{"id": "one"}]},
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
                {"count": 0},
            ),
            {"enabled": False, "count": 0},
        )

    def test_redacts_scim_secrets_in_single_and_list_authentication(self):
        resource = {
            "scim_config": {
                "authentication": [
                    {"client_secret": "secret", "method": "oauth"},
                    {"password": "secret", "token": "secret"},
                ]
            }
        }

        self.assertEqual(
            redact_scim_secrets(resource),
            {
                "scim_config": {
                    "authentication": [{"method": "oauth"}, {}],
                }
            },
        )
