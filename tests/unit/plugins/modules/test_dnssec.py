# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from unittest import TestCase
from unittest.mock import Mock

from ansible_collections.linuxhq.cloudflare.plugins.modules import dnssec
from ansible_collections.linuxhq.cloudflare.tests.unit.plugins.modules.utils import (
    FakeModule,
    ModuleExit,
    ModuleFail,
)


def params(**updates):
    values = {
        "zone_id": "zone",
        "dnssec_multi_signer": None,
        "dnssec_presigned": None,
        "dnssec_use_nsec3": None,
        "status": "active",
    }
    values.update(updates)
    return values


class DnssecTests(TestCase):
    def run_module(self, module, current, edited=None):
        client = Mock()
        client.dns.dnssec.get.return_value = current
        client.dns.dnssec.edit.return_value = edited
        with self.assertRaises((ModuleExit, ModuleFail)) as raised:
            dnssec.run(module, client)

        client.dns.dnssec.get.assert_called_once_with(zone_id="zone")
        return raised.exception.values, client.dns.dnssec

    def test_pending_status_is_equivalent_to_requested_status(self):
        for current, status in (("pending", "active"), ("pending-disabled", "disabled")):
            with self.subTest(current=current):
                result, api = self.run_module(FakeModule(params(status=status)), {"status": current})

                api.edit.assert_not_called()
                self.assertFalse(result["changed"])
                self.assertEqual(result["dnssec"], {"status": current})

    def test_check_mode_does_not_edit(self):
        result, api = self.run_module(FakeModule(params(), check_mode=True), {"status": "disabled"})

        api.edit.assert_not_called()
        self.assertTrue(result["changed"])

    def test_updates_only_explicit_fields(self):
        current = {
            "status": "disabled",
            "dnssec_multi_signer": False,
            "dnssec_presigned": False,
            "dnssec_use_nsec3": False,
        }
        result, api = self.run_module(
            FakeModule(params(dnssec_presigned=True)), current, {"status": "pending", "dnssec_presigned": True}
        )

        api.edit.assert_called_once_with(zone_id="zone", dnssec_presigned=True, status="active")
        self.assertTrue(result["changed"])

    def test_false_matches_settings_omitted_while_disabled(self):
        false_options = {"dnssec_multi_signer": False, "dnssec_presigned": False, "dnssec_use_nsec3": False}
        result, api = self.run_module(FakeModule(params(status="disabled", **false_options)), {"status": "disabled"})

        api.edit.assert_not_called()
        self.assertFalse(result["changed"])
        self.assertEqual(result["dnssec"], {"status": "disabled"})

        current = {"status": "active", "dnssec_use_nsec3": True}
        result, api = self.run_module(
            FakeModule(params(status="disabled", dnssec_use_nsec3=False)), current, {"status": "pending-disabled"}
        )

        api.edit.assert_called_once_with(zone_id="zone", dnssec_use_nsec3=False, status="disabled")
        self.assertTrue(result["changed"])

    def test_rejects_settings_without_status(self):
        result, api = self.run_module(FakeModule(params(status=None)), {"dnssec_presigned": False})

        api.edit.assert_not_called()
        self.assertEqual(result["msg"], "Cloudflare API returned malformed DNSSEC settings data")

    def test_rejects_an_unmet_update_postcondition(self):
        settings = {"status": "active", "dnssec_presigned": False}
        result, _ignored = self.run_module(FakeModule(params(dnssec_presigned=True)), settings, settings)

        self.assertEqual(result["msg"], "Cloudflare did not apply the requested DNSSEC settings")
