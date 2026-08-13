---
name: isort
description: Sort and check Python imports with isort through Tox.
---

# isort

```sh
tox run -e isort -- plugins/modules/{{ file }}.py
tox run -e isort-lint -- plugins/modules/{{ file }}.py
tox run -m format
tox run -m lint
```

- Re-read files rewritten by isort.
- Format with `black` after sorting imports.

## Dependencies

- `tox` skill
