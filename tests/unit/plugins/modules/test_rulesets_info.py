# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from unittest import TestCase
from unittest.mock import Mock

import cloudflare

from ansible_collections.linuxhq.cloudflare.plugins.modules import rulesets_info
from ansible_collections.linuxhq.cloudflare.tests.unit.plugins.modules.utils import (
    FakeModule,
    ModuleExit,
    ModuleFail,
    status_error,
)

PHASE = "http_request_firewall_custom"
ZONES = ({"id": "zone", "name": "example.com"},)


class RulesetsInfoTests(TestCase):
    def run_module(self, entrypoint, zones=ZONES):
        client = Mock()
        client.zones.list.return_value = list(zones)
        if isinstance(entrypoint, Exception):
            client.rulesets.phases.get.side_effect = entrypoint
        else:
            client.rulesets.phases.get.return_value = entrypoint

        with self.assertRaises((ModuleExit, ModuleFail)) as raised:
            rulesets_info.run(FakeModule({"phase": PHASE}), client)

        return raised.exception.values, client

    def test_lists_entrypoints_for_zones_with_ids(self):
        result, client = self.run_module({"id": "ruleset", "phase": PHASE})

        client.zones.list.assert_called_once_with()
        client.rulesets.phases.get.assert_called_once_with(PHASE, zone_id="zone")
        self.assertEqual(
            result["rulesets"],
            [{"id": "ruleset", "name": "example.com", "phase": PHASE, "rules": [], "zone_id": "zone"}],
        )

    def test_not_found_omits_conditional_fields(self):
        result, _ignored = self.run_module(status_error(404))

        self.assertEqual(result["rulesets"], [{"name": "example.com", "rules": [], "zone_id": "zone"}])

    def test_other_errors_propagate_with_context(self):
        with self.assertRaises(cloudflare.PermissionDeniedError) as raised:
            self.run_module(status_error(403))

        self.assertEqual(raised.exception._cloudflare_context, {"zone_id": "zone", "phase": PHASE})

    def test_rejects_malformed_ruleset_id_with_zone_context(self):
        result, _ignored = self.run_module({"id": "", "phase": PHASE})

        self.assertEqual(result["msg"], "Cloudflare API returned malformed ruleset data")
        self.assertEqual((result["zone_id"], result["phase"]), ("zone", PHASE))

    def test_rejects_wrong_phase(self):
        result, _ignored = self.run_module({"id": "ruleset", "phase": "http_request_transform"})

        self.assertEqual(result["msg"], "Cloudflare API returned the wrong ruleset")
        self.assertEqual((result["zone_id"], result["phase"]), ("zone", PHASE))

    def test_rejects_malformed_zone(self):
        result, _ignored = self.run_module(None, zones=[{"id": "zone"}])

        self.assertEqual(result["msg"], "Cloudflare API returned malformed zone data")

    def test_returns_header_values(self):
        rule = {
            "action": "rewrite",
            "action_parameters": {"headers": {"X-Api-Key": {"operation": "set", "value": "k"}}},
        }

        result, _client = self.run_module({"id": "ruleset", "phase": PHASE, "rules": [rule]})

        self.assertEqual(result["rulesets"][0]["rules"], [rule])


class RulesetsInfoDeletedZoneTests(TestCase):
    def run_module(self, zone_read):
        client = Mock()
        client.zones.list.return_value = [*ZONES, {"id": "kept", "name": "example.net"}]
        client.rulesets.phases.get.side_effect = [
            status_error(403, {"success": False, "errors": [{"code": 10000, "message": "Authentication error"}]}),
            {"id": "ruleset", "phase": PHASE},
        ]
        if isinstance(zone_read, Exception):
            client.zones.get.side_effect = zone_read
        else:
            client.zones.get.return_value = zone_read

        with self.assertRaises((ModuleExit, ModuleFail)) as raised:
            rulesets_info.run(FakeModule({"phase": PHASE}), client)

        return raised.exception.values, client

    def test_zone_deleted_after_listing_is_omitted(self):
        # Cloudflare answers the entrypoint request for a deleted zone with 403
        # and a read of the zone with 400 code 1001, or 404.
        for zone_read in (
            status_error(400, {"success": False, "errors": [{"code": 1001, "message": "Invalid zone identifier"}]}),
            status_error(404),
        ):
            with self.subTest(status=zone_read.status_code):
                result, client = self.run_module(zone_read)

                client.zones.get.assert_called_once_with(zone_id="zone")
                self.assertEqual(
                    result["rulesets"],
                    [{"id": "ruleset", "name": "example.net", "phase": PHASE, "rules": [], "zone_id": "kept"}],
                )

    def test_forbidden_entrypoint_of_an_existing_zone_fails(self):
        # A zone that still exists, or a zone read that fails another way,
        # reports the original 403.
        for zone_read in (
            {"id": "zone", "name": "example.com"},
            status_error(400, {"success": False, "errors": [{"code": 7003, "message": "Could not route"}]}),
            status_error(403),
            status_error(500),
        ):
            with self.subTest(zone_read=zone_read):
                with self.assertRaises(cloudflare.PermissionDeniedError) as raised:
                    self.run_module(zone_read)

                self.assertEqual(raised.exception.body["errors"][0]["code"], 10000)
                self.assertEqual(raised.exception._cloudflare_context, {"zone_id": "zone", "phase": PHASE})
