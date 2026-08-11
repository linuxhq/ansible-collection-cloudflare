# AGENTS.md

Guidance for agents working in this repository.

## Overview

An Ansible collection of Cloudflare modules and roles, published to Galaxy on tag push.

| Path               | Description            |
| ------------------ | ---------------------- |
| `plugins/modules/` | Ansible python modules |
| `plugins/lookup/`  | Ansible lookup plugins |
| `roles/`           | Ansible roles          |

## Rules

Always-on agent rules.  Append new rules to imports section below.

| Rule                       | Covers                                  |
| -------------------------- | --------------------------------------- |
| `ansible-module-utils.md`  | Reusable Ansible module utilities       |
| `ansible-plugins.md`       | Standards for Ansible Python plugins    |
| `ansible-plugins-sdk.md`   | Cloudflare SDK standards for plugins    |
| `ansible-roles.md`         | Standards for Ansible roles             |

## Tooling

Invoke skills rather than running commands ad hoc.

| Skill              | Purpose                       |
| ------------------ | ----------------------------- |
| `pyenv`            | Install pyenv + pinned Python |
| `virtualenv`       | Set up the venv               |
| `ansible-lint`     | Lint roles & playbooks        |
| `yamllint`         | Lint YAML                     |
| `black`            | Format Python                 |
| `ruff`             | Lint Python                   |
| `ansible-test`     | Module sanity                 |
| `plugins-audit`    | Exhaustive plugins audit      |
| `molecule`         | Role tests                    |
| `changelog`        | Changelog fragments & release |
| `collection-build` | Build the collection tarball  |

## Setup

Enable the review gate once: `/codex:setup --enable-review-gate`

## Imports

- @.agents/rules/ansible-module-utils.md
- @.agents/rules/ansible-plugins.md
- @.agents/rules/ansible-plugins-sdk.md
- @.agents/rules/ansible-roles.md
