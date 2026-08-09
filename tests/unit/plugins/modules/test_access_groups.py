# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from unittest import TestCase
from unittest.mock import patch

from ansible_collections.linuxhq.cloudflare.plugins.modules import access_groups
from ansible_collections.linuxhq.cloudflare.tests.unit.plugins.modules.utils import (
    FakeModule,
    ModuleExit,
)


def params(**updates):
    values = {
        "account_id": "account",
        "name": "admins",
        "include": [{"email": {"email": "admin@example.com"}}],
        "is_default": False,
    }
    values.update(updates)
    return values


class AccessGroupsTests(TestCase):
    def test_equivalent_group_is_unchanged(self):
        current = {"id": "group", **params()}
        module = FakeModule(params())

        with (
            patch.object(access_groups, "find_by_name", return_value=current),
            patch.object(access_groups, "put_result") as put,
            self.assertRaises(ModuleExit) as raised,
        ):
            access_groups.ensure_present(module, {})

        put.assert_not_called()
        self.assertFalse(raised.exception.values["changed"])

    def test_creates_group(self):
        module = FakeModule(params())
        created = {"id": "group", "name": "admins"}

        with (
            patch.object(access_groups, "find_by_name", return_value=None),
            patch.object(access_groups, "post_result", return_value=created) as post,
            self.assertRaises(ModuleExit) as raised,
        ):
            access_groups.ensure_present(module, {})

        post.assert_called_once_with(
            {},
            "/accounts/account/access/groups",
            {
                "include": [{"email": {"email": "admin@example.com"}}],
                "is_default": False,
                "name": "admins",
            },
        )
        self.assertEqual(raised.exception.values["access_group"], created)

    def test_check_mode_does_not_delete(self):
        current = {"id": "group", "name": "admins"}
        module = FakeModule(params(), check_mode=True)

        with (
            patch.object(access_groups, "find_by_name", return_value=current),
            patch.object(access_groups, "delete_result") as delete,
            self.assertRaises(ModuleExit) as raised,
        ):
            access_groups.ensure_absent(module, {})

        delete.assert_not_called()
        self.assertTrue(raised.exception.values["changed"])
