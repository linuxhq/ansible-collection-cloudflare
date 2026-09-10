---
name: changelog
description: Manage changelog fragments and releases with antsibull-changelog through Tox.
---

# changelog

- Use the `tox` skill for environment setup and run from the collection root.
- Add a YAML fragment in `changelogs/fragments/` for each user-facing change.
- `changelogs/config.yaml` controls how changes appear in `CHANGELOG.rst`.

## Add a fragment

- Create `changelogs/fragments/{{ name }}.yml` with a list of entries per section.

```yaml
minor_changes:
  - {{ module_or_role }} - add X (https://github.com/.../pull/NNN).
```

- Sections: `major_changes`, `minor_changes`, `breaking_changes`, `deprecated_features`,
  `removed_features`, `security_fixes`, `bugfixes`, and `known_issues`.
- `release_summary` takes a string for the release prelude.
- `trivial` entries are not rendered.

## Validate and generate

```sh
tox run -e changelog -- lint
tox run -e changelog -- lint-changelog-yaml --strict changelogs/changelog.yaml
tox run -e changelog -- generate
```

- `lint` validates fragments.
- `lint-changelog-yaml` validates the changelog data used to render `CHANGELOG.rst`.
- `generate` renders recorded changes; it leaves fragments untouched and omits pending ones.

## Release

- Bump `version` in `galaxy.yml`, then consume the fragments:

```sh
tox run -e changelog -- release
```

- `release` records the `galaxy.yml` version and deletes consumed fragments with
  `keep_fragments: false`.
- Review `CHANGELOG.rst` and `changelogs/changelog.yaml`, then rerun both lint commands
  before tagging.
