---
name: unit
description: Run the collection's Python unit tests with pytest through Tox.
---

# unit

```sh
tox run -m unit
tox run -m unit -- tests/unit/plugins/modules/test_{{ module }}.py
```

## Dependencies

- `tox` skill
