---
name: ruff
description: Lint and fix Python code with ruff through Tox.
---

# ruff

- Use the `tox` skill for environment setup and run from the collection root.
- Run after edits under `plugins/`; replace the example path with the changed file.
- `ruff-lint` checks for findings; `ruff` applies automatic fixes.

```sh
tox run -e ruff-lint -- plugins/modules/{{ file }}.py
tox run -e ruff -- plugins/modules/{{ file }}.py
```

- Review rewritten files and fix remaining findings by hand.
- Use the `black` skill for Python formatting.
- Run `tox run -m lint` for the full lint suite.
- Run `tox run -m format` for all formatters and automatic fixes.
