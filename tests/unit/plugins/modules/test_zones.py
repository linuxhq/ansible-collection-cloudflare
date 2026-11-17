# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from unittest import TestCase
from unittest.mock import Mock, call

import cloudflare

from ansible_collections.linuxhq.cloudflare.plugins.modules import zones
from ansible_collections.linuxhq.cloudflare.tests.unit.plugins.modules.utils import (
    FakeModule,
    ModuleExit,
    ModuleFail,
    status_error,
    timeout_error,
)

ZONE = {"id": "zone", "name": "example.com", "type": "full"}


def params(**updates):
    values = {
        "name": "example.com",
        "account_id": "account",
        "type": None,
        "vanity_name_servers": None,
        "settings": None,
        "state": "present",
    }
    values.update(updates)
    return values


def client_with(zones_found=(), created=None, edited=(), setting=None, edited_setting=None, deleted=None):
    client = Mock()
    # Retry overrides return the same client so their calls are observable.
    client.with_options.return_value = client
    client.zones.list.return_value = list(zones_found)
    client.zones.create.return_value = created
    client.zones.edit.side_effect = list(edited)
    client.zones.delete.return_value = deleted
    client.zones.settings.get.return_value = setting
    client.zones.settings.edit.return_value = edited_setting
    return client


class ZonesTests(TestCase):
    def run_module(self, module, client):
        with self.assertRaises((ModuleExit, ModuleFail)) as raised:
            zones.run(module, client)

        return raised.exception.values

    def test_create_recovers_the_zone_after_a_lost_response(self):
        recovered = {**ZONE, "account": {"id": "account"}}
        client = client_with()
        client.zones.create.side_effect = timeout_error()
        client.zones.list.side_effect = [[], [recovered]]

        result = self.run_module(FakeModule(params()), client)

        client.with_options.assert_called_once_with(max_retries=0)
        client.zones.create.assert_called_once()
        self.assertEqual(client.zones.list.call_args.kwargs, {"name": "example.com", "account": {"id": "account"}})
        self.assertEqual(result["message"], "Zone created")
        self.assertEqual(result["zone"], recovered)

    def test_setting_scalar_values_match_recursively(self):
        self.assertTrue(
            zones.setting_matches(
                {"enabled": "true", "ports": ["80", "443"], "ratio": "1.5"},
                {"enabled": True, "ports": [80, 443], "ratio": 1.5},
            )
        )
        self.assertFalse(zones.setting_matches({"ports": ["80"]}, {"ports": [80, 443]}))

    def test_whole_number_float_matches_string_setting(self):
        for current in ("1.0", "1"):
            with self.subTest(current=current):
                self.assertTrue(zones.setting_matches(current, 1.0))

        self.assertTrue(zones.setting_matches("1.3", 1.3))
        self.assertFalse(zones.setting_matches("1.2", 1.0))

    def test_integral_float_settings_match_integers(self):
        self.assertTrue(zones.setting_matches(14400.0, 14400))
        self.assertFalse(zones.setting_matches(14400.5, 14400))

    def test_partial_nested_setting_matches(self):
        current = {"strict_transport_security": {"enabled": False, "max_age": 0, "preload": False}}
        self.assertTrue(zones.setting_matches(current, {"strict_transport_security": {"enabled": False}}))
        self.assertFalse(zones.setting_matches(current, {"strict_transport_security": {"enabled": True}}))

    def test_lookup_is_scoped_to_account(self):
        for account_id, expected in (
            ("account", {"name": "example.com", "account": {"id": "account"}}),
            (None, {"name": "example.com"}),
        ):
            with self.subTest(account_id=account_id):
                client = client_with([ZONE])
                self.run_module(FakeModule(params(account_id=account_id)), client)

                client.zones.list.assert_called_once_with(**expected)

    def test_creates_zone_without_account(self):
        # Cloudflare creates the zone in the account of the API token.
        client = client_with(created=ZONE)

        result = self.run_module(FakeModule(params(account_id=None)), client)

        client.zones.list.assert_called_once_with(name="example.com")
        client.zones.create.assert_called_once_with(account=cloudflare.omit, name="example.com", type="full")
        self.assertTrue(result["changed"])

    def test_padded_setting_id_reaches_cloudflare(self):
        # Cloudflare rejects it when the setting is read, before any write.
        client = client_with([ZONE], setting={"id": " ssl", "value": "full"})

        self.run_module(FakeModule(params(settings=[{"id": " ssl", "value": "full"}])), client)

        client.zones.settings.get.assert_called_once_with(setting_id=" ssl", zone_id="zone")

    def test_padded_setting_id_fails_before_creating_a_zone(self):
        client = client_with(created=ZONE)

        result = self.run_module(FakeModule(params(settings=[{"id": " ssl", "value": "full"}])), client)

        client.zones.create.assert_not_called()
        self.assertEqual(result["msg"], "Zone setting ids must not contain leading or trailing whitespace")

    def test_rejects_invalid_setting_before_lookup(self):
        client = client_with()

        result = self.run_module(FakeModule(params(settings=[{"id": "", "value": "on"}])), client)

        client.zones.list.assert_not_called()
        self.assertEqual(result["msg"], "Each zone setting requires a unique valid id")

    def test_rejects_dot_segment_setting_id_before_any_request(self):
        for setting_id in (".", ".."):
            for check_mode in (True, False):
                with self.subTest(setting_id=setting_id, check_mode=check_mode):
                    client = client_with([ZONE])

                    result = self.run_module(
                        FakeModule(params(settings=[{"id": setting_id, "value": "on"}]), check_mode=check_mode),
                        client,
                    )

                    self.assertEqual(result["msg"], "Each zone setting id must not be '.' or '..'")
                    self.assertEqual(result["setting"], setting_id)
                    self.assertEqual(client.mock_calls, [])

    def test_rejects_duplicate_settings_before_lookup(self):
        client = client_with()
        settings = [{"id": "ssl", "value": "full"}, {"id": "ssl", "value": "strict"}]

        with self.assertRaises(ModuleFail):
            zones.run(FakeModule(params(settings=settings)), client)

        client.zones.list.assert_not_called()

    def test_unstored_setting_value_fields_fail_before_any_request(self):
        hsts = {"enabled": True, "max_age": 0, "foo": 1}
        settings = [
            {"id": "security_header", "value": {"strict_transport_security": hsts, "bar": 1}},
            {"id": "nel", "value": {"enabled": True, "foo": 1}},
            {"id": "aegis", "value": {"enabled": False, "pool_id": "p", "foo": 1}},
            {"id": "automatic_platform_optimization", "value": {"enabled": False, "foo": 1}},
            {"id": "ciphers", "value": ["ECDHE-RSA-AES128-GCM-SHA256"]},
            {"id": "other_object", "value": {"foo": 1}},
        ]
        unsupported = [
            "settings[0].value.strict_transport_security.foo",
            "settings[0].value.bar",
            "settings[1].value.foo",
            "settings[2].value.foo",
        ]
        for check_mode in (True, False):
            with self.subTest(check_mode=check_mode):
                client = client_with([ZONE])

                result = self.run_module(FakeModule(params(settings=settings), check_mode=check_mode), client)

                self.assertEqual(result["unsupported_fields"], unsupported)
                self.assertEqual(
                    result["msg"], f"Cloudflare does not store these zone setting fields: {', '.join(unsupported)}"
                )
                client.zones.list.assert_not_called()
                client.zones.settings.get.assert_not_called()
                client.zones.settings.edit.assert_not_called()

    def test_empty_setting_value_mappings_fail_before_any_request(self):
        settings = [
            {"id": "nel", "value": {}},
            {"id": "security_header", "value": {"strict_transport_security": {}}},
            {"id": "aegis", "value": {"enabled": True}},
            {"id": "other_object", "value": {}},
        ]
        empty = ["settings[0].value", "settings[1].value.strict_transport_security"]
        for check_mode in (True, False):
            with self.subTest(check_mode=check_mode):
                client = client_with([ZONE])

                result = self.run_module(FakeModule(params(settings=settings), check_mode=check_mode), client)

                self.assertEqual(result["empty_fields"], empty)
                self.assertEqual(
                    result["msg"], f"Cloudflare does not apply these empty zone setting values: {', '.join(empty)}"
                )
                client.zones.list.assert_not_called()
                client.zones.settings.get.assert_not_called()
                client.zones.settings.edit.assert_not_called()

    def test_null_setting_values_fail_before_any_request(self):
        settings = [
            {"id": "nel", "value": {"enabled": None}},
            {"id": "min_tls_version", "value": None},
            {"id": "security_header", "value": {"strict_transport_security": {"enabled": True, "max_age": None}}},
            {"id": "aegis", "value": {"enabled": True, "pool_id": None}},
            {"id": "automatic_platform_optimization", "value": {"enabled": True, "hostnames": ["a", None]}},
            {"id": "other_object", "value": {"foo": None}},
        ]
        null = [
            "settings[0].value.enabled",
            "settings[1].value",
            "settings[2].value.strict_transport_security.max_age",
        ]
        for check_mode in (True, False):
            with self.subTest(check_mode=check_mode):
                client = client_with([ZONE])

                result = self.run_module(FakeModule(params(settings=settings), check_mode=check_mode), client)

                self.assertEqual(result["null_fields"], null)
                self.assertEqual(
                    result["msg"], f"Cloudflare does not apply these null zone setting values: {', '.join(null)}"
                )
                client.zones.list.assert_not_called()
                client.zones.settings.get.assert_not_called()
                client.zones.settings.edit.assert_not_called()

    def test_null_unknown_setting_fields_are_ignored(self):
        # Cloudflare drops a null unknown field (nel foo: null is stored as {"enabled": true}).
        value = {"enabled": True, "foo": None}
        client = client_with([ZONE], setting={"id": "nel", "value": {"enabled": True}})

        result = self.run_module(FakeModule(params(settings=[{"id": "nel", "value": value}])), client)

        self.assertNotIn("msg", result)
        self.assertFalse(result["changed"])

    def test_all_null_mapping_setting_values_are_not_empty(self):
        # Cloudflare accepts aegis {pool_id: null} and does not store pool_id.
        client = client_with([ZONE], setting={"id": "aegis", "value": {"enabled": False}})

        result = self.run_module(FakeModule(params(settings=[{"id": "aegis", "value": {"pool_id": None}}])), client)

        self.assertNotIn("msg", result)
        self.assertFalse(result["changed"])
        client.zones.settings.edit.assert_not_called()

    def test_null_security_header_policy_fails_before_any_request(self):
        settings = [{"id": "security_header", "value": {"strict_transport_security": None}}]
        for check_mode in (True, False):
            with self.subTest(check_mode=check_mode):
                client = client_with([ZONE])

                result = self.run_module(FakeModule(params(settings=settings), check_mode=check_mode), client)

                self.assertEqual(result["null_fields"], ["settings[0].value.strict_transport_security"])
                client.zones.list.assert_not_called()
                client.zones.settings.edit.assert_not_called()

    def test_non_mapping_object_setting_values_fail_before_any_request(self):
        settings = [
            {"id": "min_tls_version", "value": "1.2"},
            {"id": "nel", "value": "on"},
            {"id": "aegis", "value": True},
            {"id": "automatic_platform_optimization", "value": ["enabled"]},
            {"id": "security_header", "value": {"strict_transport_security": True}},
            {"id": "other_object", "value": "on"},
        ]
        invalid = [
            "settings[1].value",
            "settings[2].value",
            "settings[4].value.strict_transport_security",
        ]
        for check_mode in (True, False):
            with self.subTest(check_mode=check_mode):
                client = client_with([ZONE])

                result = self.run_module(FakeModule(params(settings=settings), check_mode=check_mode), client)

                self.assertEqual(result["invalid_fields"], invalid)
                self.assertEqual(result["msg"], f"These zone setting values must be mappings: {', '.join(invalid)}")
                client.zones.list.assert_not_called()
                client.zones.settings.get.assert_not_called()
                client.zones.settings.edit.assert_not_called()

    def test_stored_setting_value_fields_are_sent(self):
        value = {
            "strict_transport_security": dict.fromkeys(
                ("enabled", "include_subdomains", "max_age", "nosniff", "preload"), True
            )
        }
        updated = {"id": "security_header", "value": value}
        client = client_with([ZONE], setting={"id": "security_header", "value": {}}, edited_setting=updated)

        result = self.run_module(FakeModule(params(settings=[{"id": "security_header", "value": value}])), client)

        self.assertNotIn("msg", result)
        client.zones.settings.edit.assert_called_once_with(setting_id="security_header", zone_id="zone", value=value)

    def test_check_mode_does_not_create(self):
        client = client_with()

        result = self.run_module(FakeModule(params(), check_mode=True), client)

        client.zones.create.assert_not_called()
        self.assertTrue(result["changed"])

    def test_creates_zone_with_default_type(self):
        created = {**ZONE, "account": {"id": "account"}}
        client = client_with(created=created)

        result = self.run_module(FakeModule(params()), client)

        client.zones.create.assert_called_once_with(account={"id": "account"}, name="example.com", type="full")
        client.zones.edit.assert_not_called()
        self.assertTrue(result["changed"])
        self.assertEqual(result["message"], "Zone created")
        self.assertEqual(result["zone"], created)

    def test_creates_zone_then_sets_vanity_name_servers(self):
        created = {**ZONE, "account": {"id": "account"}}
        updated = {**created, "vanity_name_servers": ["ns1.example.com"]}
        client = client_with(created=created, edited=[updated])

        result = self.run_module(FakeModule(params(vanity_name_servers=["ns1.example.com"])), client)

        client.zones.edit.assert_called_once_with(zone_id="zone", vanity_name_servers=["ns1.example.com"])
        self.assertEqual(result["zone"], updated)

    def test_rejects_create_response_for_wrong_account(self):
        client = client_with(created={**ZONE, "account": {"id": "other"}})

        result = self.run_module(FakeModule(params()), client)

        self.assertIn("did not apply", result["msg"])

    def test_not_applied_after_create_reports_the_created_zone(self):
        created = {**ZONE, "account": {"id": "other"}}
        client = client_with(created=created)

        result = self.run_module(FakeModule(params()), client)

        self.assertIn("did not apply", result["msg"])
        self.assertTrue(result["changed"])
        self.assertEqual(result["zone_id"], "zone")
        self.assertEqual(result["zone"], created)

    def test_not_applied_after_update_names_the_zone(self):
        client = client_with([ZONE], edited=[ZONE])

        result = self.run_module(FakeModule(params(type="partial")), client)

        self.assertIn("did not apply", result["msg"])
        self.assertTrue(result["changed"])
        self.assertEqual(result["zone_id"], "zone")

    def test_unmet_setting_after_create_reports_the_created_zone(self):
        created = {**ZONE, "account": {"id": "account"}}
        client = client_with(
            created=created,
            setting={"id": "min_tls_version", "value": "1.2"},
            edited_setting={"id": "min_tls_version", "value": "1.2"},
        )

        result = self.run_module(FakeModule(params(settings=[{"id": "min_tls_version", "value": "1.3"}])), client)

        self.assertIn("did not apply", result["msg"])
        self.assertTrue(result["changed"])
        self.assertEqual(result["zone"], created)
        self.assertEqual(result["settings"], [{"id": "min_tls_version", "value": "1.2"}])
        self.assertEqual(result["setting_id"], "min_tls_version")

    def test_updates_zone_fields_one_per_request(self):
        retyped = {**ZONE, "type": "partial"}
        updated = {**retyped, "vanity_name_servers": ["ns1.example.com"]}
        client = client_with([ZONE], edited=[retyped, updated])

        result = self.run_module(
            FakeModule(params(type="partial", vanity_name_servers=["ns1.example.com"])),
            client,
        )

        self.assertEqual(
            client.zones.edit.call_args_list,
            [
                call(zone_id="zone", type="partial"),
                call(zone_id="zone", vanity_name_servers=["ns1.example.com"]),
            ],
        )
        self.assertEqual(result["zone"], updated)
        self.assertEqual(result["message"], "Zone updated")

    def test_omitted_type_is_not_changed(self):
        client = client_with([{**ZONE, "type": "partial"}])

        result = self.run_module(FakeModule(params()), client)

        client.zones.edit.assert_not_called()
        self.assertFalse(result["changed"])

    def test_check_mode_does_not_update(self):
        client = client_with([ZONE])

        result = self.run_module(FakeModule(params(type="partial"), check_mode=True), client)

        client.zones.edit.assert_not_called()
        self.assertTrue(result["changed"])

    def test_equivalent_setting_is_unchanged(self):
        client = client_with([ZONE], setting={"id": "min_tls_version", "value": "1.2"})

        result = self.run_module(FakeModule(params(settings=[{"id": "min_tls_version", "value": 1.2}])), client)

        client.zones.settings.get.assert_called_once_with(setting_id="min_tls_version", zone_id="zone")
        client.zones.settings.edit.assert_not_called()
        self.assertFalse(result["changed"])

    def test_updates_changed_setting(self):
        updated = {"id": "min_tls_version", "value": "1.3"}
        client = client_with([ZONE], setting={"id": "min_tls_version", "value": "1.2"}, edited_setting=updated)

        result = self.run_module(FakeModule(params(settings=[{"id": "min_tls_version", "value": "1.3"}])), client)

        client.zones.settings.edit.assert_called_once_with(setting_id="min_tls_version", zone_id="zone", value="1.3")
        self.assertTrue(result["changed"])
        self.assertEqual(result["settings"], [updated])

    def test_updates_enabled_flag_setting(self):
        updated = {"id": "ssl_recommender", "enabled": True}
        client = client_with([ZONE], setting={"id": "ssl_recommender", "enabled": False}, edited_setting=updated)

        result = self.run_module(FakeModule(params(settings=[{"id": "ssl_recommender", "value": True}])), client)

        client.zones.settings.edit.assert_called_once_with(setting_id="ssl_recommender", zone_id="zone", enabled=True)
        self.assertEqual(result["settings"], [updated])

    def test_check_mode_does_not_update_setting(self):
        client = client_with([ZONE], setting={"id": "min_tls_version", "value": "1.2"})

        result = self.run_module(
            FakeModule(params(settings=[{"id": "min_tls_version", "value": "1.3"}]), check_mode=True),
            client,
        )

        client.zones.settings.edit.assert_not_called()
        self.assertTrue(result["changed"])

    def test_rejects_missing_setting(self):
        client = client_with([ZONE], setting=None)

        result = self.run_module(FakeModule(params(settings=[{"id": "min_tls_version", "value": "1.3"}])), client)

        self.assertEqual(result["msg"], "Cloudflare API returned malformed zone setting data")

    def test_rejects_an_unmet_setting_postcondition(self):
        client = client_with(
            [ZONE],
            setting={"id": "min_tls_version", "value": "1.2"},
            edited_setting={"id": "min_tls_version", "value": "1.2"},
        )

        result = self.run_module(FakeModule(params(settings=[{"id": "min_tls_version", "value": 1.3}])), client)

        self.assertEqual(
            result["msg"],
            'Cloudflare did not apply the requested zone setting: min_tls_version requested 1.3, stored "1.2"',
        )
        self.assertEqual(result["differences"], [{"field": "min_tls_version", "requested": 1.3, "stored": "1.2"}])
        self.assertEqual(result["zone_id"], "zone")
        self.assertEqual(result["setting_id"], "min_tls_version")
        self.assertTrue(result["changed"])

    def test_matches_zone_names_case_insensitively(self):
        client = client_with([ZONE], deleted={"id": "zone"})

        result = self.run_module(FakeModule(params(name="EXAMPLE.com", state="absent")), client)

        client.zones.delete.assert_called_once_with(zone_id="zone")
        self.assertTrue(result["changed"])

    def test_check_mode_does_not_delete(self):
        client = client_with([ZONE])

        result = self.run_module(FakeModule(params(state="absent"), check_mode=True), client)

        client.zones.delete.assert_not_called()
        self.assertTrue(result["changed"])

    def test_deletes_zone(self):
        client = client_with([ZONE], deleted={"id": "zone"})

        result = self.run_module(FakeModule(params(state="absent")), client)

        client.zones.delete.assert_called_once_with(zone_id="zone")
        self.assertTrue(result["changed"])
        self.assertEqual(result["zone"], ZONE)

    def test_strips_trailing_dot_from_name(self):
        created = {**ZONE, "account": {"id": "account"}}
        for found in ([], [ZONE]):
            with self.subTest(found=bool(found)):
                client = client_with(found, created=created)

                result = self.run_module(FakeModule(params(name="Example.COM.")), client)

                client.zones.list.assert_called_once_with(name="example.com", account={"id": "account"})
                self.assertNotIn("msg", result)
                self.assertEqual(result["changed"], not found)
                if not found:
                    client.zones.create.assert_called_once_with(
                        account={"id": "account"}, name="example.com", type="full"
                    )

    def test_root_label_name_reaches_cloudflare(self):
        # Cloudflare rejects the empty name on the only write.
        client = client_with(created={**ZONE, "name": ""})

        self.run_module(FakeModule(params(name=".")), client)

        client.zones.list.assert_called_once_with(name="", account={"id": "account"})
        client.zones.create.assert_called_once_with(account={"id": "account"}, name="", type="full")

    def test_null_aegis_pool_id_is_sent_and_converges(self):
        # Cloudflare accepts a null pool_id and does not store it.
        value = {"enabled": True, "pool_id": None}
        for stored, changed in (({"enabled": False}, True), ({"enabled": True}, False)):
            with self.subTest(stored=stored):
                client = client_with(
                    [ZONE],
                    setting={"id": "aegis", "value": stored},
                    edited_setting={"id": "aegis", "value": {"enabled": True}},
                )

                result = self.run_module(FakeModule(params(settings=[{"id": "aegis", "value": value}])), client)

                self.assertNotIn("msg", result)
                self.assertEqual(result["changed"], changed)
                if changed:
                    client.zones.settings.edit.assert_called_once_with(setting_id="aegis", zone_id="zone", value=value)
                else:
                    client.zones.settings.edit.assert_not_called()

    def test_non_editable_setting_fails_before_any_write(self):
        settings = {
            "ssl": {"id": "ssl", "value": "strict", "editable": True},
            "polish": {"id": "polish", "value": "off", "editable": False},
        }
        requested = [{"id": "ssl", "value": "full"}, {"id": "polish", "value": "lossless"}]
        for found, check_mode in (([ZONE], False), ([ZONE], True), ([], False)):
            with self.subTest(existing=bool(found), check_mode=check_mode):
                client = client_with(found, created={**ZONE, "type": "partial", "account": {"id": "account"}})
                client.zones.settings.get.side_effect = lambda setting_id, zone_id: settings[setting_id]

                result = self.run_module(
                    FakeModule(
                        params(type="partial", vanity_name_servers=["ns1.example.com"], settings=requested),
                        check_mode=check_mode,
                    ),
                    client,
                )

                self.assertEqual(result["msg"], "Zone setting polish is not editable on this zone")
                self.assertEqual(result["setting_id"], "polish")
                self.assertEqual(result["zone_id"], "zone")
                # Settings of a new zone can only be read after it is created.
                if found:
                    client.zones.create.assert_not_called()
                else:
                    client.zones.create.assert_called_once()

                client.zones.edit.assert_not_called()
                client.zones.settings.edit.assert_not_called()

    def test_non_editable_setting_already_matching_is_unchanged(self):
        client = client_with([ZONE], setting={"id": "polish", "value": "off", "editable": False})

        result = self.run_module(FakeModule(params(settings=[{"id": "polish", "value": "off"}])), client)

        client.zones.settings.edit.assert_not_called()
        self.assertFalse(result["changed"])

    def test_failures_after_create_report_the_created_zone(self):
        created = {**ZONE, "account": {"id": "account"}}
        settings = [{"id": "min_tls_version", "value": "1.3"}]
        cases = {
            "setting read": {"setting_error": timeout_error()},
            "not editable": {"setting": {"id": "min_tls_version", "value": "1.2", "editable": False}},
            "malformed setting": {"setting": {"id": "min_tls_version"}},
        }
        for case, kwargs in cases.items():
            with self.subTest(case=case):
                setting_error = kwargs.pop("setting_error", None)
                client = client_with(created=created, **kwargs)
                if setting_error is not None:
                    client.zones.settings.get.side_effect = setting_error

                try:
                    result = self.run_module(FakeModule(params(settings=settings)), client)
                except cloudflare.APIConnectionError as exc:
                    result = exc._cloudflare_context

                client.zones.create.assert_called_once()
                self.assertTrue(result["changed"])
                self.assertEqual(result["zone"], created)
                self.assertEqual(result["zone_id"], "zone")
                self.assertEqual(result["setting_id"], "min_tls_version")

    def test_rejected_zone_edit_after_create_reports_the_created_zone(self):
        created = {**ZONE, "account": {"id": "account"}}
        client = client_with(created=created)
        client.zones.edit.side_effect = status_error(400)

        with self.assertRaises(cloudflare.BadRequestError) as raised:
            zones.run(FakeModule(params(vanity_name_servers=["ns1.example.net", "ns2.example.net"])), client)

        context = raised.exception._cloudflare_context
        self.assertTrue(context["changed"])
        self.assertEqual(context["zone"], created)
        self.assertEqual(context["zone_id"], "zone")

    def test_rejected_second_setting_reports_the_first(self):
        first = {"id": "min_tls_version", "value": "1.3"}
        client = client_with([ZONE], setting={"id": "any", "value": "off"})
        client.zones.settings.get.side_effect = [
            {"id": "min_tls_version", "value": "1.2"},
            {"id": "always_use_https", "value": "off"},
        ]
        client.zones.settings.edit.side_effect = [first, status_error(400)]
        settings = [{"id": "min_tls_version", "value": "1.3"}, {"id": "always_use_https", "value": "on"}]

        with self.assertRaises(cloudflare.BadRequestError) as raised:
            zones.run(FakeModule(params(settings=settings)), client)

        context = raised.exception._cloudflare_context
        self.assertTrue(context["changed"])
        self.assertEqual(context["zone"], ZONE)
        self.assertEqual(context["settings"], [first])
        self.assertEqual(context["setting_id"], "always_use_https")

    def test_malformed_edited_setting_reports_the_write(self):
        client = client_with(
            [ZONE], setting={"id": "min_tls_version", "value": "1.2"}, edited_setting={"id": "min_tls_version"}
        )

        result = self.run_module(FakeModule(params(settings=[{"id": "min_tls_version", "value": "1.3"}])), client)

        self.assertEqual(result["msg"], "Cloudflare API returned malformed zone setting data")
        self.assertTrue(result["changed"])
        self.assertEqual(result["zone_id"], "zone")
        self.assertEqual(result["setting_id"], "min_tls_version")
        self.assertEqual(result["settings"], [{"id": "min_tls_version"}])

    def test_edited_zone_with_another_id_reports_the_write(self):
        edited = {**ZONE, "id": "other", "type": "partial"}
        client = client_with([ZONE], edited=[edited])

        result = self.run_module(FakeModule(params(type="partial")), client)

        self.assertEqual(result["msg"], "Cloudflare API returned the wrong zone")
        self.assertTrue(result["changed"])
        self.assertEqual(result["zone"], edited)
        self.assertEqual(result["zone_id"], "zone")
