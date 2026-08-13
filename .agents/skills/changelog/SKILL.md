---
name: changelog
description: Manage changelog fragments and CHANGELOG.rst with antsibull-changelog through Tox. Add a fragment per user-facing change; release consumes fragments to cut a version.
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
tox run -e changelog -- lint
tox run -e changelog -- lint-changelog-yaml --strict changelogs/changelog.yaml
tox run -e changelog -- generate
```

- `generate` doesn't touch fragments or show pending ones.
- `lint-changelog-yaml` validates the generated changelog data used to render `CHANGELOG.rst`.
## Release fragments

After bumping `version` in `galaxy.yml`, consume the fragments:

```sh
tox run -e changelog -- release
```

With `keep_fragments: false`, `release` records the `galaxy.yml` version and deletes the consumed
fragments. Review `CHANGELOG.rst` and `changelogs/changelog.yaml`, then run both lint commands again
before tagging.

## Dependencies

- `tox` skill
