# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from types import SimpleNamespace
from unittest import TestCase
from unittest.mock import patch

from ansible_collections.linuxhq.cloudflare.plugins.modules import warp_connector
from ansible_collections.linuxhq.cloudflare.tests.unit.plugins.modules.utils import (
    FakeModule,
    ModuleExit,
)


class ApiError(Exception):
    pass


class ApiConnectionError(ApiError):
    pass


class ApiStatusError(ApiError):
    pass


ERRORS = SimpleNamespace(
    APIError=ApiError,
    APIConnectionError=ApiConnectionError,
    APIStatusError=ApiStatusError,
)


def params(**updates):
    values = {
        "account_id": "account",
        "name": "connector",
        "tunnel_secret": None,
        "rotate_secrets": False,
    }
    values.update(updates)
    return values


class WarpConnectorTests(TestCase):
    def test_creates_connector(self):
        module = FakeModule(params())
        created = {"id": "connector-id", "name": "connector"}

        with (
            patch.object(warp_connector, "find_by_name", return_value=None),
            patch.object(warp_connector, "post_result", return_value=created) as post,
            self.assertRaises(ModuleExit) as raised,
        ):
            warp_connector.ensure_present(module, {})

        post.assert_called_once_with(
            {},
            "/accounts/account/warp_connector",
            {"name": "connector"},
        )
        self.assertEqual(raised.exception.values["warp_connector"], created)

    def test_secret_failure_rolls_back_created_connector(self):
        module = FakeModule(params(tunnel_secret="secret"))
        error = ApiStatusError("rejected")

        with (
            patch.object(warp_connector, "cloudflare", ERRORS),
            patch.object(warp_connector, "find_by_name", return_value=None),
            patch.object(
                warp_connector,
                "post_result",
                return_value={"id": "connector-id"},
            ),
            patch.object(warp_connector, "patch_result", side_effect=error),
            patch.object(warp_connector, "delete_result") as delete,
            self.assertRaises(ApiStatusError) as raised,
        ):
            warp_connector.ensure_present(module, {})

        self.assertIs(raised.exception, error)
        delete.assert_called_once_with(
            {},
            "/accounts/account/warp_connector/connector-id",
        )

    def test_missing_connector_is_already_absent(self):
        module = FakeModule(params())

        with (
            patch.object(warp_connector, "find_by_name", return_value=None),
            patch.object(warp_connector, "delete_result") as delete,
            self.assertRaises(ModuleExit) as raised,
        ):
            warp_connector.ensure_absent(module, {})

        delete.assert_not_called()
        self.assertFalse(raised.exception.values["changed"])
