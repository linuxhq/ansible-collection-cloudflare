---
name: unit
description: Run the collection's Python unit tests with pytest through Tox.
---

# unit

- Use the `tox` skill for environment setup and run from the collection root.
- Run all unit tests:

```sh
tox run -m unit
```

- For focused testing, replace the example path with the relevant test file:

```sh
tox run -m unit -- tests/unit/plugins/modules/test_{{ module }}.py
```
