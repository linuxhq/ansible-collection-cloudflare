---
name: ansible-test
description: Run ansible-test sanity checks on modules and plugins through Tox.
---

# ansible-test

- Use the `tox` skill for environment setup and run from the collection root.
- Run sanity checks locally and in CI to catch documentation drift, argspec mismatches,
  and import errors.
- Replace the example path with the module or plugin to check.
- Tox supplies the pinned Python version and copies the repository into the required
  `ansible_collections/{{ namespace }}/{{ name }}/` layout before each run.

```sh
git diff --check
tox run -e ansible-test -- sanity plugins/modules/{{ file }}.py
```

- Omit the path to run the full sanity suite.
- Add `--test validate-modules` to limit the run to documentation and argspec checks.
