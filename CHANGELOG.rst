================================
linuxhq.cloudflare Release Notes
================================

.. contents:: Topics

v2.0.3
======

Release Summary
---------------

This release introduces two new cloudflare dnssec related roles

Minor Changes
-------------

- dnssec - initial commit
- dnssec_info - initial commit

v2.0.2
======

Release Summary
---------------

This release introduces eight new cloudflare warp related roles

Minor Changes
-------------

- devices_policy - initial commit
- devices_policy_info - initial commit
- devices_settings - initial commit
- devices_settings_info - initial commit
- warp_connector - initial commit
- warp_connector_info - initial commit
- zerotrust_connectivity_settings - initial commit
- zerotrust_connectivity_settings_info - initial commit

v2.0.1
======

Release Summary
---------------

This release adds support for the destinations option in the access_apps role. This allows for multiple domains to be associated with a single application.

Minor Changes
-------------

- access_apps - add support for destinations

v2.0.0
======

Release Summary
---------------

This release restructures the entire collection.  All inventory and playbooks will need to be updated if you plan to use this and future releases.  Please see the examples provided.

Minor Changes
-------------

- added check_mode support to avoid failures
- added example inventory and playbooks
- added molecule tests to all roles
- added state support to all applicable roles
- addition of purge_cache role
- updated ansible-lint configuration to have no exclusions

Breaking Changes / Porting Guide
--------------------------------

- access_apps - renamed from access_app
- access_apps_info - renamed from access_app_info
- access_groups - renamed from access_group
- access_groups_info - renamed from access_group_info
- access_policies - renamed from access_policy
- access_policies_info - renamed from access_policy_info
- access_service_tokens - renamed from access_service_token
- access_service_tokens_info - renamed from access_service_token_info
- accounts_info - renamed from account_info
- cfd_tunnel - renamed from tunnel
- cfd_tunnel_info - renamed from tunnel_info
- network - role deprecated
- pagerules - renamed from page_rule
- pagerules_info - renamed from page_rule_info
- pages_projects - merged pages_domain and pages_projects roles
- pages_projects - merged pages_domain and pages_projects roles
- pages_projects_info - renamed from pages_project_info
- rules_lists - renamed from rule_list
- rules_lists_info - renamed from rule_list_info
- rulesets - renamed from ruleset_entrypoint
- rulesets_info - renamed from ruleset_entrypoint_info
- scrape_shield - role deprecated
- security - role deprecated
- ssl - role deprecated
- zones - renamed from zone
- zones_info - renamed from zone_info

v1.2.0
======

Release Summary
---------------

All 1.x.x releases are now considered deprecated and will no longer receive updates.  Please see release 2.0.0
