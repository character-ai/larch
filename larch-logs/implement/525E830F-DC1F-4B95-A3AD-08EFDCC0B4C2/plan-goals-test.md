## Goal

Ensure that 100% of error messages from any failing tool, agent, or Bash call across the /implement and /fix-issue workflow transitive closure get tracked verbatim (not summarized/distilled) and appended to execution-issues.ndjson, to enable post-hoc debugging.

## Goal

Ensure that 100% of error messages from any failing tool, agent, or Bash call across the /implement and /fix-issue workflow transitive closure get tracked **verbatim** (not summarized/distilled) and appended to `execution-issues.ndjson`, to enable post-hoc debugging. Per the user's explicit clarification: **100% of error messages must be saved, not just a distillation/summary.**

## Implementation Plan

### Existing infrastructure (preserve)

- Local sink: `$IMPLEMENT_TMPDIR/execution-issues.md` (markdown with category sections).
- Append helper: `scripts/append-execution-issue.sh` — appends a single bullet under a named category section.
- Final NDJSON flush: Step 11 of `/implement` reads `execution-issues.md` and emits the `execution-issues` larch-log batch (which becomes `larch-logs/implement/<RUN_ID>/execution-issues.ndjson`).
- Categories: `Pre-existing Code Issues`, `Tool Failures`, `Permission Prompts`, `External Reviewer Issues`, `CI Issues`, `Warnings`, `Q/A`.

### Audit findings (gaps to close)

- `/design` SKILL.md: only 2 append sites (Step 3b sanitizer/generation failures). Reviewer launches, sketches, collect-agent-results failures, judge failures are silently swallowed.
- `/review` SKILL.md: **ZERO** append sites — entire skill is silent on tool failures.
- `scripts/ship-pr.sh`: only 1 append site (line 422, PR-body diagram rejection). All other `gh`/`git`/helper failures silently `|| true` or `2>/dev/null`.
- `/implement` SKILL.md main body: many `|| true` patterns hide failures from `tracking-issue-summary.sh`, `larch-log.sh commit`, `token-report.sh`, `timing-report.sh`, etc.

### Files to create/modify

1. **NEW: `scripts/append-tool-failure.sh`** + sibling `.md` contract + test `scripts/test-append-tool-failure.sh` + `.md`.
   - Wraps `append-execution-issue.sh` with verbatim-content semantics.
   - Interface: `append-tool-failure.sh --log <path> --site <step-id> --tool <label> --exit-code <N> --category <Tool Failures|External Reviewer Issues|CI Issues|Warnings> --output-file <path-to-captured-stderr-stdout> [--redact]`
   - Reads `--output-file` verbatim (no truncation). Optionally pipes through `scripts/redact-secrets.sh` when `--redact` is passed. Composes a bullet of the form:
     ```
     - **Step <site> — <tool> failed (exit <N>)**:
       ```
       <verbatim captured content>
       ```
     ```
   - Delegates to `append-execution-issue.sh` for the actual section-insertion (preserves atomic write).
   - Exit semantics: prints `APPENDED=true LOG=<path>` on success; `FAILED=true ERROR=<msg>` non-zero on failure. **Never** propagates non-zero up: callers wrap as `append-tool-failure.sh ... || true` so a logging failure does not derail the parent flow — but the helper itself surfaces the reason for any debugging step that later inspects stderr.
   - Make the helper Bash-3.2 portable (mac default `/bin/bash`).

2. **`skills/design/SKILL.md`** — wrap every external tool / agent invocation:
   - Every `launch-review.sh --tool codex/cursor` (sketches Step 2a, plan-review reviewers Step 2a.5, judge Step 3, dialectic Step 3.5).
   - Every `collect-agent-results.sh` call — when the collector reports `STATUS=FAILED/TIMED_OUT/SENTINEL_TIMEOUT/EMPTY_OUTPUT/NOT_SUBSTANTIVE/cap_hit` for any output, read the (possibly empty) output file and the `.diag` sidecar verbatim, then call `append-tool-failure.sh` with `--category 'External Reviewer Issues'`.
   - Agent-tool subagent failures: capture the Agent return value and append on non-zero / explicit failure markers.
   - Target the parent's tmpdir when running as subagent: `$(dirname "$SESSION_ENV_PATH")/execution-issues.md` (consistent with the existing Step 3b convention).
   - Step 5 cleanup MUST NOT remove `execution-issues.md` — only its own `$DESIGN_TMPDIR` artifacts.

3. **`skills/review/SKILL.md`** — same pattern:
   - Wrap each `launch-review.sh` (specialists in Step 2.4, vote launches in Step 3.4) with `append-tool-failure.sh` on failure.
   - Wrap each `collect-agent-results.sh` call.
   - Wrap subagent dispatch failures.
   - Target the parent's `$IMPLEMENT_TMPDIR/execution-issues.md` via `$(dirname "$SESSION_ENV_PATH")`.

4. **`scripts/ship-pr.sh`** — exhaustive in-script logging:
   - Define a local helper function `append_tool_failure_local()` that:
     - Resolves the log path from the state file's `IMPLEMENT_TMPDIR` key (read non-destructively, never `source` it).
     - Calls `append-tool-failure.sh` with `--log "$IMPLEMENT_TMPDIR/execution-issues.md"`.
     - Falls back to stderr-only when the state file is absent or unreadable.
   - Audit every `gh`, `git`, and helper invocation in the script. For each:
     - Capture stderr (and stdout where it carries the error) to a `$IMPLEMENT_TMPDIR/ship-pr-fail-<phase>-<n>.log` temp file.
     - On non-zero exit, call `append_tool_failure_local --site "<phase>" --tool "<cmd>" --exit-code <N> --output-file <captured>` BEFORE deciding whether to retry, bail, or continue.
   - Cover: phase=checks, phase=bump, phase=changelog, phase=rebase, phase=pr-create, phase=ci-monitor, phase=ci-merge, phase=conflict-resolution, phase=postmerge, phase=teardown.
   - Existing single append at line 422 stays; new ones are additive.

5. **`skills/implement/SKILL.md`** main body — focused replacement of swallowed-failure `|| true` patterns:
   - Step 0.5 Branches 1-4: `tracking-issue-write.sh rename` already logs to `Tool Failures` in some places — verify uniform across all 4 branches; add for any missing.
   - Step 0.5 / Step 1 / Step 7a / Step 18: `tracking-issue-summary.sh upsert-summary || true` — upgrade to capture stderr + `append-tool-failure.sh`.
   - Step 7a tail + Step 18: `token-report.sh`, `timing-report.sh`, `larch-log.sh write`, `larch-log.sh commit` — same upgrade.
   - Step 7a code-flow generation: already partial via `append-execution-issue.sh`; ensure the same callsite captures the sanitizer's full stderr/stdout, not just the REASON_TOKEN.
   - Step 5 quick-mode reviewer-dirty-tree path: existing `Warnings` entries kept; supplement with `External Reviewer Issues` when collector reported failure.
   - Phantom Untracked Probe failures: preserve existing pattern (already appends).
   - Step 18 session-transcript commit: already has explicit logging — preserve.

6. **Flush guarantee** — verify the NDJSON batch always lands in `larch-logs/implement/<RUN_ID>/execution-issues.ndjson` before tmpdir removal:
   - Step 11 (already converts `.md` → batch records) is the green-path flush.
   - Add a safety-net flush in `implement-finalize.sh teardown` BEFORE `cleanup-tmpdir.sh` removes `$IMPLEMENT_TMPDIR`. If `execution-issues.md` has entries that have not been appended to the batch (sentinel-based or content-hash check), append the residue.
   - The Step 12d bail path already routes through Step 16 → Step 17 → Step 18; Step 11's earlier execution covers the typical case, but the teardown safety-net is needed for failures occurring AFTER Step 11's execution.

### Edge cases

- **Verbatim multi-line content**: `append-execution-issue.sh` accepts a multi-line `--entry` (its awk script uses `print entry`). Use `--entry "$(cat tmpfile)"` to pass the full content. Bash supports multi-line argv.
- **Long errors (>1 MB)**: do not truncate in the local `.md` or NDJSON. `larch-log.sh` runs `redact-tmpdir-paths.sh` + `redact-secrets.sh` automatically before writing.
- **Concurrent writers**: `append-execution-issue.sh` uses atomic `mv` via temp file; concurrent appends from parallel reviewer slots in /design and /review COULD lose entries. Mitigation: pre-stage each capture to a unique `$TMPDIR/<slot>-fail.log` and append SERIALLY in the wait-and-collect step (not in the parallel launch step).
- **Sanitization**: ship-pr.sh and the new helper script invoke `redact-secrets.sh` on captured content before composing the bullet to keep secrets out of public surfaces (the tracking issue and the committed log batch).
- **Stand-alone ship-pr.sh** (no IMPLEMENT_TMPDIR): fall back to stderr-only logging; the new helper detects an empty state file and emits a diagnostic, not a crash.

### Test plan

- `scripts/test-append-tool-failure.sh` covers:
  1. Single-line error: bullet contains exact text.
  2. Multi-line stderr: code-fenced multi-line body in the bullet; no whitespace-collapsing.
  3. Large content (~64 KB): no truncation, byte-exact preservation.
  4. Category routing: each accepted category maps to the right `### <Category>` section.
  5. Redaction: when `--redact` is passed, secrets matching `redact-secrets.sh` patterns are replaced; non-secret content is untouched.
  6. Missing input file: emits `FAILED=true ERROR=...`, exits non-zero, does not modify the log.
  7. Atomicity: a forced awk failure does not leave a partially-rewritten log (preserve tmp+mv pattern).
  8. Bash-3.2 portability: run under `bash --version` matching 3.2 (or a `LARCH_COMPAT_BASH=32` env shim if available) and assert behavior identical.
- `scripts/test-ship-pr.sh` (existing): extend or add cases that simulate a failing `gh pr create` and assert the captured stderr lands in `$IMPLEMENT_TMPDIR/execution-issues.md` under `### Tool Failures`.
- Existing harness `scripts/test-execution-issues-pipeline.sh` (verify it exists; otherwise the test above covers the flush).
- After each `Edit`, run `/relevant-checks` (pre-commit on changed files + agent-lint on full repo) and ensure clean.

### Verification (post-implementation)

- Grep audit: `grep -rnE "\\|\\| true" scripts/ship-pr.sh skills/implement/SKILL.md skills/design/SKILL.md skills/review/SKILL.md` and confirm each remaining `|| true` is either (a) deliberately benign (e.g., `mark` calls that genuinely do not affect run state) or (b) preceded/followed by an `append-tool-failure.sh` call.
- Run `/relevant-checks` once at the end (pre-commit + agent-lint) and confirm zero new lint errors.
- Run `/implement` once with `--quick --merge` on a trivial repo change; inspect `larch-logs/implement/<RUN_ID>/execution-issues.ndjson` and confirm it captures any synthetic failures emitted during the run.

### Out of scope (deliberate)

- Capturing failures from non-/implement, non-/fix-issue skills (e.g., `/research`, `/issue`).
- Backfilling `execution-issues` records for past runs.
- Auto-filing tool failures as GitHub issues (the user said "track and add to execution-issues.ndjson", not "auto-file").
- Restructuring the `execution-issues` batch format (preserve NDJSON record schema).

## Test plan

- New helper: scripts/test-append-tool-failure.sh covers single-line, multi-line, large content (~64 KB), category routing, redaction toggle, missing input, atomicity, Bash-3.2 portability.
- Extend scripts/test-ship-pr.sh with a simulated `gh pr create` failure that should land verbatim in $IMPLEMENT_TMPDIR/execution-issues.md under ### Tool Failures.
- Run /relevant-checks (pre-commit + agent-lint) after each edit; ensure clean.
- End-to-end: after implementation, inspect larch-logs/implement/<RUN_ID>/execution-issues.ndjson and confirm a synthetic failure round-trips byte-exact through the flush.
