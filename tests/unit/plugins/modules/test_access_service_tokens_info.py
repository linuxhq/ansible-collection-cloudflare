# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from unittest import TestCase
from unittest.mock import patch

from ansible_collections.linuxhq.cloudflare.plugins.modules import (
    access_service_tokens_info,
)
from ansible_collections.linuxhq.cloudflare.tests.unit.plugins.modules.utils import (
    FakeModule,
    ModuleExit,
)


class AccessServiceTokensInfoTests(TestCase):
    def test_lists_service_tokens(self):
        module = FakeModule({"account_id": "account"})
        tokens = [{"id": "one"}]

        with (
            patch.object(
                access_service_tokens_info,
                "list_all",
                return_value=tokens,
            ) as listed,
            self.assertRaises(ModuleExit) as raised,
        ):
            access_service_tokens_info.list(module, {})

        listed.assert_called_once_with(
            {},
            "/accounts/account/access/service_tokens",
        )
        self.assertEqual(raised.exception.values["service_tokens"], tokens)
