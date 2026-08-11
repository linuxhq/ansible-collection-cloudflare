# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from unittest import TestCase
from unittest.mock import patch

from ansible_collections.linuxhq.cloudflare.plugins.modules import access_apps_info
from ansible_collections.linuxhq.cloudflare.tests.unit.plugins.modules.utils import (
    FakeModule,
    ModuleExit,
)


class AccessAppsInfoTests(TestCase):
    def test_lists_apps_and_redacts_secrets(self):
        module = FakeModule({"account_id": "account"})
        apps = [
            {
                "id": "app-id",
                "name": "app",
                "saas_app": {"client_secret": "secret", "name": "example"},
                "scim_config": {
                    "authentication": {"client_secret": "secret", "method": "oauth"}
                },
            }
        ]

        with (
            patch.object(access_apps_info, "list_all", return_value=apps) as listed,
            self.assertRaises(ModuleExit) as raised,
        ):
            access_apps_info.list_resources(module, {})

        listed.assert_called_once_with({}, "/accounts/account/access/apps")
        self.assertFalse(raised.exception.values["changed"])
        self.assertEqual(
            raised.exception.values["access_apps"][0]["scim_config"]["authentication"],
            {"method": "oauth"},
        )
        self.assertEqual(
            raised.exception.values["access_apps"][0]["saas_app"],
            {"name": "example"},
        )
