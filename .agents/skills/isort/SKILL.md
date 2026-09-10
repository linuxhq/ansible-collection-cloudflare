---
name: isort
description: Sort and check Python imports with isort through Tox.
---

# isort

- Use the `tox` skill for environment setup and run from the collection root.
- Replace the example path with the file to check.
- `isort` sorts imports; `isort-lint` checks them without changing files.

```sh
tox run -e isort -- plugins/modules/{{ file }}.py
tox run -e isort-lint -- plugins/modules/{{ file }}.py
```

- Review rewritten files and use the `black` skill after sorting imports.
- Run `tox run -m format` for all formatters and automatic fixes.
- Run `tox run -m lint` for the full lint suite.
