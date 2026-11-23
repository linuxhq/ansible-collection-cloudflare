# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from unittest import TestCase
from unittest.mock import Mock, patch

import cloudflare

from ansible_collections.linuxhq.cloudflare.plugins.modules import access_service_tokens
from ansible_collections.linuxhq.cloudflare.tests.unit.plugins.modules.utils import (
    FALSY_PAGE_RESULTS,
    FakeModule,
    ModuleExit,
    ModuleFail,
    list_response,
    sdk_client,
    status_error,
    timeout_error,
)


def params(**updates):
    values = {"account_id": "account", "name": "automation", "duration": "1y", "state": "present"}
    values.update(updates)
    return values


def client_with(tokens=(), created=None, updated=None, deleted=None):
    client = Mock()
    # Retry overrides return the same client so their calls are observable.
    client.with_options.return_value = client
    api = client.zero_trust.access.service_tokens
    api.list.return_value = list(tokens)
    api.create.return_value = created
    api.update.return_value = updated
    api.delete.return_value = deleted
    return client, api


class AccessServiceTokensTests(TestCase):
    def run_module(self, module, client):
        with self.assertRaises((ModuleExit, ModuleFail)) as raised:
            access_service_tokens.run(module, client)

        return raised.exception.values

    def test_lookup_failures_name_the_account(self):
        for found in (
            [{"name": "automation"}],
            [{"id": "one", "name": "automation"}, {"id": "two", "name": "automation"}],
        ):
            client, api = client_with(found)
            with self.subTest(found=found):
                result = self.run_module(FakeModule(params()), client)

                api.create.assert_not_called()
                self.assertEqual(result["account_id"], "account")
                self.assertEqual(result["name"], "automation")

    def test_malformed_create_response_names_the_account(self):
        client, _ignored = client_with(created={"name": "automation"})

        result = self.run_module(FakeModule(params()), client)

        self.assertEqual(result["msg"], "Cloudflare API returned malformed service token data")
        self.assertTrue(result["changed"])
        self.assertEqual(result["account_id"], "account")
        self.assertEqual(result["name"], "automation")

    def test_not_applied_after_create_reports_the_change(self):
        # The client secret is returned only in the create response.
        created = {"id": "token", "name": "automation", "duration": "8760h", "client_secret": "secret"}
        client, _ignored = client_with(created=created)

        result = self.run_module(FakeModule(params()), client)

        self.assertIn("did not apply", result["msg"])
        self.assertTrue(result["changed"])
        self.assertEqual(result["account_id"], "account")
        self.assertEqual(result["resource_id"], "token")
        self.assertEqual(result["service_token"], created)

    def test_token_recovered_after_a_lost_response_fails_without_its_secret(self):
        # The list model has no client secret, so the one the create response held is lost.
        # The lost secret is reported even when Cloudflare stored another duration, with
        # the details of the create error.
        server_body = {"success": False, "errors": [{"code": 10000, "message": "Internal"}], "messages": []}
        cases = (
            ("1y", timeout_error, {"error": "Request timed out."}),
            ("8760h", timeout_error, {"error": "Request timed out."}),
            ("1y", lambda: status_error(500, server_body), {"status_code": 500, "response": server_body}),
        )
        for duration, error, details in cases:
            with self.subTest(duration=duration, details=details):
                recovered = {"id": "token", "name": "automation", "duration": duration}
                client, api = client_with()
                api.create.side_effect = error()
                api.list.side_effect = [[], [recovered]]

                with self.assertRaises(ModuleFail) as raised:
                    access_service_tokens.run(FakeModule(params()), client)

                client.with_options.assert_called_once_with(max_retries=0)
                api.create.assert_called_once()
                self.assertEqual(
                    raised.exception.values,
                    {
                        "msg": "Cloudflare returned the service token without a client secret, which it returns only "
                        "in the create response; if this run created the token, rotate or delete it to obtain a new "
                        "client secret",
                        "changed": True,
                        "account_id": "account",
                        "name": "automation",
                        "resource_id": "token",
                        "service_token": recovered,
                        **details,
                    },
                )

    def test_malformed_recovered_token_reports_the_create_error(self):
        client, api = client_with()
        api.create.side_effect = timeout_error()
        api.list.side_effect = [[], [{"name": "automation", "duration": "1y"}]]

        result = self.run_module(FakeModule(params()), client)

        self.assertEqual(result["msg"], "Cloudflare API returned malformed service token data")
        self.assertTrue(result["changed"])
        self.assertEqual(result["error"], "Request timed out.")

    def test_retried_create_without_a_secret_reports_no_earlier_error(self):
        created = {"id": "token", "name": "automation", "duration": "1y"}
        client, api = client_with()
        api.create.side_effect = [status_error(429), created]

        with patch("time.sleep"):
            result = self.run_module(FakeModule(params()), client)

        self.assertEqual(api.create.call_count, 2)
        self.assertIn("without a client secret", result["msg"])
        self.assertNotIn("status_code", result)
        self.assertNotIn("response", result)

    def test_created_token_without_a_secret_fails_without_error_details(self):
        created = {"id": "token", "name": "automation", "duration": "1y"}
        client, _ignored = client_with(created=created)

        result = self.run_module(FakeModule(params()), client)

        self.assertIn("without a client secret", result["msg"])
        self.assertTrue(result["changed"])
        self.assertEqual(result["service_token"], created)
        self.assertNotIn("error", result)
        self.assertNotIn("status_code", result)

    def test_create_failure_is_reported_without_a_single_match(self):
        for found in ([], [{"id": "one", "name": "automation"}, {"id": "two", "name": "automation"}]):
            with self.subTest(found=found):
                client, api = client_with()
                error = status_error(503)
                api.create.side_effect = error
                api.list.side_effect = [[], found]

                with self.assertRaises(cloudflare.InternalServerError) as raised:
                    self.run_module(FakeModule(params()), client)

                self.assertIs(raised.exception, error)

    def test_empty_or_whitespace_name_fails_before_any_request(self):
        # Cloudflare stores such a name as null or "", so the resource is never found again.
        for name in ("", "   "):
            with self.subTest(name=name):
                client, api = client_with()

                result = self.run_module(FakeModule(params(name=name)), client)

                self.assertEqual(result["msg"], "name must not be empty or only whitespace")
                api.list.assert_not_called()

    def test_creates_token_with_explicit_duration_and_returns_secret(self):
        created = {"id": "token", "name": "automation", "duration": "1y", "client_secret": "secret"}
        client, api = client_with(created=created)

        result = self.run_module(FakeModule(params()), client)

        api.list.assert_called_once_with(account_id="account", name="automation")
        api.create.assert_called_once_with(account_id="account", name="automation", duration="1y")
        self.assertTrue(result["changed"])
        self.assertEqual(result["service_token"], created)

    def test_creates_token_without_duration(self):
        client, api = client_with(created={"id": "token", "name": "automation", "client_secret": "secret"})

        result = self.run_module(FakeModule(params(duration=None)), client)

        self.assertEqual(result["message"], "Service token created")

        api.create.assert_called_once_with(account_id="account", name="automation")

    def test_check_mode_does_not_create(self):
        client, api = client_with()

        result = self.run_module(FakeModule(params(), check_mode=True), client)

        api.create.assert_not_called()
        self.assertTrue(result["changed"])

    def test_updates_token_duration(self):
        current = {"id": "token", "name": "automation", "duration": "1h"}
        client, api = client_with([current], updated={**current, "duration": "1y"})

        result = self.run_module(FakeModule(params()), client)

        api.update.assert_called_once_with("token", account_id="account", name="automation", duration="1y")
        self.assertTrue(result["changed"])

    def test_rejects_update_response_with_wrong_duration(self):
        current = {"id": "token", "name": "automation", "duration": "1h"}
        client, _ignored = client_with([current], updated=current)

        result = self.run_module(FakeModule(params()), client)

        self.assertEqual(
            result["msg"], 'Cloudflare did not apply the requested service token: duration requested "1y", stored "1h"'
        )
        self.assertEqual(result["differences"], [{"field": "duration", "requested": "1y", "stored": "1h"}])
        self.assertTrue(result["changed"])
        self.assertEqual(result["resource_id"], "token")
        self.assertEqual(result["account_id"], "account")

    def test_forever_token_without_expiry_is_unchanged(self):
        client, api = client_with([{"id": "token", "name": "automation", "expires_at": None}])

        result = self.run_module(FakeModule(params(duration="forever")), client)

        api.update.assert_not_called()
        self.assertFalse(result["changed"])

    def test_deletes_token_by_sdk_identifier(self):
        client, api = client_with([{"id": "token", "name": "automation"}], deleted={"id": "token"})

        result = self.run_module(FakeModule(params(duration=None, state="absent")), client)

        api.delete.assert_called_once_with("token", account_id="account")
        self.assertTrue(result["changed"])

    def test_check_mode_does_not_delete(self):
        client, api = client_with([{"id": "token", "name": "automation"}])

        result = self.run_module(FakeModule(params(state="absent"), check_mode=True), client)

        api.delete.assert_not_called()
        self.assertTrue(result["changed"])

    def test_padded_name_is_trimmed_before_any_request(self):
        # Cloudflare trims the name, so the trimmed name is looked up and sent.
        token = {"id": "token", "name": "automation", "duration": "1y"}
        client, api = client_with(created={**token, "client_secret": "secret"})

        result = self.run_module(FakeModule(params(name=" automation ")), client)

        self.assertEqual(api.list.call_args_list[0].kwargs, {"account_id": "account", "name": "automation"})
        api.create.assert_called_once_with(account_id="account", name="automation", duration="1y")
        self.assertEqual(result["message"], "Service token created")

        client, api = client_with([token])

        result = self.run_module(FakeModule(params(name=" automation ")), client)

        api.create.assert_not_called()
        api.update.assert_not_called()
        self.assertFalse(result["changed"])

    def test_created_token_with_another_name_reports_the_write(self):
        created = {"id": "token", "name": "other", "duration": "1y", "client_secret": "secret"}
        client, api = client_with(created=created)

        result = self.run_module(FakeModule(params()), client)

        api.create.assert_called_once()
        self.assertEqual(result["msg"], "Cloudflare API returned the wrong service token")
        self.assertTrue(result["changed"])
        self.assertEqual(result["service_token"], created)
        self.assertEqual(result["resource_id"], "token")
        self.assertEqual(result["account_id"], "account")


class MalformedListTests(TestCase):
    def test_falsy_page_result_fails_without_a_write(self):
        for state in ("present", "absent"):
            for result in FALSY_PAGE_RESULTS:
                requests = []
                with self.subTest(state=state, result=result), sdk_client(list_response(result, requests)) as client:
                    with self.assertRaises(ModuleFail) as raised:
                        access_service_tokens.run(FakeModule(params(state=state)), client)

                    self.assertEqual(
                        raised.exception.values["msg"], "Cloudflare API returned malformed service token data"
                    )
                    self.assertEqual([request.method for request in requests], ["GET"])
