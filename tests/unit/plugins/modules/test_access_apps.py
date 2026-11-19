# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from unittest import TestCase
from unittest.mock import Mock, patch

from ansible_collections.linuxhq.cloudflare.plugins.modules import access_apps
from ansible_collections.linuxhq.cloudflare.tests.unit.plugins.modules.utils import (
    FakeModule,
    ModuleExit,
    ModuleFail,
    status_error,
    timeout_error,
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
    # Retry overrides return the same client so their calls are observable.
    client.with_options.return_value = client
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

    def test_lookup_failures_name_the_account(self):
        for found in ([{"name": "app"}], [{"id": "one", "name": "app"}, {"id": "two", "name": "app"}]):
            client, api = client_with(found)
            with self.subTest(found=found):
                result = self.run_module(FakeModule(params()), client)

                api.create.assert_not_called()
                self.assertEqual(result["account_id"], "account")
                self.assertEqual(result["name"], "app")

    def test_empty_or_whitespace_name_fails_before_any_request(self):
        # Cloudflare stores such a name as null or "", so the resource is never found again.
        for name in ("", "   "):
            with self.subTest(name=name):
                client, api = client_with()

                result = self.run_module(FakeModule(params(name=name)), client)

                self.assertEqual(result["msg"], "name must not be empty or only whitespace")
                api.list.assert_not_called()

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

    def test_bare_ip_destination_matches_stored_cidr(self):
        public = {"type": "public", "uri": "app.example.com"}
        cases = (
            ("10.0.0.1", "10.0.0.1/32"),
            ("2001:db8::1", "2001:db8::1/128"),
            ("10.0.1.0/24", "10.0.1.0/24"),
        )
        for requested, cidr in cases:
            destinations = [public, {"type": "private", "cidr": requested}]
            current = stored(destinations=[public, {"type": "private", "cidr": cidr}])
            with self.subTest(requested=requested, converged=True):
                client, api = client_with([current])
                result = self.run_module(FakeModule(params(destinations=destinations)), client)

                api.update.assert_not_called()
                self.assertFalse(result["changed"])

            with self.subTest(requested=requested, created=True):
                client, api = client_with(created=current)
                result = self.run_module(FakeModule(params(destinations=destinations)), client)

                self.assertEqual(api.create.call_args.kwargs["destinations"][1]["cidr"], cidr)
                self.assertTrue(result["changed"])
                self.assertNotIn("msg", result)

    def test_removed_destination_key_is_a_change(self):
        private = {"type": "private", "cidr": "10.0.1.0/24"}
        current = stored(destinations=[{**private, "l4_protocol": "tcp", "port_range": "22"}])
        for check_mode in (True, False):
            with self.subTest(check_mode=check_mode):
                client, api = client_with([current], updated=stored(destinations=[private]))
                result = self.run_module(FakeModule(params(destinations=[private]), check_mode=check_mode), client)

                self.assertTrue(result["changed"])
                if check_mode:
                    api.update.assert_not_called()
                else:
                    self.assertEqual(api.update.call_args.kwargs["destinations"], [private])

        client, api = client_with([current], updated=current)
        result = self.run_module(FakeModule(params(destinations=[private])), client)

        self.assertIn("did not apply", result["msg"])

    def test_allowed_idps_match_in_any_order(self):
        requested = ["idp-b", "idp-a"]
        current = stored(allowed_idps=["idp-a", "idp-b"])
        client, api = client_with([current])
        result = self.run_module(FakeModule(params(allowed_idps=requested)), client)

        api.update.assert_not_called()
        self.assertFalse(result["changed"])
        self.assertEqual(result["access_app"]["allowed_idps"], current["allowed_idps"])

        client, api = client_with(created=current)
        result = self.run_module(FakeModule(params(allowed_idps=requested)), client)

        self.assertEqual(api.create.call_args.kwargs["allowed_idps"], requested)
        self.assertTrue(result["changed"])
        self.assertNotIn("msg", result)

        current = stored(allowed_idps=["idp-a"])
        updated = stored(allowed_idps=["idp-a", "idp-b"])
        client, api = client_with([current], updated=updated)
        result = self.run_module(FakeModule(params(allowed_idps=requested)), client)

        self.assertEqual(api.update.call_args.kwargs["allowed_idps"], requested)
        self.assertTrue(result["changed"])
        self.assertNotIn("msg", result)

    def test_cors_header_lists_match_in_any_order(self):
        requested = {
            "allowed_headers": ["X-B", "X-A"],
            "allowed_methods": ["POST", "GET"],
            "allowed_origins": ["https://b.example.com", "https://a.example.com"],
            "allow_all_origins": True,
        }
        cloudflare = {field: sorted(value) if isinstance(value, list) else value for field, value in requested.items()}
        current = stored(cors_headers=cloudflare)
        client, api = client_with([current])
        result = self.run_module(FakeModule(params(cors_headers=requested)), client)

        api.update.assert_not_called()
        self.assertFalse(result["changed"])
        self.assertEqual(result["access_app"]["cors_headers"], current["cors_headers"])

        client, api = client_with(created=current)
        result = self.run_module(FakeModule(params(cors_headers=requested)), client)

        self.assertEqual(api.create.call_args.kwargs["cors_headers"], requested)
        self.assertTrue(result["changed"])
        self.assertNotIn("msg", result)

    def test_cors_header_lists_with_duplicates_match_the_deduplicated_stored_lists(self):
        # Cloudflare drops duplicate CORS list values on write.
        requested = {"allowed_methods": ["GET", "GET", "POST"], "allowed_origins": ["https://a.example.com"] * 2}
        cloudflare = {"allowed_methods": ["POST", "GET"], "allowed_origins": ["https://a.example.com"]}
        current = stored(cors_headers=cloudflare)
        client, api = client_with(created=current)

        result = self.run_module(FakeModule(params(cors_headers=requested)), client)

        self.assertEqual(api.create.call_args.kwargs["cors_headers"], requested)
        self.assertTrue(result["changed"])
        self.assertNotIn("msg", result)

        client, api = client_with([current])
        result = self.run_module(FakeModule(params(cors_headers=requested)), client)

        api.update.assert_not_called()
        self.assertFalse(result["changed"])
        self.assertEqual(result["access_app"]["cors_headers"], cloudflare)

    def test_preserved_lists_match_in_any_order_after_an_update(self):
        # Omitted lists are sent from the stored app, and Cloudflare may return them reordered.
        for field, value, reordered in (
            ("cors_headers", {"allowed_methods": ["GET", "POST", "PUT"]}, {"allowed_methods": ["PUT", "GET", "POST"]}),
            ("allowed_idps", ["idp-a", "idp-b"], ["idp-b", "idp-a"]),
        ):
            with self.subTest(field=field):
                current = stored(session_duration="24h", **{field: value})
                updated = {**current, "session_duration": "12h", field: reordered}
                client, api = client_with([current], updated=updated)

                result = self.run_module(FakeModule(params(session_duration="12h")), client)

                self.assertEqual(api.update.call_args.kwargs[field], value)
                self.assertTrue(result["changed"])
                self.assertEqual(result["message"], "Access application updated")

    def test_changed_cors_header_lists_are_a_change(self):
        current = stored(cors_headers={"allowed_methods": ["GET", "POST"]})
        for methods in (["GET"], ["GET", "POST", "PUT"], ["GET", "GET"]):
            with self.subTest(methods=methods):
                client, api = client_with([current], updated=current)
                result = self.run_module(FakeModule(params(cors_headers={"allowed_methods": methods})), client)

                self.assertEqual(api.update.call_args.kwargs["cors_headers"], {"allowed_methods": methods})
                self.assertIn("did not apply", result["msg"])

    def test_changed_allowed_idps_are_a_change(self):
        current = stored(allowed_idps=["idp-a", "idp-b"])
        for requested in (["idp-a"], ["idp-a", "idp-b", "idp-c"], ["idp-a", "idp-a"]):
            with self.subTest(requested=requested):
                client, api = client_with([current], updated=current)
                result = self.run_module(FakeModule(params(allowed_idps=requested)), client)

                self.assertEqual(api.update.call_args.kwargs["allowed_idps"], requested)
                self.assertIn("did not apply", result["msg"])

    def test_duplicate_allowed_idps_are_a_change(self):
        # Unlike the CORS lists, Cloudflare rejects duplicate identity providers instead of dropping them.
        current = stored(allowed_idps=["idp-a"])
        client, api = client_with([current], updated=current)

        result = self.run_module(FakeModule(params(allowed_idps=["idp-a", "idp-a"])), client)

        self.assertEqual(api.update.call_args.kwargs["allowed_idps"], ["idp-a", "idp-a"])
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

    def test_proxy_endpoint_update_keeps_deny_urls_and_custom_pages(self):
        domain = "abc123.proxy.cloudflare-gateway.com"
        kept = {
            "custom_deny_url": "https://deny.example.com",
            "custom_non_identity_deny_url": "https://deny2.example.com",
            "custom_pages": ["page-id"],
        }
        # An application as Cloudflare returns it after creation with deny URLs.
        current = {
            **stored(type="proxy_endpoint", domain=domain, session_duration="24h"),
            "aud": "aud-tag",
            "created_at": "2026-11-14T02:00:00Z",
            "policies": [],
            "tags": [],
            "updated_at": "2026-11-14T02:00:00Z",
            **kept,
        }
        updated = {**current, "session_duration": "8h"}
        client, api = client_with([current], updated=updated)

        result = self.run_module(
            FakeModule(params(type="proxy_endpoint", domain=domain, session_duration="8h")), client
        )

        sent = api.update.call_args.kwargs
        for field, value in kept.items():
            self.assertEqual(sent[field], value)

        self.assertTrue(result["changed"])

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

    def test_empty_string_matches_cleared_settings(self):
        cleared = dict.fromkeys(
            ("custom_deny_message", "custom_deny_url", "logo_url", "same_site_cookie_attribute"), ""
        )
        client, api = client_with([stored()])

        result = self.run_module(FakeModule(params(**cleared)), client)

        api.update.assert_not_called()
        self.assertFalse(result["changed"])

        current = stored(
            custom_deny_message="x",
            custom_deny_url="https://deny.example.com",
            logo_url="https://example.com/logo.png",
            same_site_cookie_attribute="lax",
        )
        client, api = client_with([current], updated=stored())

        result = self.run_module(FakeModule(params(**cleared)), client)

        for field in cleared:
            self.assertEqual(api.update.call_args.kwargs[field], "")

        self.assertEqual(result["message"], "Access application updated")
        self.assertTrue(result["changed"])

    def test_policies_out_of_precedence_order_fail_before_any_request(self):
        policies = [{"id": "a", "precedence": 2}, {"id": "b"}, {"id": "c", "precedence": 1}]
        client, api = client_with()

        result = self.run_module(FakeModule(params(policies=policies)), client)

        self.assertIn("ascending precedence order", result["msg"])
        self.assertEqual(result["expected_order"], [{"id": "c", "precedence": 1}, {"id": "a", "precedence": 2}])
        api.list.assert_not_called()

    def test_inline_policy_sdk_selector_keys_fail_before_any_request(self):
        cases = (
            ("include", "github_organization", "github-organization"),
            ("exclude", "azure_ad", "azureAD"),
            ("require", "github_organization", "github-organization"),
        )
        for field, key, api_key in cases:
            policies = [{"id": "a"}, {"name": "inline", "decision": "allow", field: [{key: {"id": "x"}}]}]
            client, api = client_with()
            with self.subTest(field=field, key=key):
                result = self.run_module(FakeModule(params(policies=policies)), client)

                self.assertEqual(
                    result["msg"], f"policies[1].{field} selector {key!r} must use the Cloudflare API key {api_key!r}"
                )
                api.list.assert_not_called()

    def test_unstored_fields_fail_before_any_request(self):
        cases = (
            ({"cors_headers": {"allowed_methods": ["GET"], "foo": 1}}, ["cors_headers.foo"]),
            ({"destinations": [{"type": "public", "uri": "app.example.com", "foo": 1}]}, ["destinations[0].foo"]),
            ({"destinations": [{"type": "public", "cidr": "192.0.2.1"}]}, ["destinations[0].cidr"]),
            ({"policies": [{"id": "a", "precedence": 1, "foo": 1}]}, ["policies[0].foo"]),
            # Cloudflare accepts a policy account_id but never returns it.
            ({"policies": [{"id": "a", "precedence": 1, "account_id": "account"}]}, ["policies[0].account_id"]),
            (
                {
                    "policies": [
                        {"name": "inline", "decision": "allow", "include": [{"everyone": {}}], "account_id": "account"}
                    ]
                },
                ["policies[0].account_id"],
            ),
            (
                {"policies": [{"name": "inline", "decision": "allow", "include": [{"everyone": {}}], "foo": 1}]},
                ["policies[0].foo"],
            ),
            (
                {
                    "policies": [
                        {
                            "name": "inline",
                            "decision": "allow",
                            "include": [{"everyone": {}}],
                            "approval_groups": [{"approvals_needed": 1, "email_addresses": ["a@example.com"], "x": 1}],
                        }
                    ]
                },
                ["policies[0].approval_groups[0].x"],
            ),
        )
        for updates, unsupported in cases:
            for check_mode in (True, False):
                with self.subTest(updates=updates, check_mode=check_mode):
                    client, api = client_with()

                    result = self.run_module(FakeModule(params(**updates), check_mode=check_mode), client)

                    self.assertEqual(result["unsupported_fields"], unsupported)
                    self.assertEqual(
                        result["msg"],
                        f"Cloudflare does not store these Access application fields: {', '.join(unsupported)}",
                    )
                    api.list.assert_not_called()
                    api.create.assert_not_called()

    def test_other_destination_types_reach_cloudflare(self):
        # Cloudflare rejects an unknown type on the first write; worker fields are unverified.
        for destination in (
            {"type": "unknown", "uri": "app.example.com", "foo": 1},
            {"type": "worker", "worker_id": "w", "foo": 1},
        ):
            with self.subTest(destination=destination):
                client, api = client_with()

                self.run_module(FakeModule(params(destinations=[destination])), client)

                api.create.assert_called_once()

    def test_non_list_inline_policy_selectors_reach_cloudflare(self):
        # Cloudflare rejects these on the first write; the module must not raise TypeError.
        policies = [{"name": "inline", "decision": "allow", "include": 5, "exclude": "x"}]
        client, api = client_with()

        self.run_module(FakeModule(params(policies=policies)), client)

        api.create.assert_called_once()

    def test_unstored_nested_fields_fail_before_any_request(self):
        inline = {"name": "inline", "decision": "allow", "include": [{"everyone": {}}]}
        override = {"behavior": "public", "path_pattern": "/a"}
        cases = (
            (
                {
                    "destinations": [
                        {"type": "public", "uri": "app.example.com", "overrides": [override, {**override, "foo": 1}]}
                    ]
                },
                ["destinations[0].overrides[1].foo"],
            ),
            (
                {
                    "policies": [
                        {
                            **inline,
                            "connection_rules": {"rdp": {"allowed_clipboard_local_to_remote_formats": [], "foo": 1}},
                        }
                    ]
                },
                ["policies[0].connection_rules.rdp.foo"],
            ),
            ({"policies": [{**inline, "connection_rules": {"foo": {}}}]}, ["policies[0].connection_rules.foo"]),
        )
        for updates, unsupported in cases:
            for check_mode in (True, False):
                with self.subTest(updates=updates, check_mode=check_mode):
                    client, api = client_with()

                    result = self.run_module(FakeModule(params(**updates), check_mode=check_mode), client)

                    self.assertEqual(result["unsupported_fields"], unsupported)
                    api.list.assert_not_called()
                    api.create.assert_not_called()

    def test_destination_without_type_fails_before_any_request(self):
        destinations = [{"type": "public", "uri": "app.example.com"}, {"uri": "app.example.com/a"}, {"type": None}]
        for check_mode in (True, False):
            with self.subTest(check_mode=check_mode):
                client, api = client_with()

                result = self.run_module(FakeModule(params(destinations=destinations), check_mode=check_mode), client)

                self.assertEqual(
                    result["msg"],
                    "destinations[1], destinations[2] must set type; Cloudflare stores a destination without one as "
                    "type public",
                )
                api.list.assert_not_called()
                api.create.assert_not_called()

    def test_inline_policy_selector_with_several_rules_fails_before_any_request(self):
        include = [{"email": {"email": "a@example.com"}, "everyone": {}}]
        policies = [{"name": "inline", "decision": "allow", "include": include}]
        for check_mode in (True, False):
            with self.subTest(check_mode=check_mode):
                client, api = client_with()

                result = self.run_module(FakeModule(params(policies=policies), check_mode=check_mode), client)

                self.assertEqual(
                    result["msg"],
                    "policies[0].include[0] sets the selectors 'email', 'everyone', which Cloudflare splits into "
                    "separate include entries; list each selector as its own entry",
                )
                api.list.assert_not_called()
                api.create.assert_not_called()

    def test_inline_policy_null_selector_fails_before_any_request(self):
        policies = [{"name": "inline", "decision": "allow", "include": [{"any_valid_service_token": None}]}]
        for check_mode in (True, False):
            with self.subTest(check_mode=check_mode):
                client, api = client_with()

                result = self.run_module(FakeModule(params(policies=policies), check_mode=check_mode), client)

                self.assertEqual(
                    result["msg"],
                    "policies[0].include[0].any_valid_service_token must be a mapping; use {} for a selector without "
                    "fields, as "
                    "Cloudflare stores a null selector as {}",
                )
                api.list.assert_not_called()
                api.create.assert_not_called()

    def test_null_inline_policy_selector_list_counts_as_omitted(self):
        include = [{"email": {"email": "admin@example.com"}}]
        requested = {"name": "inline", "decision": "allow", "include": include, "exclude": None}
        sent = {"name": "inline", "decision": "allow", "include": include}
        stored_policy = {"id": "a", "precedence": 1, **sent, "exclude": [], "require": []}
        app = stored(policies=[stored_policy])
        client, api = client_with(created=app)

        result = self.run_module(FakeModule(params(policies=[requested])), client)

        self.assertNotIn("msg", result)
        self.assertTrue(result["changed"])
        self.assertEqual(api.create.call_args.kwargs["policies"], [sent])

        client, api = client_with([app])
        result = self.run_module(FakeModule(params(policies=[requested])), client)

        api.update.assert_not_called()
        self.assertFalse(result["changed"])

    def test_null_cors_header_and_inline_policy_fields_count_as_omitted(self):
        cors = {"allowed_methods": ["GET"], "allowed_origins": ["https://a.example.com"]}
        null_cors = dict.fromkeys(
            ("allow_all_headers", "allow_all_methods", "allow_all_origins", "allow_credentials", "max_age")
        )
        include = [{"everyone": {}}]
        policy = {"name": "inline", "decision": "allow", "include": include}
        null_policy = dict.fromkeys(("approval_required", "isolation_required", "purpose_justification_required"))
        requested = {"cors_headers": {**cors, **null_cors}, "policies": [{**policy, **null_policy}]}
        stored_policy = {"id": "a", "precedence": 1, **policy, "exclude": [], "require": []}
        app = stored(cors_headers=cors, policies=[stored_policy])
        client, api = client_with(created=app)

        result = self.run_module(FakeModule(params(**requested)), client)

        self.assertNotIn("msg", result)
        self.assertTrue(result["changed"])
        self.assertEqual(api.create.call_args.kwargs["cors_headers"], cors)
        self.assertEqual(api.create.call_args.kwargs["policies"], [policy])

        client, api = client_with([app])
        result = self.run_module(FakeModule(params(**requested)), client)

        self.assertNotIn("msg", result)
        api.update.assert_not_called()
        self.assertFalse(result["changed"])

    def test_null_unknown_nested_fields_are_ignored(self):
        requested = {
            "cors_headers": {"allow_all_origins": True, "foo": None},
            "destinations": [{"type": "public", "uri": "app.example.com", "foo": None}],
            "policies": [{"id": "policy-id", "precedence": 1, "account_id": None}],
        }
        client, api = client_with()

        result = self.run_module(FakeModule(params(**requested), check_mode=True), client)

        self.assertNotIn("msg", result)
        self.assertTrue(result["changed"])
        api.create.assert_not_called()

    def test_nested_null_inline_policy_fields_count_as_omitted(self):
        rdp = {"allowed_clipboard_local_to_remote_formats": ["text"]}
        policy = {
            "name": "inline",
            "decision": "allow",
            "include": [{"everyone": {}}],
            "connection_rules": {"rdp": rdp},
            "mfa_config": {"mfa_disabled": True},
        }
        requested = {
            **policy,
            "connection_rules": {"rdp": {**rdp, "allowed_clipboard_remote_to_local_formats": None}},
            "mfa_config": {"mfa_disabled": True, "allowed_authenticators": None, "session_duration": None},
        }
        stored_policy = {"id": "a", "precedence": 1, **policy, "exclude": [], "require": []}
        app = stored(policies=[stored_policy])
        client, api = client_with(created=app)

        result = self.run_module(FakeModule(params(policies=[requested])), client)

        self.assertNotIn("msg", result)
        self.assertTrue(result["changed"])
        self.assertEqual(api.create.call_args.kwargs["policies"], [policy])

        client, api = client_with([app])
        result = self.run_module(FakeModule(params(policies=[requested])), client)

        self.assertNotIn("msg", result)
        api.update.assert_not_called()
        self.assertFalse(result["changed"])

    def test_non_mapping_inline_policy_selector_fails_before_any_request(self):
        for selector in (None, "everyone", ["everyone"]):
            for check_mode in (True, False):
                with self.subTest(selector=selector, check_mode=check_mode):
                    policies = [{"name": "inline", "decision": "allow", "include": [selector]}]
                    client, api = client_with()

                    result = self.run_module(FakeModule(params(policies=policies), check_mode=check_mode), client)

                    self.assertEqual(
                        result["msg"],
                        "policies[0].include[0] must be a mapping that sets one selector, such as {'everyone': {}}",
                    )
                    api.list.assert_not_called()
                    api.create.assert_not_called()

    def test_inline_policy_empty_selector_fails_before_any_request(self):
        policies = [{"name": "inline", "decision": "allow", "include": [{"everyone": {}}], "exclude": [{}]}]
        for check_mode in (True, False):
            with self.subTest(check_mode=check_mode):
                client, api = client_with()

                result = self.run_module(FakeModule(params(policies=policies), check_mode=check_mode), client)

                self.assertEqual(
                    result["msg"], "policies[0].exclude[0] must set one selector; Cloudflare drops an empty selector"
                )
                api.list.assert_not_called()
                api.create.assert_not_called()

    def test_inline_policy_empty_selector_value_fails_before_any_request(self):
        include = [{"device_posture": {"integration_uid": "posture", "account_id": ""}}]
        policies = [{"name": "inline", "decision": "allow", "include": include}]
        for check_mode in (True, False):
            with self.subTest(check_mode=check_mode):
                client, api = client_with()

                result = self.run_module(FakeModule(params(policies=policies), check_mode=check_mode), client)

                self.assertEqual(result["empty_fields"], ["policies[0].include[0].device_posture.account_id"])
                self.assertIn("Cloudflare does not store an empty value", result["msg"])
                api.list.assert_not_called()
                api.create.assert_not_called()

    def test_empty_destination_overrides_fail_before_any_request(self):
        destinations = [
            {"type": "public", "uri": "app.example.com", "overrides": []},
            {"type": "public", "uri": "app.example.com/a"},
            {"type": "public", "uri": "app.example.com/b", "overrides": []},
        ]
        for check_mode in (True, False):
            with self.subTest(check_mode=check_mode):
                client, api = client_with()

                result = self.run_module(FakeModule(params(destinations=destinations), check_mode=check_mode), client)

                self.assertEqual(
                    result["msg"],
                    "destinations[0].overrides, destinations[2].overrides must be omitted instead of an empty list; "
                    "Cloudflare stores a destination with empty overrides without them",
                )
                api.list.assert_not_called()
                api.create.assert_not_called()

    def test_empty_values_fail_before_any_request(self):
        inline = {"name": "inline", "decision": "allow", "include": [{"everyone": {}}]}
        cases = (
            ({"cors_headers": {"allowed_origins": [], "allowed_methods": ["GET"]}}, ["cors_headers.allowed_origins"]),
            (
                {"cors_headers": {"allowed_headers": [], "allowed_methods": [], "allow_all_origins": True}},
                ["cors_headers.allowed_headers", "cors_headers.allowed_methods"],
            ),
            ({"destinations": []}, ["destinations"]),
            ({"session_duration": ""}, ["session_duration"]),
            (
                {
                    "policies": [
                        {**inline, "approval_groups": [{"approvals_needed": 1, "email_list_uuid": ""}]},
                    ]
                },
                ["policies[0].approval_groups[0].email_list_uuid"],
            ),
            ({"policies": [{**inline, "approval_groups": []}]}, ["policies[0].approval_groups"]),
            (
                {
                    "policies": [
                        {
                            **inline,
                            "approval_groups": [
                                {"approvals_needed": 1, "email_list_uuid": "list"},
                                {"approvals_needed": 1, "email_addresses": []},
                            ],
                        }
                    ]
                },
                ["policies[0].approval_groups[1].email_addresses"],
            ),
            (
                {"policies": [inline, {**inline, "purpose_justification_prompt": "", "session_duration": ""}]},
                ["policies[1].purpose_justification_prompt", "policies[1].session_duration"],
            ),
            (
                {
                    "destinations": [
                        {"type": "public", "uri": "app.example.com"},
                        {"type": "private", "hostname": "", "port_range": "", "vnet_id": ""},
                    ]
                },
                ["destinations[1].hostname", "destinations[1].port_range", "destinations[1].vnet_id"],
            ),
            (
                {"destinations": [{"type": "private", "cidr": "10.0.0.0/8", "vnet_id": ""}]},
                ["destinations[0].vnet_id"],
            ),
            (
                {
                    "policies": [
                        {
                            **inline,
                            "connection_rules": {
                                "rdp": {
                                    "allowed_clipboard_local_to_remote_formats": [],
                                    "allowed_clipboard_remote_to_local_formats": [],
                                }
                            },
                        }
                    ]
                },
                [
                    "policies[0].connection_rules.rdp.allowed_clipboard_local_to_remote_formats",
                    "policies[0].connection_rules.rdp.allowed_clipboard_remote_to_local_formats",
                ],
            ),
            (
                {
                    "policies": [
                        {
                            **inline,
                            "connection_rules": {
                                "rdp": {
                                    "allowed_clipboard_local_to_remote_formats": ["text"],
                                    "allowed_clipboard_remote_to_local_formats": [],
                                }
                            },
                        }
                    ]
                },
                ["policies[0].connection_rules.rdp.allowed_clipboard_remote_to_local_formats"],
            ),
        )
        for updates, empty in cases:
            for check_mode in (True, False):
                with self.subTest(updates=updates, check_mode=check_mode):
                    client, api = client_with()

                    result = self.run_module(FakeModule(params(**updates), check_mode=check_mode), client)

                    self.assertEqual(result["empty_fields"], empty)
                    self.assertEqual(
                        result["msg"],
                        "Cloudflare does not store an empty value for these Access application fields: "
                        f"{', '.join(empty)}; omit them instead",
                    )
                    api.list.assert_not_called()
                    api.create.assert_not_called()

    def test_inline_policy_unstored_selector_fields_fail_before_any_request(self):
        policies = [{"name": "inline", "decision": "allow", "include": [{"email": {"email": "a@example.com", "x": 1}}]}]
        client, api = client_with()

        result = self.run_module(FakeModule(params(policies=policies)), client)

        self.assertEqual(result["unsupported_fields"], ["policies[0].include[0].email.x"])
        api.list.assert_not_called()

    def test_stored_fields_are_sent(self):
        cors = dict.fromkeys(access_apps.CORS_HEADERS_FIELDS, True)
        destinations = [
            {"type": "public", "uri": "app.example.com", "overrides": [{"behavior": "public", "path_pattern": "/a"}]},
            {"type": "private", "cidr": "192.0.2.0/24", "l4_protocol": "tcp", "port_range": "22", "vnet_id": "v"},
            {"type": "public", "uri": "app.example.com/b"},
        ]
        rdp = {field: ["text"] for field in access_apps.POLICY_CONNECTION_RULES_FIELDS["rdp"]}
        policies = [
            {"id": "a", "precedence": 1},
            {
                "name": "inline",
                "decision": "allow",
                "include": [{"email": {"email": "a@example.com"}}],
                "approval_groups": [{"approvals_needed": 1, "email_list_uuid": "list"}],
                "connection_rules": {"rdp": rdp},
                "mfa_config": {"allowed_authenticators": ["totp"], "mfa_disabled": False, "session_duration": "24h"},
                "precedence": 2,
            },
        ]
        updates = {"cors_headers": cors, "destinations": destinations, "policies": policies}
        client, api = client_with(created=stored(**updates))

        result = self.run_module(FakeModule(params(**updates)), client)

        self.assertNotIn("msg", result)
        self.assertEqual(api.create.call_args.kwargs["cors_headers"], cors)
        self.assertEqual(api.create.call_args.kwargs["destinations"], destinations)
        self.assertEqual(api.create.call_args.kwargs["policies"], policies)

    def test_inline_policy_api_selector_keys_are_accepted(self):
        include = [{"github-organization": {"identity_provider_id": "idp", "name": "org"}}]
        policies = [{"name": "inline", "decision": "allow", "include": include}]
        client, api = client_with([stored(policies=policies)])

        result = self.run_module(FakeModule(params(policies=policies)), client)

        api.update.assert_not_called()
        self.assertFalse(result["changed"])

    def test_removed_inline_policy_selectors_are_a_change(self):
        github = {"identity_provider_id": "idp", "name": "org"}
        inline = {"name": "inline", "decision": "allow", "include": [{"github-organization": github}]}
        stored_policy = {
            **inline,
            "id": "policy-id",
            "precedence": 1,
            "include": [{"github-organization": {**github, "team": "admins"}}],
            "exclude": [],
            "require": [{"email_domain": {"domain": "example.com"}}],
        }
        current = stored(policies=[stored_policy])
        client, api = client_with([current], updated=stored(policies=[{**stored_policy, **inline, "require": []}]))

        result = self.run_module(FakeModule(params(policies=[inline])), client)

        self.assertEqual(api.update.call_args.kwargs["policies"], [inline])
        self.assertTrue(result["changed"])

        client, api = client_with([current], updated=current)
        result = self.run_module(FakeModule(params(policies=[inline])), client)

        self.assertIn("did not apply", result["msg"])

    def test_removed_inline_policy_approval_group_and_connection_rule_keys_are_a_change(self):
        group = {"email_addresses": ["a@example.com", "b@example.com"]}
        rdp = {"allowed_clipboard_local_to_remote_formats": ["text"]}
        inline = {
            "name": "inline",
            "decision": "allow",
            "include": [{"everyone": {}}],
            "approval_groups": [group],
            "connection_rules": {"rdp": rdp},
        }
        stored_policy = {"id": "policy-id", "precedence": 1, **inline, "exclude": [], "require": []}
        cases = (
            ("approval_groups", [{**group, "approvals_needed": 2}]),
            ("connection_rules", {"rdp": {**rdp, "allowed_clipboard_remote_to_local_formats": ["text"]}}),
            ("connection_rules", {"rdp": rdp, "extra": {}}),
        )
        for field, value in cases:
            with self.subTest(field=field, value=value):
                current = stored(policies=[{**stored_policy, field: value}])
                client, api = client_with([current], updated=stored(policies=[stored_policy]))

                result = self.run_module(FakeModule(params(policies=[inline])), client)

                self.assertNotIn("msg", result)
                self.assertEqual(api.update.call_args.kwargs["policies"], [inline])
                self.assertTrue(result["changed"])

        client, api = client_with([stored(policies=[stored_policy])])
        result = self.run_module(FakeModule(params(policies=[inline])), client)

        self.assertNotIn("msg", result)
        api.update.assert_not_called()
        self.assertFalse(result["changed"])

    def test_removed_inline_policy_settings_are_a_change(self):
        # Cloudflare replaces the inline policy on update, so omitted settings are cleared.
        inline = {"name": "inline", "decision": "allow", "include": [{"everyone": {}}]}
        stored_policy = {"id": "policy-id", "precedence": 1, **inline, "exclude": [], "require": []}
        mfa = {"allowed_authenticators": ["totp"], "session_duration": "24h"}
        cases = (
            ({}, {"approval_required": True}),
            ({}, {"isolation_required": True}),
            ({}, {"purpose_justification_required": True}),
            ({}, {"purpose_justification_prompt": "why"}),
            ({}, {"session_duration": "8h"}),
            ({}, {"approval_groups": [{"email_addresses": ["a@example.com"], "approvals_needed": 1}]}),
            ({}, {"connection_rules": {"rdp": {"allowed_clipboard_local_to_remote_formats": ["text"]}}}),
            ({}, {"mfa_config": mfa}),
            ({"mfa_config": {"allowed_authenticators": ["totp"]}}, {"mfa_config": mfa}),
        )
        for requested, extra in cases:
            with self.subTest(requested=requested, stored=extra):
                desired = {**inline, **requested}
                current = stored(policies=[{**stored_policy, **extra}])
                client, api = client_with([current], updated=stored(policies=[{**stored_policy, **requested}]))

                result = self.run_module(FakeModule(params(policies=[desired]), check_mode=True), client)

                self.assertNotIn("msg", result)
                self.assertTrue(result["changed"])
                api.update.assert_not_called()

                result = self.run_module(FakeModule(params(policies=[desired])), client)

                self.assertNotIn("msg", result)
                self.assertTrue(result["changed"])
                self.assertEqual(api.update.call_args.kwargs["policies"], [desired])

        settings = {
            "approval_required": True,
            "purpose_justification_required": True,
            "purpose_justification_prompt": "why",
            "session_duration": "8h",
            "mfa_config": mfa,
        }
        client, api = client_with([stored(policies=[{**stored_policy, **settings}])])

        result = self.run_module(FakeModule(params(policies=[{**inline, **settings}])), client)

        self.assertNotIn("msg", result)
        api.update.assert_not_called()
        self.assertFalse(result["changed"])

    def test_inline_policy_matches_assigned_github_organization_id(self):
        github = {"identity_provider_id": "idp", "name": "org"}
        inline = {"name": "inline", "decision": "allow", "include": [{"github-organization": github}]}
        stored_policy = {**inline, "id": "a", "include": [{"github-organization": {**github, "id": "314135"}}]}
        client, api = client_with([stored(policies=[stored_policy])])

        result = self.run_module(FakeModule(params(policies=[inline])), client)

        api.update.assert_not_called()
        self.assertFalse(result["changed"])

    def test_inline_policy_null_github_organization_id_matches_assigned_id(self):
        github = {"identity_provider_id": "idp", "name": "org"}
        inline = {"name": "inline", "decision": "allow", "include": [{"github-organization": {**github, "id": None}}]}
        stored_policy = {**inline, "id": "a", "include": [{"github-organization": {**github, "id": "314135"}}]}
        client, api = client_with([stored(policies=[stored_policy])])

        result = self.run_module(FakeModule(params(policies=[inline])), client)

        api.update.assert_not_called()
        self.assertFalse(result["changed"])

    def test_default_cors_header_values_match_omitted_keys(self):
        defaults = {
            "allow_all_headers": False,
            "allow_all_methods": False,
            "allow_all_origins": False,
            "allow_credentials": False,
            "max_age": 0,
        }
        for cors, cloudflare in (
            ({**defaults, "allowed_methods": ["GET"]}, {"allowed_methods": ["GET"]}),
            ({"allow_credentials": False}, None),
            ({"allow_credentials": False}, {}),
        ):
            with self.subTest(cors=cors, cloudflare=cloudflare):
                created = stored(cors_headers=cloudflare)
                client, api = client_with(created=created)

                result = self.run_module(FakeModule(params(cors_headers=cors)), client)

                self.assertEqual(api.create.call_args.kwargs["cors_headers"], cors)
                self.assertEqual(result["message"], "Access application created")

                client, api = client_with([created])

                result = self.run_module(FakeModule(params(cors_headers=cors)), client)

                api.update.assert_not_called()
                self.assertFalse(result["changed"])

    def test_non_default_cors_header_value_omitted_by_cloudflare_is_not_applied(self):
        cors = {"allowed_methods": ["GET"], "allow_credentials": True, "max_age": 0}
        client, api = client_with([stored(cors_headers={"allowed_methods": ["GET"]})])

        result = self.run_module(FakeModule(params(cors_headers=cors), check_mode=True), client)

        api.update.assert_not_called()
        self.assertTrue(result["changed"])

        client, api = client_with(created=stored(cors_headers={"allowed_methods": ["GET"]}))

        result = self.run_module(FakeModule(params(cors_headers=cors)), client)

        api.create.assert_called_once()

        self.assertEqual(
            result["differences"],
            [
                {
                    "field": "cors_headers",
                    "requested": cors,
                    "stored": {"allow_credentials": False, "max_age": 0, "allowed_methods": ["GET"]},
                }
            ],
        )

    def test_inline_policy_false_flags_match_omitted_fields(self):
        flags = dict.fromkeys(("approval_required", "isolation_required", "purpose_justification_required"), False)
        inline = {"name": "inline", "decision": "allow", "include": [{"everyone": {}}], **flags}
        stored_policy = {
            "id": "a",
            "precedence": 1,
            "name": "inline",
            "decision": "allow",
            "include": [{"everyone": {}}],
        }
        created = stored(policies=[stored_policy])
        client, api = client_with(created=created)

        result = self.run_module(FakeModule(params(policies=[inline])), client)

        self.assertEqual(api.create.call_args.kwargs["policies"], [inline])
        self.assertEqual(result["message"], "Access application created")

        client, api = client_with([created])

        result = self.run_module(FakeModule(params(policies=[inline])), client)

        api.update.assert_not_called()
        self.assertFalse(result["changed"])

        client, api = client_with([created])

        result = self.run_module(
            FakeModule(params(policies=[{**inline, "approval_required": True}]), check_mode=True), client
        )

        self.assertTrue(result["changed"])

    def test_unchanged_inline_policy_matches_empty_stored_selector_lists(self):
        include = [{"github-organization": {"identity_provider_id": "idp", "name": "org"}}]
        policies = [
            {"name": "inline", "decision": "allow", "include": include},
            {"name": "explicit", "decision": "allow", "include": include, "exclude": [], "require": []},
        ]
        stored_policies = [
            {"id": "a", "precedence": 1, "name": "inline", "decision": "allow", "include": include, "exclude": []},
            {"id": "b", "precedence": 2, "name": "explicit", "decision": "allow", "include": include},
        ]
        client, api = client_with([stored(policies=stored_policies)])

        result = self.run_module(FakeModule(params(policies=policies)), client)

        api.update.assert_not_called()
        self.assertFalse(result["changed"])

    def test_reusable_policy_link_ignores_stored_selectors(self):
        stored_policy = {
            "id": "a",
            "precedence": 1,
            "name": "reusable",
            "include": [{"everyone": {}}],
            "require": [{"email_domain": {"domain": "example.com"}}],
        }
        client, api = client_with([stored(policies=[stored_policy])])

        result = self.run_module(FakeModule(params(policies=[{"id": "a", "precedence": 1}])), client)

        api.update.assert_not_called()
        self.assertFalse(result["changed"])

    def test_policies_in_precedence_order_match_stored_order(self):
        policies = [{"id": "b", "precedence": 1}, {"id": "a", "precedence": 2}]
        client, api = client_with([stored(policies=policies)])

        result = self.run_module(FakeModule(params(policies=policies)), client)

        api.update.assert_not_called()
        self.assertFalse(result["changed"])

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

    def test_type_accepts_empty_strings_for_unsupported_options(self):
        cases = (
            ("bookmark", ("custom_deny_message", "custom_deny_url", "same_site_cookie_attribute")),
            ("proxy_endpoint", ("custom_deny_message", "logo_url", "same_site_cookie_attribute")),
        )
        for app_type, fields in cases:
            for field in fields:
                with self.subTest(type=app_type, field=field):
                    client, api = client_with([stored(type=app_type)])

                    result = self.run_module(FakeModule(params(type=app_type, **{field: ""})), client)

                    api.update.assert_not_called()
                    self.assertFalse(result["changed"])

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

    def test_omitted_policies_are_kept_as_links(self):
        # Sending an inline policy whole replaces it, and Cloudflare assigns it a
        # new updated_at, so the update would fail as not applied.
        policies = [
            {
                "id": "reusable",
                "precedence": 1,
                "name": "shared",
                "decision": "allow",
                "reusable": True,
                "include": [{"everyone": {}}],
                "updated_at": "2026-01-01T00:00:00Z",
            },
            {
                "id": "inline",
                "precedence": 2,
                "name": "admins",
                "decision": "allow",
                "include": [{"email": {"email": "admin@example.com"}}],
                "updated_at": "2026-01-01T00:00:00Z",
            },
        ]
        rewritten = [policies[0], {**policies[1], "updated_at": "2026-02-02T00:00:00Z"}]
        current = {**stored(), "policies": policies}
        updated = {**stored(session_duration="12h"), "policies": rewritten}
        client, api = client_with([current], updated=updated)

        result = self.run_module(FakeModule(params(session_duration="12h")), client)

        self.assertNotIn("msg", result)
        self.assertEqual(result["message"], "Access application updated")
        self.assertEqual(
            api.update.call_args.kwargs["policies"],
            [{"id": "reusable", "precedence": 1}, {"id": "inline", "precedence": 2}],
        )

        client, api = client_with([updated])
        result = self.run_module(FakeModule(params(session_duration="12h")), client)

        self.assertFalse(result["changed"])
        api.update.assert_not_called()

    def test_create_recovers_the_app_after_a_lost_response(self):
        client, api = client_with()
        api.create.side_effect = timeout_error()
        api.list.side_effect = [[], [stored()]]

        result = self.run_module(FakeModule(params()), client)

        client.with_options.assert_called_once_with(max_retries=0)
        api.create.assert_called_once()
        self.assertEqual(api.list.call_count, 2)
        self.assertEqual(api.list.call_args.kwargs, {"account_id": "account", "name": "app", "exact": True})
        self.assertEqual(result["message"], "Access application created")
        self.assertEqual(result["access_app"], stored())

    def test_created_app_with_another_name_reports_the_write(self):
        created = stored()
        client, api = client_with(created=created)

        result = self.run_module(FakeModule(params(name=" app")), client)

        api.create.assert_called_once()
        self.assertEqual(result["msg"], "Cloudflare API returned the wrong Access application")
        self.assertTrue(result["changed"])
        self.assertEqual(result["access_app"], created)
        self.assertEqual(result["resource_id"], "app-id")
        self.assertEqual(result["account_id"], "account")

    def test_nested_nulls_are_not_sent(self):
        destination = {
            "type": "public",
            "uri": "app.example.com",
            "overrides": [{"path_pattern": "/a", "behavior": None}],
        }
        policy = {
            "name": "inline",
            "decision": "allow",
            "include": [{"email": {"email": "a@example.com", "extra": None}}],
            "approval_groups": [{"approvals_needed": 1, "email_addresses": ["a@example.com"], "email_list_uuid": None}],
        }
        expected_destination = {"type": "public", "uri": "app.example.com", "overrides": [{"path_pattern": "/a"}]}
        expected_policy = {
            "name": "inline",
            "decision": "allow",
            "include": [{"email": {"email": "a@example.com"}}],
            "approval_groups": [{"approvals_needed": 1, "email_addresses": ["a@example.com"]}],
        }
        created = stored(destinations=[expected_destination], policies=[expected_policy])
        client, api = client_with(created=created)

        result = self.run_module(FakeModule(params(destinations=[destination], policies=[policy])), client)

        self.assertEqual(result["message"], "Access application created")
        self.assertEqual(api.create.call_args.kwargs["destinations"], [expected_destination])
        self.assertEqual(api.create.call_args.kwargs["policies"], [expected_policy])
