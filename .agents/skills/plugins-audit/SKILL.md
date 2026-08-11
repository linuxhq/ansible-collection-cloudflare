---
name: plugins-audit
description: Audit and optimize the entire plugins/ tree until three consecutive full source-audit passes find no actionable issues or worthwhile optimizations, then run checks once. Use for exhaustive plugin reviews where clean tests alone are not completion.
---

# Plugins audit

Audit every file under `plugins/` for correctness, security, maintainability,
duplication, dead code, and worthwhile simplifications. Apply ponytail: reuse
existing helpers, prefer deletion, and make the smallest root-cause fix.

## Boundaries

- Preserve unrelated worktree changes.
- Update or add the smallest relevant tests when behavior changes or non-trivial
  logic is added.

## Audit loop

1. Build a sorted list of every in-scope file under `plugins/`. Start the clean
   audit-pass count at zero.
2. Starting at the first file, open and read the full current contents of every
   listed file in bounded chunks that fit the tool output limit. Truncated,
   rejected, or omitted output does not count as reviewed; reopen it from the
   last confirmed line. Review each file's public contract, validation, check mode,
   idempotence, SDK calls and failures, pagination and waits, and returned data.
   For shared code, enumerate callers and inspect every affected path before
   editing it. This complete traversal is one audit pass.
3. If the pass finds any actionable issue or worthwhile optimization, apply
   every resulting change, update the smallest relevant tests, and reread every
   changed file and affected shared caller. Reset the clean audit-pass count to
   zero, then restart at the first file with a new full audit pass.
4. If the pass finds no actionable issue or worthwhile optimization, increment
   the clean audit-pass count. Restart at the first file and repeat until three
   consecutive full audit passes are clean.

Automated searches, diffs, AST summaries, lint, tests, and review performed in a
previous audit do not prove source coverage. Report the reviewed file count; no
persistent review ledger is required.

## Final verification

After three consecutive clean audit passes, run the full applicable checks once
through the `black`, `ruff`, and `ansible-test` skills, plus relevant unit tests.
If a check exposes an issue or changes an in-scope file, fix it and restart the
audit loop from zero. Apply the same rule when a check exposes a worthwhile
optimization; otherwise finish.

Report source-review coverage, fixes, tests run, and evidence for all three
consecutive clean audit passes.
