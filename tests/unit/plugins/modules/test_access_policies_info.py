# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from unittest import TestCase
from unittest.mock import patch

from ansible_collections.linuxhq.cloudflare.plugins.modules import access_policies_info
from ansible_collections.linuxhq.cloudflare.tests.unit.plugins.modules.utils import (
    FakeModule,
    ModuleExit,
)


class AccessPoliciesInfoTests(TestCase):
    def test_lists_policies(self):
        module = FakeModule({"account_id": "account"})
        policies = [{"id": "one"}]

        with (
            patch.object(
                access_policies_info,
                "list_all",
                return_value=policies,
            ) as listed,
            self.assertRaises(ModuleExit) as raised,
        ):
            access_policies_info.list_resources(module, {})

        listed.assert_called_once_with({}, "/accounts/account/access/policies")
        self.assertEqual(raised.exception.values["access_policies"], policies)
        self.assertFalse(raised.exception.values["changed"])
