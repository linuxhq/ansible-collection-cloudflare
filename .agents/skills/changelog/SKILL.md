---
name: changelog
description: Manage changelog fragments and CHANGELOG.rst with antsibull-changelog from the project virtualenv. Add a fragment per user-facing change; release consumes fragments to cut a version.
---

# changelog

Record user-facing changes as YAML fragments in `changelogs/fragments/`. `antsibull-changelog`
(config `changelogs/config.yaml`) folds them into `CHANGELOG.rst`.

## Add a fragment

Create `changelogs/fragments/{{ name }}.yml`, keyed by antsibull section (a list per section):

```yaml
minor_changes:
  - {{ module_or_role }} - add X (https://github.com/.../pull/NNN).
```

Sections:

- `breaking_changes`
- `bugfixes`
- `deprecated_features`
- `known_issues`
- `major_changes`
- `minor_changes`
- `release_summary` (a string, prelude)
- `removed_features`
- `security_fixes`
- `trivial` (not rendered)

## Commands

```sh
venv/bin/antsibull-changelog lint
venv/bin/antsibull-changelog generate
venv/bin/antsibull-changelog release
```

- `generate` doesn't touch fragments or show pending ones.
- `release` records the `galaxy.yml` version and (with `keep_fragments: false`) deletes the
  consumed fragments.
- Bump `version` in `galaxy.yml` before `release` / tagging.

## Dependencies

- `virtualenv` skill
