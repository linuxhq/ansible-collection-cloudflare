---
name: blank-line-after-blocks
description: Add blank lines after Python control-flow blocks through Tox.
---

# blank-line-after-blocks

Uses the version pinned in `requirements.txt`, matching the pre-commit hook.
Tox and the pre-commit hook both cover Python files under `plugins/` and `tests/`.

```sh
tox run -e blank-line-after-blocks
tox run -e blank-line-after-blocks -- plugins/modules/{{ file }}.py
```

- Exit code 1 with `Rewriting` messages means files were formatted. Inspect
  the diff and rerun; a clean second run exits 0. Investigate tracebacks or
  other errors instead of treating every exit code 1 as success.
- Run the upstream formatter directly; it modifies files.
- Use the Black skill afterward, retaining the configured 120-character
  limit. Check that another spacing pass makes no changes.
- It separates completed `if`, `for`, `while`, `with`, and `try` blocks.
  It does not infer semantic boundaries between consecutive simple statements.
- CI enforces spacing through pre-commit. This environment belongs to the
  `format` label, not `lint`, because it modifies files.

## Dependencies

- `tox` skill
- `black` skill
