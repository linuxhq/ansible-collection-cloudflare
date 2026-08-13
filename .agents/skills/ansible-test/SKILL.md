---
name: ansible-test
description: Run ansible-test sanity on modules and plugins.
---

# ansible-test

Catch `DOCUMENTATION`/`RETURN`/`EXAMPLES` drift, argspec mismatches, and import errors. Treat it as
a required local and CI check.

## Pre-checks

```sh
git diff --check
tox run -e ansible-test -- sanity --python "$(cat .python-version)" plugins/modules/{{ file }}.py
```

Tox copies the repository into the required
`ansible_collections/{{ namespace }}/{{ name }}/` layout before every run. Drop the path argument
for the full local suite; add `--test validate-modules` for only doc/argspec checks.

## Dependencies

- `tox` skill
