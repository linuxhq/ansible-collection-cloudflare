---
name: plugins-audit
description: Audit and optimize every source file in the plugins/ tree one at a time, requiring three consecutive clean full-source passes on each file before advancing, then run checks once. Use for exhaustive plugin reviews where clean tests alone are not completion.
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

1. Build a sorted list of every in-scope source file under `plugins/`. Record the
   inventory count and current line count for each file. Create a checklist with
   one entry per file containing its filename, line count, confirmed line range,
   clean-pass count, and status. Initialize every clean-pass count to zero. Keep
   the checklist in working memory or a temporary file outside the repository.
2. Start with the first file and work on that file only. Do not open or audit a
   later inventory file until the current file has three consecutive clean
   full-source passes.
3. For each pass on the current file, read its full current contents from line 1
   through its confirmed final line. Open exactly one source file per tool call;
   never combine source files in one call. Use bounded chunks when necessary,
   but every chunk call must contain only the current file. Truncated, rejected,
   omitted, or ambiguous output invalidates the pass. Immediately reopen the
   same file from the last confirmed line with a smaller output bound before any
   other source read. A prior pass, prior-turn review, automated output
   processing, diff, summary, lint result, or test result never substitutes for
   rereading the file in the current pass.
4. Review the current file's public contract, validation, check mode,
   idempotence, SDK calls and failures, pagination and waits, returned data,
   correctness, security, maintainability, duplication, dead code, and worthwhile
   simplifications. For shared code, enumerate callers and inspect every affected
   path before editing it.
5. A pass counts only when the current file was read completely from line 1 and
   its confirmed final line equals its current recorded line count. If the pass
   finds no actionable issue or worthwhile optimization, increment only that
   file's clean-pass count and begin another full pass on the same file.
6. If any pass finds an actionable issue or worthwhile optimization, apply every
   resulting change and update the smallest relevant tests. Run focused tests,
   then reread every changed file and affected shared caller completely. Update
   recorded line counts and reset the current file's clean-pass count to zero.
   The reread required after editing verifies the edit but does not count as a
   clean audit pass. Begin again at pass one on the same current file.
7. Mark the current file complete and advance to the next sorted inventory file
   only after its clean-pass count reaches three without an intervening change.
   Never reset or discard completed earlier files merely because a later file
   changes. If a later change also modifies an earlier completed source file,
   reset that modified file's counter to zero and complete three new clean passes
   on it before audit completion.
8. The source audit is complete only when the checklist contains every inventory
   file exactly once and every file is marked complete at three consecutive clean
   passes. Verify the completed count equals the inventory count.

Automated searches, diffs, AST summaries, lint, tests, and review performed in a
previous audit do not prove source coverage. Report the reviewed file count and
excluded paths. Do not claim completion or hand off an in-progress audit as if it
were complete; report partial progress only when the user interrupts or a genuine
blocker prevents continued work. No persistent repository ledger is required.

## Final verification

After every inventory file has three consecutive clean passes, run the full
applicable checks once through the `black`, `isort`, `ruff`, and `ansible-test`
skills, plus relevant unit tests. If a check exposes an issue or changes an in-scope
file, fix it, reset every affected file's clean-pass count to zero, and complete
three new clean full-source passes on each affected file before rerunning final
verification. Apply the same rule when a check exposes a worthwhile
optimization; otherwise finish.

Report source-review coverage, fixes, tests run, exclusions honored, and evidence
that every file reached three consecutive clean full-source passes.
