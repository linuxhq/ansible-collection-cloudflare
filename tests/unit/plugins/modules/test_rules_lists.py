# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from unittest import TestCase
from unittest.mock import Mock, patch

import cloudflare

from ansible_collections.linuxhq.cloudflare.plugins.modules import rules_lists
from ansible_collections.linuxhq.cloudflare.tests.unit.plugins.modules.utils import (
    FakeModule,
    ModuleExit,
    ModuleFail,
    connection_error,
    status_error,
    timeout_error,
)

PENDING_BODY = {
    "success": False,
    "errors": [{"code": 10000, "message": "a bulk operation is already pending"}],
    "messages": [],
}
CURRENT = {"id": "list", "name": "addresses", "kind": "ip", "description": "current"}


def params(**updates):
    values = {
        "account_id": "account",
        "name": "addresses",
        "kind": "ip",
        "description": None,
        "elements": None,
        "operation_timeout": 30,
        "state": "present",
    }
    values.update(updates)
    return values


def make_client(lists=(), items=(), created=None, updated=None, fetched=None, deleted=None):
    client = Mock()
    # Per-request overrides return the same client so their calls are observable.
    client.with_options.return_value = client
    api = client.rules.lists
    api.list.return_value = list(lists)
    api.create.return_value = created
    api.update.return_value = updated
    api.get.return_value = fetched
    api.delete.return_value = deleted
    api.items.list.return_value = list(items)
    api.items.update.return_value = {"operation_id": "operation"}
    api.bulk_operations.get.return_value = {"id": "operation", "status": "completed"}
    return client, api


class RulesListsTests(TestCase):
    def run_module(self, module, client):
        with self.assertRaises((ModuleExit, ModuleFail)) as raised:
            rules_lists.run(module, client)

        return raised.exception.values

    def test_normalizes_metadata_defaults_and_duplicates(self):
        items = [
            {
                "id": "provider-id",
                "comment": "",
                "redirect": {
                    "source_url": "example.com",
                    "status_code": 301,
                    "preserve_path_suffix": True,
                },
            },
            {"redirect": {"source_url": "example.com"}},
        ]

        self.assertEqual(
            rules_lists.normalize_items(items),
            [{"redirect": {"source_url": "example.com"}}],
        )

    def test_redirect_numbers_are_not_dropped_as_boolean_defaults(self):
        redirect = {"source_url": "example.com", "include_subdomains": 0, "subpath_matching": 1}

        self.assertEqual(rules_lists.normalize_items([{"redirect": redirect}]), [{"redirect": redirect}])

    def test_rejects_operation_timeout_below_one_second(self):
        client, api = make_client()

        result = self.run_module(FakeModule(params(operation_timeout=0)), client)

        api.list.assert_not_called()
        self.assertEqual(result["msg"], "operation_timeout must be at least 1 second")

    def test_submit_retries_pending_operation_within_deadline(self):
        client, api = make_client()
        api.items.update.side_effect = [status_error(409, PENDING_BODY), {"operation_id": "operation"}]

        with (
            patch.object(rules_lists.time, "monotonic", side_effect=[1, 2, 3, 4]),
            patch.object(rules_lists.time, "sleep") as sleep,
        ):
            result = rules_lists.submit_items(FakeModule({}), client, "account", "list", [{"ip": "192.0.2.1"}], 30)

        self.assertEqual(result, {"operation_id": "operation"})
        self.assertEqual(api.items.update.call_count, 2)
        api.items.update.assert_called_with("list", account_id="account", body=[{"ip": "192.0.2.1"}])
        self.assertEqual(
            [call.kwargs for call in client.with_options.call_args_list],
            [{"timeout": 29, "max_retries": 0}, {"timeout": 27, "max_retries": 0}],
        )
        sleep.assert_called_once_with(rules_lists.OPERATION_POLL_SECONDS)

    def test_submit_retries_transient_errors_within_deadline(self):
        for error in (connection_error(), timeout_error(), status_error(503)):
            client, api = make_client()
            api.items.update.side_effect = [error, {"operation_id": "operation"}]
            with (
                self.subTest(error=type(error).__name__),
                patch.object(rules_lists.time, "monotonic", side_effect=[1, 2, 3, 4]),
                patch.object(rules_lists.time, "sleep"),
            ):
                result = rules_lists.submit_items(FakeModule({}), client, "account", "list", [], 30)

            self.assertEqual(result, {"operation_id": "operation"})

    def test_submit_does_not_retry_permanent_errors_or_past_the_deadline(self):
        cases = (
            (status_error(400), [1, 2]),
            (status_error(409, PENDING_BODY), [1, 29]),
        )
        for error, clock in cases:
            client, api = make_client()
            api.items.update.side_effect = error
            with (
                self.subTest(status=error.status_code, clock=clock),
                patch.object(rules_lists.time, "monotonic", side_effect=clock),
                patch.object(rules_lists.time, "sleep") as sleep,
                self.assertRaises(cloudflare.APIStatusError) as raised,
            ):
                rules_lists.submit_items(FakeModule({}), client, "account", "list", [], 30)

            sleep.assert_not_called()
            self.assertEqual(api.items.update.call_count, 1)
            self.assertIn("submitting the Rules list items", raised.exception._cloudflare_message)

    def test_submit_honors_subsecond_and_expired_deadlines(self):
        client, api = make_client()
        with patch.object(rules_lists.time, "monotonic", return_value=0.5):
            rules_lists.submit_items(FakeModule({}), client, "account", "list", [], 1)

        client.with_options.assert_called_once_with(timeout=0.5, max_retries=0)

        client, api = make_client()
        with (
            patch.object(rules_lists.time, "monotonic", return_value=1),
            self.assertRaises(ModuleFail) as raised,
        ):
            rules_lists.submit_items(FakeModule({}), client, "account", "list", [], 1)

        api.items.update.assert_not_called()
        self.assertIn("Timed out submitting", raised.exception.values["msg"])

    def test_wait_rejects_missing_operation_identifier(self):
        for operation in ({}, {"operation_id": " operation "}):
            with (
                self.subTest(operation=operation),
                self.assertRaises(ModuleFail) as raised,
            ):
                rules_lists.wait_for_operation(FakeModule({}), Mock(), "account", operation, 30)

            self.assertEqual(
                raised.exception.values["msg"],
                "Rules list items submission did not return an operation id",
            )

    def test_wait_returns_completed_operation(self):
        client, api = make_client()

        with patch.object(rules_lists.time, "monotonic", return_value=1):
            result = rules_lists.wait_for_operation(
                FakeModule({}), client, "account", {"operation_id": "operation"}, 30
            )

        api.bulk_operations.get.assert_called_once_with("operation", account_id="account")
        client.with_options.assert_called_once_with(timeout=29, max_retries=0)
        self.assertEqual(result, {"id": "operation", "status": "completed"})

    def test_wait_polls_until_completed_without_overrunning_deadline(self):
        client, api = make_client()
        api.bulk_operations.get.side_effect = [
            {"id": "operation", "status": "pending"},
            connection_error(),
            {"id": "operation", "status": "completed"},
        ]

        with (
            patch.object(rules_lists.time, "monotonic", side_effect=[1, 2, 3, 4, 5, 29.7, 29.8, 29.9]),
            patch.object(rules_lists.time, "sleep") as sleep,
        ):
            result = rules_lists.wait_for_operation(FakeModule({}), client, "account", {"id": "operation"}, 30)

        self.assertEqual(result["status"], "completed")
        self.assertEqual(sleep.call_args_list[0].args, (rules_lists.OPERATION_POLL_SECONDS,))
        self.assertAlmostEqual(sleep.call_args_list[1].args[0], 0.3)

    def test_wait_reports_failed_operation(self):
        client, api = make_client()
        api.bulk_operations.get.return_value = {"id": "operation", "status": "failed", "error": "bad"}

        with (
            patch.object(rules_lists.time, "monotonic", return_value=1),
            self.assertRaises(ModuleFail) as raised,
        ):
            rules_lists.wait_for_operation(FakeModule({}), client, "account", {"id": "operation"}, 30)

        self.assertEqual(raised.exception.values["msg"], "Rules list items operation failed")

    def test_wait_raises_permanent_polling_errors_with_context(self):
        client, api = make_client()
        api.bulk_operations.get.side_effect = status_error(403)

        with (
            patch.object(rules_lists.time, "monotonic", return_value=1),
            self.assertRaises(cloudflare.PermissionDeniedError) as raised,
        ):
            rules_lists.wait_for_operation(FakeModule({}), client, "account", {"id": "operation"}, 30)

        self.assertEqual(raised.exception._cloudflare_context, {"account_id": "account", "operation_id": "operation"})

    def test_rejects_responses_received_after_deadline(self):
        client, _ignored = make_client()
        with (
            patch.object(rules_lists.time, "monotonic", side_effect=[0, 2]),
            self.assertRaises(ModuleFail) as raised,
        ):
            rules_lists.submit_items(FakeModule({}), client, "account", "list", [], 1)

        self.assertIn("Timed out submitting", raised.exception.values["msg"])

        with (
            patch.object(rules_lists.time, "monotonic", side_effect=[0, 2]),
            self.assertRaises(ModuleFail) as raised,
        ):
            rules_lists.wait_for_operation(FakeModule({}), client, "account", {"id": "operation"}, 1)

        self.assertIn("Timed out waiting", raised.exception.values["msg"])

    def test_wait_uses_remaining_subsecond_budget(self):
        client, _ignored = make_client()

        with patch.object(rules_lists.time, "monotonic", return_value=0.5):
            result = rules_lists.wait_for_operation(FakeModule({}), client, "account", {"id": "operation"}, 1)

        client.with_options.assert_called_once_with(timeout=0.5, max_retries=0)
        self.assertEqual(result["status"], "completed")

    def test_wait_rejects_unknown_operation_status(self):
        client, api = make_client()
        api.bulk_operations.get.return_value = {"id": "operation", "status": "unknown"}

        with (
            patch.object(rules_lists.time, "monotonic", return_value=1),
            self.assertRaises(ModuleFail) as raised,
        ):
            rules_lists.wait_for_operation(FakeModule({}), client, "account", {"operation_id": "operation"}, 30)

        self.assertEqual(
            raised.exception.values["msg"],
            "Cloudflare API returned an unknown Rules list operation status",
        )

    def test_check_mode_does_not_create(self):
        client, api = make_client()

        result = self.run_module(FakeModule(params(), check_mode=True), client)

        api.list.assert_called_once_with(account_id="account")
        api.create.assert_not_called()
        self.assertTrue(result["changed"])

    def test_create_requires_kind(self):
        client, api = make_client()

        result = self.run_module(FakeModule(params(kind=None)), client)

        api.create.assert_not_called()
        self.assertEqual(result["msg"], "kind is required when creating a Rules list")

    def test_creates_list_with_default_description(self):
        created = {"id": "list", "name": "addresses", "kind": "ip", "description": "addresses"}
        client, api = make_client(created=created)

        result = self.run_module(FakeModule(params()), client)

        api.create.assert_called_once_with(account_id="account", description="addresses", kind="ip", name="addresses")
        self.assertEqual(result["message"], "Rules list created")
        self.assertEqual(result["rules_list"], created)

    def test_existing_list_without_managed_items_is_unchanged(self):
        client, api = make_client([CURRENT])

        result = self.run_module(FakeModule(params()), client)

        api.update.assert_not_called()
        self.assertFalse(result["changed"])

    def test_rejects_update_response_with_wrong_description(self):
        client, _ignored = make_client([CURRENT], updated=CURRENT)

        result = self.run_module(FakeModule(params(description="desired")), client)

        self.assertIn("did not apply", result["msg"])

    def test_metadata_update_omits_items_operation(self):
        client, api = make_client([CURRENT], updated={**CURRENT, "description": "desired"})

        result = self.run_module(FakeModule(params(description="desired")), client)

        api.update.assert_called_once_with("list", account_id="account", description="desired")
        self.assertTrue(result["changed"])
        self.assertNotIn("items_operation", result)

    def test_rejects_kind_change(self):
        client, _ignored = make_client([CURRENT])

        result = self.run_module(FakeModule(params(kind="hostname", elements=[])), client)

        self.assertEqual(result["msg"], "An existing Rules list kind cannot be changed")

    def test_elements_without_the_list_kind_fail_before_any_write(self):
        elements = [{"ip": "192.0.2.1"}, {"hostname": {"url_hostname": "example.com"}}]
        for lists, updates in (
            ([], {}),
            ([CURRENT], {"kind": None, "description": "desired"}),
        ):
            for check_mode in (False, True):
                with self.subTest(existing=bool(lists), check_mode=check_mode):
                    client, api = make_client(lists)

                    result = self.run_module(
                        FakeModule(params(elements=elements, **updates), check_mode=check_mode), client
                    )

                    self.assertEqual(result["msg"], "elements[1] must set 'ip' for a Rules list of kind 'ip'")
                    api.create.assert_not_called()
                    api.update.assert_not_called()
                    api.items.update.assert_not_called()

    def test_invalid_ip_elements_fail_before_any_write(self):
        for value in ("not-an-ip", "192.0.2.0/7", "192.0.2.0/33", "2001:db8::/11", "192.0.2.0/", "192.0.2.0/a", 1):
            for lists, updates in (
                ([], {}),
                ([CURRENT], {"description": "desired"}),
            ):
                for check_mode in (False, True):
                    with self.subTest(value=value, existing=bool(lists), check_mode=check_mode):
                        client, api = make_client(lists)
                        elements = [{"ip": "192.0.2.1"}, {"ip": value}]

                        result = self.run_module(
                            FakeModule(params(elements=elements, **updates), check_mode=check_mode), client
                        )

                        self.assertIn("elements[1].ip must be an IP address", result["msg"])
                        self.assertEqual(result["ip"], value)
                        api.create.assert_not_called()
                        api.update.assert_not_called()
                        api.items.update.assert_not_called()

    def test_valid_ip_elements_are_accepted(self):
        for value in ("192.0.2.1", "10.0.0.0/8", "192.0.2.1/32", "2001:db8::1", "2001:db8::/12", "2001:db8::1/128"):
            with self.subTest(value=value):
                self.assertTrue(rules_lists.valid_ip(value))

    def test_invalid_hostname_and_asn_elements_fail_before_any_write(self):
        cases = [
            ("hostname", {"hostname": {"url_hostname": value}}, "elements[1].hostname.url_hostname", value)
            for value in ("https://example.com", "example.com/path", "*example.com", "a.*", "*")
        ] + [
            ("asn", {"asn": value}, "elements[1].asn must be a non-negative integer", value)
            for value in (-1, "13335", True, 1.0)
        ]
        valid = {"hostname": {"hostname": {"url_hostname": "*.example.com"}}, "asn": {"asn": 13335}}
        for kind, element, message, value in cases:
            for lists in ([], [{**CURRENT, "kind": kind}]):
                for check_mode in (False, True):
                    with self.subTest(kind=kind, value=value, existing=bool(lists), check_mode=check_mode):
                        client, api = make_client(lists)
                        elements = [valid[kind], element]

                        result = self.run_module(
                            FakeModule(params(kind=kind, elements=elements), check_mode=check_mode), client
                        )

                        self.assertIn(message, result["msg"])
                        self.assertEqual(result["url_hostname" if kind == "hostname" else "asn"], value)
                        api.create.assert_not_called()
                        api.update.assert_not_called()
                        api.items.update.assert_not_called()

    def assert_elements_fail_before_any_write(self, kind, elements, message, **expected):
        for lists, updates in (
            ([], {}),
            ([{**CURRENT, "kind": kind}], {"kind": None, "description": "desired"}),
        ):
            for check_mode in (False, True):
                with self.subTest(elements=elements, existing=bool(lists), check_mode=check_mode):
                    client, api = make_client(lists)

                    result = self.run_module(
                        FakeModule(params(elements=elements, **{"kind": kind, **updates}), check_mode=check_mode),
                        client,
                    )

                    self.assertEqual(result["msg"], message)
                    for key, value in expected.items():
                        self.assertEqual(result[key], value)

                    api.create.assert_not_called()
                    api.update.assert_not_called()
                    api.items.update.assert_not_called()

    def test_malformed_hostname_and_redirect_elements_fail_before_any_write(self):
        valid = {
            "hostname": {"hostname": {"url_hostname": "example.com"}},
            "redirect": {"redirect": {"source_url": "example.com/a", "target_url": "https://example.net"}},
        }
        cases = [
            ("hostname", value, "url_hostname")
            for value in ({}, "example.com", {"url_hostname": None}, {"url_hostname": ""}, {"url_hostname": 1})
        ] + [
            ("redirect", value, field)
            for value, field in (
                ({"source_url": "example.com/a"}, "target_url"),
                ({"target_url": "https://example.net"}, "source_url"),
                ({"source_url": "example.com/a", "target_url": ""}, "target_url"),
                ("example.com/a", "source_url"),
            )
        ]
        for kind, value, field in cases:
            self.assert_elements_fail_before_any_write(
                kind,
                [valid[kind], {kind: value}],
                f"elements[1].{kind} must be a mapping with a non-empty string {field!r}",
            )

    def test_elements_with_unexpected_keys_fail_before_any_write(self):
        for kind, element, unexpected in (
            ("ip", {"ip": "192.0.2.1", "description": "office"}, ["description"]),
            ("ip", {"ip": "192.0.2.1", "asn": 5, "comment": "office"}, ["asn"]),
            ("asn", {"asn": 13335, "id": "item", "hostname": {"url_hostname": "example.com"}}, ["hostname", "id"]),
        ):
            self.assert_elements_fail_before_any_write(
                kind,
                [element],
                f"elements[0] supports only {kind!r} and 'comment' for a Rules list of kind {kind!r}",
                unexpected_keys=unexpected,
            )

    def test_valid_redirect_and_commented_elements_are_accepted(self):
        for kind, element in (
            ("ip", {"ip": "192.0.2.1", "comment": "office"}),
            (
                "redirect",
                {
                    "redirect": {
                        "source_url": "example.com/a",
                        "target_url": "https://example.net",
                        "status_code": 302,
                    },
                    "comment": "moved",
                },
            ),
            ("hostname", {"hostname": {"url_hostname": "example.com", "exclude_exact_hostname": False}}),
        ):
            with self.subTest(element=element):
                client, _ignored = make_client()

                result = self.run_module(FakeModule(params(kind=kind, elements=[element]), check_mode=True), client)

                self.assertTrue(result["changed"])

    def test_valid_hostname_and_asn_elements_are_accepted(self):
        for kind, element in (
            ("hostname", {"hostname": {"url_hostname": "*.example.com"}}),
            ("hostname", {"hostname": {"url_hostname": "example.com"}}),
            ("asn", {"asn": 0}),
            ("asn", {"asn": 13335}),
        ):
            with self.subTest(element=element):
                client, _ignored = make_client()

                result = self.run_module(FakeModule(params(kind=kind, elements=[element]), check_mode=True), client)

                self.assertTrue(result["changed"])

    def test_generated_sdk_iterator_reads_all_current_items(self):
        current = {**CURRENT, "num_items": 2}
        client, api = make_client([current], items=[{"ip": "192.0.2.1"}, {"ip": "192.0.2.2"}])

        result = self.run_module(FakeModule(params(elements=[{"ip": "192.0.2.1"}, {"ip": "192.0.2.2"}])), client)

        api.items.list.assert_called_once_with("list", account_id="account", per_page=rules_lists.ITEMS_PER_PAGE)
        api.items.update.assert_not_called()
        self.assertFalse(result["changed"])

    def test_count_mismatch_skips_item_listing_in_check_mode(self):
        client, api = make_client([{**CURRENT, "num_items": 0}])

        result = self.run_module(FakeModule(params(elements=[{"ip": "192.0.2.1"}]), check_mode=True), client)

        api.items.list.assert_not_called()
        api.items.update.assert_not_called()
        self.assertEqual(result["message"], "Rules list items would be updated")

    def test_submits_normalized_items_and_verifies_result(self):
        current = {**CURRENT, "num_items": 0}
        elements = [{"ip": "2001:DB8::1", "comment": ""}, {"ip": "2001:db8::1"}]
        client, api = make_client([current], items=[{"ip": "2001:db8::1"}], fetched={**current, "num_items": 1})

        with patch.object(rules_lists.time, "monotonic", return_value=1):
            result = self.run_module(FakeModule(params(elements=elements)), client)

        api.items.update.assert_called_once_with("list", account_id="account", body=[{"ip": "2001:db8::1"}])
        api.get.assert_called_once_with("list", account_id="account")
        self.assertEqual(client.with_options.call_args_list[0].kwargs, {"timeout": 30, "max_retries": 0})
        self.assertTrue(result["changed"])
        self.assertEqual(result["message"], "Rules list updated")
        self.assertEqual(result["items_operation"], {"id": "operation", "status": "completed"})
        self.assertEqual(result["rules_list"]["num_items"], 1)

    def test_rejects_completed_update_with_wrong_items(self):
        current = {**CURRENT, "num_items": 0}
        client, _ignored = make_client([current], fetched=current)

        with patch.object(rules_lists.time, "monotonic", return_value=1):
            result = self.run_module(FakeModule(params(elements=[{"ip": "192.0.2.1"}])), client)

        self.assertIn("did not apply", result["msg"])

    def test_deletes_list(self):
        client, api = make_client([CURRENT], deleted={"id": "list"})

        result = self.run_module(FakeModule(params(state="absent")), client)

        api.delete.assert_called_once_with("list", account_id="account")
        self.assertTrue(result["changed"])

    def test_check_mode_does_not_delete(self):
        client, api = make_client([CURRENT])

        result = self.run_module(FakeModule(params(state="absent"), check_mode=True), client)

        api.delete.assert_not_called()
        self.assertTrue(result["changed"])


class CanonicalIpTests(TestCase):
    def test_normalizes_equivalent_addresses(self):
        self.assertEqual(
            rules_lists.normalize_items([{"ip": "2400:d400:0011:19::2"}, {"ip": "2001:DB8:0::/32"}]),
            rules_lists.normalize_items([{"ip": "2400:d400:11:19::2"}, {"ip": "2001:db8::/32"}]),
        )
        self.assertEqual(rules_lists.canonical_ip("not-an-ip"), "not-an-ip")
