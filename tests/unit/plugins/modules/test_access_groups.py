# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from unittest import TestCase
from unittest.mock import Mock

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
        "is_default": False,
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

    def test_equivalent_group_is_unchanged(self):
        current = {"id": "group", "name": "admins", "include": [{"email": {"email": "admin@example.com", "x": 1}}]}
        client, api = client_with([current])

        result = self.run_module(FakeModule(params()), client)

        api.update.assert_not_called()
        self.assertFalse(result["changed"])

    def test_creates_group(self):
        created = {"id": "group", "name": "admins", "include": INCLUDE}
        client, api = client_with(created=created)

        result = self.run_module(FakeModule(params()), client)

        api.create.assert_called_once_with(account_id="account", include=INCLUDE, is_default=False, name="admins")
        self.assertEqual(result["access_group"], created)

    def test_update_preserves_omitted_selectors(self):
        exclude = [{"email": {"email": "blocked@example.com"}}]
        include = [{"email": {"email": "new@example.com"}}]
        current = {"id": "group", "name": "admins", "include": INCLUDE, "exclude": exclude}
        updated = {**current, "include": include}
        client, api = client_with([current], updated=updated)

        result = self.run_module(FakeModule(params(include=include)), client)

        api.update.assert_called_once_with(
            "group", account_id="account", exclude=exclude, include=include, is_default=False, name="admins"
        )
        self.assertTrue(result["changed"])

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
