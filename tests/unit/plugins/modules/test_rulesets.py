# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from unittest import TestCase
from unittest.mock import Mock, patch

from ansible.module_utils import basic

from ansible_collections.linuxhq.cloudflare.plugins.modules import rulesets
from ansible_collections.linuxhq.cloudflare.tests.unit.plugins.modules.utils import (
    FakeModule,
    ModuleExit,
    ModuleFail,
    status_error,
    timeout_error,
)

PHASE = "http_request_firewall_custom"
RULES = [{"action": "block", "expression": "true", "enabled": True}]
CURRENT = {"id": "ruleset", "name": "default", "kind": "zone", "phase": PHASE, "rules": RULES}


def params(**updates):
    values = {
        "zone_id": "zone",
        "name": "default",
        "rules": None,
        "phase": PHASE,
        "kind": "zone",
        "state": "present",
    }
    values.update(updates)
    return values


def make_client(current=None, created=None, updated=None):
    client = Mock()
    # Retry overrides return the same client so their calls are observable.
    client.with_options.return_value = client
    api = client.rulesets
    if current is None:
        api.phases.get.side_effect = status_error(404)
    else:
        api.phases.get.return_value = current

    api.create.return_value = created
    api.phases.update.return_value = updated
    api.delete.return_value = None
    return client, api


class RulesetsTests(TestCase):
    def run_module(self, module, client):
        with self.assertRaises((ModuleExit, ModuleFail)) as raised:
            rulesets.run(module, client)

        return raised.exception.values

    def test_create_recovers_the_entrypoint_after_a_lost_response(self):
        client, api = make_client()
        api.create.side_effect = timeout_error()
        api.phases.get.side_effect = [status_error(404), CURRENT]

        result = self.run_module(FakeModule(params(rules=RULES)), client)

        client.with_options.assert_called_once_with(max_retries=0)
        api.create.assert_called_once()
        self.assertEqual(result["message"], "Ruleset created")
        self.assertEqual(result["ruleset"], CURRENT)

    def test_unsupported_kinds_fail_before_opening_client(self):
        for kind in ("custom", "managed", "root"):
            for state in ("present", "absent"):
                for check_mode in (False, True):
                    arguments = {
                        **params(kind=kind, state=state),
                        "api_token": "test-token",
                        "_ansible_check_mode": check_mode,
                    }
                    with (
                        self.subTest(kind=kind, state=state, check_mode=check_mode),
                        patch.object(basic, "_load_params", return_value=arguments),
                        patch.object(basic.AnsibleModule, "fail_json", side_effect=FakeModule({}).fail_json),
                        patch.object(rulesets, "cloudflare_client") as client,
                        self.assertRaises(ModuleFail) as raised,
                    ):
                        rulesets.main()

                    self.assertIn("value of kind must be one of", raised.exception.values["msg"])
                    client.assert_not_called()

    def test_null_stored_rules_count_as_no_rules(self):
        current = {key: value for key, value in CURRENT.items() if key != "rules"}
        for rules, changed in (([], False), (RULES, True)):
            client, api = make_client(current, updated={**current, "rules": RULES})
            with self.subTest(rules=rules):
                result = self.run_module(FakeModule(params(rules=rules)), client)

                self.assertEqual(result["changed"], changed)
                self.assertEqual(api.phases.update.called, changed)

    def test_malformed_entrypoint_names_the_zone_and_phase(self):
        for current in (["invalid"], {**CURRENT, "phase": "other"}, {**CURRENT, "name": None}):
            client, _ignored = make_client(current)
            with self.subTest(current=current):
                result = self.run_module(FakeModule(params()), client)

                self.assertIn("ruleset", result["msg"])
                self.assertEqual(result["zone_id"], "zone")
                self.assertEqual(result["phase"], PHASE)

    def test_rejects_sdk_cache_control_spellings_before_any_request(self):
        for key in (
            "max_age",
            "must_revalidate",
            "must_understand",
            "no_cache",
            "no_store",
            "no_transform",
            "proxy_revalidate",
            "s_maxage",
            "stale_if_error",
            "stale_while_revalidate",
        ):
            api_key = key.replace("_", "-")
            rules = [{"action": "set_cache_control", "expression": "true", "action_parameters": {key: {}}}]
            client, api = make_client(CURRENT)
            with self.subTest(key=key):
                result = self.run_module(FakeModule(params(rules=rules)), client)

            api.phases.get.assert_not_called()
            api.phases.update.assert_not_called()
            self.assertEqual(
                result["msg"], f"rules[0].action_parameters.{key} must use the Cloudflare API key {api_key!r}"
            )

    def test_null_sdk_cache_control_spellings_count_as_omitted(self):
        # A key set to null is not sent, so it is not rejected.
        action_parameters = {"cache": True}
        stored = [{"action": "set_cache_settings", "expression": "true", "action_parameters": action_parameters}]
        rules = [
            RULES[0],
            {**stored[0], "action_parameters": {**action_parameters, "max_age": None, "s_maxage": None}},
        ]
        current = {**CURRENT, "rules": [RULES[0], {**stored[0], "enabled": True}]}
        client, api = make_client({**CURRENT, "rules": RULES}, updated=current)

        result = self.run_module(FakeModule(params(rules=rules)), client)

        self.assertNotIn("msg", result)
        self.assertTrue(result["changed"])
        self.assertEqual(api.phases.update.call_args.kwargs["rules"][1]["action_parameters"], action_parameters)

        client, api = make_client(current)

        result = self.run_module(FakeModule(params(rules=rules)), client)

        self.assertFalse(result["changed"])
        api.phases.update.assert_not_called()

    def test_sdk_cache_control_spelling_names_the_rule(self):
        rules = [RULES[0], {"action": "set_cache_control", "expression": "true", "action_parameters": {"max_age": 1}}]
        client, api = make_client(CURRENT)

        result = self.run_module(FakeModule(params(rules=rules)), client)

        api.phases.get.assert_not_called()
        self.assertEqual(result["msg"], "rules[1].action_parameters.max_age must use the Cloudflare API key 'max-age'")

    def test_rejects_empty_skip_parameters_before_any_request(self):
        rules = [
            {"action": "skip", "expression": "true", "action_parameters": {"ruleset": "current"}},
            {"action": "skip", "expression": "true", "action_parameters": {"phases": [], "products": []}},
            {"action": "skip", "expression": "true", "action_parameters": {"rules": {}}},
            {"action": "skip", "expression": "true", "action_parameters": {"rulesets": []}},
        ]
        empty = [
            "rules[1].action_parameters.phases",
            "rules[1].action_parameters.products",
            "rules[2].action_parameters.rules",
            "rules[3].action_parameters.rulesets",
        ]
        for check_mode in (True, False):
            client, api = make_client(CURRENT)
            with self.subTest(check_mode=check_mode):
                result = self.run_module(FakeModule(params(rules=rules), check_mode=check_mode), client)

            api.phases.get.assert_not_called()
            api.phases.update.assert_not_called()
            self.assertEqual(result["empty_fields"], empty)
            self.assertEqual(
                result["msg"],
                f"Cloudflare does not store these empty action parameters: {', '.join(empty)}; omit them instead",
            )

    def test_rejects_skip_parameters_empty_without_their_null_keys_before_any_request(self):
        # Null keys are not sent, so these would be sent empty and dropped by Cloudflare.
        rules = [
            {
                "action": "skip",
                "expression": "true",
                "action_parameters": {"ruleset": "current", "rules": {"id": None}},
            },
            {"action": "skip", "expression": "true", "action_parameters": {"rules": {"id": ["rule"], "other": None}}},
        ]
        empty = ["rules[0].action_parameters.rules"]
        for check_mode in (True, False):
            client, api = make_client(CURRENT)
            with self.subTest(check_mode=check_mode):
                result = self.run_module(FakeModule(params(rules=rules), check_mode=check_mode), client)

            api.phases.get.assert_not_called()
            api.phases.update.assert_not_called()
            self.assertEqual(result["empty_fields"], empty)

    def test_rejects_empty_rule_id_or_ref_before_any_request(self):
        rules = [
            {**RULES[0], "ref": "kept"},
            {**RULES[0], "ref": ""},
            {**RULES[0], "id": "", "ref": ""},
        ]
        empty = ["rules[1].ref", "rules[2].id", "rules[2].ref"]
        for check_mode in (True, False):
            client, api = make_client(CURRENT)
            with self.subTest(check_mode=check_mode):
                result = self.run_module(FakeModule(params(rules=rules), check_mode=check_mode), client)

            api.phases.get.assert_not_called()
            api.phases.update.assert_not_called()
            self.assertEqual(result["empty_fields"], empty)
            self.assertEqual(
                result["msg"],
                f"Cloudflare assigns its own value for these empty rule fields: {', '.join(empty)}; omit them instead",
            )

    def test_accepts_non_empty_skip_parameters(self):
        action_parameters = {
            "phases": ["http_ratelimit"],
            "products": ["waf"],
            "rules": {"ruleset": ["rule"]},
            "rulesets": ["ruleset"],
        }
        rules = [
            {
                "action": "skip",
                "expression": "true",
                "enabled": True,
                "action_parameters": action_parameters,
                "logging": {"enabled": True},
            }
        ]
        client, api = make_client(CURRENT, updated={**CURRENT, "rules": rules})

        result = self.run_module(FakeModule(params(rules=rules)), client)

        api.phases.update.assert_called_once_with(PHASE, zone_id="zone", rules=rules)
        self.assertTrue(result["changed"])

    def test_accepts_api_cache_control_spellings(self):
        rules = [
            {
                "action": "set_cache_control",
                "expression": "true",
                "enabled": True,
                "action_parameters": {"max-age": {"operation": "set", "value": 60}},
            }
        ]
        client, api = make_client(CURRENT, updated={**CURRENT, "rules": rules})

        result = self.run_module(FakeModule(params(rules=rules)), client)

        api.phases.update.assert_called_once_with(PHASE, zone_id="zone", rules=rules)
        self.assertTrue(result["changed"])

    def test_create_without_name_reaches_cloudflare(self):
        # Cloudflare rejects a new ruleset without a name on the only write.
        client, api = make_client()

        self.run_module(FakeModule(params(name=None)), client)

        api.create.assert_called_once()
        self.assertIsNone(api.create.call_args.kwargs["name"])

    def test_check_mode_does_not_create(self):
        client, api = make_client()

        result = self.run_module(FakeModule(params(), check_mode=True), client)

        api.phases.get.assert_called_once_with(PHASE, zone_id="zone")
        api.create.assert_not_called()
        self.assertTrue(result["changed"])

    def test_creates_ruleset(self):
        client, api = make_client(created=CURRENT)

        result = self.run_module(FakeModule(params(rules=RULES)), client)

        api.create.assert_called_once_with(zone_id="zone", kind="zone", name="default", phase=PHASE, rules=RULES)
        self.assertEqual(result["message"], "Ruleset created")
        self.assertEqual(result["ruleset"], CURRENT)

    def test_omitted_rules_preserve_current_rules(self):
        for current in (CURRENT, {key: value for key, value in CURRENT.items() if key != "rules"}):
            client, api = make_client(current)
            with self.subTest(current=current):
                result = self.run_module(FakeModule(params()), client)

            api.phases.update.assert_not_called()
            self.assertFalse(result["changed"])

    def test_rejects_rename_before_update(self):
        client, api = make_client({**CURRENT, "name": "existing"})

        result = self.run_module(FakeModule(params(name="renamed", rules=[])), client)

        api.phases.update.assert_not_called()
        self.assertEqual(result["msg"], "An existing ruleset cannot be renamed")
        self.assertEqual(result["zone_id"], "zone")
        self.assertEqual(result["phase"], PHASE)

    def test_updates_rules_through_phase_entrypoint(self):
        client, api = make_client(CURRENT, updated={**CURRENT, "rules": []})

        result = self.run_module(FakeModule(params(name=None, rules=[])), client)

        api.phases.update.assert_called_once_with(PHASE, zone_id="zone", rules=[])
        self.assertEqual(result["message"], "Ruleset updated")

    def test_rules_update_keeps_current_description(self):
        current = {**CURRENT, "description": "kept"}
        client, api = make_client(current, updated={**current, "rules": []})

        result = self.run_module(FakeModule(params(name=None, rules=[])), client)

        api.phases.update.assert_called_once_with(PHASE, zone_id="zone", rules=[], description="kept")
        self.assertEqual(result["message"], "Ruleset updated")

        client, api = make_client(current)

        result = self.run_module(FakeModule(params(rules=RULES)), client)

        api.phases.update.assert_not_called()
        self.assertFalse(result["changed"])

    def test_deletes_entrypoint_ruleset_by_id(self):
        client, api = make_client(CURRENT)

        result = self.run_module(FakeModule(params(state="absent")), client)

        api.delete.assert_called_once_with("ruleset", zone_id="zone")
        self.assertTrue(result["changed"])

    def test_absent_refuses_to_delete_a_ruleset_with_another_name(self):
        for check_mode in (False, True):
            client, api = make_client({**CURRENT, "name": "existing"})
            with self.subTest(check_mode=check_mode):
                result = self.run_module(
                    FakeModule(params(name="other", state="absent"), check_mode=check_mode), client
                )

                api.delete.assert_not_called()
                self.assertEqual(result["msg"], "An existing ruleset with a different name cannot be deleted")
                self.assertEqual(result["ruleset"], {**CURRENT, "name": "existing"})
                self.assertEqual(result["zone_id"], "zone")
                self.assertEqual(result["phase"], PHASE)

    def test_absent_without_name_deletes_the_phase_entrypoint(self):
        client, api = make_client({**CURRENT, "name": "existing"})

        result = self.run_module(FakeModule(params(name=None, state="absent")), client)

        api.delete.assert_called_once_with("ruleset", zone_id="zone")
        self.assertTrue(result["changed"])

    def test_absent_ruleset_is_unchanged(self):
        client, api = make_client()

        result = self.run_module(FakeModule(params(state="absent")), client)

        api.delete.assert_not_called()
        self.assertFalse(result["changed"])

    def test_rejects_a_response_for_the_wrong_phase(self):
        client, _ignored = make_client(created={**CURRENT, "phase": "http_request_transform"})

        result = self.run_module(FakeModule(params()), client)

        self.assertEqual(result["msg"], "Cloudflare API returned the wrong ruleset")

    def test_rejects_update_response_with_wrong_rules(self):
        client, _ignored = make_client({**CURRENT, "rules": []}, updated={**CURRENT, "rules": []})

        result = self.run_module(FakeModule(params(rules=RULES)), client)

        self.assertIn("did not apply", result["msg"])

    def test_created_ruleset_in_another_phase_reports_the_write(self):
        created = {**CURRENT, "phase": "http_request_late_transform"}
        client, api = make_client(created=created)

        result = self.run_module(FakeModule(params(rules=RULES)), client)

        api.create.assert_called_once()
        self.assertEqual(result["msg"], "Cloudflare API returned the wrong ruleset")
        self.assertTrue(result["changed"])
        self.assertEqual(result["ruleset"], created)
        self.assertEqual(result["resource_id"], "ruleset")
        self.assertEqual(result["zone_id"], "zone")


class RulesetMalformedRulesTests(TestCase):
    def run_module(self, module, client):
        with self.assertRaises((ModuleExit, ModuleFail)) as raised:
            rulesets.run(module, client)

        return raised.exception.values

    def test_malformed_current_rules_fail_before_any_change(self):
        cases = (
            ("rule", "ruleset"),
            ({"action": "block"}, "ruleset"),
            ([None], "ruleset rule"),
            (["rule"], "ruleset rule"),
        )
        for rules, name in cases:
            for desired in (None, RULES):
                client, api = make_client({**CURRENT, "rules": rules})
                with self.subTest(rules=rules, desired=desired):
                    result = self.run_module(FakeModule(params(rules=desired)), client)

                    api.phases.update.assert_not_called()
                    self.assertEqual(
                        result,
                        {"msg": f"Cloudflare API returned malformed {name} data", "zone_id": "zone", "phase": PHASE},
                    )

    def test_null_rules_count_as_no_rules(self):
        client, api = make_client({**CURRENT, "rules": None})

        result = self.run_module(FakeModule(params(rules=[])), client)

        api.phases.update.assert_not_called()
        self.assertFalse(result["changed"])

    def test_malformed_written_rules_report_the_change(self):
        for rules, name in (("rule", "ruleset"), ([None], "ruleset rule")):
            written = {**CURRENT, "rules": rules}
            for write in ("create", "update"):
                if write == "create":
                    client, api = make_client(created=written)
                    sent = api.create
                else:
                    client, api = make_client({**CURRENT, "rules": []}, updated=written)
                    sent = api.phases.update

                with self.subTest(rules=rules, write=write):
                    result = self.run_module(FakeModule(params(rules=RULES)), client)

                    sent.assert_called_once()
                    self.assertEqual(result["msg"], f"Cloudflare API returned malformed {name} data")
                    self.assertTrue(result["changed"])
                    self.assertEqual(result["ruleset"], written)
                    self.assertEqual(result["resource_id"], "ruleset")
                    self.assertEqual(result["zone_id"], "zone")


HEADER_RULE = {
    "enabled": True,
    "action": "rewrite",
    "expression": "true",
    "action_parameters": {
        "headers": {
            "X-Keep": {"operation": "set", "value": "yes"},
            "Authorization": {"operation": "set", "value": "Bearer secret"},
        }
    },
}


class RulesetHeaderTests(TestCase):
    def run_module(self, module, client):
        with self.assertRaises((ModuleExit, ModuleFail)) as raised:
            rulesets.run(module, client)

        return raised.exception.values

    def test_removing_a_header_is_a_change(self):
        current = {**CURRENT, "rules": [HEADER_RULE]}
        desired = [{**HEADER_RULE, "action_parameters": {"headers": {"X-Keep": {"operation": "set", "value": "yes"}}}}]
        client, api = make_client(current, updated={**CURRENT, "rules": desired})

        result = self.run_module(FakeModule(params(rules=desired)), client)

        api.phases.update.assert_called_once()
        self.assertTrue(result["changed"])

    def test_returns_header_values(self):
        client, api = make_client({**CURRENT, "rules": [HEADER_RULE]})

        result = self.run_module(FakeModule(params(rules=[HEADER_RULE])), client)

        api.phases.update.assert_not_called()
        headers = result["ruleset"]["rules"][0]["action_parameters"]["headers"]
        self.assertEqual(headers, HEADER_RULE["action_parameters"]["headers"])

    def test_removing_a_skip_rule_entry_is_a_change(self):
        skip = {
            "enabled": True,
            "action": "skip",
            "expression": "true",
            "action_parameters": {"rules": {"a": ["1"], "b": ["2"]}},
        }
        desired = [{**skip, "action_parameters": {"rules": {"a": ["1"]}}}]
        client, api = make_client({**CURRENT, "rules": [skip]}, updated={**CURRENT, "rules": desired})

        result = self.run_module(FakeModule(params(rules=desired)), client)

        api.phases.update.assert_called_once()
        self.assertTrue(result["changed"])

    def test_removing_a_nested_action_parameter_is_a_change(self):
        # Cloudflare stores action_parameters exactly as sent and an update
        # replaces them, so a key the request omits at any level is removed.
        cases = (
            ({"cache": True, "edge_ttl": {"mode": "override_origin", "default": 60}}, {"cache": True}),
            (
                {"cache": True, "edge_ttl": {"mode": "override_origin", "default": 60}},
                {"cache": True, "edge_ttl": {"mode": "override_origin"}},
            ),
            ({"phases": ["http_ratelimit"], "products": ["waf"]}, {"phases": ["http_ratelimit"]}),
        )
        for stored, requested in cases:
            with self.subTest(requested=requested):
                rule = {"enabled": True, "action": "set_cache_settings", "expression": "true"}
                desired = [{**rule, "action_parameters": requested}]
                client, api = make_client(
                    {**CURRENT, "rules": [{**rule, "action_parameters": stored}]},
                    updated={**CURRENT, "rules": desired},
                )

                result = self.run_module(FakeModule(params(rules=desired)), client)

                api.phases.update.assert_called_once()
                self.assertTrue(result["changed"])
                self.assertNotIn("msg", result)

    def test_execute_rule_matches_the_version_cloudflare_assigns(self):
        # Cloudflare stores an execute rule without a version as version latest.
        rule = {"enabled": True, "action": "execute", "expression": "true"}
        requested = [{**rule, "action_parameters": {"id": "managed"}}]
        stored = [{**rule, "action_parameters": {"id": "managed", "version": "latest"}}]
        client, api = make_client({**CURRENT, "rules": stored})

        result = self.run_module(FakeModule(params(rules=requested)), client)

        api.phases.update.assert_not_called()
        self.assertFalse(result["changed"])

        for version in ("1", None):
            with self.subTest(version=version):
                pinned = [{**rule, "action_parameters": {"id": "managed", "version": "1"}}]
                client, api = make_client({**CURRENT, "rules": pinned}, updated={**CURRENT, "rules": stored})
                desired = requested if version is None else pinned

                result = self.run_module(FakeModule(params(rules=desired)), client)

                self.assertEqual(api.phases.update.called, version is None)

    def test_kept_nested_action_parameter_fails_postcondition(self):
        rule = {"enabled": True, "action": "set_cache_settings", "expression": "true"}
        stored = [{**rule, "action_parameters": {"cache": True, "edge_ttl": {"mode": "respect_origin"}}}]
        desired = [{**rule, "action_parameters": {"cache": True}}]
        client, _ignored = make_client({**CURRENT, "rules": stored}, updated={**CURRENT, "rules": stored})

        result = self.run_module(FakeModule(params(rules=desired)), client)

        self.assertIn("did not apply", result["msg"])

    def test_rule_without_enabled_does_not_match_a_disabled_rule(self):
        disabled = {"ref": "keep", "action": "block", "expression": "true", "enabled": False}
        requested = {"ref": "keep", "action": "block", "expression": "true"}
        client, api = make_client(
            {**CURRENT, "rules": [disabled]}, updated={**CURRENT, "rules": [{**requested, "enabled": True}]}
        )

        result = self.run_module(FakeModule(params(rules=[requested])), client)

        self.assertEqual(api.phases.update.call_args.kwargs["rules"], [{"enabled": True, **requested}])
        self.assertTrue(result["changed"])


ASSIGNED = {"id": "rule-id", "ref": "rule-id", "version": "1", "last_updated": "2026-11-13T00:00:00Z"}


class RulesetRuleFieldTests(TestCase):
    def run_module(self, module, client):
        with self.assertRaises((ModuleExit, ModuleFail)) as raised:
            rulesets.run(module, client)

        return raised.exception.values

    def test_removed_rule_field_is_a_change(self):
        requested = {"action": "skip", "expression": "true", "action_parameters": {"ruleset": "current"}}
        stored = {**ASSIGNED, **requested, "enabled": True, "logging": {"enabled": True}}
        for field, value in (("description", "removed"), ("logging", {"enabled": False}), ("ratelimit", {})):
            current = {**CURRENT, "rules": [{**stored, field: value}]}
            for check_mode in (True, False):
                with self.subTest(field=field, check_mode=check_mode):
                    client, api = make_client(current, updated={**CURRENT, "rules": [stored]})

                    result = self.run_module(FakeModule(params(rules=[requested]), check_mode=check_mode), client)

                    self.assertTrue(result["changed"])
                    self.assertNotIn("msg", result)
                    if check_mode:
                        api.phases.update.assert_not_called()
                    else:
                        api.phases.update.assert_called_once_with(
                            PHASE, zone_id="zone", rules=[{"enabled": True, **requested}]
                        )

    def test_assigned_fields_and_action_defaults_are_unchanged(self):
        for requested, stored in (
            (
                {"action": "skip", "expression": "true", "action_parameters": {"ruleset": "current"}},
                {"enabled": True, "logging": {"enabled": True}},
            ),
            ({"action": "block", "expression": "true", "description": "kept"}, {"enabled": True}),
        ):
            current = {**CURRENT, "rules": [{**ASSIGNED, **requested, **stored}]}
            with self.subTest(action=requested["action"]):
                client, api = make_client(current)

                result = self.run_module(FakeModule(params(rules=[requested])), client)

                api.phases.update.assert_not_called()
                self.assertFalse(result["changed"])
                self.assertEqual(result["ruleset"], current)

    def test_logging_default_applies_only_to_skip_rules(self):
        requested = {"action": "block", "expression": "true"}
        current = {**CURRENT, "rules": [{**ASSIGNED, **requested, "enabled": True, "logging": {"enabled": True}}]}
        client, _ignored = make_client(current)

        result = self.run_module(FakeModule(params(rules=[requested]), check_mode=True), client)

        self.assertTrue(result["changed"])

    def test_requested_assigned_field_is_compared(self):
        requested = {"action": "block", "expression": "true", "ref": "mine"}
        current = {**CURRENT, "rules": [{**ASSIGNED, "action": "block", "expression": "true", "enabled": True}]}
        client, _ignored = make_client(current)

        result = self.run_module(FakeModule(params(rules=[requested]), check_mode=True), client)

        self.assertTrue(result["changed"])

    def test_field_kept_after_update_fails_postcondition(self):
        requested = {"action": "block", "expression": "true"}
        kept = {**ASSIGNED, **requested, "enabled": True, "description": "kept"}
        client, _ignored = make_client({**CURRENT, "rules": [kept]}, updated={**CURRENT, "rules": [kept]})

        result = self.run_module(FakeModule(params(rules=[requested])), client)

        self.assertTrue(result["msg"].startswith("Cloudflare did not apply the requested ruleset: rules requested "))
        self.assertEqual([difference["field"] for difference in result["differences"]], ["rules"])

    def test_created_ruleset_with_assigned_fields_and_defaults_is_applied(self):
        requested = {"action": "skip", "expression": "true", "action_parameters": {"ruleset": "current"}}
        created = {
            **CURRENT,
            "rules": [{**ASSIGNED, **requested, "enabled": True, "logging": {"enabled": True}}],
        }
        client, api = make_client(created=created)

        result = self.run_module(FakeModule(params(rules=[requested])), client)

        api.create.assert_called_once()
        self.assertTrue(result["changed"])
        self.assertEqual(result["ruleset"], created)

    def test_empty_fields_match_rules_cloudflare_stored_without_them(self):
        stored = {**ASSIGNED, "action": "block", "expression": "true", "enabled": True}
        for field, value in (("description", ""), ("action_parameters", {})):
            requested = {"action": "block", "expression": "true", field: value}
            with self.subTest(field=field, state="created"):
                client, api = make_client(created={**CURRENT, "rules": [stored]})

                result = self.run_module(FakeModule(params(rules=[requested])), client)

                api.create.assert_called_once()
                self.assertTrue(result["changed"])
                self.assertNotIn("msg", result)

            with self.subTest(field=field, state="current"):
                client, api = make_client({**CURRENT, "rules": [stored]})

                result = self.run_module(FakeModule(params(rules=[requested])), client)

                api.phases.update.assert_not_called()
                self.assertFalse(result["changed"])

    def test_description_on_rule_without_one_is_a_change(self):
        requested = {"action": "block", "expression": "true", "description": "new"}
        current = {**CURRENT, "rules": [{**ASSIGNED, "action": "block", "expression": "true", "enabled": True}]}
        client, _ignored = make_client(current)

        result = self.run_module(FakeModule(params(rules=[requested]), check_mode=True), client)

        self.assertTrue(result["changed"])

    def test_null_fields_match_rules_cloudflare_stored_without_them(self):
        stored = {**ASSIGNED, "action": "block", "expression": "true", "enabled": True}
        for field in ("description", "action_parameters"):
            requested = {"action": "block", "expression": "true", field: None}
            with self.subTest(field=field, state="created"):
                client, api = make_client(created={**CURRENT, "rules": [stored]})

                result = self.run_module(FakeModule(params(rules=[requested])), client)

                api.create.assert_called_once()
                self.assertTrue(result["changed"])
                self.assertNotIn("msg", result)

            with self.subTest(field=field, state="current"):
                client, api = make_client({**CURRENT, "rules": [stored]})

                result = self.run_module(FakeModule(params(rules=[requested])), client)

                api.phases.update.assert_not_called()
                self.assertFalse(result["changed"])

    def test_null_rule_fields_count_as_omitted(self):
        block = {"action": "block", "expression": "true"}
        skip = {"action": "skip", "expression": "true", "action_parameters": {"ruleset": "current"}}
        for field, requested, stored in (
            ("enabled", block, {**ASSIGNED, **block, "enabled": True}),
            ("logging", skip, {**ASSIGNED, **skip, "enabled": True, "logging": {"enabled": True}}),
            ("ref", block, {**ASSIGNED, **block, "enabled": True}),
            ("id", block, {**ASSIGNED, **block, "enabled": True}),
        ):
            with self.subTest(field=field, state="created"):
                client, api = make_client(created={**CURRENT, "rules": [stored]})

                result = self.run_module(FakeModule(params(rules=[{**requested, field: None}])), client)

                self.assertEqual(api.create.call_args.kwargs["rules"], [{"enabled": True, **requested}])
                self.assertTrue(result["changed"])
                self.assertNotIn("msg", result)

            with self.subTest(field=field, state="current"):
                client, api = make_client({**CURRENT, "rules": [stored]})

                result = self.run_module(FakeModule(params(rules=[{**requested, field: None}])), client)

                api.phases.update.assert_not_called()
                self.assertFalse(result["changed"])

    def test_disabled_rule_is_a_change_from_an_enabled_rule(self):
        requested = {"action": "block", "expression": "true", "enabled": False}
        current = {**CURRENT, "rules": [{**ASSIGNED, "action": "block", "expression": "true", "enabled": True}]}
        client, _ignored = make_client(current)

        result = self.run_module(FakeModule(params(rules=[requested]), check_mode=True), client)

        self.assertTrue(result["changed"])

    def test_removing_a_nested_rule_key_is_a_change(self):
        ratelimit = {"characteristics": ["ip.src", "cf.colo.id"], "period": 10, "requests_per_period": 5}
        requested = {"action": "block", "expression": "true", "ratelimit": ratelimit}
        stored = {**ASSIGNED, **requested, "enabled": True, "ratelimit": {**ratelimit, "requests_to_origin": True}}
        client, api = make_client({**CURRENT, "rules": [stored]})

        result = self.run_module(FakeModule(params(rules=[requested]), check_mode=True), client)

        self.assertTrue(result["changed"])
        api.phases.update.assert_not_called()

    def test_requests_to_origin_false_matches_a_rule_without_it(self):
        ratelimit = {"characteristics": ["ip.src", "cf.colo.id"], "period": 10, "requests_per_period": 5}
        requested = {"action": "block", "expression": "true", "ratelimit": {**ratelimit, "requests_to_origin": False}}
        # Cloudflare drops requests_to_origin=false.
        stored = {**ASSIGNED, **requested, "enabled": True, "ratelimit": ratelimit}
        with self.subTest(state="updated"):
            current = {**CURRENT, "rules": [{**stored, "ratelimit": {**ratelimit, "requests_to_origin": True}}]}
            client, api = make_client(current, updated={**CURRENT, "rules": [stored]})

            result = self.run_module(FakeModule(params(rules=[requested])), client)

            api.phases.update.assert_called_once()
            self.assertTrue(result["changed"])
            self.assertNotIn("msg", result)

        with self.subTest(state="current"):
            client, api = make_client({**CURRENT, "rules": [stored]})

            result = self.run_module(FakeModule(params(rules=[requested])), client)

            api.phases.update.assert_not_called()
            self.assertFalse(result["changed"])

        with self.subTest(state="true requested"):
            client, _ignored = make_client({**CURRENT, "rules": [stored]})
            rule = {**requested, "ratelimit": {**ratelimit, "requests_to_origin": True}}

            result = self.run_module(FakeModule(params(rules=[rule]), check_mode=True), client)

            self.assertTrue(result["changed"])

    def test_nested_null_rule_fields_are_not_sent(self):
        nested = {
            "action_parameters": {"headers": {"X-Keep": {"operation": "set", "value": "yes", "expression": None}}},
            "ratelimit": None,
        }
        requested = {"action": "rewrite", "expression": "true", **nested}
        sent = {
            "enabled": True,
            "action": "rewrite",
            "expression": "true",
            "action_parameters": {"headers": {"X-Keep": {"operation": "set", "value": "yes"}}},
        }
        written = {**CURRENT, "rules": [{**ASSIGNED, **sent}]}
        for current in (None, CURRENT):
            with self.subTest(current=current):
                client, api = make_client(current, created=written, updated=written)

                result = self.run_module(FakeModule(params(rules=[requested])), client)

                call = api.phases.update if current else api.create
                self.assertEqual(call.call_args.kwargs["rules"], [sent])
                self.assertNotIn("msg", result)
                self.assertTrue(result["changed"])

            with self.subTest(current=current, rerun=True):
                client, api = make_client(written)

                result = self.run_module(FakeModule(params(rules=[requested])), client)

                api.phases.update.assert_not_called()
                self.assertFalse(result["changed"])


UNHASHABLE_ACTION = {"not": "a string"}


class UnhashableActionTests(TestCase):
    """A rule whose action is not a string has no action defaults."""

    def run_module(self, module, client):
        with self.assertRaises((ModuleExit, ModuleFail)) as raised:
            rulesets.run(module, client)

        return raised.exception.values

    def test_omitted_rules_keep_a_stored_rule_with_an_unhashable_action(self):
        for action in (UNHASHABLE_ACTION, ["block"]):
            for check_mode in (False, True):
                stored = {**CURRENT, "rules": [{**RULES[0], "action": action}]}
                client, api = make_client(stored)
                with self.subTest(action=action, check_mode=check_mode):
                    result = self.run_module(FakeModule(params(), check_mode=check_mode), client)

                    self.assertNotIn("msg", result)
                    self.assertFalse(result["changed"])
                    api.phases.update.assert_not_called()

    def test_removing_a_stored_rule_with_an_unhashable_action_is_a_change(self):
        stored = {**CURRENT, "rules": [*RULES, {**RULES[0], "action": UNHASHABLE_ACTION, "description": "extra"}]}
        for check_mode in (False, True):
            client, api = make_client(stored, updated=CURRENT)
            with self.subTest(check_mode=check_mode):
                result = self.run_module(FakeModule(params(rules=RULES), check_mode=check_mode), client)

                self.assertNotIn("msg", result)
                self.assertTrue(result["changed"])
                self.assertEqual(api.phases.update.call_count, 0 if check_mode else 1)

    def test_created_rule_with_an_unhashable_action_reports_the_change(self):
        # Fields the request omits are compared with the action's defaults.
        rule = {**RULES[0], "action": UNHASHABLE_ACTION, "logging": {"enabled": True}, "action_parameters": {}}
        created = {**CURRENT, "rules": [rule]}
        client, api = make_client(created=created)

        result = self.run_module(FakeModule(params(rules=RULES)), client)

        api.create.assert_called_once()
        self.assertIn("did not apply", result["msg"])
        self.assertTrue(result["changed"])
        self.assertEqual(result["ruleset"], created)
