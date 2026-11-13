# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from unittest import TestCase
from unittest.mock import Mock

from ansible_collections.linuxhq.cloudflare.plugins.modules import (
    access_service_tokens_info,
)
from ansible_collections.linuxhq.cloudflare.tests.unit.plugins.modules.utils import (
    FakeModule,
    ModuleExit,
    ModuleFail,
)


class AccessServiceTokensInfoTests(TestCase):
    def test_lists_service_tokens(self):
        client = Mock()
        tokens = [{"id": "one", "name": "automation"}]
        client.zero_trust.access.service_tokens.list.return_value = iter(tokens)

        with self.assertRaises(ModuleExit) as raised:
            access_service_tokens_info.run(FakeModule({"account_id": "account"}), client)

        client.zero_trust.access.service_tokens.list.assert_called_once_with(account_id="account")
        self.assertEqual(raised.exception.values, {"changed": False, "service_tokens": tokens})

    def test_rejects_malformed_service_tokens(self):
        client = Mock()
        client.zero_trust.access.service_tokens.list.return_value = [{"id": "one", "name": None}]

        with self.assertRaises(ModuleFail):
            access_service_tokens_info.run(FakeModule({"account_id": "account"}), client)
