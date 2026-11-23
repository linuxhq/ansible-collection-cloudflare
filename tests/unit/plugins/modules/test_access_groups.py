# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from unittest import TestCase
from unittest.mock import Mock, patch

from ansible_collections.linuxhq.cloudflare.plugins.modules import access_groups
from ansible_collections.linuxhq.cloudflare.tests.unit.plugins.modules.utils import (
    FALSY_PAGE_RESULTS,
    FakeModule,
    ModuleExit,
    ModuleFail,
    list_response,
    sdk_client,
    timeout_error,
)

INCLUDE = [{"email": {"email": "admin@example.com"}}]


def params(**updates):
    values = {
        "account_id": "account",
        "name": "admins",
        "include": INCLUDE,
        "exclude": None,
        "require": None,
        "is_default": None,
        "state": "present",
    }
    values.update(updates)
    return values


def client_with(groups=(), created=None, updated=None, deleted=None):
    client = Mock()
    # Retry overrides return the same client so their calls are observable.
    client.with_options.return_value = client
    api = client.zero_trust.access.groups
    api.list.return_value = list(groups)
    api.create.return_value = created
    api.update.return_value = updated
    api.delete.return_value = deleted
    return client, api


class AccessGroupsTests(TestCase):
    def run_module(self, module, client):
        with self.assertRaises((ModuleExit, ModuleFail)) as raised:
            access_groups.run(module, client)

        return raised.exception.values

    def test_lookup_failures_name_the_account(self):
        for found in ([{"name": "admins"}], [{"id": "one", "name": "admins"}, {"id": "two", "name": "admins"}]):
            client, api = client_with(found)
            with self.subTest(found=found):
                result = self.run_module(FakeModule(params()), client)

                api.create.assert_not_called()
                self.assertEqual(result["account_id"], "account")
                self.assertEqual(result["name"], "admins")

    def test_create_recovers_the_group_after_a_lost_response(self):
        recovered = {"id": "group", "name": "admins", "include": INCLUDE}
        client, api = client_with()
        api.create.side_effect = timeout_error()
        api.list.side_effect = [[], [recovered]]

        result = self.run_module(FakeModule(params()), client)

        client.with_options.assert_called_once_with(max_retries=0)
        api.create.assert_called_once()
        self.assertEqual(api.list.call_args.kwargs, {"account_id": "account", "name": "admins"})
        self.assertEqual(result["message"], "Access group created")

    def test_empty_or_whitespace_name_fails_before_any_request(self):
        # Cloudflare stores such a name as null or "", so the resource is never found again.
        for name in ("", "   "):
            with self.subTest(name=name):
                client, api = client_with()

                result = self.run_module(FakeModule(params(name=name)), client)

                self.assertEqual(result["msg"], "name must not be empty or only whitespace")
                api.list.assert_not_called()

    def test_nameless_group_does_not_block_lookup(self):
        # Cloudflare stores a group with an empty name as null.
        group = {"id": "group", "name": "admins", "include": [{"email": {"email": "admin@example.com"}}]}
        client, _ignored = client_with([{"id": "nameless"}, group])

        result = self.run_module(FakeModule(params()), client)

        self.assertNotIn("msg", result)
        self.assertEqual(result["access_group"]["id"], "group")

    def test_looks_up_by_name_server_side(self):
        client, api = client_with()
        self.run_module(FakeModule(params(), check_mode=True), client)

        api.list.assert_called_once_with(account_id="account", name="admins")

    def test_equivalent_group_is_unchanged(self):
        current = {"id": "group", "name": "admins", "include": INCLUDE}
        client, api = client_with([current])

        result = self.run_module(FakeModule(params()), client)

        api.update.assert_not_called()
        self.assertFalse(result["changed"])

    def test_removed_nested_selector_field_is_updated(self):
        include = [{"github-organization": {"identity_provider_id": "idp", "name": "org"}}]
        current = {
            "id": "group",
            "name": "admins",
            "include": [{"github-organization": {"identity_provider_id": "idp", "name": "org", "team": "ops"}}],
        }
        client, api = client_with([current], updated={**current, "include": include})

        result = self.run_module(FakeModule(params(include=include)), client)

        api.update.assert_called_once_with("group", account_id="account", include=include, name="admins")
        self.assertTrue(result["changed"])

    def test_assigned_github_organization_id_matches_request(self):
        include = [{"github-organization": {"identity_provider_id": "idp", "name": "org"}}]
        current = {
            "id": "group",
            "name": "admins",
            "include": [{"github-organization": {"identity_provider_id": "idp", "id": "314135", "name": "org"}}],
        }
        client, api = client_with([current])

        result = self.run_module(FakeModule(params(include=include)), client)

        api.update.assert_not_called()
        self.assertFalse(result["changed"])

        changed = [{"github-organization": {"identity_provider_id": "idp", "id": "1", "name": "org"}}]
        client, api = client_with([current], updated={**current, "include": changed})

        result = self.run_module(FakeModule(params(include=changed)), client)

        self.assertTrue(result["changed"])

    def test_null_github_organization_id_matches_assigned_id(self):
        include = [{"github-organization": {"identity_provider_id": "idp", "name": "org", "id": None}}]
        current = {
            "id": "group",
            "name": "admins",
            "include": [{"github-organization": {"identity_provider_id": "idp", "id": "314135", "name": "org"}}],
        }
        client, api = client_with(created=current)

        result = self.run_module(FakeModule(params(include=include)), client)

        sent = [{"github-organization": {"identity_provider_id": "idp", "name": "org"}}]
        api.create.assert_called_once_with(account_id="account", include=sent, name="admins")
        self.assertTrue(result["changed"])

        client, api = client_with([current])

        result = self.run_module(FakeModule(params(include=include)), client)

        api.update.assert_not_called()
        self.assertFalse(result["changed"])

    def test_rejects_sdk_selector_key_before_any_request(self):
        for key, api_key in (("github_organization", "github-organization"), ("azure_ad", "azureAD")):
            with self.subTest(key=key):
                client, api = client_with()

                result = self.run_module(FakeModule(params(require=[{key: {"identity_provider_id": "idp"}}])), client)

                self.assertEqual(result["msg"], f"require selector {key!r} must use the Cloudflare API key {api_key!r}")
                api.list.assert_not_called()
                api.create.assert_not_called()

    def test_rejects_unstored_selector_fields_before_any_request(self):
        include = [{"email": {"email": "a@example.com", "bogus": "x"}}, {"everyone": {"bogus": 1}}]
        require = [{"github-organization": {"identity_provider_id": "idp", "name": "org", "id": "1", "extra": 1}}]
        unsupported = ["include[0].email.bogus", "include[1].everyone.bogus", "require[0].github-organization.extra"]
        for check_mode in (True, False):
            with self.subTest(check_mode=check_mode):
                client, api = client_with()

                result = self.run_module(
                    FakeModule(params(include=include, require=require), check_mode=check_mode), client
                )

                self.assertEqual(result["unsupported_fields"], unsupported)
                self.assertEqual(
                    result["msg"], f"Cloudflare does not store these Access selector fields: {', '.join(unsupported)}"
                )
                api.list.assert_not_called()
                api.create.assert_not_called()

    def test_rejects_selector_with_several_rules_before_any_request(self):
        include = [{"email": {"email": "a@example.com"}}, {"email": {"email": "b@example.com"}, "everyone": {}}]
        for check_mode in (True, False):
            with self.subTest(check_mode=check_mode):
                client, api = client_with()

                result = self.run_module(FakeModule(params(include=include), check_mode=check_mode), client)

                self.assertEqual(
                    result["msg"],
                    "include[1] sets the selectors 'email', 'everyone', which Cloudflare splits into separate include "
                    "entries; list each selector as its own entry",
                )
                api.list.assert_not_called()
                api.create.assert_not_called()

    def test_rejects_null_selector_before_any_request(self):
        include = [{"email": {"email": "a@example.com"}}, {"any_valid_service_token": None}]
        for check_mode in (True, False):
            with self.subTest(check_mode=check_mode):
                client, api = client_with()

                result = self.run_module(FakeModule(params(include=include), check_mode=check_mode), client)

                self.assertEqual(
                    result["msg"],
                    "include[1].any_valid_service_token must be a mapping; use {} for a selector without fields, as "
                    "Cloudflare stores a null selector as {}",
                )
                api.list.assert_not_called()
                api.create.assert_not_called()

    def test_empty_selector_fails_before_any_request(self):
        for check_mode in (True, False):
            with self.subTest(check_mode=check_mode):
                client, api = client_with()

                result = self.run_module(FakeModule(params(exclude=[{}]), check_mode=check_mode), client)

                self.assertEqual(result["msg"], "exclude[0] must set one selector; Cloudflare drops an empty selector")
                api.list.assert_not_called()
                api.create.assert_not_called()

    def test_empty_selector_value_fails_before_any_request(self):
        include = [
            {"device_posture": {"integration_uid": "posture", "account_id": ""}},
            {"email": {"email": ""}},
            {"saml": {"attribute_name": "group", "attribute_value": "", "identity_provider_id": ""}},
        ]
        empty = ["include[0].device_posture.account_id", "include[2].saml.identity_provider_id"]
        for check_mode in (True, False):
            with self.subTest(check_mode=check_mode):
                client, api = client_with()

                result = self.run_module(FakeModule(params(include=include), check_mode=check_mode), client)

                self.assertEqual(result["empty_fields"], empty)
                self.assertEqual(
                    result["msg"],
                    f"Cloudflare does not store an empty value for these Access selector fields: {', '.join(empty)}; "
                    "omit them instead",
                )
                api.list.assert_not_called()
                api.create.assert_not_called()

    def test_empty_mapping_selector_is_unchanged(self):
        include = [{"any_valid_service_token": {}}]
        client, api = client_with([{"id": "group", "name": "admins", "include": include}])

        result = self.run_module(FakeModule(params(include=include)), client)

        api.update.assert_not_called()
        self.assertFalse(result["changed"])

    def test_stored_selector_fields_are_sent(self):
        include = [{"email": {"email": "a@example.com"}}, {"everyone": {}}, {"ip": {"ip": "192.0.2.0/24"}}]
        created = {"id": "group", "name": "admins", "include": include}
        client, api = client_with(created=created)

        result = self.run_module(FakeModule(params(include=include)), client)

        self.assertNotIn("msg", result)
        api.create.assert_called_once_with(account_id="account", include=include, name="admins")

    def test_creates_group(self):
        created = {"id": "group", "name": "admins", "include": INCLUDE}
        client, api = client_with(created=created)

        result = self.run_module(FakeModule(params()), client)

        api.create.assert_called_once_with(account_id="account", include=INCLUDE, name="admins")
        self.assertEqual(result["access_group"], created)

    def test_rewritten_selector_names_requested_and_stored_values(self):
        include = [{"email": {"email": "admin@example.com"}}]
        stored = [{"email": {"email": "other@example.com"}}]
        client, _ignored = client_with(created={"id": "group", "name": "admins", "include": stored})

        result = self.run_module(FakeModule(params(include=include)), client)

        self.assertEqual(
            result["msg"],
            "Cloudflare did not apply the requested Access group: "
            'include requested [{"email": {"email": "admin@example.com"}}], '
            'stored [{"email": {"email": "other@example.com"}}]',
        )
        self.assertEqual(result["differences"], [{"field": "include", "requested": include, "stored": stored}])

    def test_update_preserves_omitted_selectors(self):
        exclude = [{"email": {"email": "blocked@example.com"}}]
        include = [{"email": {"email": "new@example.com"}}]
        current = {"id": "group", "name": "admins", "include": INCLUDE, "exclude": exclude}
        updated = {**current, "include": include}
        client, api = client_with([current], updated=updated)

        result = self.run_module(FakeModule(params(include=include)), client)

        api.update.assert_called_once_with(
            "group", account_id="account", exclude=exclude, include=include, name="admins"
        )
        self.assertTrue(result["changed"])

    def test_is_default_has_no_module_default(self):
        with (
            patch.object(access_groups, "AnsibleModule", side_effect=RuntimeError) as module,
            self.assertRaises(RuntimeError),
        ):
            access_groups.main()

        self.assertNotIn("default", module.call_args.kwargs["argument_spec"]["is_default"])

    def test_update_preserves_omitted_default_status(self):
        include = [{"email": {"email": "new@example.com"}}]
        current = {"id": "group", "name": "admins", "include": INCLUDE, "is_default": True}
        updated = {**current, "include": include}
        client, api = client_with([current], updated=updated)

        result = self.run_module(FakeModule(params(include=include)), client)

        api.update.assert_called_once_with(
            "group", account_id="account", include=include, is_default=True, name="admins"
        )
        self.assertTrue(result["changed"])

    def test_explicit_is_default_is_compared(self):
        current = {"id": "group", "name": "admins", "include": INCLUDE, "is_default": True}
        client, api = client_with([current], updated={k: v for k, v in current.items() if k != "is_default"})

        result = self.run_module(FakeModule(params(is_default=False)), client)

        api.update.assert_called_once_with(
            "group", account_id="account", include=INCLUDE, is_default=False, name="admins"
        )
        self.assertTrue(result["changed"])

        client, api = client_with([{k: v for k, v in current.items() if k != "is_default"}])
        result = self.run_module(FakeModule(params(is_default=False)), client)

        api.update.assert_not_called()
        self.assertFalse(result["changed"])

    def test_deletes_group(self):
        client, api = client_with([{"id": "group", "name": "admins"}], deleted={"id": "group"})

        result = self.run_module(FakeModule(params(state="absent")), client)

        api.delete.assert_called_once_with("group", account_id="account")
        self.assertTrue(result["changed"])

    def test_padded_name_is_trimmed_before_any_request(self):
        # Cloudflare trims the name, so the trimmed name is looked up and sent.
        group = {"id": "group", "name": "admins", "include": INCLUDE}
        client, api = client_with(created=group)

        result = self.run_module(FakeModule(params(name=" admins ")), client)

        self.assertEqual(api.list.call_args_list[0].kwargs, {"account_id": "account", "name": "admins"})
        self.assertEqual(api.create.call_args.kwargs["name"], "admins")
        self.assertEqual(result["message"], "Access group created")

        client, api = client_with([group])

        result = self.run_module(FakeModule(params(name=" admins ")), client)

        api.create.assert_not_called()
        api.update.assert_not_called()
        self.assertFalse(result["changed"])

    def test_created_group_with_another_name_reports_the_write(self):
        created = {"id": "group", "name": "other", "include": INCLUDE}
        client, api = client_with(created=created)

        result = self.run_module(FakeModule(params()), client)

        api.create.assert_called_once()
        self.assertEqual(result["msg"], "Cloudflare API returned the wrong Access group")
        self.assertTrue(result["changed"])
        self.assertEqual(result["access_group"], created)
        self.assertEqual(result["resource_id"], "group")
        self.assertEqual(result["account_id"], "account")

    def test_update_returning_another_group_reports_the_write(self):
        current = {"id": "group", "name": "admins", "include": [{"everyone": {}}]}
        updated = {"id": "other", "name": "admins", "include": INCLUDE}
        client, api = client_with([current], updated=updated)

        result = self.run_module(FakeModule(params()), client)

        api.update.assert_called_once()
        self.assertEqual(result["msg"], "Cloudflare API returned the wrong Access group")
        self.assertTrue(result["changed"])
        self.assertEqual(result["access_group"], updated)
        self.assertEqual(result["resource_id"], "group")
        self.assertEqual(result["account_id"], "account")

    def test_null_selector_fields_are_not_sent(self):
        # A null key counts as omitted, so Cloudflare never receives it.
        requested = [{"github-organization": {"name": "org", "identity_provider_id": "idp", "team": None}}]
        sent = [{"github-organization": {"name": "org", "identity_provider_id": "idp"}}]
        exclude = [{"email": {"email": "blocked@example.com", "unknown": None}}]
        sent_exclude = [{"email": {"email": "blocked@example.com"}}]
        stored = {"id": "group", "name": "admins", "include": sent, "exclude": sent_exclude}
        for current in (None, {"id": "group", "name": "admins", "include": [{"everyone": {}}]}):
            with self.subTest(current=current):
                client, api = client_with([] if current is None else [current], created=stored, updated=stored)

                result = self.run_module(FakeModule(params(include=requested, exclude=exclude)), client)

                call = api.update if current else api.create
                self.assertEqual(call.call_args.kwargs["include"], sent)
                self.assertEqual(call.call_args.kwargs["exclude"], sent_exclude)
                self.assertTrue(result["changed"])
                self.assertNotIn("msg", result)

    def test_null_selector_field_matches_stored_selector(self):
        stored = [{"github-organization": {"name": "org", "identity_provider_id": "idp"}}]
        requested = [{"github-organization": {"name": "org", "identity_provider_id": "idp", "team": None}}]
        client, api = client_with([{"id": "group", "name": "admins", "include": stored}])

        result = self.run_module(FakeModule(params(include=requested)), client)

        api.update.assert_not_called()
        self.assertFalse(result["changed"])

    def test_ip_selectors_are_sent_and_compared_as_stored(self):
        # Cloudflare stores an ip selector as its canonical network.
        requested = [
            {"ip": {"ip": "192.0.2.1"}},
            {"ip": {"ip": "2001:db8::1"}},
            {"ip": {"ip": "2001:DB8:0:0::1/128"}},
            {"ip": {"ip": "198.51.100.7/24"}},
            {"ip": {"ip": "not an ip"}},
        ]
        stored = [
            {"ip": {"ip": "192.0.2.1/32"}},
            {"ip": {"ip": "2001:db8::1/128"}},
            {"ip": {"ip": "2001:db8::1/128"}},
            {"ip": {"ip": "198.51.100.0/24"}},
            {"ip": {"ip": "not an ip"}},
        ]
        client, api = client_with(created={"id": "group", "name": "admins", "include": stored})

        result = self.run_module(FakeModule(params(include=requested)), client)

        api.create.assert_called_once_with(account_id="account", include=stored, name="admins")
        self.assertTrue(result["changed"])
        self.assertNotIn("msg", result)

        client, api = client_with([{"id": "group", "name": "admins", "include": stored}])

        result = self.run_module(FakeModule(params(include=requested)), client)

        api.update.assert_not_called()
        self.assertFalse(result["changed"])


class MalformedListTests(TestCase):
    def test_falsy_page_result_fails_without_a_create(self):
        for result in FALSY_PAGE_RESULTS:
            requests = []
            with self.subTest(result=result), sdk_client(list_response(result, requests)) as client:
                with self.assertRaises(ModuleFail) as raised:
                    access_groups.run(FakeModule(params()), client)

                self.assertEqual(raised.exception.values["msg"], "Cloudflare API returned malformed Access group data")
                self.assertEqual([request.method for request in requests], ["GET"])
