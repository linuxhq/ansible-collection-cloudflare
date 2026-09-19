# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

import json
import signal
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from types import SimpleNamespace
from unittest import TestCase
from unittest.mock import Mock, patch

import httpx
from cloudflare import Cloudflare

from ansible_collections.linuxhq.cloudflare.plugins.modules import rules_lists
from ansible_collections.linuxhq.cloudflare.tests.unit.plugins.modules.utils import (
    FakeModule,
    ModuleExit,
    ModuleFail,
)


class ApiConnectionError(Exception):
    pass


class ApiStatusError(Exception):
    def __init__(self, message, status_code=None):
        super().__init__(message)
        self.status_code = status_code


ERRORS = SimpleNamespace(
    APIConnectionError=ApiConnectionError,
    APIStatusError=ApiStatusError,
)


class Model:
    def __init__(self, value):
        self.value = value

    def to_dict(self):
        return self.value


def params(**updates):
    values = {
        "account_id": "account",
        "name": "addresses",
        "kind": "ip",
        "description": None,
        "elements": None,
        "operation_timeout": 30,
    }
    values.update(updates)
    return values


class RulesListsTests(TestCase):
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

    def test_submit_retries_pending_operation_within_deadline(self):
        pending = ApiStatusError("bulk operation pending", status_code=409)

        with (
            patch.object(rules_lists, "cloudflare", ERRORS),
            patch.object(
                rules_lists,
                "put_result",
                side_effect=[pending, {"operation_id": "operation"}],
            ) as put,
            patch.object(
                rules_lists.time,
                "monotonic",
                side_effect=[1, 2, 3, 4],
            ),
            patch.object(rules_lists.time, "sleep") as sleep,
        ):
            result = rules_lists.submit_items(
                {},
                "account",
                "list",
                [{"ip": "192.0.2.1"}],
                30,
            )

        self.assertEqual(result, {"operation_id": "operation"})
        self.assertEqual(put.call_count, 2)
        sleep.assert_called_once_with(rules_lists.OPERATION_POLL_SECONDS)

    def test_submit_honors_subsecond_and_expired_deadlines(self):
        with (
            patch.object(rules_lists.time, "monotonic", return_value=0.5),
            patch.object(rules_lists, "put_result", return_value={"id": "operation"}) as put,
        ):
            rules_lists.submit_items({}, "account", "list", [], 1)

        put.assert_called_once_with(
            {},
            "/accounts/account/rules/lists/list/items",
            [],
            timeout=0.5,
        )

        with (
            patch.object(rules_lists.time, "monotonic", return_value=1),
            self.assertRaisesRegex(rules_lists.CloudflareResponseError, "Timed out submitting"),
        ):
            rules_lists.submit_items({}, "account", "list", [], 1)

    def test_wait_rejects_missing_operation_identifier(self):
        for operation in ({}, {"operation_id": " operation "}):
            with (
                self.subTest(operation=operation),
                self.assertRaises(ModuleFail) as raised,
            ):
                rules_lists.wait_for_operation(FakeModule({}), {}, "account", operation, 30)

            self.assertEqual(
                raised.exception.values["msg"],
                "Rules list items submission did not return an operation id",
            )

    def test_wait_returns_completed_operation(self):
        module = FakeModule({})
        completed = {"id": "operation", "status": "completed"}

        with (
            patch.object(rules_lists.time, "monotonic", return_value=1),
            patch.object(rules_lists, "get_result", return_value=completed) as get,
        ):
            result = rules_lists.wait_for_operation(
                module,
                {},
                "account",
                {"operation_id": "operation"},
                30,
            )

        get.assert_called_once_with(
            {},
            "/accounts/account/rules/lists/bulk_operations/operation",
            default={},
            timeout=29,
        )
        self.assertEqual(result, completed)

    def test_rejects_responses_received_after_deadline(self):
        with (
            patch.object(rules_lists.time, "monotonic", side_effect=[0, 2]),
            patch.object(rules_lists, "put_result", return_value={"operation_id": "operation"}),
            self.assertRaisesRegex(rules_lists.CloudflareResponseError, "Timed out submitting"),
        ):
            rules_lists.submit_items({}, "account", "list", [], 1)

        with (
            patch.object(rules_lists.time, "monotonic", side_effect=[0, 2]),
            patch.object(rules_lists, "get_result", return_value={"id": "operation", "status": "completed"}),
            self.assertRaises(ModuleFail) as raised,
        ):
            rules_lists.wait_for_operation(FakeModule({}), {}, "account", {"id": "operation"}, 1)

        self.assertIn("Timed out waiting", raised.exception.values["msg"])

    def test_deadline_restores_alarm_after_success_and_error(self):
        original_handler = signal.getsignal(signal.SIGALRM)
        for fail in (False, True):
            with self.subTest(fail=fail):
                try:
                    with rules_lists.operation_deadline(5):
                        if fail:
                            raise ValueError("failure")
                except ValueError:
                    pass

                self.assertEqual(signal.getsignal(signal.SIGALRM), original_handler)
                self.assertEqual(signal.getitimer(signal.ITIMER_REAL), (0, 0))

    def test_deadline_interrupts_slow_submission_and_polling(self):
        body = json.dumps({"success": True, "result": {"id": "operation", "status": "completed"}}).encode()

        class Handler(BaseHTTPRequestHandler):
            def log_message(self, *args):
                pass

            def respond(self):
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                try:
                    for offset in range(0, len(body), 5):
                        time.sleep(0.1)
                        self.wfile.write(body[offset : offset + 5])
                        self.wfile.flush()
                except (BrokenPipeError, ConnectionResetError):
                    pass

            def do_GET(self):
                self.respond()

            def do_PUT(self):
                self.rfile.read(int(self.headers["Content-Length"]))
                self.respond()

        server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        thread = threading.Thread(target=server.serve_forever, kwargs={"poll_interval": 0.01}, daemon=True)
        thread.start()
        original_handler = signal.getsignal(signal.SIGALRM)
        try:
            with Cloudflare(
                api_token="EXAMPLE_TOKEN",
                base_url=f"http://127.0.0.1:{server.server_port}",
                http_client=httpx.Client(trust_env=False),
            ) as client:
                for submit in (True, False):
                    with self.subTest(submit=submit):
                        with (
                            self.assertRaisesRegex(rules_lists.CloudflareResponseError, "Timed out completing"),
                            rules_lists.operation_deadline(0.5) as deadline,
                        ):
                            if submit:
                                rules_lists.submit_items(client, "account", "list", [], deadline)
                            else:
                                rules_lists.wait_for_operation(
                                    FakeModule({}), client, "account", {"id": "operation"}, deadline
                                )

                        self.assertEqual(signal.getsignal(signal.SIGALRM), original_handler)
                        self.assertEqual(signal.getitimer(signal.ITIMER_REAL), (0, 0))
        finally:
            server.shutdown()
            server.server_close()
            thread.join()

    def test_deadline_expiring_during_cleanup_is_reported_cleanly(self):
        original_handler = signal.getsignal(signal.SIGALRM)
        with (
            patch.object(rules_lists.signal, "setitimer", side_effect=[(0, 0), rules_lists.OperationDeadlineExpired()]),
            self.assertRaisesRegex(rules_lists.CloudflareResponseError, "Timed out completing"),
            rules_lists.operation_deadline(5),
        ):
            pass

        self.assertEqual(signal.getsignal(signal.SIGALRM), original_handler)

    def test_wait_uses_remaining_subsecond_budget(self):
        module = FakeModule({})
        completed = {"id": "operation", "status": "completed"}

        with (
            patch.object(rules_lists.time, "monotonic", return_value=0.5),
            patch.object(rules_lists, "get_result", return_value=completed) as get,
        ):
            result = rules_lists.wait_for_operation(module, {}, "account", {"id": "operation"}, 1)

        get.assert_called_once_with(
            {},
            "/accounts/account/rules/lists/bulk_operations/operation",
            default={},
            timeout=0.5,
        )
        self.assertEqual(result, completed)

    def test_wait_rejects_unknown_operation_status(self):
        module = FakeModule({})

        with (
            patch.object(rules_lists.time, "monotonic", return_value=1),
            patch.object(
                rules_lists,
                "get_result",
                return_value={"id": "operation", "status": "unknown"},
            ),
            self.assertRaises(ModuleFail) as raised,
        ):
            rules_lists.wait_for_operation(
                module,
                {},
                "account",
                {"operation_id": "operation"},
                30,
            )

        self.assertEqual(
            raised.exception.values["msg"],
            "Cloudflare API returned an unknown Rules list operation status",
        )

    def test_check_mode_does_not_create(self):
        module = FakeModule(params(), check_mode=True)

        with (
            patch.object(rules_lists, "find_by_field", return_value=None),
            patch.object(rules_lists, "post_result") as post,
            self.assertRaises(ModuleExit) as raised,
        ):
            rules_lists.ensure_present(module, {})

        post.assert_not_called()
        self.assertTrue(raised.exception.values["changed"])

    def test_existing_list_without_managed_items_is_unchanged(self):
        module = FakeModule(params())
        current = {
            "id": "list",
            "name": "addresses",
            "kind": "ip",
            "description": "current",
        }

        with (
            patch.object(rules_lists, "find_by_field", return_value=current),
            patch.object(rules_lists, "put_result") as put,
            self.assertRaises(ModuleExit) as raised,
        ):
            rules_lists.ensure_present(module, {})

        put.assert_not_called()
        self.assertFalse(raised.exception.values["changed"])

    def test_rejects_update_response_with_wrong_description(self):
        module = FakeModule(params(description="desired"))
        current = {
            "id": "list",
            "name": "addresses",
            "kind": "ip",
            "description": "current",
        }

        with (
            patch.object(rules_lists, "find_by_field", return_value=current),
            patch.object(rules_lists, "put_result", return_value=current),
            self.assertRaises(ModuleFail) as raised,
        ):
            rules_lists.ensure_present(module, {})

        self.assertIn("did not apply", raised.exception.values["msg"])

    def test_metadata_update_omits_items_operation(self):
        module = FakeModule(params(description="desired"))
        current = {
            "id": "list",
            "name": "addresses",
            "kind": "ip",
            "description": "current",
        }
        updated = {**current, "description": "desired"}

        with (
            patch.object(rules_lists, "find_by_field", return_value=current),
            patch.object(rules_lists, "put_result", return_value=updated),
            self.assertRaises(ModuleExit) as raised,
        ):
            rules_lists.ensure_present(module, {})

        self.assertNotIn("items_operation", raised.exception.values)

    def test_rejects_kind_change(self):
        module = FakeModule(params(kind="hostname", elements=[]))
        current = {"id": "list", "name": "addresses", "kind": "ip"}

        with (
            patch.object(rules_lists, "find_by_field", return_value=current),
            self.assertRaises(ModuleFail) as raised,
        ):
            rules_lists.ensure_present(module, Mock())

        self.assertEqual(
            raised.exception.values["msg"],
            "An existing Rules list kind cannot be changed",
        )

    def test_generated_sdk_iterator_reads_all_current_items(self):
        module = FakeModule(params(elements=[{"ip": "192.0.2.1"}, {"ip": "192.0.2.2"}]))
        current = {
            "id": "list",
            "name": "addresses",
            "kind": "ip",
            "num_items": 2,
        }
        client = Mock()
        client.rules.lists.items.list.return_value = [
            Model({"ip": "192.0.2.1"}),
            Model({"ip": "192.0.2.2"}),
        ]

        with (
            patch.object(rules_lists, "find_by_field", return_value=current),
            patch.object(rules_lists, "submit_items") as submit,
            self.assertRaises(ModuleExit) as raised,
        ):
            rules_lists.ensure_present(module, client)

        client.rules.lists.items.list.assert_called_once_with(
            "list",
            account_id="account",
            per_page=rules_lists.ITEMS_PER_PAGE,
        )
        submit.assert_not_called()
        self.assertFalse(raised.exception.values["changed"])

    def test_submits_normalized_items(self):
        elements = [{"ip": "192.0.2.1", "comment": ""}, {"ip": "192.0.2.1"}]
        module = FakeModule(params(elements=elements))
        current = {
            "id": "list",
            "name": "addresses",
            "kind": "ip",
            "num_items": 0,
        }
        client = Mock()
        client.rules.lists.items.list.return_value = [Model({"ip": "192.0.2.1"})]

        with (
            patch.object(rules_lists, "find_by_field", return_value=current),
            patch.object(rules_lists, "submit_items", return_value={"id": "operation"}) as submit,
            patch.object(
                rules_lists,
                "wait_for_operation",
                return_value={"id": "operation", "status": "completed"},
            ),
            patch.object(rules_lists, "get_result", return_value=current),
            patch.object(rules_lists.time, "monotonic", return_value=1),
            self.assertRaises(ModuleExit),
        ):
            rules_lists.ensure_present(module, client)

        submit.assert_called_once_with(client, "account", "list", [{"ip": "192.0.2.1"}], 31)

    def test_rejects_completed_update_with_wrong_items(self):
        module = FakeModule(params(elements=[{"ip": "192.0.2.1"}]))
        current = {
            "id": "list",
            "name": "addresses",
            "kind": "ip",
            "num_items": 0,
        }
        client = Mock()
        client.rules.lists.items.list.return_value = []

        with (
            patch.object(rules_lists, "find_by_field", return_value=current),
            patch.object(rules_lists, "submit_items", return_value={"id": "operation"}),
            patch.object(
                rules_lists,
                "wait_for_operation",
                return_value={"id": "operation", "status": "completed"},
            ),
            patch.object(rules_lists, "get_result", return_value=current),
            patch.object(rules_lists.time, "monotonic", return_value=1),
            self.assertRaises(ModuleFail) as raised,
        ):
            rules_lists.ensure_present(module, client)

        self.assertIn("did not apply", raised.exception.values["msg"])
