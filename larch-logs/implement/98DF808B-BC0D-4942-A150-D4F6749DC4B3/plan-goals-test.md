## Goal
Fix vendor CI-fix agent topology-validation knowledge gaps, wire exit-3 at FIX_ATTEMPTS≥10, add regression tests, and persist final-bail-reason.txt via larch-log batch

## Implementation Plan
## Plan

# Implementation Plan — Issue #2669 (revised after plan review)

ship-pr CI-fix grounding for topology drift + reachable exit-3 path + vendor-loop-exhaustion regression test + final-bail-reason.txt persistence

## Background

PR #2668 (`/implement` run `57797559-9368-4E52-9CDB-55B58AC1CE44`) exposed three coupled problems:

1. The vendor CI-fix waterfall (`launch-cursor-ci.sh` → `launch-codex-ci.sh` → `launch-claude-ci.sh`) failed to repair a topology-validation error even though the failure log printed a clear character-set constraint. The launchers' prompts are vendor-generic and carry no larch-specific knowledge of `skills/shared/topology.tsv` format rules or the `bash scripts/generate-topology-docs.sh` regen step.

2. `ship-pr.sh` reportedly exited 3 instead of 4 after the fix-loop exhausted. Diagnosis showed `exit 3` at `ship-pr.sh:2306` is effectively unreachable: `needs_user_bail_reason` requires exact-match `BAIL_REASON ∈ {fix-attempts-exhausted, design-flaw, escalate, all-vendors-failed}` and no real producer emits those tokens (`ci-decide.sh` emits free-form prose at the `FIX_ATTEMPTS >= 10` cap; the rest never set BAIL_REASON to one of the magic tokens). `/implement` Step 16 (`skills/implement/SKILL.md:1595`) still treats exit 3 as an active contract.

3. `$IMPLEMENT_TMPDIR/final-bail-reason.txt` is written by `scripts/restore-finalize-state.sh` at `/implement` Step 18 (using `BAIL_REASON` from `ship-pr-state.sh`), then removed when the session tmpdir is cleaned up. The committed run log under `larch-logs/implement/<RUN_ID>/` does not currently contain it.

Round 1 settled on: both sub-fixes ship in one plan; diagnose-then-fix; wire the `FIX_ATTEMPTS >= 10` cap to exit 3 (making the path reachable) AND add the vendor-loop-exhaustion regression test for the orthogonal exit-4 path; persist `final-bail-reason.txt` via a new committed larch-log batch slug.

Plan-review (10-reviewer panel + 6 dynamic scout slots = 16 reviewers) accepted 8 findings. FINDING_1 in particular flagged that the original plan's persistence wiring would NEVER fire on bail/stall paths because `refresh-run-logs.sh` is only invoked from ship-pr pre-push checkpoints. This revised plan moves the write into `restore-finalize-state.sh`.

## Approach

Four targeted changes, all small:

1. **Make the exit-3 path reachable**: `scripts/ci-decide.sh` at the `FIX_ATTEMPTS >= 10` branch (lines 124-128) emits the **exact-match** token `BAIL_REASON=fix-attempts-exhausted` (single line, no surrounding prose; the human-readable explanation moves to an adjacent shell comment). This causes `ship-pr.sh:2304` `needs_user_bail_reason` to return true, taking the exit-3 path at line 2306 — preserving `/implement` Step 16's exit-3 contract. The orthogonal exit-4 path (`run_evaluate_failure` `_max_fix=3` outer-attempts exhaustion → `exit_stall "10-max-retries"` at line 1503) remains untouched.

2. **Add a shared CI-fix knowledge fragment**: new file `skills/shared/ci-fix-failure-patterns.md` carries larch-specific repair patterns (topology.tsv composition character constraint `[A-Za-z0-9 ./+-]`, value-must-appear-in-runtime-authority, regen via `bash scripts/generate-topology-docs.sh`). Each of `scripts/launch-cursor-ci.sh`, `scripts/launch-codex-ci.sh`, `scripts/launch-claude-ci.sh` reads this file into a new `LARCH_PATTERNS` context block, included in their `PROMPT=` body only when `ROLE=fix`. The fragment loads from **the single canonical path `${PLUGIN_ROOT}/skills/shared/ci-fix-failure-patterns.md`** (all three launchers already define `PLUGIN_ROOT` near the top). If the file is missing the launcher continues with an empty patterns block.

3. **Add the vendor-loop-exhaustion regression test**: new block in `scripts/test-ship-pr.sh` (placed after the existing `ci_fix_escalation` block ending at line 2184) stubs `ci-wait.sh` (returns `ACTION=evaluate_failure` + `FAILED_RUN_ID=run123`), stubs `gh-run-logs.sh` (exit 0 so the vendor path engages), stubs `launch-cursor-ci.sh` + `launch-codex-ci.sh` + `launch-claude-ci.sh` **to emit `LAUNCHER_EXIT=1` on stdout AND exit 0 from the wrapper** (matching the production launcher protocol parsed at `ship-pr.sh:1364`), seeds state with `TRANSIENT_RETRIES=1` + `FAILED_RUN_ID=run123` + `FIX_ATTEMPTS=0` (so the cap doesn't fire first), and asserts ship-pr exits **4** with `STALL_STEP=10-max-retries` in state.

4. **Persist `final-bail-reason.txt` via a larch-log batch**: register `final-bail-reason .txt replace none` in `LARCH_LOG_BATCHES` in `scripts/larch-log-batches.sh`. **Move the publish call into `scripts/restore-finalize-state.sh`** at the end of `write_finalize_state()` — right after the line `printf '%s' "$(read_state BAIL_REASON)" > "$BAIL_REASON_FILE"` (line 71). Guard with `[ -s "$BAIL_REASON_FILE" ]` so empty postmerge-restored files are no-ops, and use the silent `2>/dev/null || true` pattern that matches adjacent `larch-log.sh write` calls. `$IMPLEMENT_TMPDIR` is set as a script-local variable already; the publish call needs `--log-root "$IMPLEMENT_TMPDIR/larch-logs" --skill implement --run-id "$RUN_ID"` where `RUN_ID` is read from `ship-pr-state.sh` via the existing `read_state` helper. The post-merge-sentinel guard in `larch-log.sh` already prevents any commit after merge. Update `scripts/test-larch-logs-batches.sh` for the new slug.

## Files to modify / create

- `scripts/ci-decide.sh` — replace lines 124-128 BAIL_REASON value with `fix-attempts-exhausted` (preserve adjacent comment with the human-readable explanation).
- `scripts/ci-decide.md` — update sibling. Document `fix-attempts-exhausted` as one of the exact-match terminal BAIL_REASON tokens, with a pointer to `ship-pr.sh:needs_user_bail_reason` and `/implement` Step 16 (SKILL.md:1595). Cross-reference the `scripts/ci-wait.md` forwarding contract.
- `scripts/ci-wait.md` — best-effort one-line addition noting that `fix-attempts-exhausted` is forwarded through this script and is terminal-user-input. (Skip if the existing `.md` already lists BAIL_REASON values categorically.)
- `scripts/ship-pr.sh` — **no change to the script itself**; the existing `needs_user_bail_reason` matcher already accepts `fix-attempts-exhausted` exactly.
- `scripts/ship-pr.md` — note that `FIX_ATTEMPTS >= 10` now triggers exit 3 via the magic token (was unreachable before).
- `scripts/larch-log-batches.sh` — add `final-bail-reason .txt replace none` row to LARCH_LOG_BATCHES (insert near `execution-issues`).
- `scripts/larch-log-batches.md` — enumerate the new batch slug in the prose list.
- `scripts/restore-finalize-state.sh` — at the end of `write_finalize_state()` (after line 71's `printf '%s' "$(read_state BAIL_REASON)" > "$BAIL_REASON_FILE"`), add a `larch-log.sh write --batch final-bail-reason --input-file "$BAIL_REASON_FILE"` call guarded by `[ -s "$BAIL_REASON_FILE" ]`, using `2>/dev/null || true` (silent failure). `RUN_ID` and the log-root path resolve from `ship-pr-state.sh` via `read_state RUN_ID` and from `$IMPLEMENT_TMPDIR` respectively.
- `scripts/restore-finalize-state.md` — update sibling to document the new batch publish.
- `scripts/test-restore-finalize-state.sh` — extend to assert that after `write_finalize_state` runs with a non-empty `BAIL_REASON`, the `final-bail-reason` batch is published (file appears under the mocked `$IMPLEMENT_TMPDIR/larch-logs/implement/$RUN_ID/`). When `BAIL_REASON` is empty (postmerge happy path), assert the batch is NOT published.
- `scripts/test-ship-pr.sh` — append a new test block (after the `ci_fix_escalation` block ending at line 2184) that stubs the three CI launchers (emitting `LAUNCHER_EXIT=1\n` on stdout AND `exit 0` from the wrapper, matching production protocol) and asserts the vendor-loop-exhaustion → exit-4 path. Use the existing `make_repo` + `run_subject` + `assert_rc` helpers; follow the same stub-script layout as the `ci_fix_escalation` block.
- `scripts/test-larch-logs-batches.sh` — extend assertions to verify `final-bail-reason` is in the canonical batch list (look up extension/mode/sanitizer via `larch_log_batch_info`).
- `skills/shared/ci-fix-failure-patterns.md` — new file: list larch-specific repair patterns (topology.tsv format + regen + value-must-be-in-runtime-authority).
- `scripts/launch-cursor-ci.sh` — load `${PLUGIN_ROOT}/skills/shared/ci-fix-failure-patterns.md` into `LARCH_PATTERNS` (empty fallback when the file is missing) and append to the `fix` role PROMPT only (between `FAILURE_CONTEXT` and `LOCAL_REPRO`). For non-fix roles, `LARCH_PATTERNS` remains an empty string and the splice is a no-op.
- `scripts/launch-cursor-ci.md` — update sibling.
- `scripts/launch-codex-ci.sh` — same change; same canonical path; same fix-only constraint.
- `scripts/launch-codex-ci.md` — update sibling.
- `scripts/launch-claude-ci.sh` — same change; same canonical path; same fix-only constraint.
- `scripts/launch-claude-ci.md` — update sibling.
- `scripts/test-launch-cursor-ci.sh`, `scripts/test-launch-codex-ci.sh`, `scripts/test-launch-claude-ci.sh` — add an assertion that, when `ROLE=fix` and the fragment file exists, the rendered `$PROMPT_FILE` contains **exactly the literal substring `topology.tsv`** (single canonical sentinel across all three test files for parity). Also assert that for `ROLE=resolve-conflict` / `bump-classify` / `changelog-draft`, the rendered prompt does NOT contain `topology.tsv` (negative fix-only assertion).

## Edge cases

- **Fragment file missing**: each launcher's load step falls back to an empty `LARCH_PATTERNS` block (no error). Behavior matches today's prompt minus the fragment. Mitigation: launcher tests assert the substring is present when ROLE=fix and the file exists.
- **`final-bail-reason.txt` lifecycle**: the file is written either (a) by `ship-pr.sh:write_finalize_state` on the **postmerge happy path** (line 640) with `BAIL_REASON=''` (so the file is empty — `clear_stall_keys_for_postmerge` at line 589 clears the state value before postmerge), or (b) by `restore-finalize-state.sh:write_finalize_state` at `/implement` Step 18 (line 71) with the actual bail/stall `BAIL_REASON` value from `ship-pr-state.sh`. The new larch-log batch publish in `restore-finalize-state.sh` is guarded by `[ -s "$BAIL_REASON_FILE" ]` so the empty postmerge file is a no-op; bail/stall paths produce non-empty files that DO get published.
- **`larch-log.sh` post-merge-sentinel guard**: `larch-log.sh commit` is mechanically blocked when the post-merge sentinel exists (`scripts/larch-log.sh` unconditional). The `write` operation here precedes any commit step; the existing guard remains the safety net.
- **`RUN_ID` missing in ship-pr-state.sh**: `restore-finalize-state.sh` already gracefully handles missing keys via `read_state` defaults. If `RUN_ID` is empty, skip the `larch-log.sh write` call (additional `[ -n "$RUN_ID" ]` guard) — `larch-log.sh` rejects empty `--run-id` anyway.
- **Pre-existing free-form BAIL_REASON consumers**: nothing parses BAIL_REASON for substring; the only matcher is `needs_user_bail_reason`'s exact-match `case`. Changing the cap's emitted token from prose to `fix-attempts-exhausted` does not break downstream consumers.
- **STALL_STEP `10-max-retries` is reused by `run_rebase_rebump`** at ship-pr.sh:1994 (rebase storm cap) — same token, different cap. No code change needed; operators reading bail logs distinguish via `FAILED_RUN_ID` (vendor-loop) vs `REBASE_COUNT` (rebase storm).
- **Bash 3.2 portability**: no new `declare -A` / `mapfile` / parameter-case-conversion constructs introduced.
- **Foreground markers (BASH_AUTHORING.md §4)**: no new fenced bash blocks added to SKILL.md or orchestrator-facing markdown — all changes are runtime script code or `.md` siblings.

## Failure modes (3 most likely)

1. **Prompt fragment drift across launchers**: a future PR edits one launcher's PROMPT and forgets the other two. Earliest signal: `test-launch-*-ci.sh` sentinel-substring assertion (`topology.tsv`) fails on the diverged launcher. Mitigation: the launcher-parity rule (`.claude/rules/external-tool-launcher-parity.md`) already requires symmetric edits; the new identical-substring sentinel test enforces it mechanically.

2. **Wrong exit code observed in a different environment**: a follow-up `ship-pr` run hits `FIX_ATTEMPTS=10` and now exits 3 instead of the historical exit 4. Earliest signal: `/implement` Step 16 routes via Step 12d user-input bail instead of the stall path. Mitigation: this IS the intent per Round 1 Decision 4; `/implement` Step 16's exit-3 handling has been documented at SKILL.md:1595 since before this fix. Operators who relied on exit 4 at the cap should now expect exit 3 with `BAIL_REASON=fix-attempts-exhausted` — surfaced in commit message and run-log `final-bail-reason.txt`.

3. **`final-bail-reason` larch-log batch write silently fails inside `restore-finalize-state.sh`**: a write failure is silent (`2>/dev/null || true`), matching the adjacent `token-report` / `timing-report` pattern. The BAIL_REASON content survives in `ship-pr-state.sh:BAIL_REASON` and in `$IMPLEMENT_TMPDIR/final-bail-reason.txt` (until cleanup) regardless of the batch publish outcome. No `execution-issues.md` Warnings row is added. This matches the established silent-failure pattern; consumers who need the bail reason post-cleanup must read the committed run-log `final-bail-reason.txt`.

## Testing strategy

- Run `make lint` (covers pre-commit hooks across the repo).
- Run `scripts/test-ship-pr.sh` — the existing exit-3 stub test (line 1042-1047) MUST still pass; the new vendor-loop-exhaustion test added at the bottom MUST pass.
- Run `scripts/test-larch-logs-batches.sh` — the new `final-bail-reason` batch row MUST be in the canonical table.
- Run `scripts/test-restore-finalize-state.sh` — the new `final-bail-reason` publish assertions MUST pass.
- Run `scripts/test-launch-cursor-ci.sh`, `scripts/test-launch-codex-ci.sh`, `scripts/test-launch-claude-ci.sh` — the new sentinel-substring assertion (`topology.tsv`) MUST find the literal in each launcher's rendered prompt when `ROLE=fix`; the negative non-fix assertion MUST pass.
- Optionally run `make lint-foreground-markers` / `make lint-bash32` to confirm no portability/foreground markers regress.


## Acceptance


1. `scripts/ci-decide.sh` emits `BAIL_REASON=fix-attempts-exhausted` (exact token, single line) at the `FIX_ATTEMPTS >= 10` branch.
2. `scripts/larch-log-batches.sh` LARCH_LOG_BATCHES includes the row `final-bail-reason .txt replace none`.
3. `scripts/restore-finalize-state.sh` `write_finalize_state()` calls `larch-log.sh write --batch final-bail-reason --input-file "$BAIL_REASON_FILE"` guarded by `[ -s "$BAIL_REASON_FILE" ]` and `[ -n "$RUN_ID" ]`, using `2>/dev/null || true` (silent failure).
4. `skills/shared/ci-fix-failure-patterns.md` exists and documents the topology.tsv format + regen rule.
5. Each of `scripts/launch-{cursor,codex,claude}-ci.sh` loads the fragment from **`${PLUGIN_ROOT}/skills/shared/ci-fix-failure-patterns.md`** (single canonical path) into the `fix` role PROMPT only; non-fix roles get an empty splice. Each launcher has a sibling `.md` documenting the change.
6. `scripts/test-ship-pr.sh` contains a new block asserting vendor-loop-exhaustion → exit 4, with stubs emitting `LAUNCHER_EXIT=1` on stdout and exiting 0 from the wrapper (matching production protocol). The existing exit-3 stub test (line 1042-1047) remains present and passing.
7. `scripts/test-launch-{cursor,codex,claude}-ci.sh` each assert: (a) under `ROLE=fix` with the fragment file present, the rendered `$PROMPT_FILE` contains the literal substring `topology.tsv`; (b) under non-fix roles, the rendered prompt does NOT contain `topology.tsv`.
8. `scripts/test-larch-logs-batches.sh` extended to cover `final-bail-reason`.
9. `scripts/test-restore-finalize-state.sh` extended to verify the `final-bail-reason` batch publishes when `BAIL_REASON` is non-empty and is skipped when empty.
10. `scripts/ci-decide.md` documents `fix-attempts-exhausted` as one of the exact-match terminal BAIL_REASON tokens with a pointer to `ship-pr.sh:needs_user_bail_reason` and `/implement` Step 16. `scripts/ci-wait.md` references the same when applicable.
11. All `.md` siblings updated for every `.sh` modified, per `.claude/rules/script-md-siblings.md`.
12. `make lint` passes locally.


diff_lines: 270

## Test plan
(no test plan section in plan-file)
