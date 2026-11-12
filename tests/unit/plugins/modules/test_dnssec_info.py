# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from unittest import TestCase
from unittest.mock import Mock

from ansible_collections.linuxhq.cloudflare.plugins.modules import dnssec_info
from ansible_collections.linuxhq.cloudflare.tests.unit.plugins.modules.utils import (
    FakeModule,
    ModuleExit,
    connection_error,
    status_error,
)


def client_with(dnssec=None, error=None):
    client = Mock()
    client.zones.list.return_value = [{"id": "zone", "name": "example.com"}]
    client.dns.dnssec.get.return_value = dnssec
    client.dns.dnssec.get.side_effect = error
    return client


class DnssecInfoTests(TestCase):
    def test_lists_dnssec_for_valid_zones(self):
        client = client_with({"status": "active"})

        with self.assertRaises(ModuleExit) as raised:
            dnssec_info.run(FakeModule({}), client)

        client.dns.dnssec.get.assert_called_once_with(zone_id="zone")
        self.assertEqual(
            raised.exception.values,
            {
                "changed": False,
                "dnssec": [{"id": "zone", "name": "example.com", "dnssec": {"status": "active"}}],
                "skipped_zones": [],
            },
        )

    def test_skips_unsupported_zones_with_error_details(self):
        for status_code in (400, 404):
            with self.subTest(status_code=status_code):
                error = status_error(status_code, {"errors": [{"api_token": "secret"}], "messages": ["invalid"]})

                with self.assertRaises(ModuleExit) as raised:
                    dnssec_info.run(FakeModule({}), client_with(error=error))

                self.assertEqual(raised.exception.values["dnssec"], [])
                self.assertEqual(
                    raised.exception.values["skipped_zones"],
                    [
                        {
                            "zone_id": "zone",
                            "zone_name": "example.com",
                            "status_code": status_code,
                            "errors": [{"api_token": "secret"}],
                            "messages": [],
                        }
                    ],
                )

    def test_reports_unstructured_skip_details(self):
        with self.assertRaises(ModuleExit) as raised:
            dnssec_info.run(FakeModule({}), client_with(error=status_error(404, ["not-a-mapping"])))

        self.assertEqual(
            raised.exception.values["skipped_zones"][0]["error"],
            "Cloudflare API did not return structured error details",
        )

    def test_preserves_zone_context_for_other_errors(self):
        for error in (status_error(403), connection_error()):
            with self.subTest(error=type(error).__name__), self.assertRaises(type(error)) as raised:
                dnssec_info.run(FakeModule({}), client_with(error=error))

            self.assertIs(raised.exception, error)
            self.assertEqual(
                error._cloudflare_message,
                "Cloudflare API request failed while gathering DNSSEC information",
            )
            self.assertEqual(error._cloudflare_context, {"zone_id": "zone"})
