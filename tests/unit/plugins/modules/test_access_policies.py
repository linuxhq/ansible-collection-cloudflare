# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from unittest import TestCase
from unittest.mock import patch

from ansible_collections.linuxhq.cloudflare.plugins.modules import access_policies
from ansible_collections.linuxhq.cloudflare.tests.unit.plugins.modules.utils import (
    FakeModule,
    ModuleExit,
)


def params(**updates):
    values = {
        "account_id": "account",
        "name": "admins",
        "decision": "allow",
        "include": [{"email_domain": {"domain": "example.com"}}],
        "approval_required": False,
        "isolation_required": False,
        "purpose_justification_required": False,
    }
    values.update(updates)
    return values


class AccessPoliciesTests(TestCase):
    def test_equivalent_policy_is_unchanged(self):
        current = {"id": "policy", **params()}
        current["include"] = [
            {
                "email_domain": {
                    "domain": "example.com",
                    "provider_field": "ignored",
                }
            }
        ]
        module = FakeModule(params())

        with (
            patch.object(access_policies, "find_by_field", return_value=current),
            patch.object(access_policies, "put_result") as put,
            self.assertRaises(ModuleExit) as raised,
        ):
            access_policies.ensure_present(module, {})

        put.assert_not_called()
        self.assertFalse(raised.exception.values["changed"])

    def test_updates_changed_policy(self):
        current = {"id": "policy", **params(decision="deny")}
        module = FakeModule(params())
        updated = {"id": "policy", **params()}

        with (
            patch.object(access_policies, "find_by_field", return_value=current),
            patch.object(
                access_policies,
                "put_result",
                return_value=updated,
            ) as put,
            self.assertRaises(ModuleExit) as raised,
        ):
            access_policies.ensure_present(module, {})

        put.assert_called_once()
        self.assertTrue(raised.exception.values["changed"])
        self.assertEqual(raised.exception.values["access_policy"], updated)

    def test_missing_policy_is_already_absent(self):
        module = FakeModule(params())

        with (
            patch.object(access_policies, "find_by_field", return_value=None),
            patch.object(access_policies, "delete_result") as delete,
            self.assertRaises(ModuleExit) as raised,
        ):
            access_policies.ensure_absent(module, {})

        delete.assert_not_called()
        self.assertFalse(raised.exception.values["changed"])
