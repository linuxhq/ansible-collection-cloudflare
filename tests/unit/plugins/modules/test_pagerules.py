# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from unittest import TestCase
from unittest.mock import Mock, patch

import cloudflare

from ansible_collections.linuxhq.cloudflare.plugins.module_utils import cloudflare_utils
from ansible_collections.linuxhq.cloudflare.plugins.modules import pagerules
from ansible_collections.linuxhq.cloudflare.tests.unit.plugins.modules.utils import (
    FakeModule,
    ModuleExit,
    ModuleFail,
)

ACTIONS = [{"id": "always_use_https"}]
TARGETS = [{"target": "url", "constraint": {"operator": "matches", "value": "example.com/*"}}]


def params(**updates):
    values = {
        "zone_id": "zone",
        "actions": ACTIONS,
        "targets": TARGETS,
        "priority": None,
        "status": None,
        "state": "present",
    }
    values.update(updates)
    return values


def client_with(rules=(), created=None, updated=None, deleted=None):
    client = Mock()
    api = client.page_rules
    api.list.return_value = list(rules)
    api.create.return_value = created
    api.update.return_value = updated
    api.delete.return_value = deleted
    return client, api


class PageRulesTests(TestCase):
    def run_module(self, module, client):
        with self.assertRaises((ModuleExit, ModuleFail)) as raised:
            pagerules.run(module, client)

        return raised.exception.values

    def test_dot_segment_zone_id_fails_before_any_request(self):
        for zone_id in (".", ".."):
            module = FakeModule({**params(zone_id=zone_id), "api_token": "token"})
            with (
                self.subTest(zone_id=zone_id),
                patch.object(pagerules, "AnsibleModule", return_value=module),
                patch.object(cloudflare_utils, "Cloudflare", wraps=cloudflare.Cloudflare) as constructor,
                self.assertRaises(ModuleFail) as raised,
            ):
                pagerules.main()

            constructor.assert_not_called()
            self.assertEqual(raised.exception.values["msg"], "zone_id must not be '.' or '..'")

    def test_finds_rule_by_targets(self):
        rules = [{"id": str(index), "targets": []} for index in range(124)]
        rules.append({"id": "match", "actions": ACTIONS, "targets": TARGETS})
        client, api = client_with(rules)

        result = self.run_module(FakeModule(params()), client)

        api.list.assert_called_once_with(zone_id="zone")
        self.assertEqual(result["pagerule"], rules[-1])

    def test_rejects_malformed_targets(self):
        for targets in ({}, ["invalid"]):
            with self.subTest(targets=targets):
                client, _ignored = client_with([{"id": "rule", "targets": targets}])

                result = self.run_module(FakeModule(params()), client)

                self.assertIn("malformed page rule", result["msg"])

    def test_find_pagerule_ignores_target_keys_outside_the_identity(self):
        current = {"id": "match", "actions": ACTIONS, "targets": TARGETS}
        client, _ignored = client_with([current])
        targets = [{**TARGETS[0], "foo": "bar", "constraint": {**TARGETS[0]["constraint"], "extra": 1}}]

        found, rule_count = pagerules.find_pagerule(FakeModule(params(targets=targets)), client, targets)

        self.assertEqual(found, current)
        self.assertEqual(rule_count, 1)

    def test_partial_targets_fail_before_any_request(self):
        cases = (
            ([{"target": "url"}], ["targets[0].constraint"]),
            ([{"constraint": TARGETS[0]["constraint"]}], ["targets[0].target"]),
            ([{"target": "url", "constraint": {"value": "example.com/*"}}], ["targets[0].constraint.operator"]),
            (
                [TARGETS[0], {"target": "url", "constraint": {"operator": None}}],
                ["targets[1].constraint.operator", "targets[1].constraint.value"],
            ),
        )
        for targets, missing in cases:
            for state in ("present", "absent"):
                for check_mode in (True, False):
                    with self.subTest(targets=targets, state=state, check_mode=check_mode):
                        client, api = client_with([{"id": "other", "targets": TARGETS}], deleted={"id": "other"})

                        result = self.run_module(
                            FakeModule(params(targets=targets, state=state), check_mode=check_mode), client
                        )

                        self.assertEqual(result["missing_fields"], missing)
                        self.assertEqual(
                            result["msg"],
                            f"Page rule targets must set these fields that identify the page rule: {', '.join(missing)}",
                        )
                        api.list.assert_not_called()
                        api.create.assert_not_called()
                        api.update.assert_not_called()
                        api.delete.assert_not_called()

    def test_finds_rule_only_when_targets_are_equal(self):
        other = {"target": "url", "constraint": {"operator": "matches", "value": "other.example.com/*"}}
        for stored in (
            [{"target": "url", "constraint": {"operator": "contains", "value": "example.com/*"}}],
            [{"target": "url", "constraint": {"operator": "matches", "value": "www.example.com/*"}}],
            [TARGETS[0], other],
        ):
            with self.subTest(stored=stored):
                client, _ignored = client_with([{"id": "other", "targets": stored}])

                found, rule_count = pagerules.find_pagerule(FakeModule(params()), client, TARGETS)

                self.assertIsNone(found)
                self.assertEqual(rule_count, 1)

    def test_absent_does_not_delete_a_rule_with_other_targets(self):
        stored = [{"target": "url", "constraint": {"operator": "matches", "value": "www.example.com/*"}}]
        client, api = client_with([{"id": "other", "targets": stored}], deleted={"id": "other"})

        result = self.run_module(FakeModule(params(state="absent")), client)

        api.delete.assert_not_called()
        self.assertFalse(result["changed"])
        self.assertEqual(result["message"], "Page rule already absent")

    def test_rejects_ambiguous_target_match(self):
        client, _ignored = client_with([{"id": "one", "targets": TARGETS}, {"id": "two", "targets": TARGETS}])

        result = self.run_module(FakeModule(params()), client)

        self.assertIn("Multiple page rules", result["msg"])

    def test_check_mode_does_not_create(self):
        client, api = client_with()

        result = self.run_module(FakeModule(params(), check_mode=True), client)

        api.create.assert_not_called()
        self.assertTrue(result["changed"])

    def test_create_defaults_status_to_active(self):
        created = {"id": "rule", "actions": ACTIONS, "status": "active", "targets": TARGETS}
        client, api = client_with(created=created)

        result = self.run_module(FakeModule(params()), client)

        api.create.assert_called_once_with(zone_id="zone", actions=ACTIONS, status="active", targets=TARGETS)
        self.assertEqual(result["pagerule"], created)

    def test_rejects_a_create_response_with_different_targets(self):
        client, _ignored = client_with(created={"id": "rule", "targets": []})

        result = self.run_module(FakeModule(params()), client)

        self.assertTrue(result["msg"].startswith("Cloudflare did not apply the requested page rule: "))
        self.assertIn({"field": "targets", "requested": TARGETS, "stored": []}, result["differences"])

    def test_omitted_status_and_priority_preserve_current_values(self):
        current = {"id": "rule", "actions": ACTIONS, "priority": 10, "status": "disabled", "targets": TARGETS}
        client, api = client_with([current])

        result = self.run_module(FakeModule(params()), client)

        api.update.assert_not_called()
        self.assertFalse(result["changed"])

    def test_update_sends_preserved_status_and_priority(self):
        actions = [{"id": "ssl", "value": "full"}]
        current = {"id": "rule", "actions": ACTIONS, "priority": 10, "status": "disabled", "targets": TARGETS}
        updated = {**current, "actions": actions}
        client, api = client_with([current], updated=updated)

        result = self.run_module(FakeModule(params(actions=actions)), client)

        api.update.assert_called_once_with(
            pagerule_id="rule", zone_id="zone", actions=actions, priority=10, status="disabled", targets=TARGETS
        )
        self.assertTrue(result["changed"])
        self.assertEqual(result["pagerule"], updated)

    def test_rejects_priority_above_rule_count_before_any_write(self):
        other = {"id": "other", "actions": ACTIONS, "priority": 1, "targets": []}
        current = {"id": "rule", "actions": ACTIONS, "priority": 2, "status": "active", "targets": TARGETS}
        cases = (([other], 3, 2), ([other, current], 3, 2))
        for rules, priority, maximum in cases:
            with self.subTest(rules=len(rules)):
                client, api = client_with(rules)

                result = self.run_module(FakeModule(params(priority=priority)), client)

                api.create.assert_not_called()
                api.update.assert_not_called()
                self.assertEqual(
                    result["msg"],
                    f"priority {priority} exceeds the number of page rules in the zone; the maximum is {maximum}",
                )

    def test_check_mode_accepts_priority_above_rule_count(self):
        # Rules that earlier tasks would create are not counted in check mode.
        other = {"id": "other", "actions": ACTIONS, "priority": 1, "targets": []}
        current = {"id": "rule", "actions": ACTIONS, "priority": 2, "status": "active", "targets": TARGETS}
        for rules in ([], [other], [other, current]):
            with self.subTest(rules=len(rules)):
                client, api = client_with(rules)

                result = self.run_module(FakeModule(params(priority=3), True), client)

                api.create.assert_not_called()
                api.update.assert_not_called()
                self.assertFalse(result.get("failed", False))
                self.assertTrue(result["changed"])

    def test_rejects_priority_below_one_before_any_write(self):
        current = {"id": "rule", "actions": ACTIONS, "priority": 1, "status": "active", "targets": TARGETS}
        for rules in ([], [current]):
            for check_mode in (False, True):
                with self.subTest(rules=len(rules), check_mode=check_mode):
                    client, api = client_with(rules)

                    result = self.run_module(FakeModule(params(priority=0), check_mode), client)

                    api.create.assert_not_called()
                    api.update.assert_not_called()
                    self.assertEqual(result["msg"], "priority 0 must be at least 1")

    def test_accepts_priority_up_to_rule_count(self):
        other = {"id": "other", "actions": ACTIONS, "priority": 1, "targets": []}
        created = {"id": "rule", "actions": ACTIONS, "priority": 2, "status": "active", "targets": TARGETS}
        client, api = client_with([other], created=created)

        result = self.run_module(FakeModule(params(priority=2)), client)

        api.create.assert_called_once_with(
            zone_id="zone", actions=ACTIONS, priority=2, status="active", targets=TARGETS
        )
        self.assertTrue(result["changed"])

    def test_check_mode_does_not_update(self):
        current = {"id": "rule", "actions": ACTIONS, "status": "active", "targets": TARGETS}
        client, api = client_with([current])

        result = self.run_module(FakeModule(params(status="disabled"), check_mode=True), client)

        api.update.assert_not_called()
        self.assertTrue(result["changed"])

    def test_nested_provider_fields_do_not_cause_change(self):
        current = {
            "id": "rule",
            "actions": [{"id": "always_use_https", "provider_default": True}],
            "targets": [{**TARGETS[0], "constraint": {**TARGETS[0]["constraint"], "provider_default": True}}],
        }
        client, api = client_with([current])

        result = self.run_module(FakeModule(params()), client)

        api.update.assert_not_called()
        self.assertFalse(result["changed"])

    def test_matches_target_urls_as_cloudflare_stores_them(self):
        cases = (
            ("Example.COM/Path/*", "example.com/Path/*"),
            ("example.com", "example.com/"),
            ("HTTPS://WWW.Example.com", "HTTPS://www.example.com/"),
            ("Example.com*", "example.com/*"),
            ("*.Example.com", "*.example.com/"),
            ("http://*.Example.com/Path*", "http://*.example.com/Path*"),
            ("Example.com/to/https://Other.COM/Path", "example.com/to/https://Other.COM/Path"),
            ("https://example.com?Token=ABC", "https://example.com?Token=ABC"),
        )
        for requested, stored in cases:
            with self.subTest(requested=requested):
                stored_targets = [{"target": "url", "constraint": {"operator": "matches", "value": stored}}]
                targets = [{"target": "url", "constraint": {"operator": "matches", "value": requested}}]
                current = {"id": "rule", "actions": ACTIONS, "status": "active", "targets": stored_targets}
                client, api = client_with([current])

                result = self.run_module(FakeModule(params(targets=targets)), client)

                api.update.assert_not_called()
                self.assertFalse(result["changed"])

    def test_creates_rule_with_canonical_target_url(self):
        stored_targets = [{"target": "url", "constraint": {"operator": "matches", "value": "example.com/"}}]
        targets = [{"target": "url", "constraint": {"operator": "matches", "value": "Example.com"}}]
        created = {"id": "rule", "actions": ACTIONS, "status": "active", "targets": stored_targets}
        client, api = client_with(created=created)

        result = self.run_module(FakeModule(params(targets=targets)), client)

        self.assertEqual(api.create.call_args.kwargs["targets"], stored_targets)
        self.assertTrue(result["changed"])

    def test_action_order_is_not_significant(self):
        actions = [{"id": "ssl", "value": "full"}, {"id": "browser_check", "value": "on"}]
        listed = [{"id": "browser_check", "value": "on"}, {"id": "ssl", "value": "full"}]
        current = {"id": "rule", "actions": listed, "status": "active", "targets": TARGETS}
        client, api = client_with([current])

        result = self.run_module(FakeModule(params(actions=actions)), client)

        api.update.assert_not_called()
        self.assertFalse(result["changed"])

    def test_creates_actions_sorted_by_id(self):
        actions = [{"id": "ssl", "value": "full"}, {"id": "browser_check", "value": "on"}]
        listed = [{"id": "browser_check", "value": "on"}, {"id": "ssl", "value": "full"}]
        client, api = client_with(created={"id": "rule", "actions": listed, "status": "active", "targets": TARGETS})

        result = self.run_module(FakeModule(params(actions=actions)), client)

        self.assertEqual(api.create.call_args.kwargs["actions"], listed)
        self.assertTrue(result["changed"])

    def test_removed_cache_ttl_status_is_a_change(self):
        actions = [{"id": "cache_ttl_by_status", "value": {"200": 3600}}]
        listed = [{"id": "cache_ttl_by_status", "value": {"200": 3600, "404": 60}}]
        current = {"id": "rule", "actions": listed, "status": "active", "targets": TARGETS}
        for check_mode in (True, False):
            with self.subTest(check_mode=check_mode):
                client, api = client_with([current], updated={**current, "actions": actions})

                result = self.run_module(FakeModule(params(actions=actions), check_mode=check_mode), client)

                self.assertTrue(result["changed"])
                self.assertNotIn("msg", result)
                if check_mode:
                    api.update.assert_not_called()
                else:
                    self.assertEqual(api.update.call_args.kwargs["actions"], actions)

        client, api = client_with([current], updated=current)
        result = self.run_module(FakeModule(params(actions=actions)), client)

        self.assertIn("did not apply", result["msg"])

        client, api = client_with([{**current, "actions": actions}])
        result = self.run_module(FakeModule(params(actions=actions)), client)

        api.update.assert_not_called()
        self.assertFalse(result["changed"])

    def test_other_action_values_compare_requested_keys(self):
        actions = [{"id": "forwarding_url", "value": {"url": "https://example.com"}}]
        listed = [{"id": "forwarding_url", "value": {"url": "https://example.com", "status_code": 301}}]
        client, api = client_with([{"id": "rule", "actions": listed, "status": "active", "targets": TARGETS}])

        result = self.run_module(FakeModule(params(actions=actions)), client)

        api.update.assert_not_called()
        self.assertFalse(result["changed"])

    def test_check_mode_does_not_delete_matching_rule(self):
        client, api = client_with([{"id": "rule", "targets": TARGETS}])

        result = self.run_module(FakeModule(params(state="absent"), check_mode=True), client)

        api.delete.assert_not_called()
        self.assertTrue(result["changed"])

    def test_deletes_matching_rule(self):
        client, api = client_with([{"id": "rule", "targets": TARGETS}], deleted={"id": "rule"})

        result = self.run_module(FakeModule(params(state="absent")), client)

        api.delete.assert_called_once_with(pagerule_id="rule", zone_id="zone")
        self.assertTrue(result["changed"])

    def test_unstored_fields_fail_before_any_request(self):
        constraint = {"operator": "matches", "value": "example.com/*"}
        forwarding = {"url": "https://example.com", "status_code": 301, "bar": 1}
        cases = (
            ({"targets": [{"target": "url", "constraint": constraint, "foo": 1}]}, ["targets[0].foo"]),
            ({"targets": [{"target": "url", "constraint": {**constraint, "qux": 1}}]}, ["targets[0].constraint.qux"]),
            ({"actions": [{"id": "always_use_https", "baz": 1}]}, ["actions[0].baz"]),
            ({"actions": [{"id": "forwarding_url", "value": forwarding}]}, ["actions[0].value.bar"]),
            (
                {
                    "actions": [
                        {"id": "cache_key_fields", "value": {"host": {"resolved": True, "x": 1}, "y": {}}},
                        {"id": "ssl", "value": "strict"},
                    ]
                },
                ["actions[0].value.host.x", "actions[0].value.y"],
            ),
        )
        for updates, unsupported in cases:
            for check_mode in (True, False):
                with self.subTest(updates=updates, check_mode=check_mode):
                    client, api = client_with()

                    result = self.run_module(FakeModule(params(**updates), check_mode=check_mode), client)

                    self.assertEqual(result["unsupported_fields"], unsupported)
                    self.assertEqual(
                        result["msg"], f"Cloudflare does not store these page rule fields: {', '.join(unsupported)}"
                    )
                    api.list.assert_not_called()
                    api.create.assert_not_called()

    def test_value_of_id_only_action_fails_before_any_request(self):
        for action_id in (
            "always_use_https",
            "disable_apps",
            "disable_performance",
            "disable_security",
            "disable_zaraz",
        ):
            for check_mode in (True, False):
                with self.subTest(action_id=action_id, check_mode=check_mode):
                    actions = [{"id": "ssl", "value": "strict"}, {"id": action_id, "value": "on"}]
                    client, api = client_with()

                    result = self.run_module(FakeModule(params(actions=actions), check_mode=check_mode), client)

                    self.assertEqual(result["unsupported_fields"], ["actions[1].value"])
                    self.assertEqual(
                        result["msg"], "Cloudflare does not store these page rule fields: actions[1].value"
                    )
                    api.list.assert_not_called()
                    api.create.assert_not_called()

    def test_action_without_string_id_fails_before_any_request(self):
        for action_id in ({"id": "ssl"}, ["ssl"], 1, "", None):
            for current in ([], [{"id": "rule", "actions": [{"id": "ssl", "value": "strict"}], "targets": TARGETS}]):
                for check_mode in (True, False):
                    with self.subTest(action_id=action_id, existing=bool(current), check_mode=check_mode):
                        actions = [{"id": "ssl", "value": "strict"}, {"id": action_id, "value": "on"}]
                        client, api = client_with(current)

                        result = self.run_module(FakeModule(params(actions=actions), check_mode=check_mode), client)

                        self.assertEqual(result["msg"], "actions[1].id must be a non-empty string")
                        self.assertEqual(result["invalid_fields"], ["actions[1].id"])
                        api.list.assert_not_called()
                        api.create.assert_not_called()
                        api.update.assert_not_called()

    def test_unstored_target_fields_fail_before_delete(self):
        targets = [{**TARGETS[0], "foo": 1}]
        client, api = client_with([{"id": "rule", "targets": TARGETS}])

        result = self.run_module(FakeModule(params(state="absent", targets=targets)), client)

        self.assertEqual(result["unsupported_fields"], ["targets[0].foo"])
        api.list.assert_not_called()
        api.delete.assert_not_called()

    def test_stored_fields_are_sent(self):
        targets = [{"target": "url", "constraint": {"operator": "matches", "value": "example.com/*"}}]
        cache_key = {
            "cookie": {"check_presence": ["a"], "include": ["b"]},
            "header": {"check_presence": ["a"], "exclude": ["b"], "include": ["c"]},
            "host": {"resolved": True},
            "query_string": {"exclude": "*", "include": []},
            "user": {"device_type": True, "geo": False, "lang": True},
        }
        actions = [
            {"id": "cache_key_fields", "value": cache_key},
            {"id": "cache_ttl_by_status", "value": {"404": 30}},
            {"id": "forwarding_url", "value": {"url": "https://example.com", "status_code": 301}},
        ]
        created = {"id": "rule", "actions": actions, "status": "active", "targets": targets}
        client, api = client_with(created=created)

        result = self.run_module(FakeModule(params(actions=actions, targets=targets)), client)

        self.assertNotIn("msg", result)
        api.create.assert_called_once_with(zone_id="zone", actions=actions, status="active", targets=targets)
