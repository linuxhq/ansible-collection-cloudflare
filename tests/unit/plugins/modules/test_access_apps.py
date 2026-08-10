# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from unittest import TestCase
from unittest.mock import patch

from ansible_collections.linuxhq.cloudflare.plugins.modules import access_apps
from ansible_collections.linuxhq.cloudflare.tests.unit.plugins.modules.utils import (
    FakeModule,
    ModuleExit,
)


def params(**updates):
    values = {
        "account_id": "account",
        "name": "app",
        "domain": "app.example.com",
        "type": "self_hosted",
        "app_launcher_visible": True,
        "auto_redirect_to_identity": False,
        "enable_binding_cookie": False,
        "http_only_cookie_attribute": True,
        "session_duration": "24h",
    }
    values.update(updates)
    return values


class AccessAppsTests(TestCase):
    def test_existing_app_with_provider_fields_is_unchanged(self):
        current = {
            "id": "app-id",
            "name": "app",
            "domain": "app.example.com",
            "type": "self_hosted",
            "provider": {"ignored": True},
        }
        module = FakeModule(params())

        with (
            patch.object(access_apps, "find_by_name", return_value=current),
            patch.object(access_apps, "put_result") as put,
            self.assertRaises(ModuleExit) as raised,
        ):
            access_apps.ensure_present(module, {})

        put.assert_not_called()
        self.assertFalse(raised.exception.values["changed"])

    def test_check_mode_does_not_create(self):
        module = FakeModule(params(), check_mode=True)

        with (
            patch.object(access_apps, "find_by_name", return_value=None),
            patch.object(access_apps, "post_result") as post,
            self.assertRaises(ModuleExit) as raised,
        ):
            access_apps.ensure_present(module, {})

        post.assert_not_called()
        self.assertTrue(raised.exception.values["changed"])

    def test_deletes_app_and_returns_redacted_state(self):
        current = {
            "id": "app-id",
            "name": "app",
            "scim_config": {"authentication": {"password": "secret"}},
        }
        module = FakeModule(params())

        with (
            patch.object(access_apps, "find_by_name", return_value=current),
            patch.object(access_apps, "delete_result") as delete,
            self.assertRaises(ModuleExit) as raised,
        ):
            access_apps.ensure_absent(module, {})

        delete.assert_called_once_with({}, "/accounts/account/access/apps/app-id")
        self.assertEqual(
            raised.exception.values["access_app"]["scim_config"]["authentication"],
            {},
        )
