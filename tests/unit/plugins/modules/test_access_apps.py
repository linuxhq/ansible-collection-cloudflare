# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from unittest import TestCase
from unittest.mock import Mock

from ansible_collections.linuxhq.cloudflare.plugins.modules import access_apps
from ansible_collections.linuxhq.cloudflare.tests.unit.plugins.modules.utils import (
    FakeModule,
    ModuleExit,
    ModuleFail,
    status_error,
)


def params(**updates):
    values = {
        "account_id": "account",
        "name": "app",
        "domain": "app.example.com",
        "type": "self_hosted",
        "app_launcher_visible": True,
        "auto_redirect_to_identity": False,
        "enable_binding_cookie": False,
        "http_only_cookie_attribute": True,
        "session_duration": "24h",
        "state": "present",
    }
    values.update(updates)
    return values


def client_with(apps=(), created=None, updated=None, deleted=None):
    client = Mock()
    api = client.zero_trust.access.applications
    api.list.return_value = list(apps)
    api.create.return_value = created
    api.update.return_value = updated
    api.delete.return_value = deleted
    return client, api


class AccessAppsTests(TestCase):
    def run_module(self, module, client):
        with self.assertRaises((ModuleExit, ModuleFail)) as raised:
            access_apps.run(module, client)

        return raised.exception.values

    def test_looks_up_by_exact_name_server_side(self):
        client, api = client_with()
        self.run_module(FakeModule(params(), check_mode=True), client)

        api.list.assert_called_once_with(account_id="account", name="app", exact=True)

    def test_existing_app_with_provider_fields_is_unchanged(self):
        current = {
            "id": "app-id",
            "name": "app",
            "domain": "app.example.com",
            "type": "self_hosted",
            "provider": {"ignored": True},
        }
        client, api = client_with([current])

        result = self.run_module(FakeModule(params()), client)

        api.update.assert_not_called()
        self.assertFalse(result["changed"])

    def test_update_preserves_omitted_optional_fields(self):
        policies = [{"id": "policy-id", "precedence": 1}]
        current = {**params(), "id": "app-id", "policies": policies}
        del current["state"], current["account_id"]
        updated = {**current, "domain": "new.example.com"}
        client, api = client_with([current], updated=updated)

        result = self.run_module(FakeModule(params(domain="new.example.com")), client)

        self.assertEqual(api.update.call_args.args, ("app-id",))
        self.assertEqual(api.update.call_args.kwargs["policies"], policies)
        self.assertEqual(api.update.call_args.kwargs["account_id"], "account")
        self.assertTrue(result["changed"])

    def test_domain_change_drops_kept_destinations(self):
        destinations = [{"type": "public", "uri": "app.example.com"}]
        current = {**params(), "id": "app-id", "destinations": destinations}
        del current["state"], current["account_id"]
        updated = {
            **current,
            "domain": "new.example.com",
            "destinations": [{"type": "public", "uri": "new.example.com"}],
        }
        client, api = client_with([current], updated=updated)

        result = self.run_module(FakeModule(params(domain="new.example.com")), client)

        self.assertNotIn("destinations", api.update.call_args.kwargs)
        self.assertTrue(result["changed"])

    def test_unchanged_domain_keeps_destinations(self):
        destinations = [{"type": "public", "uri": "app.example.com"}]
        current = {**params(), "id": "app-id", "destinations": destinations}
        del current["state"], current["account_id"]
        client, api = client_with([current], updated={**current, "session_duration": "1h"})

        self.run_module(FakeModule(params(session_duration="1h")), client)

        self.assertEqual(api.update.call_args.kwargs["destinations"], destinations)

    def test_update_preserves_unmanaged_settings_except_self_hosted_domains(self):
        current = {**params(), "id": "app-id", "tags": ["engineering"], "self_hosted_domains": ["app.example.com"]}
        del current["state"], current["account_id"]
        updated = {**current, "domain": "new.example.com"}
        client, api = client_with([current], updated=updated)

        result = self.run_module(FakeModule(params(domain="new.example.com")), client)

        self.assertEqual(api.update.call_args.kwargs["tags"], ["engineering"])
        self.assertNotIn("self_hosted_domains", api.update.call_args.kwargs)
        self.assertTrue(result["changed"])

    def test_rejects_options_unsupported_by_type_before_any_request(self):
        cases = (
            ("bookmark", {"session_duration": "8h", "auto_redirect_to_identity": True}),
            ("bookmark", {"enable_binding_cookie": True, "http_only_cookie_attribute": False}),
            ("proxy_endpoint", {"app_launcher_visible": False, "enable_binding_cookie": True}),
            ("proxy_endpoint", {"http_only_cookie_attribute": False}),
            ("mcp_portal", {"app_launcher_visible": False, "enable_binding_cookie": True}),
        )
        for app_type, options in cases:
            with self.subTest(type=app_type, options=options):
                client, api = client_with()

                result = self.run_module(FakeModule(params(type=app_type, **options)), client)

                self.assertEqual(result["unsupported_fields"], sorted(options))
                self.assertIn(f"type {app_type} do not support", result["msg"])
                api.list.assert_not_called()
                api.create.assert_not_called()

    def test_type_accepts_defaults_for_unsupported_options(self):
        for app_type in ("bookmark", "mcp_portal", "proxy_endpoint"):
            with self.subTest(type=app_type):
                client, api = client_with()

                result = self.run_module(FakeModule(params(type=app_type), check_mode=True), client)

                self.assertTrue(result["changed"])
                api.create.assert_not_called()

    def test_check_mode_does_not_create(self):
        client, api = client_with()

        result = self.run_module(FakeModule(params(), check_mode=True), client)

        api.create.assert_not_called()
        self.assertTrue(result["changed"])

    def test_rejects_create_response_with_wrong_configuration(self):
        client, _ignored = client_with(created={"id": "app-id", "name": "app"})

        result = self.run_module(FakeModule(params()), client)

        self.assertIn("did not apply", result["msg"])

    def test_create_returns_secrets(self):
        created = {
            "id": "app-id",
            "name": "app",
            "domain": "app.example.com",
            "type": "self_hosted",
            "saas_app": {"client_secret": "secret", "client_id": "client"},
        }
        client, _ignored = client_with(created=created)

        result = self.run_module(FakeModule(params()), client)

        self.assertEqual(result["access_app"]["saas_app"], {"client_secret": "secret", "client_id": "client"})

    def test_deletes_app_and_returns_state(self):
        current = {
            "id": "app-id",
            "name": "app",
            "scim_config": {"authentication": {"password": "secret"}},
        }
        client, api = client_with([current])

        result = self.run_module(FakeModule(params(state="absent")), client)

        api.delete.assert_called_once_with("app-id", account_id="account")
        self.assertEqual(result["access_app"], current)

    def test_lookup_failure_names_operation(self):
        client, api = client_with()
        api.list.side_effect = status_error(403)

        with self.assertRaises(Exception) as raised:
            access_apps.run(FakeModule(params()), client)

        self.assertEqual(
            raised.exception._cloudflare_message,
            "Cloudflare API request failed while finding the Access application",
        )
