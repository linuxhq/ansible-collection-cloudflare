---
name: blank-line-after-blocks
description: Add blank lines after Python control-flow blocks through Tox.
---

# blank-line-after-blocks

- Use the `tox` skill for environment setup and run from the collection root.
- Tox runs the upstream formatter pinned in `requirements.txt`, matching pre-commit.
- Omit the path to format Python files under `plugins/` and `tests/`, or select a file:

```sh
tox run -e blank-line-after-blocks
tox run -e blank-line-after-blocks -- plugins/modules/{{ file }}.py
```

- Exit code 1 with `Rewriting` messages means files changed. Review the diff and rerun;
  a clean run exits 0. Investigate tracebacks and other errors.
- Use the `black` skill afterward with the configured 120-character limit, then confirm
  another spacing pass makes no changes.
- The formatter separates completed `if`, `for`, `while`, `with`, and `try` blocks;
  it does not infer boundaries between consecutive simple statements.
- CI enforces spacing through pre-commit. The Tox environment uses the `format` label
  because it modifies files.
