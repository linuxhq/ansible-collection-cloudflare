# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from unittest import TestCase
from unittest.mock import patch

from ansible_collections.linuxhq.cloudflare.plugins.modules import access_groups_info
from ansible_collections.linuxhq.cloudflare.tests.unit.plugins.modules.utils import (
    FakeModule,
    ModuleExit,
)


class AccessGroupsInfoTests(TestCase):
    def test_lists_groups(self):
        module = FakeModule({"account_id": "account"})
        groups = [{"id": "one"}]

        with (
            patch.object(access_groups_info, "list_all", return_value=groups) as listed,
            self.assertRaises(ModuleExit) as raised,
        ):
            access_groups_info.list(module, {})

        listed.assert_called_once_with({}, "/accounts/account/access/groups")
        self.assertEqual(raised.exception.values["access_groups"], groups)
        self.assertFalse(raised.exception.values["changed"])
