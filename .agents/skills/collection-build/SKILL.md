---
name: collection-build
description: Build the collection tarball with ansible-galaxy from the project virtualenv. Local builds verify only; the tag-driven release workflow builds and publishes.
---

# collection-build

Build the collection tarball from the collection root (where `galaxy.yml` lives).

```sh
venv/bin/ansible-galaxy collection build
venv/bin/ansible-galaxy collection build --force --output-path /tmp
```

- Reads `galaxy.yml` (version, `build_ignore`).
- Local builds only **verify** the artifact — they don't publish.
- Release is tag-driven: `.github/workflows/release.yml` builds then publishes. Don't `publish`
  by hand.
- Before tagging: bump `version` in `galaxy.yml`, and record changes with the `changelog` skill.
- Inspect with `tar tzf {{ namespace }}-{{ name }}-{{ version }}.tar.gz`; don't commit the tarball.

## Dependencies

- `virtualenv` skill
