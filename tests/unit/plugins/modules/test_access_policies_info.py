# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from unittest import TestCase
from unittest.mock import Mock

from ansible_collections.linuxhq.cloudflare.plugins.modules import access_policies_info
from ansible_collections.linuxhq.cloudflare.tests.unit.plugins.modules.utils import (
    FakeModule,
    ModuleExit,
    ModuleFail,
)


class AccessPoliciesInfoTests(TestCase):
    def test_lists_policies(self):
        client = Mock()
        policies = [{"id": "one", "name": "admins"}, {"id": "two", "name": "users"}]
        client.zero_trust.access.policies.list.return_value = iter(policies)

        with self.assertRaises(ModuleExit) as raised:
            access_policies_info.run(FakeModule({"account_id": "account"}), client)

        client.zero_trust.access.policies.list.assert_called_once_with(account_id="account")
        self.assertEqual(raised.exception.values, {"changed": False, "access_policies": policies})

    def test_rejects_malformed_policies(self):
        client = Mock()
        client.zero_trust.access.policies.list.return_value = [{"name": "admins"}]

        with self.assertRaises(ModuleFail):
            access_policies_info.run(FakeModule({"account_id": "account"}), client)
