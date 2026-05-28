## Plan

## Files to modify/create

### UPDATED: `scripts/lib-quiet.sh`
Remove three helpers that have no remaining callers after callsite migration:
- `larch_quiet_write_breadcrumb_record` (lines 154-176)
- `emit_breadcrumb` (lines 287-340)
- `emit_breadcrumb_stderr` (lines 345-380)

Drop the function bodies and their header comments. **Keep `larch_quiet_bc_valid_category` (lines 147-152)** because `scripts/breadcrumb-monitor.sh` still calls it; its removal is deferred to Piece 3 (per FINDING_6). Also keep `larch_err`, `larch_errf`, `emit`, `emit_kv`, `sanitize_diagnostic_line`, `larch_quiet_truthy`, `larch_quiet_default_log`, `larch_quiet_fd3_is_visible`, `larch_quiet_init`, the paired-PID machinery (`larch_quiet_write_paired_pid_file`, `larch_quiet_warn_paired_pid_invalid`, `larch_quiet_source_larch_log_lib`), and the sentinel machinery (`larch_quiet__exit_write_done`, `larch_quiet__exit_combo`, `larch_quiet_append_done_trap`). `LARCH_BREADCRUMB_STREAM` env-var detection inside `larch_quiet_init` stays — it is consumed by `breadcrumb-monitor.sh` and the env-var plumbing is retained until Piece 3.

**Contract change is intentional** (per FINDING_7): the second path is taken — drop both `emit_breadcrumb` and `emit_breadcrumb_stderr` outright and retarget consumer expectations + harnesses (see test updates below). `larch_err` / `larch_errf` write to stderr / FD-4 and do NOT emit `larch:bc` stream records or write to the breadcrumb stream; this is the intended end state for Stage 2 callsites. Live `/implement` chat-progress regressions are accepted as Stage 2 cost; Piece 3 removes the monitor stack entirely.

### UPDATED: `scripts/lib-quiet.md`
Drop the `emit_breadcrumb` and `emit_breadcrumb_stderr` API documentation sections plus the category-vocabulary description for those APIs. Trim the changelog / summary lines that named those APIs. **Keep** the `larch_quiet_bc_valid_category` reference paragraph (still consumed by `breadcrumb-monitor.sh` until Piece 3). Keep all other sections (paired-PID, sentinel, `larch_err`, `larch_errf`, `emit`, `emit_kv`, `larch_quiet_init`).

### UPDATED: `scripts/test-lib-quiet.sh`
Delete every test case that calls the removed APIs (per FINDING_1):
- Cases #4, #5, #5b (lines 71-91) — quiet/visible/alternate-FD `emit_breadcrumb` helper-generated cases.
- Cases #13-#18 (lines 141-196) — `emit_breadcrumb_stderr` semantics, `emit_breadcrumb` stream behavior, category validation, payload-cap behavior.

Retain tests for `emit`, `emit_kv`, `larch_err`, `sanitize_diagnostic_line`, paired-PID, sentinels, `larch_quiet_init`, and the retained `larch_quiet_bc_valid_category` helper. Renumber the remaining test cases and assertion IDs to close all gaps.

### UPDATED: `scripts/test-lib-quiet.md`
Drop documentation entries for every deleted test (both the case-#4/#5/#5b group and the #13-#18 group). Remove summary prose that still describes `emit_breadcrumb` as a public contract. Renumber subsequent entries to match.

### UPDATED: `scripts/lib-larch-log.sh`
In `larch_log_publish_breadcrumbs_shared` (lines 401-489), remove the legacy ndjson stream fallback:
- Delete the `ndjson_source_ok` local-variable declaration (line 404).
- Delete the `source_dir`-existence + path-safety block (lines 409-427) since only the quiet-log loop remains and `session_root` derivation moves up.
- Delete the ndjson loop (lines 448-462).
- Update the early-return guard on line 433 from `[ "$ndjson_source_ok" != true ] && [ "$quiet_source_ok" != true ]` to `[ "$quiet_source_ok" != true ]`.
- Remove the `[ "$ndjson_source_ok" = true ]` guard on line 448 and the surrounding `if/fi`.

Keep the function signature `(source_dir, dest_dir, on_error)`, `session_root="$(dirname "$source_dir")"` computation, the `larch_log_breadcrumbs_under_session_tmp "$session_root"` guard, the quiet-log loop (lines 464-478), the atomic-swap helper, and the `larch_log_breadcrumb_source_dir` helper (still used by `larch-log.sh commit` to derive `source_dir`).

### UPDATED: `scripts/lib-larch-log.md`
Drop any reference to the transitional ndjson fallback added in Stage 1. State that the quiet-log loop is the sole staging path; ndjson streams are no longer produced or staged.

### UPDATED: `scripts/larch-log.md`
Drop the transitional-fallback sentence that was added in the Stage 1 plan's Breadcrumb commit artifact paragraph. Note quiet-log-only behavior.

### UPDATED: `SECURITY.md`
Update only the breadcrumb publication / run-log security paragraphs (per FINDING_8). Replace stale NDJSON stream-publication language with the quiet-log-only staging contract. Keep existing redaction guidance, tmpdir-boundary rules, and the rejection guards (no-symlink, no-hardlink, under-session-tmpdir) intact.

### UPDATED: `docs/run-logs.md`
Update the breadcrumb artifact contract to say committed `larch-logs/<skill>/<run-id>/breadcrumbs/` entries are staged from quiet logs only (per FINDING_8). Remove descriptions that imply `*.ndjson` stream files are produced or published by the Stage-2 surface.

### UPDATED: `scripts/ship-pr.sh`
Convert 26 `emit_breadcrumb [--category=X] TEXT` callsites to `larch_err "TEXT"`: drop `--category=X`, preserve text verbatim including the leading visual prefix (⚠ ⛔ → 🟢 etc.). No `emit_breadcrumb_stderr` callsites in this file.

### UPDATED: `scripts/ship-pr.md`
Drop any sibling-doc references to `emit_breadcrumb` or category vocabulary in the breadcrumb-related sections.

### UPDATED: `scripts/ci-wait.sh`
Convert all 12 `emit_breadcrumb_stderr --category=X FORMAT args...` callsites to `larch_errf "FORMAT" args...` (per FINDING_9: **preserve printf semantics verbatim; do NOT add `\n`**). Keep the existing trailing `\n` on the 10 callsites that already have one (lines 191, 207, 222, 238, 253, 255, 257, 259, 273, 284). For the two inline-progress callsites that omit trailing newlines, convert without adding `\n`:
- Line 184: `larch_errf "⏳ CI: waiting"` (no newline; banner stays inline).
- Line 270: `larch_errf "."` (no newline; dot progress stays on one line).

### UPDATED: `scripts/ci-wait.md`
Drop emit_breadcrumb_stderr references; note the script now uses `larch_errf` and inline-progress callsites retain their no-newline format.

### UPDATED: `scripts/collect-agent-results.sh`
Convert 2 callsites: `emit_breadcrumb --category=retry "..." >&2` (lines 156, 171) → `larch_err "..."`. Drop the `>&2` redirect. **Intentional visibility shift** (per FINDING_10): the original `>&2` wrote to current FD2 (the quiet log when `larch_quiet_init` had redirected stderr). `larch_err` writes to FD4 (original stderr) instead, so these retry breadcrumbs now reach the operator transcript directly. This is the desired Stage 2 behavior — retry events should be operator-visible — and matches the broader migration intent that `larch_err` is the operator-visible diagnostic channel.

### UPDATED: `scripts/collect-agent-results.md`
Drop emit_breadcrumb references. Note that retry events now reach operator stderr directly via `larch_err`.

### UPDATED: `scripts/implement-finalize.sh`
Convert 17 `emit_breadcrumb [--category=X] TEXT` callsites to `larch_err "TEXT"`.

### UPDATED: `scripts/implement-finalize.md`
Drop emit_breadcrumb references.

### UPDATED: `scripts/implement-bootstrap.sh`
Convert 7 `emit_breadcrumb [--category=X] TEXT` callsites to `larch_err "TEXT"`.

### UPDATED: `scripts/implement-bootstrap.md`
Drop emit_breadcrumb references.

### UPDATED: `scripts/rebase-checkpoint-probe.sh`
Convert 1 callsite.

### UPDATED: `scripts/rebase-checkpoint-probe.md`
Drop emit_breadcrumb references.

### UPDATED: `scripts/phantom-probe-with-warn.sh`
Convert 1 callsite.

### UPDATED: `scripts/lib-voter-parse-rate.sh`
Convert 1 callsite.

### UPDATED: `scripts/generate-code-reviewer-agent.sh`
Convert 1 callsite.

### UPDATED: `scripts/generate-pre-rendered-reviewer-prompts.sh`
Convert 1 callsite.

### UPDATED: `skills/cleanup/scripts/cleanup.sh`
Convert 4 callsites.

### UPDATED: `skills/upgrade-larch/scripts/upgrade-larch.sh`
Convert 20 callsites.

### UPDATED: `skills/set-up-forked-open-source-repo/scripts/setup-forked-open-source-repo.sh`
Convert 9 callsites.

### UPDATED: `skills/report-tokens/scripts/run-analysis.sh`
Convert 3 callsites.

### UPDATED: `skills/review/scripts/dispatch-panel.sh`
Convert 1 callsite.

### UPDATED: `skills/review/scripts/review-core.sh`
Convert 4 callsites.

### UPDATED: `skills/review-and-fix/scripts/review-and-fix.sh`
Convert 20 callsites.

### UPDATED: `skills/review-and-fix/scripts/review-implement-step5-loop.sh`
Convert 3 callsites.

### UPDATED: `.claude/skills/bump-version/scripts/apply-bump.sh`
Convert 1 callsite.

### UPDATED: `scripts/test-ship-pr.sh`
Delete the two `emit_breadcrumb() { :; }` stub definitions (lines 3532, 3585). Retarget any assertion that greps stdout for breadcrumb patterns to capture stderr instead (per FINDING_5) — `larch_err` writes to stderr / FD-4 under `LARCH_QUIET_DISABLE=1`, so harness `run_case` callsites that capture only stdout will miss the migrated output. Cover the test-ship-pr.sh:1107-1156 stdout-grep region called out by FINDING_7.

### UPDATED: `scripts/test-apply-bump.sh`
Retarget every stdout-only breadcrumb assertion to stderr (per FINDING_4). `scripts/apply-bump.sh` runs under `LARCH_QUIET_DISABLE=1` in tests, so replacing `emit_breadcrumb` with `larch_err` moves output from stdout to stderr. Either update `run_case` to merge stderr with stdout (`2>&1`) or update each `^apply-bump: retry` and related assertion to read from the captured stderr buffer. Apply uniformly across all retry / breadcrumb-shape cases, not just the single one originally listed.

### UPDATED: `scripts/test-implement-structure.sh`
Update emit_breadcrumb-related assertions to expect `larch_err`. Retarget any stdout-only captures to stderr per the same FINDING_5 rationale.

### UPDATED: `skills/implement/scripts/test-implement-bootstrap.sh`
Retarget stdout-only breadcrumb assertions to stderr (per FINDING_5). Covers the test-implement-bootstrap.sh:2489-2623 region called out by FINDING_7. Assertions that previously used `LARCH_QUIET_BREADCRUMB_FD=1` to surface breadcrumbs to stdout must follow the new `larch_err` contract: stderr capture instead.

### UPDATED: `skills/implement/scripts/test-implement-review-token-propagation.sh`
Update the 1 `emit_breadcrumb`-related assertion to expect `larch_err`.

### UPDATED: `skills/review-and-fix/scripts/test-review-and-fix.sh`
Update the 1 `emit_breadcrumb`-related assertion to expect `larch_err`.

### UPDATED: `scripts/test-ci-wait.sh`
Retarget every assertion that uses `LARCH_BREADCRUMB_STREAM` or expects committed NDJSON breadcrumb records from `ci-wait.sh` (per FINDING_2). After Stage 2, `ci-wait.sh` writes to stderr via `larch_errf`; tests must capture stderr and assert the format-string output instead. Drop stream-setup helpers that are no longer reached.

### UPDATED: `scripts/test-larch-log.sh`
Update breadcrumb publish assertions to expect quiet-log-only staging (per FINDING_3). Drop or retarget ndjson-only publish expectations (e.g., the legacy ndjson-loop assertions around lines 257-260). Keep redaction and hardlink-rejection cases that still apply to quiet-log files.

### UPDATED: `scripts/test-design-log-publish.sh`
Update breadcrumb publish assertions to expect quiet-log-only staging (per FINDING_3). Drop assertions that expect committed `*.ndjson` artifacts. Keep the exit-code contract (post-push hard-fail rc=1) and the `larch-quiet-*-*.log` exclusion test added in Stage 1.

## Approach

Single coherent diff in one PR. Order matters within the PR: all callsites are migrated first, then `lib-quiet.sh` drops the three removed-API helpers (`emit_breadcrumb`, `emit_breadcrumb_stderr`, `larch_quiet_write_breadcrumb_record`) while keeping `larch_quiet_bc_valid_category` intact, then `lib-larch-log.sh` drops the ndjson loop. Per-callsite substitution is mechanical:

- `emit_breadcrumb [--category=X] TEXT` → `larch_err "TEXT"` (drop `--category`, drop redundant `>&2`, preserve text verbatim)
- `emit_breadcrumb_stderr --category=X FORMAT args...` → `larch_errf "FORMAT" args...` (preserve printf semantics; do NOT add newlines)

The substitution intentionally changes the output channel (per FINDING_7): `emit_breadcrumb` previously wrote `larch:bc` records to the breadcrumb stream + quiet log; `larch_err` writes to stderr / FD-4. This is the desired end-state for Stage 2. Test harnesses that grep stdout-only must retarget to stderr — this is captured in the test file updates above.

Drop the three lib-quiet helpers once no caller references them. Drop test cases #4, #5, #5b, and #13-#18 in `test-lib-quiet.sh` and renumber the remaining cases. Trim sibling `.md` docs for changed scripts. Update `SECURITY.md` and `docs/run-logs.md` breadcrumb-publication paragraphs (per FINDING_8). Remove the ndjson loop and `ndjson_source_ok` plumbing from `larch_log_publish_breadcrumbs_shared`; the quiet-log loop is the only staging path.

`breadcrumb-monitor.sh`, `lib-redact-streaming.sh`, the Family-B portion of `lint-foreground-markers.sh`, BASH_AUTHORING.md §4, AGENTS.md, `LARCH_BREADCRUMB_*` / `LARCH_DONE_SENTINEL` / `LARCH_STATUS_FILE` / `LARCH_PAIRED_PID_FILE` env plumbing, and `larch_quiet_bc_valid_category` all stay in place — they are Piece 3 scope.

## Edge cases

- Callsites with explicit `>&2`: drop the redirect since `larch_err` already writes to stderr / FD-4 via `larch_quiet_init`. **Visibility shift is intentional** (per FINDING_10) — the original `>&2` wrote to FD2 (quiet log under `larch_quiet_init`); `larch_err` writes to FD4 (original stderr).
- Callsites using command substitution in the message (e.g., `emit_breadcrumb "step ${i} of $(wc -l < x)"`): preserve the same `"…"` text after the function rename.
- `emit_breadcrumb_stderr` callsites in `ci-wait.sh` line 184 (`"⏳ CI: waiting"`) and line 270 (`"."`) have no trailing `\n`; convert **without** adding `\n` (per FINDING_9) so inline banner / dot progress is preserved.
- Tests that stub `emit_breadcrumb` (`scripts/test-ship-pr.sh:3532, 3585`): delete the stubs entirely — no replacement needed because the migrated callsites use `larch_err` which is a real lib-quiet function.
- `larch_err` internal references inside the bodies of removed functions (e.g., `lib-quiet.sh:157`, `lib-quiet.sh:360`) disappear along with the function bodies.
- `LARCH_BREADCRUMB_STREAM` / `LARCH_QUIET_BREADCRUMBS` / `LARCH_QUIET_BREADCRUMB_FD` env vars are referenced only inside the removed functions and inside `larch_quiet_init` detection: the detection logic in `larch_quiet_init` stays untouched (Piece 3 owns env-plumbing removal).
- `larch_quiet_bc_valid_category` retained: `breadcrumb-monitor.sh` still calls it; removing the helper would break `scripts/test-breadcrumb-monitor.sh` under `set -e`.

## Failure modes

1. **Stale callsite at runtime → `emit_breadcrumb: command not found`.** A leftover callsite would fail at runtime after lib-quiet.sh drops the function. Earliest warning signal: `grep -rn 'emit_breadcrumb' --include='*.sh' --include='*.md' . | grep -v larch-logs/` at the end of the conversion pass; expected output is only Piece-3 surfaces (`breadcrumb-monitor.sh`, `lib-redact-streaming.sh`, `lint-foreground-markers.sh`, `BASH_AUTHORING.md`, `AGENTS.md`). Mitigation: run `make lint` / `bash scripts/relevant-checks.sh` which exercises affected scripts.
2. **breadcrumb-monitor regression.** If `larch_quiet_bc_valid_category` is accidentally removed, monitored `larch:bc` lines under `set -e` cause `command not found`. Earliest warning signal: `bash scripts/test-breadcrumb-monitor.sh`. Mitigation: leave the helper in `lib-quiet.sh` (per FINDING_6) and explicitly note this in the Approach section.
3. **lib-larch-log publish regression.** Removing the ndjson loop while a session still has `*.ndjson` files in `$IMPLEMENT_TMPDIR/breadcrumbs/` from a pre-Stage-2 run would silently drop those files. Earliest warning signal: `scripts/test-larch-log.sh`. Mitigation: keep the quiet-log loop; pre-Stage-2 ndjson loss is forensics-only and tolerated.
4. **test renumbering drift.** Deleting cases #4, #5, #5b, #13-#18 in `test-lib-quiet.sh` requires renumbering downstream cases and the sibling `test-lib-quiet.md`. Earliest warning signal: side-by-side diff review. Mitigation: renumber both files in the same commit.
5. **Stdout/stderr capture regression in test harnesses.** If a test harness still greps stdout for migrated breadcrumb output, the assertion silently passes against an empty buffer (false positive). Earliest warning signal: explicit retargeting in `test-apply-bump.sh`, `test-implement-bootstrap.sh`, `test-ship-pr.sh`, `test-ci-wait.sh` (per FINDINGS 2/4/5/7). Mitigation: every test file in scope that previously captured stdout for `emit_breadcrumb` output must update its capture to `2>&1` or to a stderr-only buffer; the test files listed above name the specific line ranges to retarget.

## Testing strategy

- Run `bash scripts/test-lib-quiet.sh` — verifies the trimmed lib-quiet API surface (`emit`, `emit_kv`, `larch_err`, `larch_errf`, paired-PID, sentinels, `sanitize_diagnostic_line`, retained `larch_quiet_bc_valid_category`) still passes after case-#4/#5/#5b and case-#13-#18 deletion + renumbering.
- Run `bash scripts/test-larch-log.sh` — verifies `larch_log_publish_breadcrumbs_shared` still stages quiet-log files into the committed `breadcrumbs/` directory after ndjson loop removal.
- Run `bash scripts/test-design-log-publish.sh` — verifies publish path still functions end-to-end after ndjson-only assertions are removed.
- Run `bash scripts/test-breadcrumb-monitor.sh` (per FINDING_6) — verifies the monitor still functions with `larch_quiet_bc_valid_category` retained but the emit APIs gone.
- Run `bash scripts/test-ci-wait.sh` — verifies `ci-wait.sh` writes the expected `larch_errf` stderr output with original inline-progress format preserved (no extra newlines).
- Run `bash scripts/test-ship-pr.sh` — verifies the largest callsite-migration target still passes after stub removal and stdout→stderr assertion retargeting.
- Run `bash scripts/test-apply-bump.sh` — verifies all `^apply-bump: retry` and breadcrumb-shape assertions still pass after stderr retargeting.
- Run `bash scripts/test-implement-structure.sh`, `bash skills/implement/scripts/test-implement-bootstrap.sh`, `bash skills/implement/scripts/test-implement-review-token-propagation.sh`, `bash skills/review-and-fix/scripts/test-review-and-fix.sh` — covers the remaining test files updated in this pass.
- Run `make lint` (which exercises `bash scripts/relevant-checks.sh` and the full pre-commit hook chain).
- Final check: `grep -rn 'emit_breadcrumb\|larch_quiet_write_breadcrumb_record' --include='*.sh' . | grep -v larch-logs/` — expected output is empty (`larch_quiet_bc_valid_category` is excluded from the grep; it intentionally stays). A separate grep `grep -rn 'larch_quiet_bc_valid_category' scripts/breadcrumb-monitor.sh` confirms the monitor still references the retained helper.


## Acceptance

- `grep -rn 'emit_breadcrumb\|larch_quiet_write_breadcrumb_record' --include='*.sh' . | grep -v larch-logs/` returns the empty set (the three removed APIs leave zero callsites in tree).
- `grep -rn 'larch_quiet_bc_valid_category' scripts/breadcrumb-monitor.sh` returns at least one hit (helper retained for Piece 3 per FINDING_6).
- `bash scripts/test-lib-quiet.sh` passes after deletion of cases #4, #5, #5b, #13-#18 and renumbering.
- `bash scripts/test-larch-log.sh` passes; quiet-log-only staging verified after ndjson loop removal.
- `bash scripts/test-design-log-publish.sh` passes; ndjson-only publish expectations removed.
- `bash scripts/test-breadcrumb-monitor.sh` passes (helper retention validated).
- `bash scripts/test-ci-wait.sh` passes; ci-wait stderr output preserves inline-progress format (no added `\n` on the two no-newline callsites).
- `bash scripts/test-ship-pr.sh` passes after stub removal and stdout→stderr assertion retargeting (covers test-ship-pr.sh:1107-1156 region).
- `bash scripts/test-apply-bump.sh` passes after stderr retargeting for all `^apply-bump: retry` and breadcrumb-shape assertions.
- `bash skills/implement/scripts/test-implement-bootstrap.sh` passes after stderr retargeting (covers test-implement-bootstrap.sh:2489-2623 region).
- `bash scripts/test-implement-structure.sh`, `bash skills/implement/scripts/test-implement-review-token-propagation.sh`, `bash skills/review-and-fix/scripts/test-review-and-fix.sh` pass.
- `make lint` passes (full pre-commit hook chain).
- `scripts/lib-quiet.sh` no longer defines `emit_breadcrumb`, `emit_breadcrumb_stderr`, or `larch_quiet_write_breadcrumb_record`; `larch_quiet_bc_valid_category`, `larch_err`, `larch_errf`, `emit`, `emit_kv`, `sanitize_diagnostic_line`, paired-PID, and sentinel helpers are preserved.
- `scripts/lib-larch-log.sh::larch_log_publish_breadcrumbs_shared` no longer contains the ndjson loop or `ndjson_source_ok` plumbing; the quiet-log loop is the sole staging path.
- `SECURITY.md` and `docs/run-logs.md` no longer describe NDJSON stream publication; quiet-log-only staging language replaces it.
- `scripts/breadcrumb-monitor.sh`, `scripts/lib-redact-streaming.sh`, the Family-B portion of `scripts/lint-foreground-markers.sh`, `BASH_AUTHORING.md` §4, `AGENTS.md`, and the `LARCH_BREADCRUMB_*` / `LARCH_DONE_SENTINEL` / `LARCH_STATUS_FILE` / `LARCH_PAIRED_PID_FILE` env-var plumbing are unchanged (Piece 3 scope).

diff_lines: 720
