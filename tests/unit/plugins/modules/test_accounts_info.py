# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from types import SimpleNamespace
from unittest import TestCase
from unittest.mock import Mock, patch

from ansible_collections.linuxhq.cloudflare.plugins.modules import accounts_info
from ansible_collections.linuxhq.cloudflare.tests.unit.plugins.modules.utils import (
    FakeModule,
    ModuleExit,
    ModuleFail,
)


class AccountsInfoTests(TestCase):
    def test_finds_exact_account_and_stops_iteration(self):
        module = FakeModule({"name": "wanted"})
        client = Mock()
        client.accounts.list.return_value = [
            SimpleNamespace(name="other"),
            SimpleNamespace(name="wanted"),
            SimpleNamespace(name="wanted"),
        ]

        with (
            patch.object(
                accounts_info,
                "serialize_resource",
                side_effect=(
                    {"id": "other", "name": "other"},
                    {"id": "account", "name": "wanted"},
                ),
            ),
            self.assertRaises(ModuleExit) as raised,
        ):
            accounts_info.info(module, client)

        client.accounts.list.assert_called_once_with(name="wanted")
        self.assertEqual(
            raised.exception.values["account"],
            {"id": "account", "name": "wanted"},
        )
        self.assertFalse(raised.exception.values["changed"])

    def test_missing_account_returns_empty_mapping(self):
        module = FakeModule({"name": "missing"})
        client = Mock()
        client.accounts.list.return_value = []

        with self.assertRaises(ModuleExit) as raised:
            accounts_info.info(module, client)

        self.assertEqual(raised.exception.values["account"], {})

    def test_rejects_malformed_accounts(self):
        module = FakeModule({"name": "wanted"})
        client = Mock()
        client.accounts.list.return_value = [SimpleNamespace(name=None)]

        with self.assertRaises(ModuleFail) as raised:
            accounts_info.info(module, client)

        self.assertEqual(
            raised.exception.values["msg"],
            "Cloudflare API returned malformed account data",
        )
