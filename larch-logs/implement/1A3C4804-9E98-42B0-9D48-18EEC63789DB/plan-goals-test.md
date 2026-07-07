## Goal
Implement issue #6556: [IMPLEMENTING] ship-pr: autonomous CI-fix sub-agent loop (30 rounds) before main-agent bail.

## Implementation Plan
## Plan

## Context

`approach-synthesis.txt` content is `NO_SKETCHES`, so this plan is based on direct repo inspection, the approved outline, and issue acceptance criteria.

The operator's binding Round 1 decision sets a **20-round** fixer cap in one persistent Agent session (this supersedes the issue's "30 rounds" wording; the `larch:plan` block is authoritative), with early-bail classes and main-agent inline repair after fixer exhaustion or bail. Budgets are separate counters:

- **Fixer path (default):** one Agent-tool fixer owns up to **20** rounds per `FAILED_RUN_ID`.
- **Kill switch (`LARCH_CI_FIXER=0`):** restore today's inline main-agent procedure with the existing **30-attempt** counter surface (`main-agent-ci-fix-$FAILED_RUN_ID.attempted` / `main-agent-ci-fix.count`). Do not fold kill-switch behavior into the post-bail fallback path.
- **Post-bail main-agent fallback:** after fixer bail or exhaustion, the main agent reads `fixer-bail.md` first, then runs inline repair capped at **10** attempts stored durably under `$IMPLEMENT_TMPDIR/ci-fixer-$FAILED_RUN_ID/`. After 10 attempts, route `ci-fix-exhausted` operator-bail; never re-spawn the fixer for the same run id.
- **No-respawn invariant:** `fixer-spawned.sentinel` or `fixer-bail.md` for a run id blocks any later fixer spawn for that run id, including after fixer success.

Round 1 scope is binding: 20-round fixer cap, 10-attempt post-bail main-agent cap, remove the old `ci_agentic_fix.py` path; never re-spawn the fixer for the same failed run id after fixer bail; keep `LARCH_CI_FIXER=0` as the kill switch (it restores today's 30-attempt inline behavior for A/B).

## Approach

1. Keep the Python ship driver immediate-bail behavior.
   - `ship route-exit` still emits `NEXT_ACTION=ci-fix`.
   - `skills/implement/SKILL.md` still owns the Step 8 pre-fix rebase gate.
   - After the gate, `ship-pr-ci-fix.md` decides among kill-switch inline repair, the new fixer path, and post-bail inline fallback.

2. Retire the Python-side agentic-fix delegate cleanly.
   - The monitor loop already bails immediately to `first-fixer-non-health` without log download on the non-rebase path.
   - **`evaluate_failure()` must not call deleted code:** when `ci_fix_rebase_pending=false`, return immediate main-agent handoff semantics (mirror monitor `first-fixer-non-health`; no subprocess fixer, no log classification loop).
   - Keep only the `ci_fix_rebase_pending=true` retry path inside `evaluate_failure()`.
   - Delete `_agentic_fix_result`, `_agentic_fix_delegate_timeout_sec`, and dead `agentic-fix` argv construction plus agentic-fix-only baseline/rollback helpers.

3. Add a file-backed CI digest helper with full failing-job coverage.
   - Add `python3 python/cli.py ci distill-log --run-id <id> --repo <owner/repo> --output <path>`.
   - **Do not delegate to `collect_failed_logs` or any tail-only truncation helper.** `collect_failed_logs` tails the last `CI_MONITOR_LOG_TAIL_LINES` lines and is unsuitable for multi-job distillation.
   - **Implementation contract:**
     1. Fetch the full failed-job log stream via `gh.run_log_failed_read` (`gh run view <id> --repo <repo> --log-failed`), not `gh run-logs` tail helpers.
     2. Optionally cross-check job names via `gh.failed_jobs_read` / `parse_failed_jobs_json` so every failed job GitHub exposes is represented in the digest.
     3. Parse the `--log-failed` stream into per-job sections (split on job/step boundaries GitHub emits).
     4. Within each section, extract failing step labels where parseable and nearby error context.
     5. When an individual step log is huge, apply **per-step** head/tail windows (config caps), not a single repo-wide tail chop.
     6. Dedupe repeated shard noise (for example identical matrix-shard failure blocks).
     7. Cap total digest size after per-job assembly.
     8. Redact with `redact secrets` before write.
   - Stdout emits only small KVs such as `STATUS=ok`, `OUTPUT=...`, `FAILED_JOBS_COUNT=...`, and `BAIL_CLASS=...`.
   - The digest starts with an untrusted-data warning.
   - The digest must include evidence from **all** failing jobs when GitHub exposes them, so one fixer round can address every known failure.

4. Rework `ship-pr-ci-fix.md` into three distinct paths.
   - **Kill switch path (`LARCH_CI_FIXER=0`):** skip fixer spawn entirely; run the existing inline main-agent procedure with the **30-attempt** counter surface. Main agent may capture/read CI logs as today. Do not write `fixer-spawned.sentinel`.
   - **Default fixer path:** after preconditions pass, run the pre-spawn distill fence (step 5 below), write `fixer-spawned.sentinel`, spawn exactly one Agent-tool fixer per `FAILED_RUN_ID`, and stay notification-only while the fixer runs.
   - **Post-bail fallback path:** if the fixer wrote `fixer-bail.md` (or returns non-success without a bail artifact, fail closed with a tool-failure note), the main agent reads the bail artifact first, then runs inline fallback with the **10-attempt** durable counter under `$IMPLEMENT_TMPDIR/ci-fixer-$FAILED_RUN_ID/`.
   - **Success path:** main agent reads only `fixer-status.env` and a small success line; do **not** Read `distilled-failure.md` or CI logs; clear stale Step 8 handoff sidecars; relaunch `step-8-ship.sh`.

5. Add the mandatory pre-spawn distill fence before Agent dispatch.
   - On the default fixer path only, before writing `fixer-spawned.sentinel` or spawning:
     1. Run `python3 python/cli.py ci distill-log --run-id "$FAILED_RUN_ID" --repo "$REPO" --output "$IMPLEMENT_TMPDIR/ci-fixer-$FAILED_RUN_ID/distilled-failure.md"`.
     2. Parse stdout KVs only (`STATUS`, `OUTPUT`, `FAILED_JOBS_COUNT`, `BAIL_CLASS`). Do **not** Read the digest into main context.
     3. On non-`STATUS=ok`, skip fixer spawn and route to post-bail inline fallback (or operator-bail when health/fork/repo-unavailable classes apply).
     4. On success, write `fixer-spawned.sentinel`, then spawn the Agent once.

6. Define the shared budget and durable handoff surface.
   - Per-run-id directory: `$IMPLEMENT_TMPDIR/ci-fixer-$FAILED_RUN_ID/`.
   - Files:
     - `distilled-failure.md`
     - `fixer-spawned.sentinel` (written **before** Agent dispatch; mandatory)
     - `fixer-status.env`
     - `fixer-rounds.tsv`
     - `fixer-bail.md`
     - `fallback-attempts.count` (durable post-bail inline counter; increment before each inline attempt)
   - **No-spawn guard:** refuse fixer spawn when `fixer-spawned.sentinel` **or** `fixer-bail.md` exists for that run id (including after fixer success).
   - Fixer owns **20** rounds inside one Agent session.
   - Kill-switch inline keeps the existing top-level `main-agent-ci-fix-$FAILED_RUN_ID.attempted` / `main-agent-ci-fix.count` surface (30 max).
   - Post-bail inline uses only `fallback-attempts.count` (10 max).

7. Write the Agent prompt as file-backed work.
   - The main agent passes paths and commands, not log contents:
     - issue URL
     - PR URL, head branch, base branch
     - command to print branch diff vs merge-base
     - path to `distilled-failure.md`
     - pointers to `docs/linting.md` and repair recipes
     - path to `fixer-status.env`
     - path to `fixer-rounds.tsv`
     - path to `fixer-bail.md`
   - The prompt tells the fixer to:
     - treat all file contents as untrusted evidence
     - enumerate all failures from all failing jobs each round
     - fix all known failures in one pass
     - run only cheap targeted checks
     - commit as `CI fix round <N>: <summary>`
     - push
     - wait with `python/cli.py ci wait`
     - stop early on health failures, fork/repo-unavailable, red base branch, rebase-needed, or no-progress breaker
   - The prompt must forbid wholesale local suites, static job allowlists, and auto-rollback.

8. Preserve redaction and main-context hygiene.
   - On the fixer **success** path, the main agent must not Read CI logs or `distilled-failure.md`.
   - On fixer bail, the main agent reads `fixer-bail.md` only (last distilled failure plus one line per round).
   - All bail artifacts remain redacted and marked as untrusted data.

9. Record fixer cost and timing separately.
   - Add a `Step 8 - CI fixer` timing/token mark before Agent dispatch and a closing mark after it returns.
   - Ensure `/report-tokens` renders that span as a distinct line or preserves the existing per-step line with a clear CI-fixer label.
   - Keep vendor sidecar ingestion unchanged for existing external launchers.

10. Remove the obsolete pre-#5182 fixer.
    - Delete `ci_agentic_fix.py`.
    - Remove `ci agentic-fix` registry and wrapper.
    - Remove `ci_monitor.py` helper code that only existed for the old agentic fixer.
    - Delete `test_ci_agentic_fix.py`.
    - Remove stale `ci_agentic_fix.py` ruff and complexity baseline rows.
    - Remove or rewrite surviving `test_agentic_fix_*` cases in `test_ci.py` in the same change set.

## Files to modify/create

### UPDATED: skills/implement/SKILL.md

Update only Step 8 ci-fix prose, not the Step 8 launcher fence unless unavoidable.

Required changes:
- State that `NEXT_ACTION=ci-fix` loads `ship-pr-ci-fix.md`, which by default runs `ci distill-log`, writes `fixer-spawned.sentinel`, and spawns one Agent-tool fixer.
- State that `LARCH_CI_FIXER=0` restores the existing **30-attempt** inline main-agent repair path (separate from post-bail fallback).
- State that on fixer success the main agent clears stale handoff sidecars and relaunches `step-8-ship.sh` without reading CI logs.
- State that on fixer bail the main agent reads `fixer-bail.md` and continues the **10-attempt** post-bail inline fallback.
- Preserve the pre-fix rebase proof guard.

### UPDATED: skills/implement/references/ship-pr-ci-fix.md

Rewrite the reference around the new three-path contract.

Required sections:
- Preconditions: `NEXT_ACTION=ci-fix`, fork and repo-unavailable ruled out, pre-fix rebase passed, non-empty `FAILED_RUN_ID` where applicable.
- Architectural-invariants branch preserved before CI-run-id path (existing step 0 behavior).
- **Kill switch:** `LARCH_CI_FIXER=0` → existing inline main-agent procedure with **30-attempt** counter; no fixer spawn; no `fixer-spawned.sentinel`.
- **Pre-spawn distill fence:** `ci distill-log` → parse KVs only → write `fixer-spawned.sentinel` → spawn once.
- **Fixer spawn:** one Agent-tool call per run id; main agent idle during fixer task.
- **Fixer inputs:** file-backed paths and commands only.
- **Fixer loop:** **20** rounds, one commit per round, push, `ci wait`, targeted checks only.
- **Early bail classes:** health, fork/repo unavailable, base branch red, rebase needed, no-progress.
- **Success handoff:** `fixer-status.env` and small status line only; explicit **do not Read** `distilled-failure.md` or `gh run-logs` on success path.
- **Bail handoff:** `fixer-bail.md`, then **10-attempt** durable post-bail main-agent fallback via `fallback-attempts.count`.
- **Post-bail exhaustion:** after 10 inline attempts, route `ci-fix-exhausted` operator-bail; do not re-spawn fixer.
- **Durable guards:** `fixer-spawned.sentinel` OR `fixer-bail.md` blocks respawn for same run id.
- Untrusted data handling and redaction rules.
- Preserve guideline-refresh prohibition (`Do not rerun architectural-guidelines Phase A...`) for inline fallback commits.

### UPDATED: skills/implement/references/ship-pr-exit-matrix.md

Document the new internal ci-fix outcomes.

Add or update:
- `ci-fixer-success`
- `ci-fixer-health-bail`
- `ci-fixer-exhausted`
- `ci-fixer-no-progress`
- `ci-fixer-rebase-needed`
- `ci-fixer-disabled`

Clarify that these are Step 8 ci-fix handoff statuses, not new Python ship driver `NEXT_ACTION` tokens unless implementation makes them machine tokens.

### UPDATED: python/larch/core/config.py

Add single-source constants:
- `ENV_LARCH_CI_FIXER`
- `CI_FIXER_AGENT_MAX_ROUNDS = 20`
- `CI_FIXER_MAIN_FALLBACK_MAX_ATTEMPTS = 10`
- `CI_FIXER_KILL_SWITCH_INLINE_MAX_ATTEMPTS = 30` (or document reuse of existing main-agent counter constant)
- digest size/window caps (`CI_FIXER_DISTILL_*` head/tail per-step and total-byte caps)
- fixer status token literals
- bail artifact filenames if shared across modules

Remove `CI_AGENTIC_FIX_MAX_CYCLES` when no remaining code uses it.

### UPDATED: python/larch/cli.py

Add registry entry:
- `("ci", "distill-log")`

Remove registry entry:
- `("ci", "agentic-fix")`

### UPDATED: python/larch/implement/ci.py

Add `distill_log_main(argv)`.

Implement:
- argv validation for `--run-id`, `--repo`, and `--output`
- output containment check under `IMPLEMENT_TMPDIR`
- fetch full failed-job logs via `gh.run_log_failed_read` (`gh run view --log-failed`); **forbid** calling `ci_monitor.collect_failed_logs` or other tail-only helpers
- parse the `--log-failed` stream into per-job sections; optional `gh.failed_jobs_read` / `parse_failed_jobs_json` cross-check for `FAILED_JOBS_COUNT`
- within each job section, locate failing steps and error context; apply per-step head/tail windows when a step exceeds config caps; dedupe repeated shard noise; cap total digest size
- redact before write
- emit stable KVs (`STATUS`, `OUTPUT`, `FAILED_JOBS_COUNT`, `BAIL_CLASS`)
- return distinct exit codes for usage, GitHub/log health failure, and write failure

Remove:
- `ci_agentic_fix` import
- `agentic_fix_main`

### UPDATED: python/larch/implement/ci_monitor.py

Replace `evaluate_failure()` non-pending branch (`ci_fix_rebase_pending=false`) with immediate main-agent handoff semantics: return a fix result that routes to main-agent CI-fix without calling any subprocess fixer (mirror monitor `first-fixer-non-health` behavior; no log download or agentic delegate).

Keep the `ci_fix_rebase_pending=true` retry loop intact.

Remove old agentic-fix-only helpers and call paths:
- `_capture_baseline`
- `_rollback_to_baseline`
- `_delta_paths`
- `_agentic_output_dir`
- `_read_push_checkpoint_from_ctx`
- `_agentic_fix_delegate_timeout_sec`
- `_agentic_fix_result`
- dead `agentic-fix` argv construction

Leave `collect_failed_logs` unchanged for the CI monitor poll loop; distill-log is a separate code path.

### REWRITTEN: python/larch/implement/ci_agentic_fix.py

Delete this file. It is the superseded pre-#5182 fixer.

### REWRITTEN: python/tests/implement/test_ci_agentic_fix.py

Delete this test file with the removed fixer.

### UPDATED: python/tests/implement/test_ci.py

Add tests for `ci distill-log`:
- usage errors
- output must be under `IMPLEMENT_TMPDIR`
- successful digest writes redacted content
- digest is capped at total size
- **does not call `collect_failed_logs`** (monkeypatch/assert the helper is never invoked)
- multi-job `--log-failed` fixtures include every failing job section, not only the last tail window
- per-step head/tail caps preserve error context from the start and end of huge steps
- shard dedupe collapses repeated matrix noise without dropping distinct failures
- in-progress and GitHub health failures emit distinct statuses

Remove in the same change set:
- `test_agentic_fix_usage_exits_nonzero`
- `test_agentic_fix_rejects_relative_repo_root`
- `test_agentic_fix_accepts_optional_flags`
- any other `test_agentic_fix_*` cases tied to the deleted registry entry

### UPDATED: python/tests/implement/test_ci_monitor.py

Remove assertions and tests for the old agentic fixer dispatch (`test_agentic_fix_*`, `_agentic_fix_result` success paths, delegate timeout helpers).

Explicitly delete in the same change set:
- `test_agentic_fix_delegate_timeout_includes_verify_budget` (monkeypatches `CI_AGENTIC_FIX_MAX_CYCLES` and asserts `_agentic_fix_delegate_timeout_sec`)
- any remaining tests that monkeypatch or assert `CI_AGENTIC_FIX_MAX_CYCLES`

Add coverage that:
- `evaluate_failure()` with `ci_fix_rebase_pending=false` returns immediate main-agent handoff without invoking agentic fix
- remaining `ci_fix_rebase_pending=true` retry behavior stays intact
- monitor immediate-bail `first-fixer-non-health` path unchanged

### UPDATED: python/tests/core/test_config.py

Replace the `CI_AGENTIC_FIX_MAX_CYCLES == 30` assertion with assertions on the new `CI_FIXER_*` constants (for example `CI_FIXER_AGENT_MAX_ROUNDS`, `CI_FIXER_MAIN_FALLBACK_MAX_ATTEMPTS`, `CI_FIXER_KILL_SWITCH_INLINE_MAX_ATTEMPTS`).

### UPDATED: python/tests/report/test_tokens.py

Add or adjust tests so the `Step 8 - CI fixer` mark is surfaced as a distinct token/timing slice.

### MAY_UPDATE: python/tests/report/test_progress_report.py

Update only if the progress or final report renderer needs a label mapping for the new CI-fixer span.

### UPDATED: python/complexity-baseline.json

Remove rows for deleted `larch/implement/ci_agentic_fix.py`.

Regenerate or manually shrink only the affected rows.

### UPDATED: python/ruff.toml

Remove the per-file complexity ignore entry for `ci_agentic_fix.py`.

Keep unrelated ignores unchanged.

### MAY_UPDATE: python/skill-closure-baseline.json

Update only if prompt edits intentionally grow the implement closure and `skill-closure-growth` requires a new baseline.

### UPDATED: skills/implement/scripts/test-architectural-guidelines-step.sh

Preserve the pinned guideline-refresh assertion (`Do not rerun architectural-guidelines Phase A...`) if step numbering moves in the rewrite.

### UPDATED: scripts/test-implement-structure.sh

Retarget `ship-pr-ci-fix.md` needles for the rewritten reference. Explicit updates:

- **Add/require:** `LARCH_CI_FIXER=0`, `ci distill-log`, `fixer-spawned.sentinel`, `fixer-bail.md`, `fixer-status.env`, `fallback-attempts.count`, `20` fixer rounds, `10` post-bail fallback attempts, explicit success-path prohibition on main-agent log reads.
- **Remove/forbid on default fixer path:** main-agent `gh run-logs` capture as the first repair action when fixer is enabled; forbid `collect_failed_logs` delegation for distill-log.
- **Preserve where still valid:** `first-fixer-non-health`, `ci-fix-exhausted`, pre-fix rebase ordering, stale-handoff clear before `step-8-ship.sh` re-invoke, architectural-invariants branch, empty-`FAILED_RUN_ID` fallback.
- **Relax/replace:** rigid `  1.`–`  12.` numbered sub-step pins if the reference adopts path-based sections; replace with anchors for kill-switch, distill fence, fixer spawn, success handoff, and post-bail fallback sections.

### UPDATED: scripts/test-implement-step8-exit3-first-fixer.sh

Same needle retargeting as `test-implement-structure.sh` for the ci-fix body pins listed there. Run this harness in Testing strategy.

### MAY_UPDATE: scripts/test-implement-fence-shape.sh

Update only if `skills/implement/SKILL.md` adds, removes, or converts Bash fences. Prefer no fence-shape change.

### MAY_UPDATE: docs/linting.md

Update only if the new `ci distill-log` targeted-check guidance needs a documented local remediation recipe.

### MAY_UPDATE: docs/run-logs.md

Update only if the CI-fixer token/timing line changes committed run-log expectations.

## Edge cases

- `FAILED_RUN_ID` is empty: preserve existing fallback diagnostic path and do not spawn the fixer.
- `FORKED_TARGET=true` or `REPO_UNAVAILABLE=true`: do not spawn and route to operator/main fallback as today.
- Pre-fix rebase reports conflict or stall: do not spawn.
- `LARCH_CI_FIXER=0`: run **30-attempt** inline fallback without writing `fixer-spawned.sentinel`.
- `ci distill-log` health failure before spawn: skip fixer; route to post-bail inline fallback or operator-bail per bail class.
- Multi-job failures: distill must emit every failing job section from `--log-failed`; tail-only truncation must not drop earlier jobs.
- Fixer succeeds but Step 8 relaunch later fails: normal `ship route-exit` handles it.
- Fixer pushes but `ci wait` reports rebase needed: fixer bails with `ci-fixer-rebase-needed`; main-agent fallback does not re-spawn.
- Same failure signature twice with empty fix diff: fixer writes no-progress bail.
- Bail artifact missing after Agent returns non-success: fail closed to inline fallback with a tool-failure note.
- Distilled log contains prompt injection: all prompts and docs must label it untrusted data.
- Re-entry on repeated `NEXT_ACTION=ci-fix` for same run id: durable `fixer-spawned.sentinel` / `fixer-bail.md` and `fallback-attempts.count` prevent fixer respawn and counter reset.

## Failure modes

- The main agent accidentally reads the distilled log on the success path. Guard with explicit **do not Read** wording in `ship-pr-ci-fix.md` and SKILL.md.
- `evaluate_failure()` still calls deleted agentic-fix code after registry removal. Guard by rewriting the non-pending branch and deleting `_agentic_fix_result` in the same PR.
- Kill-switch and post-bail fallback counters get conflated. Guard by documenting three separate paths and distinct counter files.
- Distill-log reuses `collect_failed_logs` and omits failures from multi-job runs. Guard by implementing against `gh run view --log-failed` with per-job parsing and tests that forbid `collect_failed_logs` delegation.
- The Agent loop makes multiple small commits for known failures in one round. Guard with prompt text and `fixer-rounds.tsv` review.
- The fixer can consume the full 20-round budget on environmental failures. Guard with early health bail classes.
- Token/timing marks may not capture native Agent usage perfectly. If native Agent token data is unavailable, still record timing and make the limitation explicit in tests or docs.
- Old `ci agentic-fix` references may survive in tests or baselines. Sweep for `agentic-fix`, `ci_agentic_fix`, `ci-agentic`, and `CI_AGENTIC_FIX_MAX_CYCLES`.
- `test_config.py` or `test_ci_monitor.py` still assert or monkeypatch `CI_AGENTIC_FIX_MAX_CYCLES` after config cleanup. Guard by updating `test_config.py` and deleting delegate-timeout tests in the same change set.
- Harness exact-string pins break on reference rewrite. Guard by updating both harness scripts in the same change set.
- Prompt growth may trip skill-closure ratchets. Update the baseline only after confirming the growth is required.

## Testing strategy

Run targeted tests and harnesses:

- `python3 -m pytest python/tests/implement/test_ci.py python/tests/implement/test_ci_monitor.py`
- `python3 -m pytest python/tests/core/test_config.py`
- `python3 -m pytest python/tests/report/test_tokens.py python/tests/report/test_progress_report.py`
- `python3 -m pytest python/tests/agents/test_agents.py`
- `bash skills/implement/scripts/test-step-8-ship.sh`
- `bash skills/implement/scripts/test-architectural-guidelines-step.sh`
- `bash scripts/test-implement-structure.sh`
- `bash scripts/test-implement-step8-exit3-first-fixer.sh`
- `bash scripts/test-implement-fence-shape.sh` if any `skills/implement/SKILL.md` Bash fence changes
- `python3 python/cli.py lint complexity-baseline`
- `python3 python/cli.py lint skill-closure-growth --skill implement` if prompt closure changes
- `python3 python/cli.py ci distill-log --help`

Also run a grep sweep before finalizing:
- `rg "agentic-fix|ci_agentic_fix|ci-agentic|CI_AGENTIC_FIX_MAX_CYCLES" python skills docs scripts`

## Rollout notes

- Default is new fixer path with **20** rounds.
- `LARCH_CI_FIXER=0` is the A/B and emergency rollback switch restoring **30-attempt** inline repair.
- Post-bail inline fallback remains bounded at **10** attempts and never re-spawns the fixer.
- Do not remove existing external CI launcher token tests unless no remaining code uses those launchers.

## Acceptance

Run targeted tests and harnesses:

- `python3 -m pytest python/tests/implement/test_ci.py python/tests/implement/test_ci_monitor.py`
- `python3 -m pytest python/tests/core/test_config.py`
- `python3 -m pytest python/tests/report/test_tokens.py python/tests/report/test_progress_report.py`
- `python3 -m pytest python/tests/agents/test_agents.py`
- `bash skills/implement/scripts/test-step-8-ship.sh`
- `bash skills/implement/scripts/test-architectural-guidelines-step.sh`
- `bash scripts/test-implement-structure.sh`
- `bash scripts/test-implement-step8-exit3-first-fixer.sh`
- `bash scripts/test-implement-fence-shape.sh` if any `skills/implement/SKILL.md` Bash fence changes
- `python3 python/cli.py lint complexity-baseline`
- `python3 python/cli.py lint skill-closure-growth --skill implement` if prompt closure changes
- `python3 python/cli.py ci distill-log --help`

Also run a grep sweep before finalizing:
- `rg "agentic-fix|ci_agentic_fix|ci-agentic|CI_AGENTIC_FIX_MAX_CYCLES" python skills docs scripts`

diff_added: 1200
diff_deleted: 1480
mechanical_churn: true
diff_lines: 2680

## Test plan
(no test plan section in plan-file)
