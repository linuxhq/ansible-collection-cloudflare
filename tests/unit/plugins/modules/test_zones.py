# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from unittest import TestCase
from unittest.mock import Mock, call

from ansible_collections.linuxhq.cloudflare.plugins.modules import zones
from ansible_collections.linuxhq.cloudflare.tests.unit.plugins.modules.utils import (
    FakeModule,
    ModuleExit,
    ModuleFail,
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

    def test_create_requires_account(self):
        client = client_with()

        result = self.run_module(FakeModule(params(account_id=None)), client)

        client.zones.create.assert_not_called()
        self.assertEqual(result["msg"], "account_id is required when creating a zone")

    def test_rejects_invalid_setting_before_lookup(self):
        client = client_with()

        result = self.run_module(FakeModule(params(settings=[{"id": " ", "value": "on"}])), client)

        client.zones.list.assert_not_called()
        self.assertEqual(result["msg"], "Each zone setting requires a unique valid id")

    def test_rejects_duplicate_settings_before_lookup(self):
        client = client_with()
        settings = [{"id": "ssl", "value": "full"}, {"id": "ssl", "value": "strict"}]

        with self.assertRaises(ModuleFail):
            zones.run(FakeModule(params(settings=settings)), client)

        client.zones.list.assert_not_called()

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

        self.assertEqual(result["msg"], "Cloudflare did not apply the requested zone setting")

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

    def test_rejects_root_label_name(self):
        client = client_with()

        result = self.run_module(FakeModule(params(name=".")), client)

        client.zones.list.assert_not_called()
        self.assertEqual(result["msg"], "name must not be empty")

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
                client.zones.edit.assert_not_called()
                client.zones.settings.edit.assert_not_called()

    def test_non_editable_setting_already_matching_is_unchanged(self):
        client = client_with([ZONE], setting={"id": "polish", "value": "off", "editable": False})

        result = self.run_module(FakeModule(params(settings=[{"id": "polish", "value": "off"}])), client)

        client.zones.settings.edit.assert_not_called()
        self.assertFalse(result["changed"])
