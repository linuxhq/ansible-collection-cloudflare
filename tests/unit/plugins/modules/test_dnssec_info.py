# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from types import SimpleNamespace
from unittest import TestCase
from unittest.mock import Mock, patch

from ansible_collections.linuxhq.cloudflare.plugins.modules import dnssec_info
from ansible_collections.linuxhq.cloudflare.tests.unit.plugins.modules.utils import (
    FakeModule,
    ModuleExit,
)


class Model:
    def __init__(self, value):
        self.value = value

    def to_dict(self):
        return self.value


class ApiError(Exception):
    pass


class ApiStatusError(ApiError):
    pass


class ApiConnectionError(ApiError):
    pass


class DnssecInfoTests(TestCase):
    def test_lists_dnssec_for_valid_zones(self):
        module = FakeModule({})
        client = Mock()
        client.zones.list.return_value = [
            Model({"id": "zone", "name": "example.com"}),
        ]
        client.dns.dnssec.get.return_value = Model({"status": "active"})

        with self.assertRaises(ModuleExit) as raised:
            dnssec_info.list_resources(module, client)

        client.dns.dnssec.get.assert_called_once_with(zone_id="zone")
        self.assertEqual(
            raised.exception.values["dnssec"],
            [
                {
                    "id": "zone",
                    "name": "example.com",
                    "dnssec": {"status": "active"},
                }
            ],
        )
        self.assertEqual(raised.exception.values["skipped_zones"], [])
        self.assertFalse(raised.exception.values["changed"])

    def test_redacts_skipped_zone_error_details(self):
        client = Mock()
        client.zones.list.return_value = [
            Model({"id": "zone", "name": "example.com"}),
        ]
        error = ApiStatusError("unsupported")
        error.status_code = 400
        error.response = Mock()
        error.response.json.return_value = {
            "errors": [{"api_token": "secret"}],
            "messages": ["invalid"],
        }
        client.dns.dnssec.get.side_effect = error

        with (
            patch.object(
                dnssec_info,
                "cloudflare",
                SimpleNamespace(
                    APIConnectionError=ApiConnectionError,
                    APIStatusError=ApiStatusError,
                    APIError=ApiError,
                ),
            ),
            self.assertRaises(ModuleExit) as raised,
        ):
            dnssec_info.list_resources(FakeModule({}), client)

        self.assertEqual(
            raised.exception.values["skipped_zones"][0]["errors"],
            [{"api_token": "********"}],
        )
        self.assertEqual(
            raised.exception.values["skipped_zones"][0]["messages"],
            [],
        )

    def test_preserves_zone_context_for_generic_sdk_errors(self):
        client = Mock()
        client.zones.list.return_value = [
            Model({"id": "zone", "name": "example.com"}),
        ]
        error = ApiError("invalid response")
        client.dns.dnssec.get.side_effect = error

        with (
            patch.object(
                dnssec_info,
                "cloudflare",
                SimpleNamespace(
                    APIConnectionError=ApiConnectionError,
                    APIStatusError=ApiStatusError,
                    APIError=ApiError,
                ),
            ),
            self.assertRaises(ApiError),
        ):
            dnssec_info.list_resources(FakeModule({}), client)

        self.assertEqual(
            error._cloudflare_message,
            "Cloudflare API error while gathering DNSSEC information",
        )
        self.assertEqual(
            error._cloudflare_context,
            {"zone": {"id": "zone", "name": "example.com"}},
        )
