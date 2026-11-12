# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from unittest import TestCase
from unittest.mock import Mock

from ansible_collections.linuxhq.cloudflare.plugins.modules import (
    access_identity_providers_info,
)
from ansible_collections.linuxhq.cloudflare.tests.unit.plugins.modules.utils import (
    FakeModule,
    ModuleExit,
    ModuleFail,
)


def client_with(providers):
    client = Mock()
    client.zero_trust.identity_providers.list.return_value = iter(providers)
    return client


class AccessIdentityProvidersInfoTests(TestCase):
    def test_lists_providers_with_all_fields(self):
        client = client_with(
            [
                {
                    "id": "provider",
                    "name": "",
                    "type": "onetimepin",
                    "config": {
                        "client_id": "id",
                        "nested": [{"client_secret": "secret"}],
                    },
                    "scim_config": [{"secret": "secret"}],
                }
            ]
        )

        with self.assertRaises(ModuleExit) as raised:
            access_identity_providers_info.run(FakeModule({"account_id": "account"}), client)

        client.zero_trust.identity_providers.list.assert_called_once_with(account_id="account")
        self.assertEqual(
            raised.exception.values,
            {
                "changed": False,
                "access_identity_providers": [
                    {
                        "id": "provider",
                        "name": "",
                        "type": "onetimepin",
                        "config": {"client_id": "id", "nested": [{"client_secret": "secret"}]},
                        "scim_config": [{"secret": "secret"}],
                    }
                ],
            },
        )

    def test_rejects_padded_name(self):
        client = client_with([{"id": "provider", "name": " idp", "type": "onetimepin"}])

        with self.assertRaises(ModuleFail) as raised:
            access_identity_providers_info.run(FakeModule({"account_id": "account"}), client)

        self.assertEqual(
            raised.exception.values["msg"],
            "Cloudflare API returned malformed Access identity provider data",
        )
