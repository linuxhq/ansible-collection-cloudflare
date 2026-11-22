# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from unittest import TestCase
from unittest.mock import Mock, patch

import cloudflare
import httpx

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
CURRENT = {"id": "list", "name": "addresses", "kind": "ip", "description": "current", "num_items": 0}


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

    def test_create_recovers_the_list_after_a_lost_response(self):
        recovered = {"id": "list", "name": "addresses", "kind": "ip", "description": "addresses"}
        client, api = make_client()
        api.create.side_effect = timeout_error()
        api.list.side_effect = [[], [recovered]]

        result = self.run_module(FakeModule(params()), client)

        client.with_options.assert_called_once_with(max_retries=0)
        api.create.assert_called_once()
        self.assertEqual(result["message"], "Rules list created")
        self.assertEqual(result["rules_list"], recovered)

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
        redirect = {"source_url": "example.com/a", "include_subdomains": 0, "subpath_matching": 1}

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
        for operation in ({}, {"operation_id": ""}, {"id": "operation"}):
            with (
                self.subTest(operation=operation),
                self.assertRaises(ModuleFail) as raised,
            ):
                rules_lists.wait_for_operation(FakeModule({}), Mock(), "account", "list", operation, 30)

            self.assertEqual(
                raised.exception.values["msg"],
                "Rules list items submission did not return an operation id",
            )
            self.assertEqual(raised.exception.values["rules_list_id"], "list")

    def test_wait_returns_completed_operation(self):
        client, api = make_client()

        with patch.object(rules_lists.time, "monotonic", return_value=1):
            result = rules_lists.wait_for_operation(
                FakeModule({}), client, "account", "list", {"operation_id": "operation"}, 30
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
            patch.object(rules_lists.time, "monotonic", side_effect=[1, 2, 3, 4, 29.7, 29.8]),
            patch.object(rules_lists.time, "sleep") as sleep,
        ):
            result = rules_lists.wait_for_operation(
                FakeModule({}), client, "account", "list", {"operation_id": "operation"}, 30
            )

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
            rules_lists.wait_for_operation(FakeModule({}), client, "account", "list", {"operation_id": "operation"}, 30)

        self.assertEqual(raised.exception.values["msg"], "Rules list items operation failed")
        self.assertEqual(raised.exception.values["rules_list_id"], "list")

    def test_wait_reports_an_operation_without_status_as_unknown(self):
        operation = {"id": "operation"}
        client, api = make_client()
        api.bulk_operations.get.return_value = operation

        with (
            patch.object(rules_lists.time, "monotonic", return_value=1),
            self.assertRaises(ModuleFail) as raised,
        ):
            rules_lists.wait_for_operation(FakeModule({}), client, "account", "list", {"operation_id": "operation"}, 30)

        self.assertEqual(
            raised.exception.values["msg"], "Cloudflare API returned an unknown Rules list operation status"
        )
        self.assertEqual(raised.exception.values["operation"], operation)

    def test_wait_raises_permanent_polling_errors_with_context(self):
        client, api = make_client()
        api.bulk_operations.get.side_effect = status_error(403)

        with (
            patch.object(rules_lists.time, "monotonic", return_value=1),
            self.assertRaises(cloudflare.PermissionDeniedError) as raised,
        ):
            rules_lists.wait_for_operation(FakeModule({}), client, "account", "list", {"operation_id": "operation"}, 30)

        self.assertEqual(
            raised.exception._cloudflare_context,
            {"account_id": "account", "rules_list_id": "list", "operation_id": "operation"},
        )

    def test_late_submit_response_reports_the_submitted_operation(self):
        # Cloudflare accepted the operation, so the timeout names it.
        client, api = make_client([{**CURRENT, "num_items": 0}])
        with (
            patch.object(rules_lists.time, "monotonic", side_effect=[0, 0, 31]),
            self.assertRaises(ModuleFail) as raised,
        ):
            rules_lists.run(FakeModule(params(elements=[{"ip": "192.0.2.1"}])), client)

        api.items.update.assert_called_once()
        api.bulk_operations.get.assert_not_called()
        self.assertEqual(
            raised.exception.values["msg"], "Timed out waiting for the Rules list items operation to complete"
        )
        self.assertEqual(raised.exception.values["operation_id"], "operation")

    def test_late_operation_status_is_used(self):
        cases = (
            ({"id": "operation", "status": "completed"}, None),
            ({"id": "operation", "status": "failed"}, "Rules list items operation failed"),
            (
                {"id": "operation", "status": "running"},
                "Timed out waiting for the Rules list items operation to complete",
            ),
        )
        for status, msg in cases:
            client, api = make_client()
            api.bulk_operations.get.return_value = status
            with (
                self.subTest(status=status["status"]),
                patch.object(rules_lists.time, "monotonic", side_effect=[0, 2, 2]),
                patch.object(rules_lists.time, "sleep"),
            ):
                try:
                    result = rules_lists.wait_for_operation(
                        FakeModule({}), client, "account", "list", {"operation_id": "operation"}, 1
                    )
                except ModuleFail as exc:
                    result = exc.values

            api.bulk_operations.get.assert_called_once()
            if msg is None:
                self.assertEqual(result, status)
            else:
                self.assertEqual(result["msg"], msg)
                self.assertEqual(result["rules_list_id"], "list")
                self.assertEqual(result["operation_id"], "operation")
                self.assertEqual(result["operation"], status)

    def test_wait_uses_remaining_subsecond_budget(self):
        client, _ignored = make_client()

        with patch.object(rules_lists.time, "monotonic", return_value=0.5):
            result = rules_lists.wait_for_operation(
                FakeModule({}), client, "account", "list", {"operation_id": "operation"}, 1
            )

        client.with_options.assert_called_once_with(timeout=0.5, max_retries=0)
        self.assertEqual(result["status"], "completed")

    def test_wait_rejects_unknown_operation_status(self):
        client, api = make_client()
        api.bulk_operations.get.return_value = {"id": "operation", "status": "unknown"}

        with (
            patch.object(rules_lists.time, "monotonic", return_value=1),
            self.assertRaises(ModuleFail) as raised,
        ):
            rules_lists.wait_for_operation(FakeModule({}), client, "account", "list", {"operation_id": "operation"}, 30)

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

    def test_create_without_kind_reaches_cloudflare(self):
        # Cloudflare rejects a new list without a kind on the only write.
        # Element checks depend on the kind, so they are skipped without one.
        client, api = make_client()

        self.run_module(FakeModule(params(kind=None, elements=[{"ip": "not an ip"}])), client)

        api.create.assert_called_once_with(account_id="account", description="addresses", kind=None, name="addresses")

    def test_creates_list_with_default_description(self):
        created = {"id": "list", "name": "addresses", "kind": "ip", "description": "addresses", "num_items": 0}
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
        self.assertTrue(result["changed"])
        self.assertEqual(result["account_id"], "account")
        self.assertEqual(result["rules_list_id"], "list")

    def test_not_applied_after_create_reports_the_created_list(self):
        created = {"id": "list", "name": "addresses", "kind": "ip", "description": "other"}
        client, _ignored = make_client(created=created)

        result = self.run_module(FakeModule(params(description="desired")), client)

        self.assertIn("did not apply", result["msg"])
        self.assertTrue(result["changed"])
        self.assertEqual(result["rules_list"], created)
        self.assertEqual(result["rules_list_id"], "list")
        self.assertEqual(result["account_id"], "account")

    def test_unapplied_items_after_create_report_the_created_list(self):
        created = {"id": "list", "name": "addresses", "kind": "ip", "description": "addresses", "num_items": 0}
        client, _ignored = make_client(created=created, fetched=created)

        with patch.object(rules_lists.time, "monotonic", return_value=1):
            result = self.run_module(FakeModule(params(elements=[{"ip": "192.0.2.1"}])), client)

        self.assertIn("did not apply", result["msg"])
        self.assertTrue(result["changed"])
        self.assertEqual(result["rules_list"], created)
        self.assertEqual(result["rules_list_id"], "list")

    def test_empty_description_matches_list_without_description(self):
        created = {"id": "list", "name": "addresses", "kind": "ip"}
        for lists, updated, called in (
            ([], None, False),
            ([CURRENT], created, True),
            ([created], None, False),
        ):
            with self.subTest(existing=bool(lists), stored=lists[0].get("description") if lists else None):
                client, api = make_client(lists, created=created, updated=updated)

                result = self.run_module(FakeModule(params(description="")), client)

                self.assertNotIn("msg", result)
                self.assertEqual(result["changed"], called or not lists)
                self.assertEqual(api.update.called, called)
                if not lists:
                    api.create.assert_called_once_with(
                        account_id="account", description="", kind="ip", name="addresses"
                    )

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
        self.assertEqual(result["account_id"], "account")
        self.assertEqual(result["name"], "addresses")
        self.assertEqual(result["rules_list_id"], "list")

    def test_malformed_lookup_names_the_account_and_list(self):
        for current, rules_list_id in (({**CURRENT, "id": None}, None), ({**CURRENT, "kind": None}, "list")):
            client, api = make_client([current])
            with self.subTest(current=current):
                result = self.run_module(FakeModule(params()), client)

                api.update.assert_not_called()
                self.assertEqual(result["msg"], "Cloudflare API returned malformed Rules list data")
                self.assertEqual(result["account_id"], "account")
                self.assertEqual(result["name"], "addresses")
                self.assertEqual(result.get("rules_list_id"), rules_list_id)

    def test_ambiguous_lookup_names_the_account(self):
        client, _ignored = make_client([CURRENT, {**CURRENT, "id": "other"}])

        result = self.run_module(FakeModule(params()), client)

        self.assertEqual(result["matching_ids"], ["list", "other"])
        self.assertEqual(result["account_id"], "account")
        self.assertEqual(result["name"], "addresses")

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
        for value in (
            "not-an-ip",
            "192.0.2.0/7",
            "192.0.2.0/33",
            "2001:db8::/11",
            "192.0.2.0/",
            "192.0.2.0/a",
            1,
            "1.2.3.4/8",
            "2001:db0::/12",
            "::ffff:1.2.3.4",
            "::ffff:0:0/96",
            "fe80::1%eth0",
            "fe80::%1/64",
        ):
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
        for value in (
            "192.0.2.1",
            "10.0.0.0/8",
            "192.0.2.1/32",
            "2001:db8::1",
            "2000::/12",
            "1.2.3.0/24",
            "2001:db8::1/128",
            "2001:0DB8::1",
            "10.0.0.0/08",
        ):
            with self.subTest(value=value):
                self.assertTrue(rules_lists.valid_ip(value))

    def test_invalid_hostname_and_asn_elements_fail_before_any_write(self):
        cases = [
            ("hostname", {"hostname": {"url_hostname": value}}, "elements[1].hostname.url_hostname", value)
            for value in (
                "https://example.com",
                "example.com/path",
                "*example.com",
                "a.*",
                "*",
                "ex*.example.com",
                "a.*.example.com",
                "*.*.example.com",
                "example.com:443",
                "exa mple.com",
                "bücher.example",
                "-a.example.com",
                "a-.example.com",
                "a.-b.example.com",
                "a..example.com",
                ".example.com",
                "*.",
                "*.-a.example.com",
                "example.com..",
                ".",
                f"{'a' * 64}.example.com",
                f"*.{'a' * 64}.example.com",
                ".".join(["a" * 63] * 4),
                ".".join(["a" * 63] * 3 + ["b" * 58, "com"]),
            )
        ] + [
            ("asn", {"asn": value}, "elements[1].asn must be an integer from 1 to 4294967295", value)
            for value in (0, -1, 2**32, "13335", True, 1.0)
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

    def test_invalid_redirect_status_codes_fail_before_any_write(self):
        redirect = {"source_url": "example.com/a", "target_url": "https://example.net"}
        for value in (303, 200, "301", True, 301.0):
            self.assert_elements_fail_before_any_write(
                "redirect",
                [{"redirect": {**redirect, "status_code": value}}],
                "elements[0].redirect.status_code must be one of 301, 302, 307, or 308",
                status_code=value,
            )

    def test_source_urls_with_unsupported_components_fail_before_any_write(self):
        for value, problem in (
            ("example.com/a?x=1", "must not include a query string"),
            ("example.com/?x=1", "must not include a query string"),
            ("example.com/a?", "must not include a query string"),
            ("https://example.com/a?x=1", "must not include a query string"),
            ("example.com/a#frag", "must not include a fragment"),
            ("example.com#f", "must not include a fragment"),
            ("https://user@example.com/a", "must not include userinfo"),
            ("https://user:pass@example.com/a", "must not include userinfo"),
            ("user:pass@example.com/a", "must not include userinfo"),
            ("example.com:8080/a", "must not include a port"),
            ("localhost:80/a", "must not include a port"),
            ("https://example.com:8080/a", "must not include a port"),
            ("https://example.com:443", "must not include a port"),
            ("https://[2001:db8::1]:8080/a", "must not use an IPv6 address as its host"),
            ("ftp://example.com/a", "must use the http or https scheme, or none"),
            ("a+b://example.com/a", "must use the http or https scheme, or none"),
            # Cloudflare rejects these when it replaces the list items.
            ("https://example.com:abc/", "must not include a port"),
            ("http:example.com", "must use the http or https scheme followed by '://', or none"),
            ("example.com:/", "must use the http or https scheme followed by '://', or none"),
            ("example.com:abc/", "must use the http or https scheme followed by '://', or none"),
            ("2001:db8::1/", "must not use an IPv6 address as its host"),
            ("https://2001:db8::1/a", "must not use an IPv6 address as its host"),
            # Cloudflare stores these without the brackets, a form it rejects.
            ("[2001:db8::1]/", "must not use an IPv6 address as its host"),
            ("https://[2001:db8::1]/a", "must not use an IPv6 address as its host"),
            # Cloudflare decodes these to "?", "#", and "%", which it then rejects.
            (
                "example.com/a%3fx",
                "must not contain %3F, %23, or %25, which Cloudflare decodes to characters it rejects",
            ),
            (
                "example.com/a%3Fx",
                "must not contain %3F, %23, or %25, which Cloudflare decodes to characters it rejects",
            ),
            (
                "example.com/a%23",
                "must not contain %3F, %23, or %25, which Cloudflare decodes to characters it rejects",
            ),
            (
                "example.com/a%25",
                "must not contain %3F, %23, or %25, which Cloudflare decodes to characters it rejects",
            ),
            # Cloudflare rejects a source URL without a host after the list is created.
            ("https:///a", "must include a host"),
            ("https://", "must include a host"),
            ("http://", "must include a host"),
            ("/a", "must include a host"),
            ("//a", "must include a host"),
            ("example.com/%zz", "must use '%' only in a percent-escape such as %20"),
            ("example.com/%2", "must use '%' only in a percent-escape such as %20"),
            ("example.com/a%", "must use '%' only in a percent-escape such as %20"),
        ):
            self.assert_elements_fail_before_any_write(
                "redirect",
                [
                    {"redirect": {"source_url": "example.com/b", "target_url": "https://example.net"}},
                    {"redirect": {"source_url": value, "target_url": "https://example.net"}},
                ],
                f"elements[1].redirect.source_url {problem}",
                source_url=value,
            )

    def test_target_urls_without_scheme_fail_before_any_write(self):
        for value in (
            "www.example.org/d",
            "example.org",
            "/relative",
            "//example.org/d",
            "https://[::1/d",
            "https://exa mple.com/",
            "https://exa\tmple.com/",
            "https://example.com :443/",
            "https://example.com:abc/",
            "https://example.com:80x/",
            "https://[2001:db8::1]:abc/",
            "https://user@example.com:abc/",
            # Cloudflare rejects these when it replaces the list items.
            " https://example.com/",
            "\thttps://example.com/",
            "\u00a0https://example.com/",
            "https://example.com/a\tb",
            "https://example.com/a\nb",
            "https://example.com/a\rb",
            "https://example.com/a\x7fb",
            "https://example.com/%zz",
            "https://example.com/%2",
        ):
            self.assert_elements_fail_before_any_write(
                "redirect",
                [
                    {"redirect": {"source_url": "example.com/b", "target_url": "https://example.net"}},
                    {"redirect": {"source_url": "example.com/a", "target_url": value}},
                ],
                (
                    "elements[1].redirect.target_url must start with a scheme, have "
                    "no whitespace in its authority, and only digits in its port, must not start with whitespace "
                    "or contain an ASCII control character, and may use '%' only in a percent-escape such as %20"
                ),
                target_url=value,
            )

    def test_absolute_target_urls_are_accepted(self):
        for value in (
            "https://example.net",
            "http://example.net/d?x=1",
            "HTTPS://Example.net/d",
            "https://[2001:db8::1]/",
            # Cloudflare stores these as written.
            "https://example.com:99999/",
            "https://example.com:8443/ok",
            "https://[2001:db8::1]:8443/",
            "https://user@example.com/",
            "https://user:pass@example.com/",
            "https://-a.example.com/",
            "https://ex\u00e4mple.com/",
            "https://example.com/a b",
            "https://example.com/ ",
            "https://example.com/%2F",
            "ftp://example.com/",
            "https://",
            "https:///d",
        ):
            with self.subTest(value=value):
                client, _ignored = make_client()
                element = {"redirect": {"source_url": "example.com/a", "target_url": value}}

                result = self.run_module(
                    FakeModule(params(kind="redirect", elements=[element]), check_mode=True), client
                )

                self.assertTrue(result["changed"])

    def test_source_urls_cloudflare_stores_as_written_are_accepted(self):
        for value in (
            "example.com/",
            "example.com/a",
            "https://example.com/a",
            "http://example.com/a",
            "example.com/a:b",
            "example.com/a@b",
            "example.com/a%2Fb",
            "example.com/https://example.net",
            "example.com/%2F",
            "example.com/a%2Fb%41",
            # Cloudflare stores this as https://example.com/.
            "https://example.com:/",
        ):
            with self.subTest(source_url=value):
                self.assertIsNone(rules_lists.source_url_error(value))

    def test_valid_redirect_status_codes_are_accepted(self):
        for value in (301, 302, 307, 308, None):
            with self.subTest(status_code=value):
                client, _ignored = make_client()
                redirect = {"source_url": "example.com/a", "target_url": "https://example.net", "status_code": value}

                result = self.run_module(
                    FakeModule(params(kind="redirect", elements=[{"redirect": redirect}]), check_mode=True), client
                )

                self.assertTrue(result["changed"])

    def test_elements_with_unexpected_keys_fail_before_any_write(self):
        for kind, element, unexpected in (
            ("ip", {"ip": "192.0.2.1", "description": "office"}, ["description"]),
            ("ip", {"ip": "192.0.2.1", "asn": 5, "comment": "office"}, ["asn"]),
            ("asn", {"asn": 13335, "id": "item", "hostname": {"url_hostname": "example.com"}}, ["hostname"]),
        ):
            self.assert_elements_fail_before_any_write(
                kind,
                [element],
                f"elements[0] supports only {kind!r} and 'comment' for a Rules list of kind {kind!r}",
                unexpected_keys=unexpected,
            )

    def test_unknown_hostname_and_redirect_fields_fail_before_any_write(self):
        redirect = {"source_url": "example.com/a", "target_url": "https://example.net"}
        for kind, value, unknown, fields in (
            (
                "hostname",
                {"url_hostname": "example.com", "bogus": 1, "comment": "x"},
                ["elements[0].hostname.bogus", "elements[0].hostname.comment"],
                "exclude_exact_hostname, url_hostname",
            ),
            (
                "redirect",
                {**redirect, "preserve_path": True},
                ["elements[0].redirect.preserve_path"],
                ", ".join(rules_lists.ITEM_VALUE_FIELDS["redirect"]),
            ),
        ):
            self.assert_elements_fail_before_any_write(
                kind,
                [{kind: value}],
                f"elements[0].{kind} supports only {fields}",
                unsupported_fields=unknown,
            )

    def test_non_boolean_item_flags_fail_before_any_write(self):
        redirect = {"source_url": "example.com/a", "target_url": "https://example.net"}
        for kind, value, invalid in (
            (
                "hostname",
                {"url_hostname": "*.example.com", "exclude_exact_hostname": "false"},
                ["exclude_exact_hostname"],
            ),
            ("hostname", {"url_hostname": "*.example.com", "exclude_exact_hostname": 0}, ["exclude_exact_hostname"]),
            (
                "redirect",
                {**redirect, "include_subdomains": 1, "preserve_path_suffix": "yes", "subpath_matching": False},
                ["include_subdomains", "preserve_path_suffix"],
            ),
            ("redirect", {**redirect, "preserve_query_string": "true"}, ["preserve_query_string"]),
        ):
            paths = [f"elements[0].{kind}.{field}" for field in invalid]
            self.assert_elements_fail_before_any_write(
                kind,
                [{kind: value}],
                f"{', '.join(paths)} must be true or false",
                invalid_fields=paths,
            )

    def test_invalid_comments_fail_before_any_write(self):
        for comment in (1, True, ["a"], "x" * 501):
            self.assert_elements_fail_before_any_write(
                "ip",
                [{"ip": "192.0.2.1", "comment": "ok"}, {"ip": "192.0.2.2", "comment": comment}],
                "elements[1].comment must be a string of at most 500 characters",
                comment=comment,
            )

    def test_valid_item_fields_comments_and_nulls_are_accepted(self):
        redirect = {
            "source_url": "example.com/a",
            "target_url": "https://example.net",
            "include_subdomains": True,
            "preserve_path_suffix": False,
            "preserve_query_string": None,
            "subpath_matching": True,
        }
        for kind, element in (
            ("ip", {"ip": "192.0.2.1", "comment": "x" * 500}),
            ("ip", {"ip": "192.0.2.1", "comment": None}),
            ("ip", {"ip": "192.0.2.1", "asn": None, "id": "item", "created_on": "x", "modified_on": "y"}),
            ("redirect", {"redirect": redirect, "comment": ""}),
            ("hostname", {"hostname": {"url_hostname": "*.example.com", "exclude_exact_hostname": True}}),
            ("hostname", {"hostname": {"url_hostname": "example.com", "exclude_exact_hostname": None}}),
        ):
            with self.subTest(element=element):
                client, _ignored = make_client()

                result = self.run_module(FakeModule(params(kind=kind, elements=[element]), check_mode=True), client)

                self.assertTrue(result["changed"])

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
            ("hostname", {"hostname": {"url_hostname": "*.example.com", "exclude_exact_hostname": False}}),
        ):
            with self.subTest(element=element):
                client, _ignored = make_client()

                result = self.run_module(FakeModule(params(kind=kind, elements=[element]), check_mode=True), client)

                self.assertTrue(result["changed"])

    def test_valid_hostname_and_asn_elements_are_accepted(self):
        for kind, element in (
            ("hostname", {"hostname": {"url_hostname": "*.example.com"}}),
            ("hostname", {"hostname": {"url_hostname": "example.com"}}),
            ("hostname", {"hostname": {"url_hostname": "a_b.example.com"}}),
            ("hostname", {"hostname": {"url_hostname": "example.com."}}),
            ("hostname", {"hostname": {"url_hostname": "Example.COM"}}),
            ("hostname", {"hostname": {"url_hostname": "xn--bcher-kva.example"}}),
            ("hostname", {"hostname": {"url_hostname": "a-b.example.com"}}),
            ("hostname", {"hostname": {"url_hostname": "*.example.com."}}),
            ("hostname", {"hostname": {"url_hostname": f"{'a' * 63}.example.com"}}),
            ("hostname", {"hostname": {"url_hostname": ".".join(["a" * 63] * 3 + ["b" * 61])}}),
            ("hostname", {"hostname": {"url_hostname": ".".join(["a" * 63] * 3 + ["b" * 61]) + "."}}),
            ("hostname", {"hostname": {"url_hostname": "*." + ".".join(["a" * 63] * 3 + ["b" * 59])}}),
            # Cloudflare stores a wildcard of a 252-character name, 254 characters in all.
            ("hostname", {"hostname": {"url_hostname": "*." + ".".join(["a" * 63] * 3 + ["b" * 56, "com"])}}),
            ("asn", {"asn": 1}),
            ("asn", {"asn": 13335}),
            ("asn", {"asn": 4294967295}),
        ):
            with self.subTest(element=element):
                client, _ignored = make_client()

                result = self.run_module(FakeModule(params(kind=kind, elements=[element]), check_mode=True), client)

                self.assertTrue(result["changed"])

    def test_repeated_kind_values_fail_before_any_write(self):
        for kind, elements, value in (
            ("ip", [{"ip": "1.2.3.4", "comment": "a"}, {"ip": "1.2.3.4/32"}], "1.2.3.4"),
            ("ip", [{"ip": "2001:DB8::1/128"}, {"ip": "2001:db8::1", "comment": "b"}], "2001:db8::1"),
            ("asn", [{"asn": 13335}, {"asn": 13335, "comment": "b"}], 13335),
        ):
            self.assert_elements_fail_before_any_write(
                kind,
                elements,
                f"elements must not repeat the {kind!r} value {value!r}",
                **{kind: value},
            )

    def test_repeated_identity_fields_fail_before_any_write(self):
        redirect = {"source_url": "example.com/a", "target_url": "https://example.net/1"}
        for kind, elements, field, value in (
            (
                "hostname",
                [
                    {"hostname": {"url_hostname": "*.example.com"}},
                    {"hostname": {"url_hostname": "*.example.com", "exclude_exact_hostname": False}},
                ],
                "url_hostname",
                "*.example.com",
            ),
            (
                "hostname",
                [
                    {"hostname": {"url_hostname": "*.example.com", "exclude_exact_hostname": True}},
                    {"hostname": {"url_hostname": "*.example.com", "exclude_exact_hostname": False}},
                ],
                "url_hostname",
                "*.example.com",
            ),
            (
                "redirect",
                [{"redirect": redirect}, {"redirect": {**redirect, "target_url": "https://example.net/2"}}],
                "source_url",
                "example.com/a",
            ),
            (
                "redirect",
                [{"redirect": {**redirect, "status_code": 301}}, {"redirect": {**redirect, "status_code": 302}}],
                "source_url",
                "example.com/a",
            ),
            (
                "redirect",
                [{"redirect": redirect}, {"redirect": {**redirect, "include_subdomains": True}}],
                "source_url",
                "example.com/a",
            ),
        ):
            self.assert_elements_fail_before_any_write(
                kind,
                elements,
                f"elements must not repeat the '{kind}.{field}' value {value!r}",
                **{field: value},
            )

    def test_identity_values_cloudflare_accepts_together_are_accepted(self):
        for kind, values in (
            ("hostname", ("example.com", "Example.com", "example.com.")),
            (
                "redirect",
                (
                    "example.com/a",
                    "example.com/A",
                    "Example.com/a",
                    "example.com/a/",
                    "https://example.com/a",
                    "example.com/",
                    "example.com//",
                ),
            ),
        ):
            with self.subTest(kind=kind):
                client, _ignored = make_client()
                field = rules_lists.IDENTITY_FIELDS[kind]
                elements = [
                    {
                        kind: (
                            {field: value, "target_url": "https://example.net"}
                            if kind == "redirect"
                            else {field: value}
                        )
                    }
                    for value in values
                ]

                result = self.run_module(FakeModule(params(kind=kind, elements=elements), check_mode=True), client)

                self.assertTrue(result["changed"])

    def test_exclude_exact_hostname_false_requires_a_wildcard_before_any_write(self):
        self.assert_elements_fail_before_any_write(
            "hostname",
            [
                {"hostname": {"url_hostname": "*.example.org", "exclude_exact_hostname": False}},
                {"hostname": {"url_hostname": "example.com", "exclude_exact_hostname": False}},
            ],
            "elements[1].hostname.exclude_exact_hostname may be false only for a wildcard "
            "url_hostname such as '*.example.com'",
            url_hostname="example.com",
        )

    def test_exclude_exact_hostname_default_on_exact_hostname_is_accepted(self):
        # The default, true, is omitted from the request, so Cloudflare accepts it.
        for value in (None, True):
            with self.subTest(exclude_exact_hostname=value):
                current = {**CURRENT, "kind": "hostname", "num_items": 1}
                client, api = make_client([current], items=[{"hostname": {"url_hostname": "example.com"}}])
                elements = [{"hostname": {"url_hostname": "example.com", "exclude_exact_hostname": value}}]

                result = self.run_module(FakeModule(params(kind="hostname", elements=elements)), client)

                api.items.update.assert_not_called()
                self.assertFalse(result["changed"])

    def test_wildcard_with_its_exact_hostname_fails_before_any_write(self):
        for wildcard in ({}, {"exclude_exact_hostname": True}, {"exclude_exact_hostname": False}):
            self.assert_elements_fail_before_any_write(
                "hostname",
                [
                    {"hostname": {"url_hostname": "example.com"}},
                    {"hostname": {"url_hostname": "*.example.com", **wildcard}},
                ],
                "elements must not set both 'url_hostname' values '*.example.com' and 'example.com'",
                url_hostname=["*.example.com", "example.com"],
            )

    def test_hostnames_cloudflare_accepts_together_are_accepted(self):
        for hostnames in (
            ("*.example.com", "a.example.com"),
            ("*.example.com", "*.a.example.com"),
            ("example.com", "EXAMPLE.com"),
            ("*.example.com", "EXAMPLE.com"),
        ):
            with self.subTest(hostnames=hostnames):
                client, _ignored = make_client()
                elements = [{"hostname": {"url_hostname": hostname}} for hostname in hostnames]

                result = self.run_module(
                    FakeModule(params(kind="hostname", elements=elements), check_mode=True), client
                )

                self.assertTrue(result["changed"])

    def test_full_length_prefixes_match_bare_addresses(self):
        current = {**CURRENT, "num_items": 2}
        items = [{"ip": "1.2.3.4"}, {"ip": "2001:db8::1"}]
        for elements in (
            [{"ip": "1.2.3.4/32"}, {"ip": "2001:db8::1/128"}],
            [{"ip": "1.2.3.4/032"}, {"ip": "2001:DB8::1/128"}, {"ip": "1.2.3.4"}],
        ):
            with self.subTest(elements=elements):
                client, api = make_client([current], items=items)

                result = self.run_module(FakeModule(params(elements=elements)), client)

                api.items.update.assert_not_called()
                self.assertFalse(result["changed"])

    def test_prefix_lengths_with_leading_zeros_match_stored_prefixes(self):
        current = {**CURRENT, "num_items": 2}
        items = [{"ip": "10.0.0.0/8"}, {"ip": "2001:db8::/32"}]
        client, api = make_client([current], items=items)

        result = self.run_module(FakeModule(params(elements=[{"ip": "10.0.0.0/08"}, {"ip": "2001:db8::/032"}])), client)

        api.items.update.assert_not_called()
        self.assertFalse(result["changed"])

    def test_list_items_reads_every_cursor_page_through_the_sdk(self):
        stamps = {"created_on": "2024-01-01T00:00:00Z", "modified_on": "2024-01-01T00:00:00Z"}
        redirect = {
            "source_url": "example.com/",
            "target_url": "https://example.net/",
            "include_subdomains": False,
            "preserve_path_suffix": True,
            "preserve_query_string": False,
            "status_code": 301,
            "subpath_matching": False,
        }
        hostname = {"url_hostname": "*.example.com", "exclude_exact_hostname": False}
        pages = {
            None: (
                [{"id": "a", **stamps, "redirect": redirect}, {"id": "b", **stamps, "hostname": hostname}],
                {"cursors": {"after": "page2"}},
            ),
            "page2": (
                [{"id": "c", **stamps, "asn": 13335, "comment": ""}, {"id": "d", **stamps, "ip": "10.0.0.0/8"}],
                {"cursors": {}},
            ),
        }
        requests = []

        def respond(request):
            requests.append(request)
            result, result_info = pages[request.url.params.get("cursor")]
            body = {"success": True, "errors": [], "messages": [], "result": result, "result_info": result_info}
            return httpx.Response(200, json=body)

        client = cloudflare.Cloudflare(
            api_token="EXAMPLE-token",
            http_client=httpx.Client(transport=httpx.MockTransport(respond)),
        )
        with client:
            items = rules_lists.list_items(client, "account", "list")

        self.assertEqual(
            [(request.url.path, dict(request.url.params)) for request in requests],
            [
                ("/client/v4/accounts/account/rules/lists/list/items", {"per_page": "500"}),
                ("/client/v4/accounts/account/rules/lists/list/items", {"per_page": "500", "cursor": "page2"}),
            ],
        )
        self.assertEqual(
            items,
            [
                {"id": "a", **stamps, "redirect": redirect},
                {"id": "b", **stamps, "hostname": hostname},
                {"id": "c", **stamps, "asn": 13335, "comment": ""},
                {"id": "d", **stamps, "ip": "10.0.0.0/8"},
            ],
        )
        self.assertEqual(
            rules_lists.normalize_items(items),
            [
                {"asn": 13335},
                {"hostname": hostname},
                {"ip": "10.0.0.0/8"},
                {"redirect": {"source_url": "example.com/", "target_url": "https://example.net/"}},
            ],
        )

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

    def test_created_list_is_kept_when_items_are_rejected(self):
        created = {"id": "list", "name": "addresses", "kind": "ip", "description": "addresses", "num_items": 0}
        body = {"success": False, "errors": [{"code": 10026, "message": "filter parsing error"}], "messages": []}
        client, api = make_client(created=created)
        api.items.update.side_effect = status_error(400, body)

        with (
            patch.object(rules_lists.time, "monotonic", return_value=1),
            self.assertRaises(cloudflare.BadRequestError) as raised,
        ):
            rules_lists.run(FakeModule(params(elements=[{"ip": "192.0.2.1"}])), client)

        api.delete.assert_not_called()
        self.assertEqual(
            raised.exception._cloudflare_message, "Cloudflare API request failed while submitting the Rules list items"
        )
        self.assertEqual(
            raised.exception._cloudflare_context,
            {"account_id": "account", "rules_list_id": "list", "changed": True, "rules_list": created},
        )

    def test_created_list_is_kept_when_the_items_operation_fails(self):
        created = {"id": "list", "name": "addresses", "kind": "ip", "description": "addresses", "num_items": 0}
        client, api = make_client(created=created)
        api.bulk_operations.get.return_value = {"id": "operation", "status": "failed", "error": "bad"}

        with patch.object(rules_lists.time, "monotonic", return_value=1):
            result = self.run_module(FakeModule(params(elements=[{"ip": "192.0.2.1"}])), client)

        api.delete.assert_not_called()
        self.assertEqual(result["msg"], "Rules list items operation failed")
        self.assertEqual(result["operation"], {"id": "operation", "status": "failed", "error": "bad"})

    def test_wrong_operation_id_fails(self):
        created = {"id": "list", "name": "addresses", "kind": "ip", "description": "addresses", "num_items": 0}
        client, api = make_client(created=created)
        api.bulk_operations.get.return_value = {"id": "other", "status": "completed"}

        with patch.object(rules_lists.time, "monotonic", return_value=1):
            result = self.run_module(FakeModule(params(elements=[{"ip": "192.0.2.1"}])), client)

        api.delete.assert_not_called()
        self.assertEqual(result["msg"], "Cloudflare API returned the wrong Rules list operation")
        self.assertEqual(result["operation_id"], "operation")

    def test_existing_list_is_not_deleted_when_items_are_rejected(self):
        current = {**CURRENT, "num_items": 0}
        client, api = make_client([current])
        api.items.update.side_effect = status_error(400)
        api.bulk_operations.get.return_value = {"id": "operation", "status": "failed"}

        with (
            patch.object(rules_lists.time, "monotonic", return_value=1),
            self.assertRaises(cloudflare.BadRequestError),
        ):
            rules_lists.run(FakeModule(params(elements=[{"ip": "192.0.2.1"}])), client)

        api.items.update.side_effect = None
        with patch.object(rules_lists.time, "monotonic", return_value=1):
            result = self.run_module(FakeModule(params(elements=[{"ip": "192.0.2.1"}])), client)

        self.assertEqual(result["msg"], "Rules list items operation failed")
        api.delete.assert_not_called()

    def test_rejects_completed_update_with_wrong_items(self):
        current = {**CURRENT, "num_items": 0}
        client, _ignored = make_client([current], fetched=current)

        with patch.object(rules_lists.time, "monotonic", return_value=1):
            result = self.run_module(FakeModule(params(elements=[{"ip": "192.0.2.1"}])), client)

        self.assertEqual(
            result["msg"], "Cloudflare did not apply the requested Rules list items: requested '192.0.2.1', stored None"
        )
        self.assertEqual(result["missing_items"], [{"ip": "192.0.2.1"}])
        self.assertEqual(result["unexpected_items"], [])
        self.assertEqual(result["rules_list_id"], "list")
        self.assertTrue(result["changed"])

    def test_not_applied_failure_message_pairs_a_bounded_number_of_items(self):
        current = {**CURRENT, "num_items": 0}
        elements = [{"ip": f"192.0.2.{index}"} for index in range(1, 13)]
        stored = [{"ip": f"198.51.100.{index}"} for index in range(1, 13)]
        client, _ignored = make_client([current], items=stored, fetched=current)

        with patch.object(rules_lists.time, "monotonic", return_value=1):
            result = self.run_module(FakeModule(params(elements=elements)), client)

        self.assertEqual(result["msg"].count("requested '"), rules_lists.MESSAGE_ITEMS)
        self.assertTrue(result["msg"].endswith("; 2 more requested items are listed in missing_items"))
        self.assertEqual(len(result["missing_items"]), 12)
        self.assertEqual(len(result["unexpected_items"]), 12)

    def test_not_applied_failure_names_unrequested_stored_values(self):
        current = {**CURRENT, "num_items": 0}
        client, _ignored = make_client([current], items=[{"ip": "192.0.2.1"}, {"ip": "192.0.2.9"}], fetched=current)

        with patch.object(rules_lists.time, "monotonic", return_value=1):
            result = self.run_module(FakeModule(params(elements=[{"ip": "192.0.2.1"}])), client)

        self.assertEqual(
            result["msg"],
            "Cloudflare did not apply the requested Rules list items: stored '192.0.2.9', not requested",
        )
        self.assertEqual(result["missing_items"], [])
        self.assertEqual(result["unexpected_items"], [{"ip": "192.0.2.9"}])

    def test_not_applied_failure_names_requested_and_stored_values(self):
        redirect = {"target_url": "https://example.net/"}
        current = {**CURRENT, "kind": "redirect", "num_items": 0}
        stored = [
            {"redirect": {**redirect, "source_url": "example.com/"}},
            {"redirect": {**redirect, "source_url": "example.com/b"}},
            {"redirect": {**redirect, "source_url": "https://example.com/c"}},
        ]
        elements = [
            {"redirect": {**redirect, "source_url": "example.com"}},
            {"redirect": {**redirect, "source_url": "example.com/b"}},
            {"redirect": {**redirect, "source_url": "HTTPS://example.com/c"}},
        ]
        client, _ignored = make_client([current], items=stored, fetched=current)

        with patch.object(rules_lists.time, "monotonic", return_value=1):
            result = self.run_module(FakeModule(params(kind=None, elements=elements)), client)

        self.assertEqual(
            result["msg"],
            "Cloudflare did not apply the requested Rules list items: "
            "requested 'HTTPS://example.com/c', stored 'https://example.com/c'; "
            "requested 'example.com', stored 'example.com/'",
        )
        self.assertEqual(result["missing_items"], [elements[2], elements[0]])
        self.assertEqual(result["unexpected_items"], [stored[0], stored[2]])

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

    def test_failures_after_create_report_the_created_list(self):
        created = {"id": "list", "name": "addresses", "kind": "ip", "description": "addresses", "num_items": 0}
        written = {"changed": True, "account_id": "account", "rules_list_id": "list", "rules_list": created}
        operations = {
            "failed": {"id": "operation", "status": "failed"},
            "wrong": {"id": "other", "status": "completed"},
            "malformed": {"id": "operation"},
            "unknown": {"id": "operation", "status": "lost"},
        }
        for case, operation in operations.items():
            with self.subTest(case=case):
                client, api = make_client(created=created)
                api.bulk_operations.get.return_value = operation

                with patch.object(rules_lists.time, "monotonic", return_value=1):
                    result = self.run_module(FakeModule(params(elements=[{"ip": "192.0.2.1"}])), client)

                self.assertEqual({key: result[key] for key in written}, written)
                self.assertEqual(result["operation_id"], "operation")

        client, api = make_client(created=created)
        api.items.update.return_value = {}
        with patch.object(rules_lists.time, "monotonic", return_value=1):
            result = self.run_module(FakeModule(params(elements=[{"ip": "192.0.2.1"}])), client)

        self.assertEqual(result["msg"], "Rules list items submission did not return an operation id")
        self.assertEqual({key: result[key] for key in written}, written)

        client, api = make_client(created=created)
        with patch.object(rules_lists.time, "monotonic", side_effect=[1, 100]):
            result = self.run_module(FakeModule(params(elements=[{"ip": "192.0.2.1"}])), client)

        self.assertEqual(result["msg"], "Timed out submitting the Rules list items operation")
        self.assertEqual({key: result[key] for key in written}, written)

    def test_created_list_of_another_kind_reports_the_write(self):
        created = {"id": "list", "name": "addresses", "kind": "asn", "description": "addresses"}
        client, api = make_client(created=created)

        result = self.run_module(FakeModule(params()), client)

        api.create.assert_called_once()
        self.assertEqual(result["msg"], "Cloudflare API returned the wrong Rules list")
        self.assertTrue(result["changed"])
        self.assertEqual(result["rules_list"], created)
        self.assertEqual(result["rules_list_id"], "list")
        self.assertEqual(result["account_id"], "account")

    def test_failure_after_items_update_reports_the_write(self):
        fetched = {**CURRENT, "kind": "asn"}
        client, api = make_client([CURRENT], fetched=fetched)

        with patch.object(rules_lists.time, "monotonic", return_value=1):
            result = self.run_module(FakeModule(params(elements=[{"ip": "192.0.2.1"}])), client)

        api.items.update.assert_called_once()
        self.assertEqual(result["msg"], "Cloudflare API returned the wrong Rules list")
        self.assertTrue(result["changed"])
        self.assertEqual(result["rules_list"], fetched)
        self.assertEqual(result["items_operation"], {"id": "operation", "status": "completed"})


class CanonicalIpTests(TestCase):
    def test_normalizes_equivalent_addresses(self):
        self.assertEqual(
            rules_lists.normalize_items([{"ip": "2400:d400:0011:19::2"}, {"ip": "2001:DB8:0::/32"}]),
            rules_lists.normalize_items([{"ip": "2400:d400:11:19::2"}, {"ip": "2001:db8::/32"}]),
        )
        self.assertEqual(rules_lists.canonical_ip("not-an-ip"), "not-an-ip")
