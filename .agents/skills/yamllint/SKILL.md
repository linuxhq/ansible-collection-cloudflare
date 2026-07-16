---
name: yamllint
description: Strict-lint YAML with yamllint from the project virtualenv. Run after every change to a .yml/.yaml file.
---

# yamllint

Lint YAML with the venv's `yamllint`, after every change to a `.yml`/`.yaml` file. CI runs it
`--strict`; match that.

```sh
venv/bin/yamllint --strict .
venv/bin/yamllint --strict roles/{{ role }}/tasks/main.yml
```

- Clean run prints nothing; fix each line by hand.
- Checks raw YAML only — also run `ansible-lint` on role changes.

## Dependencies

- `virtualenv` skill
