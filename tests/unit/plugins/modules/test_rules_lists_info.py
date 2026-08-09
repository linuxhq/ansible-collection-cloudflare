# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from unittest import TestCase
from unittest.mock import patch

from ansible_collections.linuxhq.cloudflare.plugins.modules import rules_lists_info
from ansible_collections.linuxhq.cloudflare.tests.unit.plugins.modules.utils import (
    FakeModule,
    ModuleExit,
)


class RulesListsInfoTests(TestCase):
    def test_lists_rules_lists_without_client_pagination(self):
        module = FakeModule({"account_id": "account"})
        rules_lists = [{"name": "addresses"}]

        with (
            patch.object(
                rules_lists_info,
                "list_all",
                return_value=rules_lists,
            ) as listed,
            self.assertRaises(ModuleExit) as raised,
        ):
            rules_lists_info.list(module, {})

        listed.assert_called_once_with(
            {},
            "/accounts/account/rules/lists",
            paginate=False,
        )
        self.assertEqual(raised.exception.values["rules_lists"], rules_lists)
