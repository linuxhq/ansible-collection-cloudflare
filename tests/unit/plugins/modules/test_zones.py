# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from unittest import TestCase
from unittest.mock import patch

from ansible_collections.linuxhq.cloudflare.plugins.modules import zones
from ansible_collections.linuxhq.cloudflare.tests.unit.plugins.modules.utils import (
    FakeModule,
    ModuleExit,
    ModuleFail,
)


def params(**updates):
    values = {
        "name": "example.com",
        "account_id": "account",
        "type": None,
        "vanity_name_servers": None,
        "settings": None,
    }
    values.update(updates)
    return values


class ZonesTests(TestCase):
    def test_normalizes_setting_scalar_values_recursively(self):
        self.assertEqual(
            zones.normalize_setting_value(
                {"enabled": True, "ports": [80, 443], "ratio": 1.5}
            ),
            {"enabled": "true", "ports": ["80", "443"], "ratio": "1.5"},
        )

    def test_create_requires_account(self):
        module = FakeModule(params(account_id=None))

        with (
            patch.object(zones, "find_by_name", return_value=None),
            patch.object(zones, "post_result") as post,
            self.assertRaises(ModuleFail) as raised,
        ):
            zones.ensure_present(module, {})

        post.assert_not_called()
        self.assertEqual(
            raised.exception.values["msg"],
            "account_id is required when creating a zone",
        )

    def test_rejects_invalid_setting_before_lookup(self):
        module = FakeModule(params(settings=[{"id": " ", "value": "on"}]))

        with (
            patch.object(zones, "find_by_name") as find,
            self.assertRaises(ModuleFail) as raised,
        ):
            zones.ensure_present(module, {})

        find.assert_not_called()
        self.assertEqual(
            raised.exception.values["msg"],
            "Each zone setting requires a unique valid id and value",
        )

    def test_rejects_duplicate_settings_before_lookup(self):
        module = FakeModule(
            params(
                settings=[
                    {"id": "ssl", "value": "full"},
                    {"id": "ssl", "value": "strict"},
                ]
            )
        )

        with (
            patch.object(zones, "find_by_name") as find,
            self.assertRaises(ModuleFail),
        ):
            zones.ensure_present(module, {})

        find.assert_not_called()

    def test_creates_zone_with_default_type(self):
        module = FakeModule(params())
        created = {
            "id": "zone",
            "account": {"id": "account"},
            "name": "example.com",
            "type": "full",
        }

        with (
            patch.object(zones, "find_by_name", return_value=None),
            patch.object(zones, "post_result", return_value=created) as post,
            self.assertRaises(ModuleExit) as raised,
        ):
            zones.ensure_present(module, {})

        post.assert_called_once_with(
            {},
            "/zones",
            {
                "account": {"id": "account"},
                "name": "example.com",
                "type": "full",
            },
        )
        self.assertTrue(raised.exception.values["changed"])

    def test_rejects_create_response_for_wrong_account(self):
        module = FakeModule(params())

        with (
            patch.object(zones, "find_by_name", return_value=None),
            patch.object(
                zones,
                "post_result",
                return_value={
                    "id": "zone",
                    "account": {"id": "other"},
                    "name": "example.com",
                    "type": "full",
                },
            ),
            self.assertRaises(ModuleFail) as raised,
        ):
            zones.ensure_present(module, {})

        self.assertIn("did not apply", raised.exception.values["msg"])

    def test_updates_zone_fields_in_one_request(self):
        module = FakeModule(
            params(type="partial", vanity_name_servers=["ns1.example.com"])
        )
        current = {"id": "zone", "name": "example.com", "type": "full"}
        updated = {
            **current,
            "type": "partial",
            "vanity_name_servers": ["ns1.example.com"],
        }

        with (
            patch.object(zones, "find_by_name", return_value=current),
            patch.object(zones, "patch_result", return_value=updated) as patch_result,
            self.assertRaises(ModuleExit) as raised,
        ):
            zones.ensure_present(module, {})

        patch_result.assert_called_once_with(
            {},
            "/zones/zone",
            {
                "type": "partial",
                "vanity_name_servers": ["ns1.example.com"],
            },
        )
        self.assertEqual(raised.exception.values["zone"], updated)

    def test_equivalent_setting_is_unchanged(self):
        module = FakeModule(params(settings=[{"id": "min_tls_version", "value": 1.2}]))
        current = {"id": "zone", "name": "example.com"}

        with (
            patch.object(
                zones,
                "get_result",
                return_value={"value": "1.2"},
            ),
            patch.object(zones, "find_by_name", return_value=current),
            patch.object(zones, "patch_result") as patch_result,
            self.assertRaises(ModuleExit) as raised,
        ):
            zones.ensure_present(module, {})

        patch_result.assert_not_called()
        self.assertFalse(raised.exception.values["changed"])

    def test_rejects_an_unmet_setting_postcondition(self):
        module = FakeModule(params(settings=[{"id": "min_tls_version", "value": 1.3}]))
        current = {"id": "zone", "name": "example.com"}

        with (
            patch.object(zones, "find_by_name", return_value=current),
            patch.object(zones, "get_result", return_value={"value": "1.2"}),
            patch.object(
                zones,
                "patch_result",
                return_value={"id": "min_tls_version", "value": "1.2"},
            ),
            self.assertRaises(ModuleFail) as raised,
        ):
            zones.ensure_present(module, {})

        self.assertEqual(
            raised.exception.values["msg"],
            "Cloudflare did not apply the requested zone setting",
        )

    def test_check_mode_does_not_delete(self):
        current = {"id": "zone", "name": "example.com"}
        module = FakeModule(params(), check_mode=True)

        with (
            patch.object(zones, "find_by_name", return_value=current),
            patch.object(zones, "delete_result") as delete,
            self.assertRaises(ModuleExit) as raised,
        ):
            zones.ensure_absent(module, {})

        delete.assert_not_called()
        self.assertTrue(raised.exception.values["changed"])
