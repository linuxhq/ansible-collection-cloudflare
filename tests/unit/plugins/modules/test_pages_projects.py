# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from unittest import TestCase
from unittest.mock import Mock

from ansible_collections.linuxhq.cloudflare.plugins.modules import pages_projects
from ansible_collections.linuxhq.cloudflare.tests.unit.plugins.modules.utils import (
    FakeModule,
    ModuleExit,
    ModuleFail,
    status_error,
)

PROJECT = {"name": "docs", "production_branch": "main"}


def params(**updates):
    values = {
        "account_id": "account",
        "name": "docs",
        "production_branch": "main",
        "build_config": None,
        "deployment_configs": None,
        "rotate_secrets": False,
        "source": None,
        "domains": None,
        "state": "present",
    }
    values.update(updates)
    return values


def client_with(projects=(), created=None, edited=None, domains=(), created_domain=None):
    """Return a client whose successive project reads return projects; None means not found."""
    client = Mock()
    api = client.pages.projects
    api.get.side_effect = [status_error(404) if project is None else project for project in projects]
    api.create.return_value = created
    api.edit.return_value = edited
    api.domains.list.return_value = list(domains)
    api.domains.create.return_value = created_domain
    return client, api


class PagesProjectsTests(TestCase):
    def run_module(self, module, client):
        with self.assertRaises((ModuleExit, ModuleFail)) as raised:
            pages_projects.run(module, client)

        return raised.exception.values

    def test_secret_values_are_ignored_without_mutating_payload(self):
        payload = {
            "build_config": {"web_analytics_token": "analytics-secret"},
            "deployment_configs": {
                "production": {
                    "env_vars": {
                        "TOKEN": {"type": "secret_text", "value": "secret"},
                        "MODE": {"type": "plain_text", "value": "prod"},
                    }
                }
            },
        }

        comparable = pages_projects.comparable_pages_payload(payload)

        self.assertEqual(
            comparable,
            {
                "build_config": {"web_analytics_token": "analytics-secret"},
                "deployment_configs": {
                    "production": {
                        "env_vars": {
                            "TOKEN": {"type": "secret_text"},
                            "MODE": {"type": "plain_text", "value": "prod"},
                        }
                    }
                },
            },
        )
        self.assertEqual(payload["deployment_configs"]["production"]["env_vars"]["TOKEN"]["value"], "secret")
        self.assertEqual(payload["build_config"]["web_analytics_token"], "analytics-secret")

    def test_create_requires_production_branch(self):
        client, api = client_with([None])

        result = self.run_module(FakeModule(params(production_branch=None)), client)

        api.get.assert_called_once_with(project_name="docs", account_id="account")
        api.create.assert_not_called()
        self.assertEqual(result["msg"], "production_branch is required when creating a Pages project")

    def test_check_mode_does_not_create(self):
        client, api = client_with([None])

        result = self.run_module(FakeModule(params(), check_mode=True), client)

        api.create.assert_not_called()
        self.assertTrue(result["changed"])

    def test_rotation_requires_credentials(self):
        for updates in (
            {},
            {"deployment_configs": {"production": {"env_vars": {"MODE": {"type": "plain_text", "value": "prod"}}}}},
            {"deployment_configs": {"production": {"env_vars": {"OLD": None}}}},
            {"build_config": {"web_analytics_token": None}},
        ):
            with self.subTest(updates=updates):
                client, api = client_with()

                result = self.run_module(FakeModule(params(rotate_secrets=True, **updates)), client)

                api.get.assert_not_called()
                self.assertEqual(
                    result["msg"],
                    "rotate_secrets requires a secret_text value or build_config.web_analytics_token",
                )

    def test_rejects_invalid_requested_domains_before_api_calls(self):
        for state in ("present", "absent"):
            with self.subTest(state=state):
                client, api = client_with()

                result = self.run_module(
                    FakeModule(params(state=state, domains=[{"name": " invalid.example.com"}])), client
                )

                api.get.assert_not_called()
                self.assertEqual(result["msg"], "Each Pages project domain requires a valid name")

    def test_rejects_unsupported_domain_names_before_api_calls(self):
        for name in (
            "p38fix.linuxhq.dev.",
            "bücher.example.com",
            "a_b.example.com",
            "*.example.com",
            "a..example.com",
            ".example.com",
            "-a.example.com",
            "a-.example.com",
            f"{'a' * 64}.example.com",
            ".".join(["a" * 63] * 4) + ".com",
        ):
            for state, check_mode in (("present", False), ("present", True), ("absent", False)):
                with self.subTest(name=name, state=state, check_mode=check_mode):
                    client, api = client_with([PROJECT], created=PROJECT, edited=PROJECT)

                    result = self.run_module(
                        FakeModule(params(state=state, domains=[{"name": name}]), check_mode=check_mode), client
                    )

                    self.assertIn("Each Pages project domain name may contain only", result["msg"])
                    self.assertEqual(result["domain"], name)
                    api.get.assert_not_called()
                    api.create.assert_not_called()
                    api.edit.assert_not_called()
                    api.domains.create.assert_not_called()

    def test_rejects_provider_invalid_domain_names_before_api_calls(self):
        for name in (
            "localhost",
            "com",
            "a.123",
            "192.0.2.1",
            "pages.dev",
            "other-p39fix.pages.dev",
            "Other.Pages.Dev",
        ):
            for state, check_mode in (("present", False), ("present", True), ("absent", False)):
                with self.subTest(name=name, state=state, check_mode=check_mode):
                    client, api = client_with([PROJECT], created=PROJECT, edited=PROJECT)

                    result = self.run_module(
                        FakeModule(params(state=state, domains=[{"name": name}]), check_mode=check_mode), client
                    )

                    self.assertIn("must have at least two labels", result["msg"])
                    self.assertEqual(result["domain"], name)
                    api.get.assert_not_called()
                    api.create.assert_not_called()
                    api.edit.assert_not_called()
                    api.domains.create.assert_not_called()

    def test_accepts_domain_names_with_numeric_inner_labels(self):
        for name in ("123.example.com", "mypages.dev", "pages.dev.example.com"):
            with self.subTest(name=name):
                current = {**PROJECT, "domains": [name]}
                client, api = client_with([current], domains=[{"name": name}])

                result = self.run_module(FakeModule(params(domains=[{"name": name}])), client)

                self.assertFalse(result["changed"])
                api.domains.create.assert_not_called()

    def test_accepts_domain_names_at_the_length_limits(self):
        for name in (f"{'a' * 63}.example.com", ".".join(["a" * 63] * 3 + ["b" * 61]), "xn--bcher-kva.Example.com"):
            with self.subTest(name=name):
                current = {**PROJECT, "domains": [name.lower()]}
                client, api = client_with([current], domains=[{"name": name.lower()}])

                result = self.run_module(FakeModule(params(domains=[{"name": name}])), client)

                self.assertFalse(result["changed"])
                api.domains.create.assert_not_called()

    def test_null_bindings_are_deleted(self):
        keep = {"namespace_id": "keep-id"}
        current = {
            **PROJECT,
            "deployment_configs": {"production": {"kv_namespaces": {"OLD": {"namespace_id": "old-id"}, "KEEP": keep}}},
        }
        desired = {"production": {"kv_namespaces": {"OLD": None, "KEEP": keep}}}
        edited = {**PROJECT, "deployment_configs": {"production": {"kv_namespaces": {"KEEP": keep}}}}
        client, api = client_with([current], edited=edited)

        result = self.run_module(FakeModule(params(deployment_configs=desired)), client)

        self.assertEqual(api.edit.call_args.kwargs["deployment_configs"], desired)
        self.assertTrue(result["changed"])

        client, _ignored = client_with([current], edited=current)
        result = self.run_module(FakeModule(params(deployment_configs=desired)), client)
        self.assertIn("did not apply", result["msg"])

    def test_deleting_one_binding_keeps_unmanaged_bindings(self):
        keep = {"namespace_id": "keep-id"}
        current = {
            **PROJECT,
            "deployment_configs": {"production": {"kv_namespaces": {"OLD": {"namespace_id": "old-id"}, "KEEP": keep}}},
        }
        desired = {"production": {"kv_namespaces": {"OLD": None}}}
        edited = {**PROJECT, "deployment_configs": {"production": {"kv_namespaces": {"KEEP": keep}}}}
        client, _ignored = client_with([current], edited=edited)

        result = self.run_module(FakeModule(params(deployment_configs=desired)), client)

        self.assertTrue(result["changed"])

        client, api = client_with([edited])
        result = self.run_module(FakeModule(params(deployment_configs=desired)), client)

        api.edit.assert_not_called()
        self.assertFalse(result["changed"])

    def test_null_build_setting_is_cleared(self):
        current = {**PROJECT, "build_config": {"build_command": "make", "web_analytics_tag": "tag"}}
        cleared = {**PROJECT, "build_config": {"build_command": "make"}}
        desired = {"build_command": "make", "web_analytics_tag": None}
        client, api = client_with([current], edited=cleared)

        result = self.run_module(FakeModule(params(build_config=desired)), client)

        self.assertEqual(api.edit.call_args.kwargs["build_config"], desired)
        self.assertTrue(result["changed"])

        client, api = client_with([cleared])
        result = self.run_module(FakeModule(params(build_config=desired)), client)

        api.edit.assert_not_called()
        self.assertFalse(result["changed"])

    def test_rejects_null_for_settings_cloudflare_keeps_before_any_request(self):
        cases = (
            ({"build_config": {"build_caching": None}}, ["build_config.build_caching"]),
            (
                {"deployment_configs": {"production": {"compatibility_date": None, "env_vars": {"A": None}}}},
                ["deployment_configs.production.compatibility_date"],
            ),
            (
                {"deployment_configs": {"preview": {"placement": {"mode": None}}}},
                ["deployment_configs.preview.placement"],
            ),
            ({"deployment_configs": {"preview": None}}, ["deployment_configs.preview"]),
            (
                {"deployment_configs": {"production": {"env_vars": None, "kv_namespaces": None}}},
                ["deployment_configs.production.env_vars", "deployment_configs.production.kv_namespaces"],
            ),
            (
                {
                    "deployment_configs": {
                        "production": {
                            "env_vars": {"A": {"type": "plain_text", "value": None}},
                            "kv_namespaces": {"NS": {"namespace_id": None}},
                            "r2_buckets": {"B": {"name": None, "jurisdiction": None}},
                            "services": {"S": {"service": "worker", "environment": None, "entrypoint": None}},
                        }
                    }
                },
                [
                    "deployment_configs.production.env_vars.A.value",
                    "deployment_configs.production.kv_namespaces.NS.namespace_id",
                    "deployment_configs.production.r2_buckets.B.name",
                    "deployment_configs.production.services.S.environment",
                ],
            ),
        )
        for options, unsupported in cases:
            with self.subTest(options=options):
                client, api = client_with([PROJECT])

                result = self.run_module(FakeModule(params(**options)), client)

                self.assertEqual(result["unsupported_settings"], unsupported)
                self.assertIn("does not clear Pages project settings set to null", result["msg"])
                api.get.assert_not_called()
                api.edit.assert_not_called()

    def test_rejects_empty_settings_cloudflare_does_not_store_before_any_request(self):
        cases = (
            (
                {"production": {"wrangler_config_hash": ""}},
                ["deployment_configs.production.wrangler_config_hash"],
            ),
            (
                {"preview": {"placement": {"mode": ""}}, "production": {"placement": {"mode": "smart"}}},
                ["deployment_configs.preview.placement.mode"],
            ),
            (
                {"production": {"compatibility_date": ""}},
                ["deployment_configs.production.compatibility_date"],
            ),
            (
                {"preview": {"usage_model": "", "compatibility_date": "2024-01-01"}},
                ["deployment_configs.preview.usage_model"],
            ),
            (
                {"production": {"usage_model": "", "compatibility_date": "", "wrangler_config_hash": ""}},
                [
                    "deployment_configs.production.compatibility_date",
                    "deployment_configs.production.usage_model",
                    "deployment_configs.production.wrangler_config_hash",
                ],
            ),
        )
        for deployment_configs, empty in cases:
            for check_mode in (True, False):
                with self.subTest(deployment_configs=deployment_configs, check_mode=check_mode):
                    client, api = client_with([PROJECT])

                    result = self.run_module(
                        FakeModule(params(deployment_configs=deployment_configs), check_mode=check_mode), client
                    )

                    self.assertEqual(result["empty_settings"], empty)
                    self.assertEqual(
                        result["msg"],
                        "Cloudflare does not store an empty value for these Pages project settings: "
                        f"{', '.join(empty)}; omit them instead",
                    )
                    api.get.assert_not_called()
                    api.edit.assert_not_called()

    def test_rejects_unstored_setting_names_before_any_request(self):
        cases = (
            (
                {"build_config": {"build_command": "true", "build_image_major_version": 3}},
                ["build_config.build_image_major_version"],
            ),
            ({"build_config": {"bogus_key": 1}}, ["build_config.bogus_key"]),
            (
                {"deployment_configs": {"production": {"compatibility_date": "2024-01-01", "bogus_key": 1}}},
                ["deployment_configs.production.bogus_key"],
            ),
            (
                {
                    "build_config": {"bogus_key": 1},
                    "deployment_configs": {"preview": {"bogus_key": 1}, "production": {"other": 2}},
                },
                [
                    "build_config.bogus_key",
                    "deployment_configs.preview.bogus_key",
                    "deployment_configs.production.other",
                ],
            ),
        )
        for options, unsupported in cases:
            for found, check_mode in (([PROJECT], False), ([PROJECT], True), ([None], False)):
                with self.subTest(options=options, existing=found != [None], check_mode=check_mode):
                    client, api = client_with(found, created=PROJECT, edited=PROJECT)

                    result = self.run_module(FakeModule(params(**options), check_mode=check_mode), client)

                    self.assertEqual(result["unsupported_settings"], unsupported)
                    self.assertEqual(
                        result["msg"],
                        f"Cloudflare does not store these Pages project settings: {', '.join(unsupported)}",
                    )
                    api.get.assert_not_called()
                    api.create.assert_not_called()
                    api.edit.assert_not_called()

    def test_stored_setting_names_are_sent(self):
        build_config = dict.fromkeys(pages_projects.BUILD_SETTINGS, "value")
        build_config.pop("web_analytics_token")
        deployment = {"build_image_major_version": 3, "compatibility_date": "2024-01-01"}
        project = {
            **PROJECT,
            "build_config": build_config,
            "deployment_configs": {"preview": deployment, "production": deployment},
        }
        client, api = client_with([{**PROJECT, "build_config": {}}], edited=project)

        result = self.run_module(
            FakeModule(
                params(
                    build_config=build_config,
                    deployment_configs={"preview": deployment, "production": deployment},
                )
            ),
            client,
        )

        self.assertNotIn("msg", result)
        self.assertTrue(result["changed"])
        api.edit.assert_called_once()

    def test_rejects_unstored_nested_setting_names_before_any_request(self):
        cases = (
            (
                {"production": {"env_vars": {"A": {"type": "plain_text", "value": "x", "extra": 1}}}},
                ["deployment_configs.production.env_vars.A.extra"],
            ),
            (
                {"preview": {"kv_namespaces": {"KV": {"namespace_id": "id", "bogus": 1}}}},
                ["deployment_configs.preview.kv_namespaces.KV.bogus"],
            ),
            (
                {"production": {"services": {"S": {"service": "api", "environment": "production", "bogus": 1}}}},
                ["deployment_configs.production.services.S.bogus"],
            ),
            ({"production": {"browsers": {"B": {"bogus": 1}}}}, ["deployment_configs.production.browsers.B.bogus"]),
            (
                {"production": {"placement": {"mode": "smart", "bogus": 1}}},
                ["deployment_configs.production.placement.bogus"],
            ),
            ({"preview": {"limits": {"cpu_ms": 50, "bogus": 1}}}, ["deployment_configs.preview.limits.bogus"]),
            (
                {
                    "preview": {"bogus_key": {"extra": 1}, "env_vars": {"A": None, "B": {"extra": 1}}},
                    "production": {"r2_buckets": {"R": {"name": "bucket", "jurisdiction": None, "bogus": None}}},
                },
                [
                    "deployment_configs.preview.bogus_key",
                    "deployment_configs.preview.env_vars.B.extra",
                    "deployment_configs.production.r2_buckets.R.bogus",
                ],
            ),
        )
        for deployment_configs, unsupported in cases:
            for found, check_mode in (([PROJECT], False), ([PROJECT], True), ([None], False)):
                with self.subTest(
                    deployment_configs=deployment_configs, existing=found != [None], check_mode=check_mode
                ):
                    client, api = client_with(found, created=PROJECT, edited=PROJECT)

                    result = self.run_module(
                        FakeModule(params(deployment_configs=deployment_configs), check_mode=check_mode), client
                    )

                    self.assertEqual(result["unsupported_settings"], unsupported)
                    self.assertEqual(
                        result["msg"],
                        f"Cloudflare does not store these Pages project settings: {', '.join(unsupported)}",
                    )
                    api.get.assert_not_called()
                    api.create.assert_not_called()
                    api.edit.assert_not_called()

    def test_stored_nested_setting_names_are_sent(self):
        entries = {
            key: {"X": dict.fromkeys(fields, "value"), "GONE": None}
            for key, fields in pages_projects.DEPLOYMENT_ENTRY_FIELDS.items()
        }
        deployment = {**entries, "limits": {"cpu_ms": 50}, "placement": {"mode": "smart"}}
        stored = {
            **{key: {"X": entry["X"]} for key, entry in entries.items()},
            "limits": {"cpu_ms": 50},
            "placement": {"mode": "smart"},
        }
        client, api = client_with([PROJECT], edited={**PROJECT, "deployment_configs": {"production": stored}})

        result = self.run_module(FakeModule(params(deployment_configs={"production": deployment})), client)

        self.assertNotIn("msg", result)
        self.assertTrue(result["changed"])
        self.assertEqual(api.edit.call_args.kwargs["deployment_configs"], {"production": deployment})

    def test_null_r2_jurisdiction_is_sent(self):
        current = {
            **PROJECT,
            "deployment_configs": {"production": {"r2_buckets": {"B": {"name": "bucket", "jurisdiction": "eu"}}}},
        }
        cleared = {**PROJECT, "deployment_configs": {"production": {"r2_buckets": {"B": {"name": "bucket"}}}}}
        desired = {"production": {"r2_buckets": {"B": {"name": "bucket", "jurisdiction": None}}}}
        client, api = client_with([current], edited=cleared)

        result = self.run_module(FakeModule(params(deployment_configs=desired)), client)

        self.assertEqual(api.edit.call_args.kwargs["deployment_configs"], desired)
        self.assertTrue(result["changed"])

    def test_empty_string_build_setting_counts_as_cleared(self):
        current = {**PROJECT, "build_config": {"build_command": "make", "web_analytics_tag": ""}}
        client, api = client_with([current])

        result = self.run_module(
            FakeModule(params(build_config={"build_command": "make", "web_analytics_tag": None})), client
        )

        api.edit.assert_not_called()
        self.assertFalse(result["changed"])

    def test_empty_binding_map_keeps_existing_bindings(self):
        current = {**PROJECT, "deployment_configs": {"production": {"kv_namespaces": {"NS": {"namespace_id": "id"}}}}}
        client, api = client_with([current])

        result = self.run_module(FakeModule(params(deployment_configs={"production": {"kv_namespaces": {}}})), client)

        api.edit.assert_not_called()
        self.assertFalse(result["changed"])

    def test_empty_binding_map_matches_a_null_collection(self):
        current = {**PROJECT, "deployment_configs": {"production": {"kv_namespaces": None}}}
        client, api = client_with([current])

        result = self.run_module(FakeModule(params(deployment_configs={"production": {"kv_namespaces": {}}})), client)

        api.edit.assert_not_called()
        self.assertFalse(result["changed"])

    def test_empty_source_is_unchanged(self):
        client, api = client_with([{**PROJECT, "source": {"type": "github"}}])

        result = self.run_module(FakeModule(params(source={})), client)

        api.edit.assert_not_called()
        self.assertFalse(result["changed"])

    def test_null_nested_binding_field_is_cleared(self):
        service = {"service": "worker", "environment": "production"}
        current = {
            **PROJECT,
            "deployment_configs": {"production": {"services": {"API": {**service, "entrypoint": "Main"}}}},
        }
        cleared = {**PROJECT, "deployment_configs": {"production": {"services": {"API": service}}}}
        desired = {"production": {"services": {"API": {**service, "entrypoint": None}}}}
        client, api = client_with([current], edited=cleared)

        result = self.run_module(FakeModule(params(deployment_configs=desired)), client)

        self.assertEqual(api.edit.call_args.kwargs["deployment_configs"], desired)
        self.assertTrue(result["changed"])

        client, _ignored = client_with([current], edited=current)
        result = self.run_module(FakeModule(params(deployment_configs=desired)), client)
        self.assertIn("did not apply", result["msg"])

    def test_binding_named_env_vars_keeps_omitted_fields(self):
        for binding, stored in (
            ("services", {"service": "worker", "environment": "production", "entrypoint": "Main"}),
            ("r2_buckets", {"name": "bucket", "jurisdiction": "eu"}),
        ):
            with self.subTest(binding=binding):
                current = {**PROJECT, "deployment_configs": {"production": {binding: {"env_vars": stored}}}}
                name = "service" if binding == "services" else "name"
                desired = {"production": {binding: {"env_vars": {name: stored[name]}}}}
                client, api = client_with([current])

                result = self.run_module(FakeModule(params(deployment_configs=desired)), client)

                api.edit.assert_not_called()
                self.assertFalse(result["changed"])

    def test_nested_deletion_only_request_ignores_unmanaged_fields(self):
        service = {"service": "worker", "environment": "production"}
        current = {
            **PROJECT,
            "deployment_configs": {"production": {"services": {"API": {**service, "entrypoint": "Main"}}}},
        }
        cleared = {**PROJECT, "deployment_configs": {"production": {"services": {"API": service}}}}
        desired = {"production": {"services": {"API": {"entrypoint": None}}}}
        client, _ignored = client_with([current], edited=cleared)

        result = self.run_module(FakeModule(params(deployment_configs=desired)), client)

        self.assertTrue(result["changed"])

        client, api = client_with([cleared])
        result = self.run_module(FakeModule(params(deployment_configs=desired)), client)

        api.edit.assert_not_called()
        self.assertFalse(result["changed"])

    def test_plain_variable_named_like_a_secret_is_compared(self):
        def project(value):
            env_vars = {"web_analytics_token": {"type": "plain_text", "value": value}}
            return {**PROJECT, "deployment_configs": {"production": {"env_vars": env_vars}}}

        client, api = client_with([project("old")], edited=project("new"))

        result = self.run_module(FakeModule(params(deployment_configs=project("new")["deployment_configs"])), client)

        api.edit.assert_called_once()
        self.assertTrue(result["changed"])

    def test_returns_project_values(self):
        deployment_configs = {"production": {"env_vars": {"TOKEN": {"type": "secret_text", "value": "secret"}}}}
        created = {**PROJECT, "deployment_configs": deployment_configs}
        client, api = client_with([None], created=created)

        result = self.run_module(FakeModule(params(deployment_configs=deployment_configs)), client)

        api.create.assert_called_once_with(
            account_id="account", name="docs", production_branch="main", deployment_configs=deployment_configs
        )
        secret = result["pages_project"]["deployment_configs"]["production"]["env_vars"]["TOKEN"]
        self.assertEqual(secret, {"type": "secret_text", "value": "secret"})
        self.assertEqual(result["message"], "Pages project created")

    def test_rotates_web_analytics_token(self):
        client, api = client_with([PROJECT], edited={**PROJECT, "build_config": {"web_analytics_token": "new-secret"}})

        result = self.run_module(
            FakeModule(params(build_config={"web_analytics_token": "new-secret"}, rotate_secrets=True)),
            client,
        )

        api.edit.assert_called_once_with(
            project_name="docs",
            account_id="account",
            name="docs",
            production_branch="main",
            build_config={"web_analytics_token": "new-secret"},
        )
        self.assertTrue(result["changed"])

    def test_changed_analytics_token_is_applied(self):
        current = {**PROJECT, "build_config": {"build_command": "make", "web_analytics_token": "old-token"}}
        desired = {"web_analytics_token": "new-token"}
        updated = {**PROJECT, "build_config": {"build_command": "make", **desired}}
        for check_mode in (True, False):
            with self.subTest(check_mode=check_mode):
                client, api = client_with([current], edited=updated)

                result = self.run_module(FakeModule(params(build_config=desired), check_mode=check_mode), client)

                self.assertTrue(result["changed"])
                if check_mode:
                    api.edit.assert_not_called()
                else:
                    self.assertEqual(api.edit.call_args.kwargs["build_config"], desired)

        client, api = client_with([updated])
        result = self.run_module(FakeModule(params(build_config=desired)), client)

        api.edit.assert_not_called()
        self.assertFalse(result["changed"])

        client, api = client_with([current], edited=current)
        result = self.run_module(FakeModule(params(build_config=desired)), client)

        self.assertIn("did not apply", result["msg"])

    def test_cleared_analytics_token_matches_null(self):
        for stored in (None, ""):
            with self.subTest(stored=stored):
                client, api = client_with([{**PROJECT, "build_config": {"web_analytics_token": stored}}])

                result = self.run_module(FakeModule(params(build_config={"web_analytics_token": None})), client)

                api.edit.assert_not_called()
                self.assertFalse(result["changed"])

    def test_empty_build_config_is_unchanged(self):
        client, api = client_with([{**PROJECT, "build_config": {"build_command": "make"}}])

        result = self.run_module(FakeModule(params(build_config={})), client)

        api.edit.assert_not_called()
        self.assertFalse(result["changed"])

    def test_removed_environment_variables_are_sent_as_null(self):
        keep = {"type": "plain_text", "value": "yes"}
        current = {
            **PROJECT,
            "deployment_configs": {
                "production": {"env_vars": {"KEEP": keep, "REMOVE": {"type": "plain_text", "value": "old"}}}
            },
        }
        desired = {"production": {"env_vars": {"KEEP": keep}}}
        client, api = client_with([current], edited={**PROJECT, "deployment_configs": desired})

        result = self.run_module(FakeModule(params(deployment_configs=desired)), client)

        sent = api.edit.call_args.kwargs["deployment_configs"]
        self.assertEqual(sent, {"production": {"env_vars": {"KEEP": keep, "REMOVE": None}}})
        self.assertNotIn("REMOVE", desired["production"]["env_vars"])
        self.assertTrue(result["changed"])

    def test_empty_deployment_configs_are_unchanged(self):
        current = {**PROJECT, "deployment_configs": {"production": {"compatibility_date": "2024-01-01"}}}
        for configs in ({}, {"production": {}}):
            with self.subTest(configs=configs):
                client, api = client_with([current])

                result = self.run_module(FakeModule(params(deployment_configs=configs)), client)

                api.edit.assert_not_called()
                self.assertFalse(result["changed"])

    def test_null_env_vars_match_an_empty_map(self):
        current = {**PROJECT, "deployment_configs": {"production": {"env_vars": None}}}
        client, api = client_with([current])

        result = self.run_module(FakeModule(params(deployment_configs={"production": {"env_vars": {}}})), client)

        api.edit.assert_not_called()
        self.assertFalse(result["changed"])

    def test_explicit_null_environment_variables_are_removed(self):
        keep = {"type": "plain_text", "value": "yes"}
        current = {
            **PROJECT,
            "deployment_configs": {
                "production": {"env_vars": {"KEEP": keep, "REMOVE": {"type": "plain_text", "value": "old"}}}
            },
        }
        desired = {"production": {"env_vars": {"KEEP": keep, "REMOVE": None}}}
        client, api = client_with(
            [current], edited={**PROJECT, "deployment_configs": {"production": {"env_vars": {"KEEP": keep}}}}
        )

        result = self.run_module(FakeModule(params(deployment_configs=desired)), client)

        sent = api.edit.call_args.kwargs["deployment_configs"]
        self.assertEqual(sent, {"production": {"env_vars": {"KEEP": keep, "REMOVE": None}}})
        self.assertTrue(result["changed"])

    def test_rejects_unremoved_environment_variables(self):
        current = {
            **PROJECT,
            "deployment_configs": {"production": {"env_vars": {"REMOVE": {"type": "plain_text", "value": "old"}}}},
        }
        client, _ignored = client_with([current], edited=current)

        result = self.run_module(FakeModule(params(deployment_configs={"production": {"env_vars": {}}})), client)

        self.assertEqual(
            result["msg"],
            "Cloudflare did not apply the requested Pages project: deployment_configs.production.env_vars.REMOVE "
            'requested null, stored {"type": "plain_text", "value": "old"}',
        )
        self.assertEqual(
            result["differences"],
            [
                {
                    "field": "deployment_configs.production.env_vars.REMOVE",
                    "requested": None,
                    "stored": {"type": "plain_text", "value": "old"},
                }
            ],
        )

    def test_check_mode_does_not_update(self):
        client, api = client_with([PROJECT])

        result = self.run_module(FakeModule(params(production_branch="release"), check_mode=True), client)

        api.edit.assert_not_called()
        self.assertTrue(result["changed"])

    def test_rejects_update_response_with_wrong_branch(self):
        client, _ignored = client_with([PROJECT], edited=PROJECT)

        result = self.run_module(FakeModule(params(production_branch="release")), client)

        self.assertIn("did not apply", result["msg"])

    def test_rejects_project_with_wrong_name(self):
        client, _ignored = client_with([{**PROJECT, "name": "other"}])

        result = self.run_module(FakeModule(params()), client)

        self.assertEqual(result["msg"], "Cloudflare API returned the wrong Pages project")

    def test_adds_only_missing_unique_domains(self):
        domains = [{"name": "docs.example.com"}, {"name": "new.example.com"}, {"name": "new.example.com"}]
        current = {**PROJECT, "domains": ["docs.example.com"]}
        refreshed = {**current, "domains": ["docs.example.com", "new.example.com"]}
        client, api = client_with(
            [current, refreshed],
            domains=[{"name": "docs.example.com"}],
            created_domain={"name": "new.example.com"},
        )

        result = self.run_module(FakeModule(params(domains=domains)), client)

        api.domains.list.assert_called_once_with(project_name="docs", account_id="account")
        api.domains.create.assert_called_once_with(project_name="docs", account_id="account", name="new.example.com")
        self.assertTrue(result["changed"])
        self.assertEqual(result["pages_project"], refreshed)
        self.assertEqual(result["domains"], [{"name": "new.example.com"}])

    def test_domain_names_compare_case_insensitively(self):
        current = {**PROJECT, "domains": ["docs.example.com"]}
        client, api = client_with([current], domains=[{"name": "docs.example.com"}])

        result = self.run_module(FakeModule(params(domains=[{"name": "Docs.Example.com"}])), client)

        api.domains.create.assert_not_called()
        self.assertFalse(result["changed"])

    def test_adds_mixed_case_domain_in_lowercase(self):
        refreshed = {**PROJECT, "domains": ["new.example.com"]}
        client, api = client_with([PROJECT, refreshed], created_domain={"name": "new.example.com"})

        result = self.run_module(FakeModule(params(domains=[{"name": "New.Example.com"}])), client)

        api.domains.create.assert_called_once_with(project_name="docs", account_id="account", name="new.example.com")
        self.assertEqual(result["domains"], [{"name": "new.example.com"}])

    def test_project_deleted_while_adding_domains_fails_clearly(self):
        client, api = client_with([PROJECT, None], created_domain={"name": "new.example.com"})

        result = self.run_module(FakeModule(params(domains=[{"name": "new.example.com"}])), client)

        api.domains.create.assert_called_once_with(project_name="docs", account_id="account", name="new.example.com")
        self.assertEqual(result["msg"], "Pages project was deleted while its domains were being added")
        self.assertEqual(result["account_id"], "account")
        self.assertEqual(result["name"], "docs")

    def test_check_mode_does_not_add_domains(self):
        client, api = client_with([PROJECT])

        result = self.run_module(FakeModule(params(domains=[{"name": "new.example.com"}]), check_mode=True), client)

        api.domains.create.assert_not_called()
        self.assertTrue(result["changed"])

    def test_rejects_malformed_project_domains(self):
        for domains in ("docs.example.com", [" docs.example.com "]):
            with self.subTest(domains=domains):
                client, _ignored = client_with([{**PROJECT, "domains": domains}])

                result = self.run_module(FakeModule(params(domains=[{"name": "new.example.com"}])), client)

                self.assertEqual(result["msg"], "Cloudflare API returned malformed Pages domain data")

    def test_absent_project_is_unchanged(self):
        client, api = client_with([None])

        result = self.run_module(FakeModule(params(state="absent")), client)

        api.delete.assert_not_called()
        self.assertFalse(result["changed"])

    def test_check_mode_does_not_delete(self):
        client, api = client_with([PROJECT])

        result = self.run_module(FakeModule(params(state="absent", domains=[{"name": "a.example.com"}]), True), client)

        api.domains.delete.assert_not_called()
        api.delete.assert_not_called()
        self.assertTrue(result["changed"])

    def test_deletes_only_the_project(self):
        project = {**PROJECT, "domains": ["a.example.com"]}
        client, api = client_with([project], domains=[{"name": "a.example.com"}])

        result = self.run_module(
            FakeModule(params(state="absent", domains=[{"name": "A.Example.com"}, {"name": "b.example.com"}])),
            client,
        )

        api.domains.list.assert_not_called()
        api.domains.delete.assert_not_called()
        api.delete.assert_called_once_with(project_name="docs", account_id="account")
        self.assertEqual(result["message"], "Pages project deleted")
        self.assertTrue(result["changed"])

    def test_lookup_errors_other_than_not_found_propagate(self):
        client = Mock()
        client.pages.projects.get.side_effect = status_error(403)

        with self.assertRaises(Exception) as raised:
            pages_projects.run(FakeModule(params()), client)

        self.assertEqual(raised.exception.status_code, 403)
        self.assertEqual(
            raised.exception._cloudflare_message,
            "Cloudflare API request failed while gathering the Pages project",
        )
