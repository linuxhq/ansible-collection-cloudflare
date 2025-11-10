================================
linuxhq.cloudflare Release Notes
================================

.. contents:: Topics

v2.0.2
======

Release Summary
---------------

This release introduces eight new cloudflare warp related roles

Minor Changes
-------------

- Initial commit of devices_policy role
- Initial commit of devices_policy_info role
- Initial commit of devices_settings role
- Initial commit of devices_settings_info role
- Initial commit of warp_connector role
- Initial commit of warp_connector_info role
- Initial commit of zerotrust_connectivity_settings role
- Initial commit of zerotrust_connectivity_settings_info role

v2.0.1
======

Release Summary
---------------

This release adds support for the destinations option in the access_apps role. This allows for multiple domains to be associated with a single application.

Minor Changes
-------------

- Added support for destinations in access_apps role

v2.0.0
======

Release Summary
---------------

This release restructures the entire collection.  All inventory and playbooks will need to be updated if you plan to use this and future releases.  Please see the examples provided.

Minor Changes
-------------

- Added check_mode support to avoid failures
- Added example inventory and playbooks
- Added molecule tests to all roles
- Added state support to all applicable roles
- Addition of purge_cache role
- Updated ansible-lint configuration to have no exclusions

Breaking Changes / Porting Guide
--------------------------------

- Deprecated network role in favor of zones role
- Deprecated scrape_shield role role in favor of zones role
- Deprecated security role in favor of zones role
- Deprecated ssl role in favor of zones role
- Merged pages_domain and pages_project roles into pages_projects role
- Renamed role access_app -> access_apps and associated role variables
- Renamed role access_app_info -> access_apps_info and associated role variables
- Renamed role access_group -> access_groups and associated role variables
- Renamed role access_group_info -> access_groups_info and associated role variables
- Renamed role access_policy -> access_policies and associated role variables
- Renamed role access_policy_info -> access_policies_info and associated role variables
- Renamed role access_service_token -> access_service_tokens and associated role variables
- Renamed role access_service_token_info -> access_service_tokens_info and associated role variables
- Renamed role account_info -> accounts_info and associated role variables
- Renamed role page_rule -> pagerules and associated role variables
- Renamed role page_rule_info -> pagerules_info and associated role variables
- Renamed role pages_project -> pages_projects and associated role variables
- Renamed role pages_project_info -> pages_projects_info and associated role variables
- Renamed role rule_list -> rules_lists and associated role variables
- Renamed role rule_list_info -> rules_lists_info and associated role variables
- Renamed role ruleset_entrypoint -> rulesets and associated role variables
- Renamed role ruleset_entrypoint_info -> rulesets_info and associated role variables
- Renamed role tunnel -> cfd_tunnel and associated role variables
- Renamed role tunnel_info -> cfd_tunnel_info and associated role variables
- Renamed role zone -> zones and associated role variables
- Renamed role zone_info -> zones_info and associated role variables

v1.2.0
======

Release Summary
---------------

All 1.x.x releases are now considered deprecated and will no longer receive updates.  Please see release 2.0.0
