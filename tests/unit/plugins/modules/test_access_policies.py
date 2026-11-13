# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from unittest import TestCase
from unittest.mock import Mock

from ansible_collections.linuxhq.cloudflare.plugins.modules import access_policies
from ansible_collections.linuxhq.cloudflare.tests.unit.plugins.modules.utils import (
    FakeModule,
    ModuleExit,
    ModuleFail,
)

INCLUDE = [{"email_domain": {"domain": "example.com"}}]


def params(**updates):
    values = {
        "account_id": "account",
        "name": "admins",
        "decision": "allow",
        "include": INCLUDE,
        "approval_required": False,
        "isolation_required": False,
        "purpose_justification_required": False,
        "state": "present",
    }
    values.update(updates)
    return values


def policy(**updates):
    values = {"id": "policy", "name": "admins", "decision": "allow", "include": INCLUDE}
    values.update(updates)
    return values


def client_with(policies=(), created=None, updated=None, deleted=None):
    client = Mock()
    api = client.zero_trust.access.policies
    api.list.return_value = list(policies)
    api.create.return_value = created
    api.update.return_value = updated
    api.delete.return_value = deleted
    return client, api


class AccessPoliciesTests(TestCase):
    def run_module(self, module, client):
        with self.assertRaises((ModuleExit, ModuleFail)) as raised:
            access_policies.run(module, client)

        return raised.exception.values

    def test_matches_name_across_listed_policies(self):
        other = policy(id="other", name="users")
        client, api = client_with([other, policy()])

        result = self.run_module(FakeModule(params()), client)

        api.list.assert_called_once_with(account_id="account")
        self.assertFalse(result["changed"])
        self.assertEqual(result["access_policy"]["id"], "policy")

    def test_creates_policy(self):
        client, api = client_with(created=policy())

        result = self.run_module(FakeModule(params()), client)

        api.create.assert_called_once_with(
            account_id="account",
            approval_required=False,
            decision="allow",
            include=INCLUDE,
            isolation_required=False,
            name="admins",
            purpose_justification_required=False,
        )
        self.assertTrue(result["changed"])

    def test_update_preserves_omitted_fields(self):
        exclude = [{"email": {"email": "blocked@example.com"}}]
        client, api = client_with([policy(exclude=exclude)], updated=policy(decision="deny", exclude=exclude))

        result = self.run_module(FakeModule(params(decision="deny")), client)

        self.assertEqual(api.update.call_args.args, ("policy",))
        self.assertEqual(api.update.call_args.kwargs["exclude"], exclude)
        self.assertTrue(result["changed"])

    def test_update_preserves_unmanaged_settings(self):
        current = policy(session_duration="8h")
        client, api = client_with([current], updated=policy(decision="deny", session_duration="8h"))

        result = self.run_module(FakeModule(params(decision="deny")), client)

        self.assertEqual(api.update.call_args.kwargs["session_duration"], "8h")
        self.assertTrue(result["changed"])

    def test_update_preserves_policy_resolution_account_id(self):
        current = policy(policy_resolution_account_id="trusted")
        client, api = client_with([current], updated=policy(decision="deny", policy_resolution_account_id="trusted"))

        result = self.run_module(FakeModule(params(decision="deny")), client)

        self.assertEqual(api.update.call_args.kwargs["policy_resolution_account_id"], "trusted")
        self.assertTrue(result["changed"])

    def test_equivalent_policy_is_unchanged(self):
        client, api = client_with([policy(purpose_justification_required=False)])

        result = self.run_module(FakeModule(params()), client)

        api.update.assert_not_called()
        self.assertFalse(result["changed"])

    def test_removed_nested_selector_field_is_updated(self):
        include = [{"device_posture": {"integration_uid": "posture"}}]
        current = policy(include=[{"device_posture": {"integration_uid": "posture", "account_id": "other"}}])
        client, api = client_with([current], updated=policy(include=include))

        result = self.run_module(FakeModule(params(include=include)), client)

        self.assertEqual(api.update.call_args.kwargs["include"], include)
        self.assertTrue(result["changed"])

    def test_rejects_sdk_selector_key_before_any_request(self):
        client, api = client_with()

        result = self.run_module(
            FakeModule(params(include=[{"github_organization": {"identity_provider_id": "idp", "name": "org"}}])),
            client,
        )

        self.assertEqual(
            result["msg"],
            "include selector 'github_organization' must use the Cloudflare API key 'github-organization'",
        )
        api.list.assert_not_called()
        api.create.assert_not_called()

    def test_updates_changed_policy(self):
        updated = policy()
        client, api = client_with([policy(decision="deny")], updated=updated)

        result = self.run_module(FakeModule(params()), client)

        api.update.assert_called_once()
        self.assertTrue(result["changed"])
        self.assertEqual(result["access_policy"], updated)

    def test_check_mode_does_not_update(self):
        client, api = client_with([policy(decision="deny")])

        result = self.run_module(FakeModule(params(), check_mode=True), client)

        api.update.assert_not_called()
        self.assertTrue(result["changed"])

    def test_rejects_update_response_with_wrong_policy(self):
        current = policy(decision="deny")
        client, _ignored = client_with([current], updated=current)

        result = self.run_module(FakeModule(params()), client)

        self.assertIn("did not apply", result["msg"])

    def test_missing_policy_is_already_absent(self):
        client, api = client_with()

        result = self.run_module(FakeModule(params(state="absent")), client)

        api.delete.assert_not_called()
        self.assertFalse(result["changed"])

    def test_deletes_policy(self):
        client, api = client_with([policy()], deleted={"id": "policy"})

        result = self.run_module(FakeModule(params(state="absent")), client)

        api.delete.assert_called_once_with("policy", account_id="account")
        self.assertTrue(result["changed"])
