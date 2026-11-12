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

    def test_rejects_non_mapping_rules(self):
        result, _ignored = self.run_module({"id": "ruleset", "phase": PHASE, "rules": ["invalid"]})

        self.assertEqual(result["msg"], "Cloudflare API returned malformed ruleset rule data")

    def test_rejects_wrong_phase(self):
        result, _ignored = self.run_module({"id": "ruleset", "phase": "http_request_transform"})

        self.assertEqual(result["msg"], "Cloudflare API returned the wrong ruleset")

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
