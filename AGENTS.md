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

| Rule                  | Covers                                     |
| --------------------- | ------------------------------------------ |
| `helpers.md`          | Helper reference for `module_utils`        |
| `module-authoring.md` | Standards for writing python module code   |
| `module-docs.md`      | Standards for writing python documentation |
| `role-authoring.md`   | Standards for writing ansible roles        |

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
| `molecule`         | Role tests                    |
| `changelog`        | Changelog fragments & release |
| `collection-build` | Build the collection tarball  |

## Setup

Enable the review gate once: `/codex:setup --enable-review-gate`

## Imports

- @.agents/rules/helpers.md
- @.agents/rules/module-authoring.md
- @.agents/rules/module-docs.md
- @.agents/rules/role-authoring.md
