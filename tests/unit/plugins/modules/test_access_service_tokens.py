# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from unittest import TestCase
from unittest.mock import Mock, patch

from ansible_collections.linuxhq.cloudflare.plugins.modules import access_service_tokens
from ansible_collections.linuxhq.cloudflare.tests.unit.plugins.modules.utils import (
    FakeModule,
    ModuleExit,
)


class Model:
    def __init__(self, value):
        self.value = value

    def to_dict(self):
        return self.value


class AccessServiceTokensTests(TestCase):
    def test_creates_token_with_explicit_duration(self):
        module = FakeModule(
            {"account_id": "account", "name": "automation", "duration": "1y"}
        )
        client = Mock()
        client.zero_trust.access.service_tokens.create.return_value = Model(
            {"id": "token", "name": "automation"}
        )

        with (
            patch.object(access_service_tokens, "find_by_name", return_value=None),
            self.assertRaises(ModuleExit) as raised,
        ):
            access_service_tokens.ensure_present(module, client)

        client.zero_trust.access.service_tokens.create.assert_called_once_with(
            account_id="account",
            name="automation",
            duration="1y",
        )
        self.assertEqual(
            raised.exception.values["service_token"],
            {"id": "token", "name": "automation"},
        )

    def test_forever_token_without_expiry_is_unchanged(self):
        module = FakeModule(
            {"account_id": "account", "name": "automation", "duration": "forever"}
        )
        client = Mock()

        with (
            patch.object(
                access_service_tokens,
                "find_by_name",
                return_value={"id": "token", "name": "automation", "expires_at": None},
            ),
            self.assertRaises(ModuleExit) as raised,
        ):
            access_service_tokens.ensure_present(module, client)

        client.zero_trust.access.service_tokens.update.assert_not_called()
        self.assertFalse(raised.exception.values["changed"])

    def test_deletes_token_by_sdk_identifier(self):
        module = FakeModule(
            {"account_id": "account", "name": "automation", "duration": None}
        )
        client = Mock()
        current = {"id": "token", "name": "automation"}

        with (
            patch.object(
                access_service_tokens,
                "find_by_name",
                return_value=current,
            ),
            self.assertRaises(ModuleExit) as raised,
        ):
            access_service_tokens.ensure_absent(module, client)

        client.zero_trust.access.service_tokens.delete.assert_called_once_with(
            "token",
            account_id="account",
        )
        self.assertTrue(raised.exception.values["changed"])
