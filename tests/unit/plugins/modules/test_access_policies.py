# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from unittest import TestCase
from unittest.mock import Mock, patch

from ansible_collections.linuxhq.cloudflare.plugins.modules import access_policies
from ansible_collections.linuxhq.cloudflare.tests.unit.plugins.modules.utils import (
    FakeModule,
    ModuleExit,
    ModuleFail,
    timeout_error,
)

INCLUDE = [{"email_domain": {"domain": "example.com"}}]


def params(**updates):
    values = {
        "account_id": "account",
        "name": "admins",
        "decision": "allow",
        "include": INCLUDE,
        "approval_required": None,
        "isolation_required": None,
        "purpose_justification_required": None,
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
    # Retry overrides return the same client so their calls are observable.
    client.with_options.return_value = client
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

    def test_lookup_failures_name_the_account(self):
        for found in ([{"name": "admins"}], [{"id": "one", "name": "admins"}, {"id": "two", "name": "admins"}]):
            client, api = client_with(found)
            with self.subTest(found=found):
                result = self.run_module(FakeModule(params()), client)

                api.create.assert_not_called()
                self.assertEqual(result["account_id"], "account")
                self.assertEqual(result["name"], "admins")

    def test_create_recovers_the_policy_after_a_lost_response(self):
        client, api = client_with()
        api.create.side_effect = timeout_error()
        api.list.side_effect = [[], [policy(name="other", id="other"), policy()]]

        result = self.run_module(FakeModule(params()), client)

        client.with_options.assert_called_once_with(max_retries=0)
        api.create.assert_called_once()
        self.assertEqual(result["message"], "Access policy created")
        self.assertEqual(result["access_policy"], policy())

    def test_empty_name_fails_before_any_request(self):
        # Cloudflare stores an empty name as null, so the policy is never found again.
        client, api = client_with()

        result = self.run_module(FakeModule(params(name="")), client)

        self.assertEqual(result["msg"], "name must not be empty")
        api.list.assert_not_called()

    def test_nameless_policy_does_not_block_lookup(self):
        # Cloudflare stores a policy with an empty name as null.
        client, _ignored = client_with([{"id": "nameless", "decision": "allow"}, policy()])

        result = self.run_module(FakeModule(params()), client)

        self.assertFalse(result["changed"])
        self.assertEqual(result["access_policy"]["id"], "policy")

    def test_matches_name_across_listed_policies(self):
        other = policy(id="other", name="users")
        client, api = client_with([other, policy()])

        result = self.run_module(FakeModule(params()), client)

        api.list.assert_called_once_with(account_id="account")
        self.assertFalse(result["changed"])
        self.assertEqual(result["access_policy"]["id"], "policy")

    def test_policy_stored_with_a_padded_name_does_not_block_another(self):
        padded = policy(id="padded", name="users ")
        client, api = client_with([padded, policy()])

        result = self.run_module(FakeModule(params()), client)

        api.update.assert_not_called()
        self.assertFalse(result["changed"])

    def test_padded_name_is_created_then_unchanged(self):
        # Cloudflare stores an Access policy name with its surrounding whitespace.
        padded = policy(name=" p43 ")
        client, api = client_with(created=padded)

        result = self.run_module(FakeModule(params(name=" p43 ")), client)

        api.create.assert_called_once_with(account_id="account", decision="allow", include=INCLUDE, name=" p43 ")
        self.assertTrue(result["changed"])

        client, api = client_with([padded])

        result = self.run_module(FakeModule(params(name=" p43 ")), client)

        api.create.assert_not_called()
        api.update.assert_not_called()
        self.assertFalse(result["changed"])

    def test_whitespace_only_name_is_created_then_unchanged(self):
        # Cloudflare stores a whitespace-only Access policy name verbatim.
        blank = policy(name="   ")
        client, api = client_with([{"id": "nameless"}], created=blank)

        result = self.run_module(FakeModule(params(name="   ")), client)

        self.assertNotIn("msg", result)
        self.assertTrue(result["changed"])

        client, api = client_with([blank])

        result = self.run_module(FakeModule(params(name="   ")), client)

        api.create.assert_not_called()
        self.assertFalse(result["changed"])

    def test_creates_policy(self):
        client, api = client_with(created=policy())

        result = self.run_module(FakeModule(params()), client)

        api.create.assert_called_once_with(account_id="account", decision="allow", include=INCLUDE, name="admins")
        self.assertTrue(result["changed"])

    def test_update_preserves_omitted_fields(self):
        exclude = [{"email": {"email": "blocked@example.com"}}]
        client, api = client_with([policy(exclude=exclude)], updated=policy(decision="deny", exclude=exclude))

        result = self.run_module(FakeModule(params(decision="deny")), client)

        self.assertEqual(api.update.call_args.args, ("policy",))
        self.assertEqual(api.update.call_args.kwargs["exclude"], exclude)
        self.assertTrue(result["changed"])

    def test_required_flags_have_no_module_default(self):
        with (
            patch.object(access_policies, "AnsibleModule", side_effect=RuntimeError) as module,
            self.assertRaises(RuntimeError),
        ):
            access_policies.main()

        argument_spec = module.call_args.kwargs["argument_spec"]
        for field in access_policies.FALSE_FIELDS:
            self.assertNotIn("default", argument_spec[field])

    def test_update_preserves_omitted_required_flags(self):
        flags = dict.fromkeys(access_policies.FALSE_FIELDS, True)
        client, api = client_with([policy(**flags)], updated=policy(decision="deny", **flags))

        result = self.run_module(FakeModule(params(decision="deny")), client)

        sent = api.update.call_args.kwargs
        self.assertEqual({field: sent[field] for field in flags}, flags)
        self.assertTrue(result["changed"])

        client, api = client_with([policy(decision="deny", **flags)])
        result = self.run_module(FakeModule(params(decision="deny")), client)

        api.update.assert_not_called()
        self.assertFalse(result["changed"])

    def test_explicit_required_flags_compare_with_cloudflare_defaults(self):
        flags = dict.fromkeys(access_policies.FALSE_FIELDS, False)
        client, api = client_with([policy()])

        result = self.run_module(FakeModule(params(**flags)), client)

        api.update.assert_not_called()
        self.assertFalse(result["changed"])

        client, api = client_with([policy(isolation_required=True)], updated=policy(isolation_required=False))
        result = self.run_module(FakeModule(params(isolation_required=False)), client)

        self.assertIs(api.update.call_args.kwargs["isolation_required"], False)
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

    def test_empty_prompt_matches_cleared_prompt(self):
        client, api = client_with([policy()])

        result = self.run_module(FakeModule(params(purpose_justification_prompt="")), client)

        api.update.assert_not_called()
        self.assertFalse(result["changed"])

        client, api = client_with([policy(purpose_justification_prompt="why")], updated=policy())

        result = self.run_module(FakeModule(params(purpose_justification_prompt="")), client)

        self.assertEqual(api.update.call_args.kwargs["purpose_justification_prompt"], "")
        self.assertEqual(result["message"], "Access policy updated")
        self.assertTrue(result["changed"])

    def test_removed_nested_selector_field_is_updated(self):
        include = [{"device_posture": {"integration_uid": "posture"}}]
        current = policy(include=[{"device_posture": {"integration_uid": "posture", "account_id": "other"}}])
        client, api = client_with([current], updated=policy(include=include))

        result = self.run_module(FakeModule(params(include=include)), client)

        self.assertEqual(api.update.call_args.kwargs["include"], include)
        self.assertTrue(result["changed"])

    def test_assigned_github_organization_id_matches_request(self):
        include = [{"github-organization": {"identity_provider_id": "idp", "name": "org"}}]
        created = policy(
            include=[{"github-organization": {"identity_provider_id": "idp", "id": "314135", "name": "org"}}]
        )
        client, api = client_with(created=created)

        result = self.run_module(FakeModule(params(include=include)), client)

        self.assertEqual(result["message"], "Access policy created")

        client, api = client_with([created])

        result = self.run_module(FakeModule(params(include=include)), client)

        api.update.assert_not_called()
        self.assertFalse(result["changed"])

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

    def test_null_unknown_approval_group_fields_are_ignored(self):
        approval_groups = [{"approvals_needed": 1, "email_addresses": ["a@example.com"], "foo": None}]
        client, _api = client_with([policy()])

        result = self.run_module(FakeModule(params(approval_groups=approval_groups), check_mode=True), client)

        self.assertNotIn("msg", result)

    def test_rejects_unstored_approval_group_fields_before_any_request(self):
        approval_groups = [
            {"approvals_needed": 1, "email_addresses": ["a@example.com"]},
            {"approvals_needed": 1, "email_list_uuid": "list", "foo": 1},
        ]
        for check_mode in (True, False):
            with self.subTest(check_mode=check_mode):
                client, api = client_with([policy()])

                result = self.run_module(
                    FakeModule(params(approval_groups=approval_groups), check_mode=check_mode), client
                )

                self.assertEqual(result["unsupported_fields"], ["approval_groups[1].foo"])
                self.assertEqual(
                    result["msg"], "Cloudflare does not store these Access policy fields: approval_groups[1].foo"
                )
                api.list.assert_not_called()
                api.update.assert_not_called()

    def test_rejects_empty_approval_group_email_addresses_before_any_request(self):
        approval_groups = [
            {"approvals_needed": 1, "email_addresses": []},
            {"approvals_needed": 1, "email_list_uuid": "list"},
        ]
        for check_mode in (True, False):
            with self.subTest(check_mode=check_mode):
                client, api = client_with([policy()])

                result = self.run_module(
                    FakeModule(params(approval_groups=approval_groups), check_mode=check_mode), client
                )

                self.assertEqual(result["empty_fields"], ["approval_groups[0].email_addresses"])
                self.assertEqual(
                    result["msg"],
                    "Cloudflare does not store an empty value for these Access policy fields: "
                    "approval_groups[0].email_addresses; omit them instead",
                )
                api.list.assert_not_called()
                api.update.assert_not_called()

    def test_rejects_empty_approval_group_email_list_uuid_before_any_request(self):
        approval_groups = [
            {"approvals_needed": 1, "email_addresses": ["a@example.com"]},
            {"approvals_needed": 1, "email_addresses": [], "email_list_uuid": ""},
        ]
        empty = ["approval_groups[1].email_addresses", "approval_groups[1].email_list_uuid"]
        for check_mode in (True, False):
            with self.subTest(check_mode=check_mode):
                client, api = client_with([policy()])

                result = self.run_module(
                    FakeModule(params(approval_groups=approval_groups), check_mode=check_mode), client
                )

                self.assertEqual(result["empty_fields"], empty)
                self.assertEqual(
                    result["msg"],
                    "Cloudflare does not store an empty value for these Access policy fields: "
                    f"{', '.join(empty)}; omit them instead",
                )
                api.list.assert_not_called()
                api.update.assert_not_called()

    def test_empty_approval_groups_match_cleared_groups(self):
        client, api = client_with([policy()])

        result = self.run_module(FakeModule(params(approval_groups=[])), client)

        api.update.assert_not_called()
        self.assertFalse(result["changed"])

        groups = [{"approvals_needed": 1, "email_addresses": ["a@example.com"]}]
        client, api = client_with([policy(approval_groups=groups)], updated=policy())

        result = self.run_module(FakeModule(params(approval_groups=[])), client)

        self.assertEqual(api.update.call_args.kwargs["approval_groups"], [])
        self.assertEqual(result["message"], "Access policy updated")
        self.assertTrue(result["changed"])

    def test_approval_group_key_removal_is_a_change(self):
        requested = [{"email_addresses": ["a@example.com", "b@example.com"]}]
        stored = [{**requested[0], "approvals_needed": 2}]
        client, api = client_with([policy(approval_groups=stored)], updated=policy(approval_groups=requested))

        result = self.run_module(FakeModule(params(approval_groups=requested)), client)

        self.assertEqual(api.update.call_args.kwargs["approval_groups"], requested)
        self.assertNotIn("msg", result)
        self.assertTrue(result["changed"])

    def test_identical_approval_groups_are_unchanged(self):
        groups = [{"approvals_needed": 2, "email_addresses": ["a@example.com", "b@example.com"]}]
        client, api = client_with([policy(approval_groups=groups)])

        result = self.run_module(FakeModule(params(approval_groups=groups)), client)

        api.update.assert_not_called()
        self.assertFalse(result["changed"])

    def test_null_github_organization_id_matches_assigned_id(self):
        include = [{"github-organization": {"identity_provider_id": "idp", "name": "org", "id": None}}]
        stored = policy(
            include=[{"github-organization": {"identity_provider_id": "idp", "id": "314135", "name": "org"}}]
        )
        client, api = client_with([stored])

        result = self.run_module(FakeModule(params(include=include)), client)

        api.update.assert_not_called()
        self.assertFalse(result["changed"])

    def test_rejects_unstored_selector_fields_before_any_request(self):
        client, api = client_with()

        result = self.run_module(
            FakeModule(params(exclude=[{"email_domain": {"domain": "x.com", "bogus": 1}}])), client
        )

        self.assertEqual(result["unsupported_fields"], ["exclude[0].email_domain.bogus"])
        api.list.assert_not_called()
        api.create.assert_not_called()

    def test_stored_approval_group_fields_are_sent(self):
        approval_groups = [{"approvals_needed": 1, "email_addresses": ["a@example.com"], "email_list_uuid": "list"}]
        client, api = client_with(created=policy(approval_groups=approval_groups))

        result = self.run_module(FakeModule(params(approval_groups=approval_groups)), client)

        self.assertNotIn("msg", result)
        self.assertEqual(api.create.call_args.kwargs["approval_groups"], approval_groups)

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

    def test_null_selector_and_approval_group_fields_are_not_sent(self):
        # A null key counts as omitted, so Cloudflare never receives it.
        saml = {"attribute_name": "group", "attribute_value": "admins"}
        group = {"approvals_needed": 1, "email_addresses": ["a@example.com"]}
        requested = {
            "include": [{"saml": {**saml, "identity_provider_id": None}}],
            "approval_groups": [{**group, "email_list_uuid": None}],
        }
        sent = {"include": [{"saml": saml}], "approval_groups": [group]}
        for current in (None, policy()):
            with self.subTest(current=current):
                found = [] if current is None else [current]
                client, api = client_with(found, created=policy(**sent), updated=policy(**sent))

                result = self.run_module(FakeModule(params(**requested)), client)

                call = api.update if current else api.create
                self.assertEqual(call.call_args.kwargs["include"], sent["include"])
                self.assertEqual(call.call_args.kwargs["approval_groups"], sent["approval_groups"])
                self.assertTrue(result["changed"])
                self.assertNotIn("msg", result)
