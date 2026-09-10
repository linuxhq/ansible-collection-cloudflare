---
name: yamllint
description: Lint YAML files in strict mode with yamllint through Tox.
---

# yamllint

- Use the `tox` skill for environment setup and run from the collection root.
- Run after `.yml` or `.yaml` edits; replace the example path with the changed file.
- Tox enables `--strict`, matching CI.

```sh
tox run -e yamllint -- roles/{{ role }}/tasks/main.yml
```

- Fix reported findings by hand; a clean yamllint run prints nothing.
- Also use the `ansible-lint` skill for role and playbook changes.
- Run `tox run -m lint` for the full lint suite.
