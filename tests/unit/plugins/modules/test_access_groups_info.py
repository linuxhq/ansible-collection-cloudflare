# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from unittest import TestCase
from unittest.mock import Mock

from ansible_collections.linuxhq.cloudflare.plugins.modules import access_groups_info
from ansible_collections.linuxhq.cloudflare.tests.unit.plugins.modules.utils import (
    FakeModule,
    ModuleExit,
    ModuleFail,
)


class AccessGroupsInfoTests(TestCase):
    def test_lists_all_groups(self):
        client = Mock()
        groups = [{"id": "one", "name": "admins"}, {"id": "two", "name": "users"}]
        client.zero_trust.access.groups.list.return_value = iter(groups)

        with self.assertRaises(ModuleExit) as raised:
            access_groups_info.run(FakeModule({"account_id": "account"}), client)

        client.zero_trust.access.groups.list.assert_called_once_with(account_id="account")
        self.assertEqual(raised.exception.values, {"changed": False, "access_groups": groups})

    def test_rejects_malformed_groups(self):
        client = Mock()
        client.zero_trust.access.groups.list.return_value = [{"id": "one"}]

        with self.assertRaises(ModuleFail):
            access_groups_info.run(FakeModule({"account_id": "account"}), client)
