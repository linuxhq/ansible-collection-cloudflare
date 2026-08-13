---
name: collection-build
description: Build the collection tarball with ansible-galaxy through Tox. Local builds verify only; the tag-driven release workflow builds and publishes.
---

# collection-build

Build the collection tarball from the collection root (where `galaxy.yml` lives).

```sh
collection_artifact_dir="$(mktemp -d)"
tox run -e build -- --force --output-path "${collection_artifact_dir}"
```

- Reads `galaxy.yml` (version, `build_ignore`).
- Local builds only **verify** the artifact — they don't publish.
- Release is tag-driven: `.github/workflows/release.yml` builds then publishes. Don't `publish`
  by hand.
- Before tagging: bump `version` in `galaxy.yml`, and record changes with the `changelog` skill.
- Inspect the file list with `tar tzf` and `MANIFEST.json` with `tar xOf`; verify the artifact's
  version and collection dependencies. Don't commit the tarball.

## Dependencies

- `tox` skill
