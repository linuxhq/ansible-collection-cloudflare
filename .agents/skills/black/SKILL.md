---
name: black
description: Format Python code with black through Tox.
---

# black

- Use the `tox` skill for environment setup and run from the collection root.
- Run after edits under `plugins/`; replace the example path with the changed file.
- Review rewritten files and use the `ruff` skill for linting.

```sh
tox run -e black -- plugins/modules/{{ file }}.py
```

- Run `tox run -m format` for all formatters and automatic fixes.
- Run `tox run -m lint` for the full lint suite.
