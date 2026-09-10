---
name: collection-build
description: Build and inspect the collection tarball through Tox.
---

# collection-build

- Use the `tox` skill for environment setup and run from the collection root.
- Build settings, including version and `build_ignore`, come from `galaxy.yml`.
- Build into a temporary directory for local verification.

```sh
collection_artifact_dir="$(mktemp -d)"
tox run -e build -- --force --output-path "${collection_artifact_dir}"
```

- Inspect the file list with `tar tzf` and `MANIFEST.json` with `tar xOf`.
- Verify the artifact's version and collection dependencies; do not commit the tarball.
- Before tagging a release, bump `version` in `galaxy.yml` and use the `changelog` skill.
- `.github/workflows/release.yml` builds and publishes on tag push; do not publish manually.
