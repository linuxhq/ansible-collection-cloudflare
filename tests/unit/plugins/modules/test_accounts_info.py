# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from unittest import TestCase
from unittest.mock import Mock

from ansible_collections.linuxhq.cloudflare.plugins.modules import accounts_info
from ansible_collections.linuxhq.cloudflare.tests.unit.plugins.modules.utils import (
    FakeModule,
    ModuleExit,
    ModuleFail,
)


def client_with(accounts):
    client = Mock()
    client.accounts.list.return_value = accounts
    return client


class AccountsInfoTests(TestCase):
    def test_finds_exact_account_and_stops_iteration(self):
        accounts = iter(
            [
                {"id": "other", "name": "other"},
                {"id": "account", "name": "wanted"},
                {"id": "unread", "name": "wanted"},
            ]
        )
        client = client_with(accounts)

        with self.assertRaises(ModuleExit) as raised:
            accounts_info.run(FakeModule({"name": "wanted"}), client)

        client.accounts.list.assert_called_once_with(name="wanted")
        self.assertEqual(
            raised.exception.values,
            {"changed": False, "account": {"id": "account", "name": "wanted"}},
        )
        self.assertEqual(next(accounts)["id"], "unread")

    def test_missing_account_returns_empty_mapping(self):
        with self.assertRaises(ModuleExit) as raised:
            accounts_info.run(FakeModule({"name": "missing"}), client_with([]))

        self.assertEqual(raised.exception.values["account"], {})

    def test_rejects_malformed_accounts(self):
        with self.assertRaises(ModuleFail) as raised:
            accounts_info.run(FakeModule({"name": "wanted"}), client_with([{"id": "account"}]))

        self.assertEqual(raised.exception.values["msg"], "Cloudflare API returned malformed account data")

    def test_rejects_matching_account_without_id(self):
        with self.assertRaises(ModuleFail) as raised:
            accounts_info.run(FakeModule({"name": "wanted"}), client_with([{"name": "wanted"}]))

        self.assertEqual(raised.exception.values["msg"], "Cloudflare API returned malformed account data")
