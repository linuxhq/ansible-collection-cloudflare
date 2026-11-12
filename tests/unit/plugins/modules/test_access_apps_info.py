# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from unittest import TestCase
from unittest.mock import Mock

from ansible_collections.linuxhq.cloudflare.plugins.modules import access_apps_info
from ansible_collections.linuxhq.cloudflare.tests.unit.plugins.modules.utils import (
    FakeModule,
    ModuleExit,
    ModuleFail,
)


class AccessAppsInfoTests(TestCase):
    def test_lists_apps_with_all_fields(self):
        client = Mock()
        client.zero_trust.access.applications.list.return_value = iter(
            [
                {
                    "id": "app-id",
                    "name": "app",
                    "saas_app": {"client_secret": "secret", "name": "example"},
                    "scim_config": {"authentication": {"client_secret": "secret", "method": "oauth"}},
                }
            ]
        )

        with self.assertRaises(ModuleExit) as raised:
            access_apps_info.run(FakeModule({"account_id": "account"}), client)

        client.zero_trust.access.applications.list.assert_called_once_with(account_id="account")
        values = raised.exception.values
        self.assertFalse(values["changed"])
        self.assertEqual(values["access_apps"][0]["saas_app"], {"client_secret": "secret", "name": "example"})

    def test_rejects_malformed_apps(self):
        client = Mock()
        client.zero_trust.access.applications.list.return_value = [{"id": "app-id"}]

        with self.assertRaises(ModuleFail):
            access_apps_info.run(FakeModule({"account_id": "account"}), client)
