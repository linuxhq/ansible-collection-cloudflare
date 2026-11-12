# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from unittest import TestCase
from unittest.mock import Mock

from ansible_collections.linuxhq.cloudflare.plugins.modules import rules_lists_info
from ansible_collections.linuxhq.cloudflare.tests.unit.plugins.modules.utils import (
    FakeModule,
    ModuleExit,
    ModuleFail,
)


class RulesListsInfoTests(TestCase):
    def run_module(self, lists):
        client = Mock()
        client.rules.lists.list.return_value = lists
        with self.assertRaises((ModuleExit, ModuleFail)) as raised:
            rules_lists_info.run(FakeModule({"account_id": "account"}), client)

        return raised.exception.values, client.rules.lists

    def test_lists_rules_lists(self):
        lists = [{"id": "list", "name": "addresses", "kind": "ip"}]

        result, api = self.run_module(lists)

        api.list.assert_called_once_with(account_id="account")
        self.assertFalse(result["changed"])
        self.assertEqual(result["rules_lists"], lists)

    def test_rejects_list_without_kind(self):
        result, _ignored = self.run_module([{"id": "list", "name": "addresses"}])

        self.assertEqual(result["msg"], "Cloudflare API returned malformed Rules list data")
