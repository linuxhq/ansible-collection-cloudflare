# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from unittest import TestCase
from unittest.mock import Mock, patch

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
        "app_launcher_visible": None,
        "auto_redirect_to_identity": None,
        "enable_binding_cookie": None,
        "http_only_cookie_attribute": None,
        "session_duration": None,
        "state": "present",
    }
    values.update(updates)
    return values


def stored(**updates):
    """Return the application Cloudflare stores for params(**updates)."""
    values = {key: value for key, value in params(**updates).items() if value is not None}
    del values["account_id"], values["state"]
    return {"id": "app-id", **values}


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

    def test_removed_cors_header_key_is_a_change(self):
        cors = {"allowed_methods": ["GET"]}
        current = stored(cors_headers={**cors, "allow_all_origins": True})
        client, api = client_with([current], updated={**current, "cors_headers": cors})

        result = self.run_module(FakeModule(params(cors_headers=cors)), client)

        self.assertEqual(api.update.call_args.kwargs["cors_headers"], cors)
        self.assertTrue(result["changed"])

        client, api = client_with([current], updated=current)
        result = self.run_module(FakeModule(params(cors_headers=cors)), client)

        self.assertIn("did not apply", result["msg"])

    def test_change_to_bookmark_carries_only_fields_bookmarks_store(self):
        current = {
            **stored(),
            "allowed_idps": [],
            "cors_headers": {"allowed_methods": ["GET"]},
            "custom_deny_message": "denied",
            "destinations": [{"type": "public", "uri": "app.example.com"}],
            "eager_redirect_cookie_setting": False,
            "logo_url": "https://example.com/logo.png",
            "options_preflight_bypass": False,
            "policies": [{"id": "policy-id", "precedence": 1}],
            "skip_interstitial": True,
            "tags": ["tag"],
        }
        updated = {
            "id": "app-id",
            "name": "app",
            "domain": "app.example.com",
            "type": "bookmark",
            "app_launcher_visible": True,
            "logo_url": current["logo_url"],
            "policies": current["policies"],
            "tags": current["tags"],
        }
        client, api = client_with([current], updated=updated)

        result = self.run_module(FakeModule(params(type="bookmark")), client)

        sent = api.update.call_args.kwargs
        for field in ("allowed_idps", "cors_headers", "custom_deny_message", "destinations", "skip_interstitial"):
            self.assertNotIn(field, sent)

        for field in ("eager_redirect_cookie_setting", "options_preflight_bypass"):
            self.assertNotIn(field, sent)

        self.assertEqual(sent["policies"], current["policies"])
        self.assertEqual(sent["tags"], current["tags"])
        self.assertEqual(sent["logo_url"], current["logo_url"])
        self.assertTrue(result["changed"])

        client, api = client_with([updated])
        result = self.run_module(FakeModule(params(type="bookmark")), client)

        api.update.assert_not_called()
        self.assertFalse(result["changed"])

    def test_update_preserves_omitted_optional_fields(self):
        policies = [{"id": "policy-id", "precedence": 1}]
        current = stored(policies=policies)
        updated = {**current, "domain": "new.example.com"}
        client, api = client_with([current], updated=updated)

        result = self.run_module(FakeModule(params(domain="new.example.com")), client)

        self.assertEqual(api.update.call_args.args, ("app-id",))
        self.assertEqual(api.update.call_args.kwargs["policies"], policies)
        self.assertEqual(api.update.call_args.kwargs["account_id"], "account")
        self.assertTrue(result["changed"])

    def test_settings_have_no_module_default(self):
        with (
            patch.object(access_apps, "AnsibleModule", side_effect=RuntimeError) as module,
            self.assertRaises(RuntimeError),
        ):
            access_apps.main()

        argument_spec = module.call_args.kwargs["argument_spec"]
        for field in access_apps.DEFAULT_FIELDS:
            self.assertNotIn("default", argument_spec[field])

    def test_create_omits_unset_settings(self):
        created = stored()
        client, api = client_with(created=created)

        result = self.run_module(FakeModule(params()), client)

        api.create.assert_called_once_with(
            account_id="account", domain="app.example.com", name="app", type="self_hosted"
        )
        self.assertTrue(result["changed"])

    def test_update_preserves_omitted_settings(self):
        settings = {
            "app_launcher_visible": False,
            "auto_redirect_to_identity": True,
            "enable_binding_cookie": True,
            "http_only_cookie_attribute": False,
            "session_duration": "8h",
        }
        current = stored(**settings)
        client, api = client_with([current], updated={**current, "domain": "new.example.com"})

        result = self.run_module(FakeModule(params(domain="new.example.com")), client)

        sent = api.update.call_args.kwargs
        self.assertEqual({field: sent[field] for field in settings}, settings)
        self.assertTrue(result["changed"])

        client, api = client_with([{**current, "domain": "new.example.com"}])
        result = self.run_module(FakeModule(params(domain="new.example.com")), client)

        api.update.assert_not_called()
        self.assertFalse(result["changed"])

    def test_explicit_settings_compare_with_cloudflare_defaults(self):
        client, api = client_with([stored()])

        result = self.run_module(FakeModule(params(**access_apps.DEFAULT_FIELDS)), client)

        api.update.assert_not_called()
        self.assertFalse(result["changed"])

        current = stored(auto_redirect_to_identity=True)
        client, api = client_with([current], updated=stored(auto_redirect_to_identity=False))

        result = self.run_module(FakeModule(params(auto_redirect_to_identity=False)), client)

        self.assertIs(api.update.call_args.kwargs["auto_redirect_to_identity"], False)
        self.assertTrue(result["changed"])

    def test_change_to_bookmark_keeps_launcher_visibility(self):
        current = stored(app_launcher_visible=False, session_duration="8h")
        updated = stored(type="bookmark", app_launcher_visible=False)
        client, api = client_with([current], updated=updated)

        result = self.run_module(FakeModule(params(type="bookmark")), client)

        sent = api.update.call_args.kwargs
        self.assertIs(sent["app_launcher_visible"], False)
        self.assertNotIn("session_duration", sent)
        self.assertTrue(result["changed"])

    def test_change_to_proxy_endpoint_carries_only_fields_proxy_endpoints_store(self):
        current = {
            **stored(app_launcher_visible=True, auto_redirect_to_identity=True, session_duration="8h"),
            "allowed_idps": ["idp"],
            "eager_redirect_cookie_setting": True,
            "options_preflight_bypass": False,
            "policies": [{"id": "policy-id", "precedence": 1}],
            "tags": ["tag"],
        }
        # The fields Cloudflare returns after a change to proxy_endpoint.
        updated = {
            **stored(type="proxy_endpoint", auto_redirect_to_identity=True, session_duration="8h"),
            "allowed_idps": current["allowed_idps"],
            "policies": current["policies"],
            "tags": current["tags"],
        }
        client, api = client_with([current], updated=updated)

        result = self.run_module(FakeModule(params(type="proxy_endpoint")), client)

        sent = api.update.call_args.kwargs
        for field in ("eager_redirect_cookie_setting", "options_preflight_bypass", "app_launcher_visible"):
            self.assertNotIn(field, sent)

        for field in ("allowed_idps", "auto_redirect_to_identity", "policies", "session_duration", "tags"):
            self.assertEqual(sent[field], current[field])

        self.assertTrue(result["changed"])

        client, api = client_with([updated])
        result = self.run_module(FakeModule(params(type="proxy_endpoint")), client)

        api.update.assert_not_called()
        self.assertFalse(result["changed"])

    def test_false_interstitial_and_401_redirect_match_omitted_settings(self):
        false_options = {"service_auth_401_redirect": False, "skip_interstitial": False}
        for app_type in ("self_hosted", "bookmark", "proxy_endpoint"):
            with self.subTest(type=app_type):
                client, api = client_with([stored(type=app_type)])

                result = self.run_module(FakeModule(params(type=app_type, **false_options)), client)

                api.update.assert_not_called()
                self.assertFalse(result["changed"])

        current = stored(service_auth_401_redirect=True, skip_interstitial=True)
        client, api = client_with([current], updated=stored())

        result = self.run_module(FakeModule(params(**false_options)), client)

        for field in false_options:
            self.assertIs(api.update.call_args.kwargs[field], False)

        self.assertTrue(result["changed"])

    def test_change_to_mcp_portal_drops_launcher_visibility(self):
        current = stored(app_launcher_visible=False, auto_redirect_to_identity=True)
        updated = stored(type="mcp_portal", auto_redirect_to_identity=True)
        client, api = client_with([current], updated=updated)

        result = self.run_module(FakeModule(params(type="mcp_portal")), client)

        sent = api.update.call_args.kwargs
        self.assertNotIn("app_launcher_visible", sent)
        self.assertIs(sent["auto_redirect_to_identity"], True)
        self.assertTrue(result["changed"])

    def test_domain_change_drops_kept_destinations(self):
        destinations = [{"type": "public", "uri": "app.example.com"}]
        current = stored(destinations=destinations)
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
        current = stored(destinations=destinations)
        client, api = client_with([current], updated={**current, "session_duration": "1h"})

        self.run_module(FakeModule(params(session_duration="1h")), client)

        self.assertEqual(api.update.call_args.kwargs["destinations"], destinations)

    def test_update_preserves_unmanaged_settings_except_self_hosted_domains(self):
        current = {**stored(), "tags": ["engineering"], "self_hosted_domains": ["app.example.com"]}
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
            ("mcp_portal", {"app_launcher_visible": False}),
        )
        for app_type, options in cases:
            with self.subTest(type=app_type, options=options):
                client, api = client_with()

                result = self.run_module(FakeModule(params(type=app_type, **options)), client)

                self.assertEqual(result["unsupported_fields"], sorted(options))
                self.assertIn(f"type {app_type} do not support", result["msg"])
                api.list.assert_not_called()
                api.create.assert_not_called()

    def test_mcp_portal_accepts_cookie_and_interstitial_options(self):
        options = {"enable_binding_cookie": True, "skip_interstitial": True, "service_auth_401_redirect": True}
        client, api = client_with()

        result = self.run_module(FakeModule(params(type="mcp_portal", **options), check_mode=True), client)

        self.assertTrue(result["changed"])
        api.list.assert_called_once()

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
