# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from unittest import TestCase
from unittest.mock import Mock

from ansible_collections.linuxhq.cloudflare.plugins.modules import (
    zerotrust_connectivity_settings_info,
)
from ansible_collections.linuxhq.cloudflare.tests.unit.plugins.modules.utils import (
    FakeModule,
    ModuleExit,
)


class ZeroTrustConnectivitySettingsInfoTests(TestCase):
    def test_gets_connectivity_settings(self):
        client = Mock()
        api = client.zero_trust.connectivity_settings
        api.get.return_value = {"icmp_proxy_enabled": True}

        with self.assertRaises(ModuleExit) as raised:
            zerotrust_connectivity_settings_info.run(FakeModule({"account_id": "account"}), client)

        api.get.assert_called_once_with(account_id="account")
        self.assertEqual(
            raised.exception.values, {"changed": False, "connectivity_settings": {"icmp_proxy_enabled": True}}
        )
