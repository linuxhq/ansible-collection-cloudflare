# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from unittest import TestCase
from unittest.mock import Mock, patch

from ansible_collections.linuxhq.cloudflare.plugins.modules import access_groups
from ansible_collections.linuxhq.cloudflare.tests.unit.plugins.modules.utils import (
    FakeModule,
    ModuleExit,
    ModuleFail,
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

    def test_looks_up_by_name_server_side(self):
        client, api = client_with()
        self.run_module(FakeModule(params(), check_mode=True), client)

        api.list.assert_called_once_with(account_id="account", name="admins")

    def test_non_mapping_selector_fails_cleanly(self):
        current = {"id": "group", "name": "admins", "include": INCLUDE}
        for selector in (None, "everyone", ["everyone"]):
            with self.subTest(selector=selector):
                client, api = client_with([current], updated=current)

                result = self.run_module(FakeModule(params(include=[selector])), client)

                self.assertEqual(api.update.call_args.kwargs["include"], [selector])
                self.assertIn("Cloudflare did not apply the requested Access group", result["msg"])

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
        include = [{"ip": {"ip": "192.0.2.1"}}]
        stored = [{"ip": {"ip": "192.0.2.1/32"}}]
        client, _ignored = client_with(created={"id": "group", "name": "admins", "include": stored})

        result = self.run_module(FakeModule(params(include=include)), client)

        self.assertEqual(
            result["msg"],
            "Cloudflare did not apply the requested Access group: "
            'include requested [{"ip": {"ip": "192.0.2.1"}}], stored [{"ip": {"ip": "192.0.2.1/32"}}]',
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

    def test_rejects_update_response_for_wrong_group(self):
        current = {"id": "group", "name": "admins", "include": INCLUDE}
        client, _ignored = client_with([current], updated={"id": "other", "name": "admins"})

        result = self.run_module(FakeModule(params(include=[{"everyone": {}}])), client)

        self.assertEqual(result["msg"], "Cloudflare API returned the wrong Access group")

    def test_deletes_group(self):
        client, api = client_with([{"id": "group", "name": "admins"}], deleted={"id": "group"})

        result = self.run_module(FakeModule(params(state="absent")), client)

        api.delete.assert_called_once_with("group", account_id="account")
        self.assertTrue(result["changed"])
