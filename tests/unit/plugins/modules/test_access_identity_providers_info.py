# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from unittest import TestCase
from unittest.mock import patch

from ansible_collections.linuxhq.cloudflare.plugins.modules import (
    access_identity_providers_info,
)
from ansible_collections.linuxhq.cloudflare.tests.unit.plugins.modules.utils import (
    FakeModule,
    ModuleExit,
)


class AccessIdentityProvidersInfoTests(TestCase):
    def test_lists_providers_without_secrets(self):
        module = FakeModule({"account_id": "account"})
        providers = [
            {
                "config": {"client_id": "id", "client_secret": "secret"},
                "scim_config": {"secret": "secret"},
            }
        ]

        with (
            patch.object(
                access_identity_providers_info,
                "list_all",
                return_value=providers,
            ) as listed,
            self.assertRaises(ModuleExit) as raised,
        ):
            access_identity_providers_info.list(module, {})

        listed.assert_called_once_with(
            {},
            "/accounts/account/access/identity_providers",
        )
        self.assertEqual(
            raised.exception.values["access_identity_providers"],
            [{"config": {"client_id": "id"}, "scim_config": {}}],
        )
