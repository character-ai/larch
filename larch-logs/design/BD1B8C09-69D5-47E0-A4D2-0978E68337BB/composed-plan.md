## Plan

## Approach

- Add a shared Python `commit-route` verb in `python/implement_dispatch.py` that owns the repeated commit-phase gate: run `review-and-fix commit-fixes --stage-all`, parse line-anchored `COMMIT_OUTCOME=`, allow only `ok` and `noop`, seed durable stall state on failure, and emit exactly one `NEXT_ACTION=continue|stall`.
- Mirror the `step8_oos_checkpoint_main` exit contract: **process rc `0` whenever `NEXT_ACTION` is emitted** (`continue` or `stall`); reserve non-zero for usage errors, missing tmpdir, or stall-seed failure with **no** `NEXT_ACTION`.
- Use frozen per-site metadata for the only intentional differences:
  - `step5-self-review`: `STALL_STEP=5`, `BAIL_REASON=review-fix-commit-failed`; no porcelain probe.
  - `step5-resume-handoff`: `STALL_STEP=5`, `BAIL_REASON=resume-handoff-commit-failed`; **porcelain probe after commit success** (same hardened contract as today's `step-5-resume.sh`).
  - `step7`: `STALL_STEP=7`, `BAIL_REASON=review-fix-commit-failed`; no porcelain probe.
- Extend shared KV relay to include `NEXT_ACTION` alongside commit KVs (`COMMITTED`, `ERROR`, `SHA`, `COMMIT_OUTCOME`) so orchestrator-visible stdout from both the shell wrapper and Python parity paths carries the routing token commit-route emitted.
- Wire the **live** resume-handoff hot path: `/implement` calls `step-5-resume.sh --ready-to-commit`, not `python/cli.py implement step-5-resume`. The shell wrapper must delegate its commit phase to `commit-route`, relay `NEXT_ACTION=` to orchestrator-visible stdout on both stall and continue branches, then call `review-and-fix step5` only on continue; `step5_resume_main` must call the same shared helper for Python parity.
- **Python parity stall contract:** `_step5_resume_commit_phase` (and `step5_resume_main`) must treat `NEXT_ACTION=stall` as a **terminal commit-phase failure** even when commit-route returns process rc `0`. Relay commit KVs and `NEXT_ACTION=stall`, return non-zero (e.g. `1`) **without** calling `review-and-fix step5`. Do not map `commit_rc==0` alone to success when `NEXT_ACTION=stall` is present.
- Collapse orchestrator prose at self-review, resume-handoff, and Step 7 to `NEXT_ACTION` branching. Preserve the existing Step 5 review-loop status table: when stdout contains `STEP5_REVIEW_STATUS=`, route by that envelope only; `NEXT_ACTION` gates only the commit handoff failure path.
- In the lacks-envelope resume-handoff branch, treat `STEP5_REVIEW_STATUS=` as the **only** Step 6 authorization. `NEXT_ACTION=continue` without `STEP5_REVIEW_STATUS=` is **not** Step 6 continuation; route to the existing Step 5 preflight/resume failure path (skip to Step 18).
- **Self-review and Step 7 foreground fences** must fail closed on invalid commit-route envelopes: require exactly one line-anchored `NEXT_ACTION=`; continue only on `NEXT_ACTION=continue`; skip to Step 18 on `NEXT_ACTION=stall`; on missing, duplicated, malformed, or non-zero-without-`NEXT_ACTION` output, treat as an **invalid commit-route envelope**, log to `Warnings`, set prompt-side `STALL_TRACKING=true` with the site-appropriate `STALL_STEP` when durable seed is absent, and **skip to Step 18** (do not proceed to the next step, Step 6, Step 7a, or Step 8).

## Files to modify/create

### UPDATED: python/implement_dispatch.py

- Add a frozen `CommitRouteSite` dataclass (or constant map) keyed by `--site` with:
  - `stall_step: str`
  - `bail_reason: str`
  - `failure_log_label: str` (e.g. `Step 5 — self-review commit failed`)
  - `porcelain_probe: bool` (true only for `step5-resume-handoff`)
- Add shared helpers:
  - `_parse_line_anchored_commit_kv(stdout, key)` (reuse or fold existing `_step5_resume_first_commit_kv` pattern)
  - `_relay_commit_kvs(stdout)` for `COMMITTED`, `ERROR`, `SHA`, `COMMIT_OUTCOME`, and **`NEXT_ACTION`** (extend `_STEP5_RESUME_COMMIT_RELAY_KEYS` or equivalent allowlist)
  - `_seed_durable_stall_state(implement_tmpdir, *, stall_step, bail_reason)`:
    - if `ship-pr-state.sh` already has shell KVs, patch allowed keys only: `STALL_TRACKING=true`, `STALL_STEP`, `BAIL_REASON`;
    - if absent or empty, call the existing initial-state seeder path (`ship seed-initial-state` via `step8_seed_initial_main` argv assembly) with `--stall-tracking true`, `--stall-step`, `--bail-reason`;
    - fail closed on seed/patch failure.
  - `_commit_route_porcelain_gate()` for resume-handoff only: probe `git status --porcelain`; on probe failure or dirty tree, treat as commit-phase failure with `resume-handoff-commit-failed` durable seeding (not merely relay `COMMIT_OUTCOME=failed` without stall state).
  - `_commit_route_log_failure(implement_tmpdir, *, site, exit_code, output_file)` wrapping `run-log append-failure` with **`--redact`** (mirror `_step8_oos_checkpoint_log_failure` pattern) so raw `git commit` / hook output never lands unredacted in committed execution issues.
- Add `commit_route_main(argv)` with:
  - required `--site` (`step5-self-review`, `step5-resume-handoff`, `step7`);
  - optional `--implement-tmpdir`, defaulting to `$IMPLEMENT_TMPDIR`;
  - run `review-and-fix commit-fixes --stage-all` via `_invoke_cli`;
  - parse line-anchored `COMMIT_OUTCOME` only (never from `ERROR=` text).
- On `COMMIT_OUTCOME in {"ok", "noop"}`:
  - when site `porcelain_probe=true`, run porcelain gate; on porcelain failure:
    - write bounded diagnostic under `$IMPLEMENT_TMPDIR` (e.g. `commit-route-<site>.failure.log`);
    - call `_commit_route_log_failure` (best-effort `--redact` append);
    - seed durable stall state;
    - on successful seed: relay commit KVs **and `NEXT_ACTION=stall`** when present, emit `NEXT_ACTION=stall`, return `0`;
    - on seed failure: return non-zero, emit **no** `NEXT_ACTION`;
  - relay `COMMITTED`, `SHA`, `ERROR`, `COMMIT_OUTCOME`, **`NEXT_ACTION`**;
  - emit `NEXT_ACTION=continue`;
  - return `0`.
- On missing, malformed, non-allowlisted, or `failed` `COMMIT_OUTCOME`:
  - write bounded diagnostic under `$IMPLEMENT_TMPDIR` (e.g. `commit-route-<site>.failure.log`);
  - call `_commit_route_log_failure` (best-effort `--redact` append; still attempt stall seed if append fails);
  - seed durable stall state;
  - on successful seed: relay commit KVs **and `NEXT_ACTION=stall`** when present, emit `NEXT_ACTION=stall`, return `0`;
  - on seed failure: return non-zero, emit **no** `NEXT_ACTION`.
- Refactor `_step5_resume_commit_phase` / `step5_resume_main` ready-to-commit path to call the shared commit-route implementation (or an in-process helper shared with `commit_route_main`) so Python parity matches the shell wrapper; ensure `_step5_resume_relay_commit_kvs` forwards **`NEXT_ACTION`**.
- **`_step5_resume_commit_phase` stall fail-closed:** after commit-route returns, parse line-anchored `NEXT_ACTION=` from stdout. When `NEXT_ACTION=stall` (even if commit-route process rc is `0`), relay commit KVs and `NEXT_ACTION=stall`, return non-zero (e.g. `1`) **without** invoking `review-and-fix step5`. When `NEXT_ACTION=continue`, relay KVs and return `None` so `step5_resume_main` may proceed to the review loop. When `NEXT_ACTION` is missing, duplicated, or malformed, return non-zero without starting step5.
- Enroll routing KVs via existing `_emit_kv` helpers.

### UPDATED: python/cli.py

- Register:
  - `("implement", "commit-route"): ("implement_dispatch", "commit_route_main")`
- Add `("implement", "commit-route")` to `_MACHINE_STDOUT_KEYS` beside `("implement", "step-8-oos-checkpoint")` so inherited quiet mode cannot suppress `NEXT_ACTION` / commit KVs.
- Add the command to the allowed command list near other `implement` verbs.

### UPDATED: python/test_implement_dispatch.py

- Add registry coverage for `implement commit-route`.
- Add success tests per site:
  - `ok` relays commit KVs **and `NEXT_ACTION=continue`**, rc `0`;
  - `noop` relays commit KVs **and `NEXT_ACTION=continue`**, rc `0`;
  - no `run-log append-failure` or stall seed on success.
- Add resume-handoff-only porcelain tests:
  - dirty porcelain after `ok`/`noop` → `NEXT_ACTION=stall`, rc `0`, `BAIL_REASON=resume-handoff-commit-failed`, durable state seeded;
  - porcelain probe failure → same stall contract;
  - **both porcelain failure cases assert `_commit_route_log_failure` / `run-log append-failure --redact` was invoked** before `NEXT_ACTION=stall` is emitted.
- Add failure tests per site:
  - missing `COMMIT_OUTCOME`;
  - malformed or non-allowlisted outcome;
  - child non-zero with `COMMIT_OUTCOME=failed`.
- Assert each failure:
  - emits `NEXT_ACTION=stall` only after durable stall state is seeded;
  - rc `0` when `NEXT_ACTION` is emitted;
  - correct `STALL_STEP` and `BAIL_REASON` in `ship-pr-state.sh`;
  - logs via `run-log append-failure` **with `--redact`**.
- Add state-shape tests:
  - absent or empty `ship-pr-state.sh` uses initial seeder path;
  - existing state uses key patching, not full reseeding;
  - seed failure → non-zero rc, no `NEXT_ACTION`.
- Add exit-contract test mirroring `step8_oos_checkpoint`: seeded stall returns rc `0` with `NEXT_ACTION=stall`; seed failure returns non-zero without `NEXT_ACTION`.
- Add relay-shape test: `_relay_commit_kvs` / wrapper relay includes `NEXT_ACTION` in forwarded keys.
- Update `test_step5_resume_*` so ready-to-commit routes through shared commit-route logic:
  - commit failure must not start another review round;
  - **`NEXT_ACTION=stall` with commit-route rc `0` → non-zero `step5_resume_main` / `_step5_resume_commit_phase` rc, no `review-and-fix step5` relaunch, stdout relays `NEXT_ACTION=stall`**.

### UPDATED: python/test_cli.py

- Extend `test_machine_stdout_entrypoints_disable_inherited_quiet` with `(["implement", "commit-route"], "implement_dispatch", "commit_route_main")`.

### UPDATED: skills/implement/scripts/step-5-resume.sh

- Replace the inline `review-and-fix commit-fixes --stage-all` block (lines 108–136) with delegation to commit-route using the **same errexit-safe capture guard** as today's commit-fixes block:
  - `set +e`
  - `commit_output="$(python3 "$CLAUDE_PLUGIN_ROOT/python/cli.py" implement commit-route --site step5-resume-handoff)"`
  - `commit_rc=$?`
  - `set -e`
- Parse `NEXT_ACTION` from **captured** `commit_output` (never from a bare unguarded call that errexit can abort before capture):
  - **relay `NEXT_ACTION=` to orchestrator-visible stdout on both stall and continue paths** before any filtered commit-KV relay or `review-and-fix step5` re-entry (extend `relay_commit_kvs` awk filter or add explicit `NEXT_ACTION` passthrough);
  - on `NEXT_ACTION=stall`: relay commit KVs **and `NEXT_ACTION`** from captured stdout, exit non-zero **only if** the Python verb returned non-zero without `NEXT_ACTION` (envelope invalid); when Python returns rc `0` with `NEXT_ACTION=stall`, exit `1` so the immediate-background fence is visibly failed while orchestrator parses `NEXT_ACTION` from stdout (document this pairing in `step-5-resume.md`);
  - on `NEXT_ACTION=continue`: relay commit KVs **and `NEXT_ACTION`**, then proceed to `review-and-fix step5` unchanged;
  - on missing, duplicated, or malformed `NEXT_ACTION` (including non-zero `commit_rc` without `NEXT_ACTION`): relay captured stdout when present, exit non-zero so orchestrator reaches lacks-envelope branch 3.
- Remove local `commit_outcome` allowlist gate, porcelain probe, and `relay_commit_failure_from_porcelain_gate` helpers once commit-route owns resume porcelain + stall seeding (keep `relay_commit_kvs` only if still needed for stdout relay; extend it to include `NEXT_ACTION`).
- Preserve timing mark, `--record-only`, and review-loop re-entry unchanged.

### UPDATED: skills/implement/scripts/step-5-resume.md

- Document that `--ready-to-commit` delegates commit phase to `python/cli.py implement commit-route --site step5-resume-handoff`.
- Document the **errexit-safe capture block**: `set +e` → capture `commit_output` and `commit_rc` → `set -e` → parse `NEXT_ACTION` from captured stdout; relay on all paths including invalid-envelope / seed-failure cases.
- Update KV grammar: wrapper relays **`NEXT_ACTION`**, `COMMITTED`, `ERROR`, `SHA`, `COMMIT_OUTCOME` from commit-route; porcelain probe lives inside commit-route for this site.
- Document that **`NEXT_ACTION=` must appear on orchestrator-visible stdout** on both stall and continue branches (not only commit KVs).
- Document wrapper exit pairing with orchestrator: rc `0` + `NEXT_ACTION=stall` from Python is relayed; wrapper may exit non-zero to surface handoff failure to the background fence while durable stall state is already seeded.
- Note Python parity: `step5_resume_main` uses the same shared commit-route helper, treats `NEXT_ACTION=stall` as terminal commit-phase failure (non-zero return, no step5 relaunch), and relays `NEXT_ACTION`.

### UPDATED: skills/implement/SKILL.md

- Replace Step 5 self-review commit block with:
  - `bash "$IMPLEMENT_TMPDIR/larch-run.sh" python/cli.py implement commit-route --site step5-self-review`
  - parse stdout for exactly one line-anchored `NEXT_ACTION=`:
    - on `NEXT_ACTION=continue`: proceed to the next self-review step;
    - on `NEXT_ACTION=stall`: skip to Step 18;
    - on missing, duplicated, malformed, or non-zero-without-`NEXT_ACTION` output: treat as an **invalid commit-route envelope**; log to `Warnings`, set prompt-side `STALL_TRACKING=true` and `STALL_STEP=5` when durable seed is absent, **skip to Step 18**; do **not** proceed to the next step or Step 6.
- Replace Step 7 review-fix commit block with:
  - `bash "$IMPLEMENT_TMPDIR/larch-run.sh" python/cli.py implement commit-route --site step7`
  - same invalid-envelope contract as self-review:
    - on `NEXT_ACTION=continue`: proceed to Step 7a;
    - on `NEXT_ACTION=stall`: skip to Step 18 (stall recovery runs before the final report; durable bail already seeded by commit-route);
    - on missing, duplicated, malformed, or non-zero-without-`NEXT_ACTION` output: treat as an **invalid commit-route envelope**; log to `Warnings`, set prompt-side `STALL_TRACKING=true` and `STALL_STEP=7` when durable seed is absent, **skip to Step 18**; do **not** proceed to Step 7a or Step 8.
- Thin Step 5 resume-handoff post-fence prose with explicit lacks-envelope order when stdout lacks `STEP5_REVIEW_STATUS=`:
  1. **`NEXT_ACTION=stall`** → skip to Step 18 (durable stall already seeded by commit-route);
  2. **`NEXT_ACTION=continue` without `STEP5_REVIEW_STATUS=`** → route to the existing Step 5 preflight/resume failure path (log to `Warnings`, set `STALL_TRACKING=true`, `STALL_STEP=5`, skip to Step 18); **`NEXT_ACTION=continue` without `STEP5_REVIEW_STATUS=` is not Step 6 continuation**;
  3. **missing, duplicated, malformed, or non-zero-without-`NEXT_ACTION`** → invalid commit-route envelope; route to the existing Step 5 preflight/resume failure path (log to `Warnings`, set `STALL_TRACKING=true`, `STALL_STEP=5`, skip to Step 18); do **not** proceed to Step 6;
  4. **non-zero wrapper rc with a parsed `NEXT_ACTION=continue`** → envelope/preflight failure per existing preflight branch.
- When stdout **contains** `STEP5_REVIEW_STATUS=`, route by the Step 5 status table only; do not map normal loop stalls to `resume-handoff-commit-failed`.
- State explicitly: **`STEP5_REVIEW_STATUS=` is the only Step 6 authorization**; commit-phase success (`NEXT_ACTION=continue` or `COMMIT_OUTCOME=ok|noop`) alone does not satisfy NEVER #4.
- Remove repeated prompt-side prose that hand-parses `COMMIT_OUTCOME`, logs Tool Failures, sets `STALL_TRACKING` / `STALL_STEP` / `STALL_REASON`, and seeds `ship-pr-state.sh` for self-review, resume-handoff commit failure, and Step 7.

### UPDATED: scripts/test-implement-structure.sh

- **Launcher row** (line ~105): replace `python/cli.py review-and-fix commit-fixes --stage-all` with `python/cli.py implement commit-route --site step5-self-review` in the `for script in [...]` block so `make lint` passes after SKILL self-review fence swap.
- Replace retired `step-5-resume.sh` commit/porcelain needles with pins requiring:
  - `implement commit-route --site step5-resume-handoff`
  - **`NEXT_ACTION` relay / parse contract** (orchestrator-visible stdout includes `NEXT_ACTION=`)
- **Replace line ~369 errexit needle:** migrate from `commit-fixes` capture to a pin requiring the same `set +e` / `commit_output="$(python3 ... implement commit-route --site step5-resume-handoff)"` / `commit_rc=$?` / `set -e` guard around commit-route (forbid bare unguarded commit-route substitution that errexit can abort before stdout capture).
- Replace SKILL `COMMIT_OUTCOME` orchestrator-parse stall pins (self-review, resume lacks-envelope, Step 7) with:
  - `implement commit-route` fences for self-review and Step 7
  - `NEXT_ACTION=stall|continue` routing pins
- Add self-review and Step 7 pins requiring **invalid-envelope fail-closed** prose: exactly one line-anchored `NEXT_ACTION=`; continue only on `NEXT_ACTION=continue`; stall only on `NEXT_ACTION=stall`; missing/duplicated/malformed/non-zero-without-`NEXT_ACTION` must set prompt-side `STALL_TRACKING` / site `STALL_STEP` and **skip to Step 18** (not merely do-not-proceed).
- Add Step 7 pin requiring **`NEXT_ACTION=stall` → skip to Step 18** (replace the dropped `STALL_REASON=review-fix-commit-failed` orchestrator pin at ~line 379); durable bail is owned by commit-route, not prompt-side `STALL_REASON` seeding.
- Replace the lacks-envelope second-branch pin (~line 384) with an explicit **`NEXT_ACTION=continue` without `STEP5_REVIEW_STATUS=` → preflight/resume failure (not Step 6)** needle (adapt from today's `COMMIT_OUTCOME=ok|noop` second-branch pin).
- Add lacks-envelope third-branch pin for **invalid commit-route envelope** (missing/duplicated/malformed/non-zero-without-`NEXT_ACTION`) → preflight/resume failure with `STALL_TRACKING` / `STALL_STEP=5`, skip to Step 18, not Step 6.
- Keep envelope-precedence pins (`STEP5_REVIEW_STATUS` present vs lacks-envelope preflight branch).
- Add `require('python/cli.py', '("implement", "commit-route"),', 'commit-route machine stdout')`.
- Drop obsolete needles that require inline `review-and-fix commit-fixes` in `step-5-resume.sh` and prompt-side durable-bail seeding prose.

### MAY_UPDATE: scripts/test-implement-fence-shape.sh

- Update `EXPECTED_OLD` / `EXPECTED_NEW` only if SKILL edits change Bash fence count or fence shape (e.g. self-review / Step 7 commit blocks remain one-line `larch-run.sh` fences with swapped argv).
- Do not edit if changes only swap command arguments inside existing new-shape fences.

## Edge cases

- `ERROR=` may contain text that looks like `COMMIT_OUTCOME`; parse only line-anchored commit KVs.
- `COMMIT_OUTCOME=noop` is success for the commit phase.
- Porcelain probe runs **only** for `step5-resume-handoff`; self-review and Step 7 must not gain prompt-side or shared porcelain gates.
- Step 5 resume may still return a normal review-loop stall after commit phase succeeds; the Step 5 status table still owns that route.
- A non-zero child rc with `COMMIT_OUTCOME=ok` or `noop` should not be treated as commit failure unless the existing helper already fails closed for that case.
- Resume-handoff porcelain failure must write bounded diagnostic + `_commit_route_log_failure --redact`, seed durable stall state with `BAIL_REASON=resume-handoff-commit-failed`, then emit `NEXT_ACTION=stall` (not only emit `COMMIT_OUTCOME=failed` without logging or seeding).
- Missing `$IMPLEMENT_TMPDIR` is a usage failure (rc `2`, no `NEXT_ACTION`).
- Existing malformed or symlinked `ship-pr-state.sh` should fail closed rather than silently continue.
- Immediate-background `step-5-resume.sh` fence: orchestrator must parse stdout for `NEXT_ACTION` even when wrapper exit code is non-zero, as long as Python emitted `NEXT_ACTION=stall` with rc `0`.
- `NEXT_ACTION=continue` after successful commit-route does **not** authorize Step 6 when `STEP5_REVIEW_STATUS=` is absent (e.g. `review-and-fix step5` preflight failure with no review-loop envelope).
- Self-review and Step 7 foreground fences: zero, multiple, or malformed line-anchored `NEXT_ACTION=` values, or non-zero fence rc without `NEXT_ACTION=`, must fail closed with prompt-side `STALL_TRACKING` / site `STALL_STEP` when durable seed is absent and **skip to Step 18**; valid `NEXT_ACTION=stall` must skip to Step 18 at both sites.
- `_step5_resume_commit_phase`: `NEXT_ACTION=stall` with commit-route rc `0` must return non-zero and must not relaunch `review-and-fix step5` (Python parity with shell wrapper stall exit before step5).
- Under `set -euo pipefail`, `step-5-resume.sh` must not invoke commit-route without `set +e` capture; otherwise seed-failure / usage-error rc aborts the wrapper before stdout relay.

## Failure modes

- If commit routing cannot append Tool Failures (even with `--redact`), still attempt durable stall seeding and report the append failure on stderr.
- If durable stall seeding fails, return non-zero and omit `NEXT_ACTION` so the orchestrator treats the route envelope as invalid.
- If `--site` is unknown, return usage rc `2`.
- If `run-log append-failure` and stall seed both fail, non-zero rc with no `NEXT_ACTION` prevents silent continuation to Step 6/7/18 without durable bail.
- If the shell wrapper relays commit KVs but omits `NEXT_ACTION`, lacks-envelope orchestrator branching cannot fire and may incorrectly fall through toward Step 6.
- If `step-5-resume.sh` omits errexit-safe capture around commit-route, wrapper abort on non-zero rc can prevent stdout relay and block lacks-envelope branch 3, mis-routing to generic preflight failure or stranding the session.
- If `_step5_resume_commit_phase` maps commit-route rc `0` to success without checking `NEXT_ACTION`, a seeded commit-phase stall can incorrectly relaunch `review-and-fix step5`.
- If self-review or Step 7 SKILL prose branches only on `stall`/`continue` without invalid-envelope → Step 18 routing, seed failure or malformed stdout can halt mid-step without stall teardown.
- If resume-handoff porcelain failure omits `_commit_route_log_failure`, Step 18 can run with durable state but no committed Tool Failures entry.
- If Step 7 SKILL prose omits the `NEXT_ACTION=stall` → Step 18 branch, implementers may wire commit-route correctly yet leave Step 7 without the durable-bail skip path that today runs on `COMMIT_OUTCOME` failure.

## Testing strategy

- Run focused tests:
  - `python3 -m pytest python/test_implement_dispatch.py -k 'commit_route or step5_resume'`
  - `python3 -m pytest python/test_cli.py -k 'machine_stdout_entrypoints_disable_inherited_quiet'`
- Run Python checks:
  - `make py-lint`
  - `make py-test`
- Run full lint (includes structure harness):
  - `make lint`
- Confirm `scripts/test-implement-structure.sh` passes with updated commit-route / `NEXT_ACTION` relay pins, launcher row (~105), **errexit-safe commit-route capture pin (~369)**, lacks-envelope second- and third-branch pins, self-review / Step 7 invalid-envelope fail-closed pins (including **skip to Step 18** + prompt-side `STALL_TRACKING` / `STALL_STEP`), and the Step 7 `NEXT_ACTION=stall` → Step 18 pin replacing the retired `STALL_REASON=review-fix-commit-failed` needle.
- Confirm porcelain failure tests assert `run-log append-failure --redact` before `NEXT_ACTION=stall`.
- Confirm `test_step5_resume_*` asserts `NEXT_ACTION=stall` → non-zero rc, no step5 relaunch.
- Confirm `scripts/test-implement-fence-shape.sh` still passes if fence count unchanged.

## Acceptance

The implementation is complete when:
- `python/cli.py implement commit-route --site <SITE>` exists and emits `NEXT_ACTION=continue|stall` with rc `0` on all seeded-stall paths.
- `step-5-resume.sh` delegates `--ready-to-commit` to `commit-route` with errexit-safe capture and relays `NEXT_ACTION=` to orchestrator-visible stdout.
- `step5_resume_main` / `_step5_resume_commit_phase` treat `NEXT_ACTION=stall` (rc `0`) as terminal commit-phase failure.
- `skills/implement/SKILL.md` Step 5 self-review, resume-handoff, and Step 7 collapse inline `COMMIT_OUTCOME` parse-and-stall prose to `NEXT_ACTION` branching.
- `make py-lint`, `make py-test`, and `make lint` all pass clean.
- `scripts/test-implement-structure.sh` passes with updated pins.

review_status: complete
rounds_completed: 5
diff_lines: 750
