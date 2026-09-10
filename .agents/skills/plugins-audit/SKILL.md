---
name: plugins-audit
description: Audit and improve every plugin source file, requiring three consecutive clean passes per file.
---

# plugins-audit

- Audit source files under `plugins/` for correctness, security, maintainability,
  duplication, dead code, and useful simplifications.
- Reuse existing helpers, prefer deletion, and make the smallest fix that addresses the cause.

## Boundaries

- Preserve unrelated worktree changes.
- Add or update focused tests when behavior changes or non-trivial logic is added.

## Track coverage

- Build a sorted inventory of every in-scope source file under `plugins/` and record the count.
- Keep a checklist in memory or a temporary file outside the repository. Track each file's
  name, current line count, confirmed line range, clean-pass count, and status.
- Start every clean-pass count at zero. Record excluded paths.

## Review each file

- Work through the inventory in order. Finish three consecutive clean full-source passes
  on the current file before auditing the next file.
- Read the current file from line 1 through its confirmed final line on every pass.
  Read exactly one source file per tool call; use bounded chunks for large files.
- Truncated, rejected, omitted, or ambiguous output invalidates the pass. Reopen the same
  file from the last confirmed line with a smaller output bound before reading another source.
- Review the public contract, validation, check mode, idempotence, SDK calls and failures,
  pagination, waits, returned data, and the concerns listed above.
- Before editing shared code, enumerate callers and inspect every affected path.
- Count a pass only when the full file was read, its final line matches the recorded line
  count, and no actionable issue or useful optimization remains.
- Searches, diffs, summaries, lint, tests, and prior reviews do not replace a fresh full read.

## Handle changes

- Apply fixes and relevant test updates, then run focused tests.
- Reread every changed file and affected shared caller completely. Update line counts
  and reset the current file's clean-pass count to zero.
- The reread after editing verifies the change; it does not count as a clean audit pass.
- Mark a file complete after three consecutive clean passes without an intervening change.
- Keep completed files complete unless they change. If a later edit changes an earlier file,
  reset that file's counter and complete three new clean passes before finishing the audit.

## Verify and report

- Confirm every inventory file appears exactly once in the checklist and has three clean
  passes. The completed count must equal the inventory count.
- Run the full applicable checks once through the `black`, `isort`, `ruff`, `ansible-test`,
  and `unit` skills after completing source review.
- If checks expose an issue or useful optimization, fix it. If checks or fixes change source
  files, reset each affected file's counter and complete three new clean full-source passes
  before rerunning final verification.
- Report coverage, fixes, tests run, exclusions honored, and evidence of three clean passes
  for every file.
- Report partial progress only if the user interrupts or a blocker prevents continuation;
  do not present an unfinished audit as complete.
