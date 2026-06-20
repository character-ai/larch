### External Reviewer Issues

- **Step review Step 2 — cursor-review failed (exit 1 — auth — auth-retries=2, transient-retries=1)**:
  ```
===== sidecar.history =====
===== cursor auth attempt diag =====
Error: Security command failed: Security process exited with code: 45
Failed with exit code 1. Output size: 0 bytes.
===== diag =====
[31m✗ Failed to reach the Cursor API. If you are behind a corporate proxy, set the HTTPS_PROXY environment variable.[0m
Failed with exit code 1. Output size: 0 bytes.
===== launch-stderr =====
❌ cursor agent: FAILED (exit code 1, output 0 bytes)
❌ cursor agent: FAILED (exit code 1, output 0 bytes)

===== additional failure diagnostics =====
===== sidecar.history =====
===== cursor auth attempt diag =====
Error: Security command failed: Security process exited with code: 45
Failed with exit code 1. Output size: 0 bytes.
===== diag =====
[31m✗ Failed to reach the Cursor API. If you are behind a corporate proxy, set the HTTPS_PROXY environment variable.[0m
Failed with exit code 1. Output size: 0 bytes.
===== launch-stderr =====
❌ cursor agent: FAILED (exit code 1, output 0 bytes)
❌ cursor agent: FAILED (exit code 1, output 0 bytes)
  ```

- **Step review Step 2 — cursor-review failed (exit 1 — auth — auth-retries=2, transient-retries=1)**:
  ```
===== sidecar.history =====
===== cursor auth attempt diag =====
Error: Password not found for account 'cursor-user' and service 'cursor-access-token'
Failed with exit code 1. Output size: 0 bytes.
===== diag =====
[31m✗ Failed to reach the Cursor API. If you are behind a corporate proxy, set the HTTPS_PROXY environment variable.[0m
Failed with exit code 1. Output size: 0 bytes.
===== launch-stderr =====
❌ cursor agent: FAILED (exit code 1, output 0 bytes)
❌ cursor agent: FAILED (exit code 1, output 0 bytes)

===== additional failure diagnostics =====
===== sidecar.history =====
===== cursor auth attempt diag =====
Error: Password not found for account 'cursor-user' and service 'cursor-access-token'
Failed with exit code 1. Output size: 0 bytes.
===== diag =====
[31m✗ Failed to reach the Cursor API. If you are behind a corporate proxy, set the HTTPS_PROXY environment variable.[0m
Failed with exit code 1. Output size: 0 bytes.
===== launch-stderr =====
❌ cursor agent: FAILED (exit code 1, output 0 bytes)
❌ cursor agent: FAILED (exit code 1, output 0 bytes)
  ```

- **Step design Step 3 — collect-results cursor NOT_SUBSTANTIVE failed (exit 0)**:
  ```
## Structured collector record

REVIEWER_FILE=<TMPDIR>/plan-review/round-1/dyn-cursor-plan-runtime-contracts.txt|TOOL=cursor|STATUS=NOT_SUBSTANTIVE|EXIT_CODE=0|FAILURE_REASON=structured records not found after repair

## Reviewer output (<TMPDIR>/plan-review/round-1/dyn-cursor-plan-runtime-contracts.txt)

Searching the repo for the plan and proposed changes for Items 1, 9, and 13.
**Verdict:** Items **1** and **9** mostly preserve machine contracts on the default path; **Item 13** is only partially aligned because the Step 0 authority doc was not updated.

Scope: **plan `### UPDATED:` headings** 1 (`python/agents.py`), 9 (`python/test_collect_results.py`), 13 (`docs/external-reviewers.md`) from the #4756 plan (`larch-logs/implement/23DAC8E4-EE0F-4743-A440-FEE99676625A/plan-goals-test.md`). Reviewed against current `main` (working tree clean).

---

## Item 1 — `### UPDATED: python/agents.py` (probe timeout + failure-path changes)

**Plan bullets:** `_max_timeout_probe_retries()` / `LARCH_PROBE_TIMEOUT_RETRIES`; timeout retry in `_run_codex_probes` / `_run_cursor_probes`; pass budget from `check_reviewers`; review/implement failure resolver wiring.


- **Step design Step 3 — collect-results codex NOT_SUBSTANTIVE failed (exit 0)**:
  ```
## Structured collector record

REVIEWER_FILE=<TMPDIR>/plan-review/round-1/dyn-codex-plan-runtime-contracts.txt|TOOL=codex|STATUS=NOT_SUBSTANTIVE|EXIT_CODE=0|FAILURE_REASON=structured records not found after repair

## Reviewer output (<TMPDIR>/plan-review/round-1/dyn-codex-plan-runtime-contracts.txt)

Found **4 contract-drift issues**.

1. **High: collector quiet-init and stderr prefix contract is inverted.**
   - **Plan support:** `collect_results_main` must call `quiet_init(argv0="collect-agent-results.sh")` before flag parsing: `larch-logs/design/E473D567-A588-441A-809A-1DAD31B47E38/plan.txt:39-41`, `:71-76`.
   - **Issue:** implementation parses args first, then calls `quiet_init(argv0="collect-results")`.
   - **Paths:** `python/collect_results.py:1037-1116`, especially `:1110-1116`.
   - **Breakage:** bad argv or timeout errors bypass quiet routing and legacy `collect-agent-results.sh:` diagnostics. That can hide failures from `/design` or `/implement` rerun logs.

2. **High: initial-wait fatal trailer changed.**
   - **Plan support:** fatal wait must emit `collect-agent-results.sh: wait-for-reviewers.sh exited <rc>`: `larch-logs/design/E473D567-A588-441A-809A-1DAD31B47E38/plan.txt:43-50`, `:101-104`.
   - **Issue:** implementation emits `collect-results: wait-reviewers exited <rc>`.
   - **Path:** `python/collect_results.py:901-916`.
   - **Breakage:** callers or harnesses matching the legacy trailer can miss the failure reason on rerun recovery.

3. **High: structured NS retry is not implemented.**
   - **Plan support:** Item 9 requires structured NS retry to preserve sidecar publish and `CURSOR_EMPTY_RESPONSE` downgrade: `larch-logs/design/E473D567-A588-441A-809A-1DAD31B47E38/plan.txt:681-684`. The detailed retry flow is specified at `:196-212`.
   - **Issue:** after structured validation fails, code marks `NOT_SUBSTANTIVE` and only emits diagnostics. It never queues or waits for an NS retry.
   - **Paths:** `python/collect_results.py:740-761`, `:982-999`.
   - **Test drift:** tests now assert no retry artifacts exist: `python/test_collect_results.py:200-217`.
   - **Breakage:** `/design` Step 3 uses `--structured-reviewer-validation`, so retryable structured failures become terminal dropped reviewers.

4. **Medium: run-log tool label is inconsistent for design Step 3 collector failures.**
   - **Plan support:** plan-review run-log labels should use `agent collect-results <tool> <status>`: `larch-logs/design/E473D567-A588-441A-809A-1DAD31B47E38/plan.txt:535-542`. Current docs say `python/cli.py agent collect-results <tool> <status>`: `skills/design/references/plan-review.md:129-134`.
   - **Issue:** implementation logs `collect-results {tool} {status}`, missing the `agent` prefix.
   - **Path:** `python/plan_review_round.py:240-257`.
   - **Breakage:** committed run-log batches and execution-issue dedupe can split the same failure class across two tool labels during `/design` reruns.
## Reviewer stderr (<TMPDIR>/plan-review/round-1/dyn-codex-plan-runtime-contracts.txt.diag)

(file missing: <TMPDIR>/plan-review/round-1/dyn-codex-plan-runtime-contracts.txt.diag)

## Failed-agent stderr tail (<TMPDIR>/plan-review/round-1/dyn-codex-plan-runtime-contracts.txt.stderr-tail)

(file missing: <TMPDIR>/plan-review/round-1/dyn-codex-plan-runtime-contracts.txt.stderr-tail)

## Launcher stderr (<TMPDIR>/plan-review/round-1/dyn-codex-plan-runtime-contracts.txt.launch-stderr)

⏳ codex agent: still running (1m elapsed)
⏳ codex agent: still running (2m elapsed)
⏳ codex agent: still running (3m elapsed)
✓ codex agent: completed (exit code 0, output 2642 bytes)
  ```

- **Step design Step 3 — collect-results codex NOT_SUBSTANTIVE failed (exit 0)**:
  ```
## Structured collector record

REVIEWER_FILE=<TMPDIR>/plan-review/round-1/dyn-cursor-plan-dirty-tree-safety-phase2.txt|TOOL=codex|STATUS=NOT_SUBSTANTIVE|EXIT_CODE=0|FAILURE_REASON=structured records not found after repair

## Reviewer output (<TMPDIR>/plan-review/round-1/dyn-cursor-plan-dirty-tree-safety-phase2.txt)

Not enough for `main-agent-required` handoff commits.

**Findings:**

- **[P1] Add a pre-commit dirty-path guard for main-agent handoff commits.**
  - **Plan support:** The plan’s **“Step 5 resume / Step 7 backup”** bullet says main-agent handoff fixes are committed through `commit-fixes --stage-all` using review delta pathspecs, not `git add -A`: `larch-logs/design/BD9CFCF6-95EC-49B8-B0BD-7A3DCF227885/plan.txt:17`.
  - **Plan support:** The heading **“B. `commit_fixes --stage-all` pathspec-only staging”** says `_collect_review_fix_stage_paths` supplies the commit path list, then `git add --pathspec-from-file` and `git-commit.sh --only --pathspec-from-file` run: `larch-logs/design/BD9CFCF6-95EC-49B8-B0BD-7A3DCF227885/plan.txt:164-168`.
  - **Issue:** The commit happens before the dirty-tree failure check. `step-5-resume.sh` calls `commit-fixes --stage-all`, then probes porcelain only afterward: `skills/implement/scripts/step-5-resume.sh:85-97`.
  - **Issue:** `commit_fixes` writes the pathspec and commits immediately. It does not first reject dirty paths outside the computed review-delta set: `python/review_and_fix.py:3039-3075`.
  - **Issue:** The current test allows this shape. It simulates `M a.py` plus `M unrelated.py`, stages only `a.py`, and still expects `COMMITTED=true`: `python/test_review_and_fix.py:946-971`.
  - **Why filters are insufficient:** `_collect_review_fix_stage_paths` depends on existing round snapshots and `_collect_round_stage_paths`: `python/review_and_fix.py:2036-2056`, `python/review_and_fix.py:908-943`. Those snapshots predate the main-agent handoff. They do not prove the tree is clean except for the main-agent edits at commit time.
  - **Smallest guard:** Before `git add`, compute current dirty tracked plus untracked paths. If any path is outside `review-fix-stage-paths.txt`, emit `COMMITTED=false`, set `ERROR=dirty-paths-outside-review-delta`, and return nonzero. For strongest safety on `main-agent-required`, also require a handoff-local snapshot written immediately before the main agent edits, and derive commit paths from deltas against that snapshot.

**Safe as planned:**

- **Automated lint-fix `applied` paths are better covered.** The plan captures a pre-lint snapshot, unions lint `delta_paths`, and commits pathspec-only: `larch-logs/design/BD9CFCF6-95EC-49B8-B0BD-7A3DCF227885/plan.txt:140-162`.
- **`lint-fix-main-agent-required` itself is unchanged.** The plan says to leave that behavior unchanged, so this risk is in the later main-agent handoff commit path, not the lint-fix loop’s own successful-break commit: `larch-logs/design/BD9CFCF6-95EC-49B8-B0BD-7A3DCF227885/plan.txt:162`.

**Tests:** Not run. Read-only review only.
## Reviewer stderr (<TMPDIR>/plan-review/round-1/dyn-cursor-plan-dirty-tree-safety-phase2.txt.diag)

(file missing: <TMPDIR>/plan-review/round-1/dyn-cursor-plan-dirty-tree-safety-phase2.txt.diag)

## Failed-agent stderr tail (<TMPDIR>/plan-review/round-1/dyn-cursor-plan-dirty-tree-safety-phase2.txt.stderr-tail)

(file missing: <TMPDIR>/plan-review/round-1/dyn-cursor-plan-dirty-tree-safety-phase2.txt.stderr-tail)

## Launcher stderr (<TMPDIR>/plan-review/round-1/dyn-cursor-plan-dirty-tree-safety-phase2.txt.launch-stderr)

⏳ codex agent: still running (1m elapsed)
⏳ codex agent: still running (2m elapsed)
⏳ codex agent: still running (3m elapsed)
✓ codex agent: completed (exit code 0, output 2717 bytes)
  ```

- **Step design Step 3 — collect-results codex NOT_SUBSTANTIVE failed (exit 0)**:
  ```
## Structured collector record

REVIEWER_FILE=<TMPDIR>/plan-review/round-1/dyn-codex-plan-dirty-tree-safety.txt|TOOL=codex|STATUS=NOT_SUBSTANTIVE|EXIT_CODE=0|FAILURE_REASON=structured records not found after repair

## Reviewer output (<TMPDIR>/plan-review/round-1/dyn-codex-plan-dirty-tree-safety.txt)

**Not enough.** The snapshot helps, but it does not prove authorship of post-snapshot dirt.


- **Step design Step 3 — collect-results cursor NOT_SUBSTANTIVE failed (exit 0)**:
  ```
## Structured collector record

REVIEWER_FILE=<TMPDIR>/plan-review/round-1/dyn-cursor-plan-checkpoint-staleness.txt|TOOL=cursor|STATUS=NOT_SUBSTANTIVE|EXIT_CODE=0|FAILURE_REASON=structured records not found after repair

## Reviewer output (<TMPDIR>/plan-review/round-1/dyn-cursor-plan-checkpoint-staleness.txt)

Searching the repo for the CI checkpoint validation plan and related implementation.
**Verdict:** The plan’s post-push `FAILED_RUN_ID` rules are sound and fail-closed, but the tree only partially implements them. The main Claude delegation path still fail-opens on missing or matching `FAILED_RUN_ID`. Push-checkpoint timeout recovery does not validate `RUN_ID` or `CYCLE`.

---


- **Step design Step 3 — collect-results codex NOT_SUBSTANTIVE failed (exit 0)**:
  ```
## Structured collector record

REVIEWER_FILE=<TMPDIR>/plan-review/round-1/dyn-codex-plan-checkpoint-staleness.txt|TOOL=codex|STATUS=NOT_SUBSTANTIVE|EXIT_CODE=0|FAILURE_REASON=structured records not found after repair

## Reviewer output (<TMPDIR>/plan-review/round-1/dyn-codex-plan-checkpoint-staleness.txt)

Found **3 issues**.

## Findings

- **[P1] OOS checkpoint can fail open from stale `finalize-state.sh`.**
  - **Issue:** `python/file_oos.py` merges `ship-pr-state.sh` with `finalize-state.sh`, with `finalize-state.sh` overriding. A stale `FORKED_TARGET=true` or `REPO_UNAVAILABLE=true` can skip the disposition gate and return success.
  - **Location:** `python/file_oos.py:547-549`, `python/file_oos.py:462-464`, `python/file_oos.py:600`.
  - **Plan support:** `skills/implement/SKILL.md:802` says checkpoint skip flags come from `$IMPLEMENT_TMPDIR/ship-pr-state.sh` and says “do not substitute `finalize-state.sh` for those OOS gate inputs.”
  - **Fix:** Read OOS checkpoint inputs only from `ship-pr-state.sh`. Treat conflicting `finalize-state.sh` values as irrelevant.

- **[P1] Stale `RUN_ID` can bind a foreign `oos-issues.ndjson`.**
  - **Issue:** `RUN_ID` is taken from state before `session-id`. If state has a stale but existing run ID, the checkpoint can use a foreign run’s NDJSON and pass incorrectly.
  - **Location:** `python/file_oos.py:560-567`.
  - **Plan support:** `skills/implement/scripts/oos-disposition-checkpoint.md:32-41` under **“Ndjson discovery”** says the helper reads `$IMPLEMENT_TMPDIR/session-id` as `RUN_ID`, uses only that keyed path when non-empty, and stale `RUN_ID` must fail closed.
  - **Test gap:** `skills/implement/scripts/test-oos-disposition-gate.sh:692-730` covers keyed and stale `session-id`, but not stale state `RUN_ID` conflicting with `session-id`.
  - **Fix:** Make `session-id` authoritative, or require state `RUN_ID == session-id`. On mismatch, exit `2`.

- **[P2] Cycle validation is needed after clearing `OOS_PENDING`.**
  - **Issue:** The orchestrator text says to set `OOS_PENDING=false`, read state, then re-invoke `step-8-ship.sh`. It does not require a fail-closed assertion that the persisted value is actually false.
  - **Location:** `skills/implement/SKILL.md:802`, `skills/implement/SKILL.md:806-810`.
  - **Plan support:** `larch-logs/design/9F937A0D-29F6-4DBC-B85F-2419956076AE/acceptance.md:9` says `OOS_PENDING` clear and re-entry remain orchestrator-owned.
  - **Risk:** If the write fails or stale state remains, re-entry can cycle back into the same OOS checkpoint path.
  - **Fix:** After writing, re-read `ship-pr-state.sh`. If `OOS_PENDING` is not exactly `false`, log `step-8-oos-checkpoint-validation` and stop. Do not re-invoke.

## Non-issue

- **Missing `RUN_ID` behavior is contract-backed.**
  - `skills/implement/scripts/oos-disposition-checkpoint.md:36-40` explicitly allows find fallback when `session-id` is empty.
  - `skills/implement/scripts/test-oos-disposition-gate.sh:738-766` covers single-match fallback and ambiguity exit `2`.
  - This is fail-open by preference, but the current contract requires it.
## Reviewer stderr (<TMPDIR>/plan-review/round-1/dyn-codex-plan-checkpoint-staleness.txt.diag)

(file missing: <TMPDIR>/plan-review/round-1/dyn-codex-plan-checkpoint-staleness.txt.diag)

## Failed-agent stderr tail (<TMPDIR>/plan-review/round-1/dyn-codex-plan-checkpoint-staleness.txt.stderr-tail)

(file missing: <TMPDIR>/plan-review/round-1/dyn-codex-plan-checkpoint-staleness.txt.stderr-tail)

## Launcher stderr (<TMPDIR>/plan-review/round-1/dyn-codex-plan-checkpoint-staleness.txt.launch-stderr)

⏳ codex agent: still running (1m elapsed)
⏳ codex agent: still running (2m elapsed)
⏳ codex agent: still running (3m elapsed)
✓ codex agent: completed (exit code 0, output 2812 bytes)
  ```

- **findings aggregator**: merged output failed validation; leaving <TMPDIR>/findings-in-scope.md unchanged. See <TMPDIR>/aggregator-validate.stderr.
### In-Scope Findings

- **correctness** `python/ci_agentic_fix.py:699-702` — The production post-push tail still does `next_run = wait.get("FAILED_RUN_ID") or run_id` and returns `"pushed"`, so a missing `FAILED_RUN_ID` reuses the current run and `main()` burns another cycle (`804-805`). That violates **Plan → `UPDATED: python/ci_agentic_fix.py` → “After a successful push, fail closed when post-push wait output cannot justify another cycle”** (lines 26-30), **Edge cases** (“Parsed post-push `CI_STATUS=fail`/`failure` with `ACTION` set but no `FAILED_RUN_ID` must fail closed…”, lines 146-147), and **Failure modes** (“If post-push failure wait reuses `run_id` without `FAILED_RUN_ID`…”, lines 159-160). **Suggested fix:** After pass/rebase/behind branches, require non-empty `FAILED_RUN_ID != run_id` before advancing; otherwise return `ci-fix-exhausted` with `ci-wait-missing-failed-run-id` or `ci-wait-stale-failed-run-id` and `next_run_id=None`.

- **correctness** `python/ci_agentic_fix.py:483-486` — The known-harness branch advances when `CI_STATUS in {fail, failure}` and `FAILED_RUN_ID` is truthy, without checking `FAILED_RUN_ID != run_id`. A matching ID still returns `"continue"` with the same `next_run_id`, so cycles burn on the same failing run. Same plan bullets as above (lines 29-30, 147-148, 160). **Suggested fix:** Add `next_run != run_id` before returning `"continue"`.

- **correctness** `python/ci_agentic_fix.py:317-320` — `_wait_for_ci` treats `CI_STATUS in {fail, failure}` plus any `ACTION` as parse-valid even when `FAILED_RUN_ID` is absent. That lets failure-shaped output reach the fail-open tail on the Claude path. Plan allows parser churn avoidance (**`UPDATED: python/ci_agentic_fix.py` → “Keep `_wait_for_ci` parsing small”**, lines 31-34) but also lists optional tightening: fail+`ACTION` without `FAILED_RUN_ID` should return `wait_err`. **Suggested fix:** Either return `wait_err` from the parser, or enforce the stale/missing guard on every post-push path before any `next_run` assignment (plan **FINDING_2**, `rejected-findings.md` lines 13-19).

- **risk-integration** `python/ci_monitor.py:1386-1407` — On delegate timeout, `_agentic_fix_result` reads `ci-agentic-push-checkpoint.latest` with no `RUN_ID` or `CYCLE` validation against the current delegate `--run-id`. A prior run’s checkpoint can report `status="pushed"` for the wrong run. Plan **Edge cases** (line 145) covers malformed wait after push, not checkpoint staleness; stale-checkpoint trust was marked OOS (`oos-combined.md`). Under a fail-closed default, this is still a gap. **Suggested fix:** Require `checkpoint["RUN_ID"] == run_id` (and optionally `int(checkpoint["CYCLE"]) <= max_cycles`) before timeout recovery; otherwise return `fix-exhausted`.

- **testing** `python/test_ci_agentic_fix.py` — Plan **UPDATED: python/test_ci_agentic_fix.py** mandates stubbed tests for missing `FAILED_RUN_ID` (lines 85-87) and stale equal `FAILED_RUN_ID` (lines 88-91). No such tests exist (`grep` finds no `stale` / `ci-wait-stale` / `ci-wait-missing`). `test_run_cycle_wait_untrusted_action` (`1115-1138`) uses `ACTION=retry`, which hits the guard at `665-674`, not the production `evaluate_failure` tail at `701-702`. **Suggested fix:** Add stubs for `ACTION=evaluate_failure, CI_STATUS=fail` with absent and equal `FAILED_RUN_ID`; assert `ci-fix-exhausted`, stable detail tokens, and `next_run_id is None`.

- **testing** `python/test_ci_agentic_fix.py:712-753` — `test_agentic_fix_result_timeout_reads_push_checkpoint` writes `RUN_ID=99` while the delegate uses `run_id="42"` and expects `status="pushed"`. That encodes fail-open checkpoint acceptance instead of fail-closed `RUN_ID` matching. **Suggested fix:** Flip the assertion: mismatched `RUN_ID` should yield `fix-exhausted`, not `pushed`.

- **plan-fidelity** `larch-logs/design/A766165B-1241-41D9-A828-87DDB65AFD2B/composed-plan.md:26-29` vs `plan.txt:26-30` — The composed plan omits explicit stale-equal and missing-`FAILED_RUN_ID` bullets when `ACTION` is in the expected set (e.g. `evaluate_failure`). It only guards “ACTION not in expected set and no `FAILED_RUN_ID`”. That leaves a documented hole for the common production path. **Suggested fix:** Merge `plan.txt` lines 28-30 into the composed plan before implement.

---

### Matching `RUN_ID` behavior

| Scenario | Plan requirement | Current behavior |
|---|---|---|
| Post-push `FAILED_RUN_ID == run_id` | `ci-fix-exhausted`, detail `ci-wait-stale-failed-run-id` (`plan.txt` 29, Edge cases 147-148) | Claude path: reuses via `or run_id` (`701-702`). Harness path: advances if truthy (`483-486`). |
| Push-checkpoint `RUN_ID` on timeout | Not specified (OOS stale checkpoint) | No check; mismatched checkpoint trusted (`ci_monitor.py:1387-1407`; test `712-753`). |

**Plan support:** Explicit for post-push wait (`plan.txt` 26-30). Silent for push-checkpoint `RUN_ID` match.

---

### Missing `RUN_ID` / `FAILED_RUN_ID` behavior

| Scenario | Plan requirement | Current behavior |
|---|---|---|
| Post-push fail shape, no `FAILED_RUN_ID` | `ci-fix-exhausted`, `ci-wait-missing-failed-run-id` (`plan.txt` 28, Edge cases 146-147) | Claude path: `or run_id` fallback (`701-702`). Harness path: fail-closed (`486`) but only when `CI_STATUS` is fail/failure. |
| `_wait_for_ci` parse of fail+`ACTION`, no `FAILED_RUN_ID` | Optional `wait_err` (`plan.txt` 34) | Parse-valid (`317-320`), reaches fail-open tail on Claude path. |
| Checkpoint missing `RUN_ID` key | Unspecified | Empty string; no rejection (`1306-1315`). |

---

### Whether cycle validation is needed

**For post-push wait advancement:** Yes. Plan **Failure modes** (159-160) and `main()`’s `if next_run_id: run_id = next_run_id` (804-805) mean cycle validation is implicit: advancing without a *new* failing run burns the cap. Matching `FAILED_RUN_ID` must fail closed.

**For push-checkpoint timeout recovery:** `RUN_ID` validation is needed for fail-closed behavior; the plan does not require it but writes `CYCLE=` (`ci_agentic_fix.py:266`) without reading it on recovery. Recommend:

1. **`RUN_ID` match** (required): reject stale checkpoints from a prior delegate or CI run.
2. **`CYCLE` bound** (recommended): reject when `int(CYCLE) > CI_AGENTIC_FIX_MAX_CYCLES` or when checkpoint predates delegate start; lower priority than `RUN_ID` but cheap insurance.
3. **Delegate start:** truncate or version `ci-agentic-push-checkpoint.latest` so a new `--run-id` cannot inherit an old file.

Plan does not mandate (2) or (3); they are consistent with **Approach** (“Fail closed when the delegated fixer cannot trust CI wait output”, `plan.txt` line 8).

---

### Out-of-Scope Observations

- Wait-error, `ACTION=bail`, and `ACTION=retry` paths are largely fail-closed with `next_run_id=None` (`448-470`, `643-674`, `1085-1164`). Good partial progress vs plan.
- Later-cycle non-health → `waterfall-failed` (`540`, `1167-1234`) matches plan.
- Stale push-checkpoint on timeout was explicitly OOS (`oos-combined.md`); flagging it here because the review brief prefers fail-closed unless a contract says otherwise.
## Reviewer stderr (<TMPDIR>/plan-review/round-1/dyn-cursor-plan-checkpoint-staleness.txt.diag)

(empty: <TMPDIR>/plan-review/round-1/dyn-cursor-plan-checkpoint-staleness.txt.diag)

## Failed-agent stderr tail (<TMPDIR>/plan-review/round-1/dyn-cursor-plan-checkpoint-staleness.txt.stderr-tail)

(file missing: <TMPDIR>/plan-review/round-1/dyn-cursor-plan-checkpoint-staleness.txt.stderr-tail)

## Launcher stderr (<TMPDIR>/plan-review/round-1/dyn-cursor-plan-checkpoint-staleness.txt.launch-stderr)

⏳ cursor agent: still running (1m elapsed)
⏳ cursor agent: still running (2m elapsed)
⏳ cursor agent: still running (3m elapsed)
⏳ cursor agent: still running (4m elapsed)
✓ cursor agent: completed (exit code 0, output 7932 bytes)
  ```
### Findings

- **[Important] `main-agent-required` has no safe commit boundary.**
  - **Plan support:** `larch-logs/design/BD9CFCF6-95EC-49B8-B0BD-7A3DCF227885/plan.txt` under **`### UPDATED: python/review_and_fix.py`**, lines **140-162**. The key bullet says to leave `lint-fix-main-agent-required` unchanged at line **162**.
  - **Issue:** current `python/review_and_fix.py` only calls the lint snapshot commit helper on successful lint-loop breaks. It returns immediately on `LINT_FIX_STATUS=main-agent-required`, so no snapshot-filtered commit happens there. See `python/review_and_fix.py` lines **1772-1791** and **1793-1826**.
  - **Risk:** adding a commit on that branch using the planned broad candidate set could sweep unrelated files changed after the pre-lint snapshot.

- **[Important] Snapshot filtering excludes unchanged carryover, but not unrelated new dirt.**
  - **Plan support:** same plan heading, especially `_lint_fix_delta_paths` bullets at lines **147-150**. The plan says to include paths from `git diff --name-only <pre_lint_head>` when they diverge from snapshots.
  - **Issue:** that proves a path changed since the pre-lint snapshot. It does not prove lint-fix or main-agent repair changed it.
  - **Code evidence:** `checks._delta_paths_after_dispatch` only reports paths absent from the dispatch baseline, so it can miss in-place edits to already-dirty files. See `python/checks.py` lines **1317-1335**. The current lint snapshot helper only commits reported paths after excluding unchanged pre-dirty paths. See `python/review_and_fix.py` lines **1139-1159**.
  - **Risk:** broadening to all diverged paths catches missed in-place lint edits, but can also catch unrelated post-snapshot edits.

### Smallest guard

Add a **main-agent-required-only commit guard**:

- Compute planned `commit_paths`.
- Compute `unsafe = commit_paths - unioned_lint_delta_paths`.
- If `unsafe` is non-empty, **do not commit automatically**.
- Surface the paths and continue as `lint-fix-main-agent-required` or a commit-failed stall.

This is conservative. It may leave pre-dirty in-place lint edits for manual handling. It prevents unrelated files from being committed with the smallest change.
## Reviewer stderr (<TMPDIR>/plan-review/round-1/dyn-codex-plan-dirty-tree-safety.txt.diag)

(file missing: <TMPDIR>/plan-review/round-1/dyn-codex-plan-dirty-tree-safety.txt.diag)

## Failed-agent stderr tail (<TMPDIR>/plan-review/round-1/dyn-codex-plan-dirty-tree-safety.txt.stderr-tail)

(file missing: <TMPDIR>/plan-review/round-1/dyn-codex-plan-dirty-tree-safety.txt.stderr-tail)

## Launcher stderr (<TMPDIR>/plan-review/round-1/dyn-codex-plan-dirty-tree-safety.txt.launch-stderr)

⏳ codex agent: still running (1m elapsed)
⏳ codex agent: still running (2m elapsed)
⏳ codex agent: still running (3m elapsed)
✓ codex agent: completed (exit code 0, output 2300 bytes)
  ```
### Preserved (default path, `LARCH_PROBE_TIMEOUT_RETRIES=0`)

| Contract | Status |
|---|---|
| `check-reviewers` stdout KV set + order | **OK** — six keys unchanged: `CODEX_BINARY_FOUND`, `CURSOR_BINARY_FOUND`, `CODEX_PRESENT`, `CURSOR_PRESENT`, `CODEX_PROBE_TIMED_OUT`, `CURSOR_PROBE_TIMED_OUT` |
| `check-reviewers` exit code | **OK** — still `0` on success path |
| Default probe behavior | **OK** — `_max_timeout_probe_retries()` defaults invalid/missing to `0`; one timeout attempt, then `(False, True)` |
| Degraded-tools gate envelope | **OK** — `DEGRADED`, `CODEX_STATE`, `CURSOR_STATE`, `BOTH_DOWN`, `DEGRADED_EXPLANATION_*` unchanged; gate still keys off `*_PRESENT` only |
| Review launcher KV grammar | **OK** — `LAUNCHER_EXIT`, `LAUNCHER_FAILURE_CLASS`, `LAUNCHER_FAILURE_REASON`, `OUTPUT` still emitted from `_review_emit_launcher_result` |
| Success-path compose guard | **OK** — compose runs only when `launcher_exit != 0`, matching plan-review scope reduction |

```194:203:python/agents.py
    def kv_lines(self) -> tuple[str, ...]:
        data = self.kv()
        return tuple(f"{key}={data[key]}" for key in (
            "CODEX_BINARY_FOUND",
            "CURSOR_BINARY_FOUND",
            "CODEX_PRESENT",
            "CURSOR_PRESENT",
            "CODEX_PROBE_TIMED_OUT",
            "CURSOR_PROBE_TIMED_OUT",
        ))
```

```4323:4337:python/agents.py
def _review_emit_launcher_result(output: Path, tool: str, launcher_exit: int, *, stderr_sink: str = "") -> None:
    if launcher_exit != 0:
        _compose_failure_diag(output, sink=stderr_sink)
    sidecar = _review_failure_source(output, sink=stderr_sink)
    failure = classify_launch_failure(
        launcher_exit,
        sidecar,
        ...
    )
    _emit_kv("LAUNCHER_EXIT", launcher_exit)
    _emit_kv("LAUNCHER_FAILURE_CLASS", failure.failure_class)
    _emit_kv("LAUNCHER_FAILURE_REASON", failure.reason)
```

### Intentional failure-behavior change (non-default)

When `LARCH_PROBE_TIMEOUT_RETRIES>0`, a timeout followed by a successful retry sets `*_PRESENT=true` and `*_PROBE_TIMED_OUT=false`. That matches the plan **Edge cases** bullet (“timeout followed by success…”). Legacy behavior was `present=false`, `timed_out=true` on first timeout.

### Contract drift risks

**Important — `session setup` drops timeout KVs**

`session_env.py` forwards only four probe keys to Step 0 stdout, not `CODEX_PROBE_TIMED_OUT` / `CURSOR_PROBE_TIMED_OUT`:

```1604:1611:python/session_env.py
        probed = reviewer.kv()
        for key in ("CODEX_PRESENT", "CURSOR_PRESENT", "CODEX_BINARY_FOUND", "CURSOR_BINARY_FOUND"):
            if probed.get(key):
                _emit_kv(key, probed[key])
```

`/design` and `/implement` Step 0 never see `*_PROBE_TIMED_OUT` on the setup envelope. Direct `agent check-reviewers` still emits all six. Not introduced by this branch, but timeout retries make the distinction matter more when operators tune `LARCH_PROBE_TIMEOUT_RETRIES`.

**Important — preflight integration tests still missing (plan `### UPDATED: python/test_agents.py`)**

Plan requires preflight/auth paths with `stderr_sink` to prefer sink/retry/NS-retry over bare `.diag`. Unit tests cover `_review_emit_launcher_result` / `_review_append_launch_failure` directly (`test_review_emit_launcher_result_*`, `test_review_append_launch_failure_*`). There is no parametrized test through `launch_codex_review_main` / `launch_cursor_review_main` at the six preflight call sites (~4409, ~4418, ~4488, ~4618, ~4634, ~4690). Code review **FINDING_9** (round 1) is still open on that gap.

**Latent — brainstorm failures skip `run-log append-failure`**

On brainstorm paths (`codex-brainstorm` / `cursor-brainstorm`), non-zero exits call `_review_write_failure_sink` + `_review_emit_launcher_result` but not `_review_append_launch_failure` (e.g. ```4670:4674:python/agents.py```). `LAUNCHER_FAILURE_*` KVs are emitted; **execution-issues / run-log batches** may be absent. Pre-existing pattern, but resolver work increases the gap between KV classification and logged failures.

---

## Item 9 — `### UPDATED: python/test_collect_results.py` (stderr-tail ordering)

**Plan bullets:** NS-retry phase resolution; per-candidate ordering (retry/NS-retry before `.launch-stderr`); `.launch-stderr` render coverage.

### Preserved

| Contract | Status |
|---|---|
| `collect-results` stdout blocks | **OK** — `REVIEWER_FILE`, `STATUS`, `EXIT_CODE`, `FAILURE_REASON` grammar unchanged |
| Primary ordering | **OK** — primary `*-retry.txt.stderr-tail` beats primary `*-ns-retry.txt.stderr-tail` (`test_stderr_tail_resolution_primary_retry_beats_primary_ns_retry`) |
| Phase NS-retry | **OK** — `*-phase3.txt` resolves `*-phase2-ns-retry.txt.stderr-tail` (`test_stderr_tail_resolution_uses_phase2_ns_retry_for_phase3`) |
| Launch-stderr deferral | **OK** — phase NS-retry tail beats `*-phase2.launch-stderr` (`test_stderr_tail_resolution_phase_retry_tails_beat_launch_stderr`) |

```801:828:python/collect_results.py
def resolve_collector_stderr_tail_file(reviewer_file: str) -> str:
    base = reviewer_file.removesuffix(".txt")
    retry_tail = f"{base}-retry.txt.stderr-tail"
    ...
    for candidate in collector_stderr_tail_candidates(reviewer_file):
        ...
        for launch_stderr in (
            f"{candidate_base}-retry.txt.launch-stderr",
            f"{candidate_base}-ns-retry.txt.launch-stderr",
            f"{candidate}.launch-stderr",
        ):
            rendered_tail = _render_launch_stderr_tail(launch_stderr)
```

### Contract drift risk

**Nit — `*-ns-retry.txt.launch-stderr` path untested**

Plan bullet: “Retry **or NS-retry** `.launch-stderr` is rendered… only after retry/NS-retry stderr-tail candidates are absent.” Tests cover retry `.launch-stderr` (`test_stderr_tail_resolution_renders_retry_launch_stderr_after_tails_absent`) but not NS-retry `.launch-stderr`. Implementation handles both suffixes in the loop above; a rerun could regress NS-retry launch-stderr ordering without failing CI.

**Intentional diagnostic change**

When phase-derived retry/NS-retry tails exist, `_emit_failed_agent_stderr_tails` surfaces different stderr in collector diagnostics / execution-issues. That does **not** change collector `STATUS`/`FAILURE_REASON` KVs, but it **does** change operator-visible failure text on `/design` and `/review` reruns. Plan **Failure modes** (“pin order in tests”) covers the main paths; NS-retry launch-stderr is the remaining hole.

---

## Item 13 — `### UPDATED: docs/external-reviewers.md`

**Plan bullets:** mention `LARCH_PROBE_TIMEOUT_RETRIES`; default zero; unchanged health-gate latency; Cursor keychain under startup lock; no retired Bash refs.

### Partially preserved

`docs/external-reviewers.md` documents the new env var and keychain lock:

```10:15:docs/external-reviewers.md
Probe retries keep separate budgets. `LARCH_PROBE_RETRIES` covers transient
`rc == 1` failures. `LARCH_EXTERNAL_AUTH_RETRIES` covers auth-classified
failures. `LARCH_PROBE_TIMEOUT_RETRIES` covers timeout exits only, defaults to
`0`, and therefore leaves the default health-gate timeout latency unchanged.
Cursor keychain preflight and preread on Darwin run under the shared external
startup lock unless `CURSOR_API_KEY` is already usable.
```

`docs/configuration-and-permissions.md` has the full `(N+1) * LARCH_PROBE_TIMEOUT_SECONDS` latency formula (plan Item 14).

### Contract drift — reruns

**Important — Step 0 authority doc not synced**

`/design`, `/implement`, `/review`, and `/research` Step 0 read **`skills/shared/external-reviewers.md`** for the degraded-tools gate (not `docs/external-reviewers.md`). That file has **no** `LARCH_PROBE_TIMEOUT_RETRIES` or keychain-lock text. Plan **Item 5** called for syncing both surfaces; Item 13 only lists `docs/external-reviewers.md`.

Operators and orchestrators following the skill contract will not see timeout-retry semantics or keychain-lock behavior documented on the path that actually runs at Step 0. That is doc contract drift, not a stdout/sentinel break, but it can mislead `/design` and `/implement` reruns when tuning failure behavior.

---

## Cross-item summary

| Item | Machine stdout / sentinels / exit codes | Run-log batches | Rerun risk |
|---|---|---|---|
| **1** (`agents.py`) | **Preserved** at default `N=0` | Mostly preserved; brainstorm path may skip append-failure | Medium if `LARCH_PROBE_TIMEOUT_RETRIES>0` without reading `configuration-and-permissions.md` |
| **9** (`test_collect_results.py`) | **Preserved** (`collect-results` KV blocks) | Diagnostic stderr tails may differ (intentional) | Low if tests stay green; NS-retry `.launch-stderr` untested |
| **13** (`docs/external-reviewers.md`) | N/A | N/A | **High** for Step 0 operators using `skills/shared/external-reviewers.md` |

**Bottom line:** Default-path probe and collector contracts look safe for `/implement` and `/design` reruns. The main gaps are (1) missing preflight launch integration tests for Item 1’s failure-path changes, (2) missing NS-retry `.launch-stderr` test for Item 9’s ordering contract, and (3) Item 13 updating the wrong doc surface relative to the skill authority that Step 0 actually loads.
## Reviewer stderr (<TMPDIR>/plan-review/round-1/dyn-cursor-plan-runtime-contracts.txt.diag)

(empty: <TMPDIR>/plan-review/round-1/dyn-cursor-plan-runtime-contracts.txt.diag)

## Failed-agent stderr tail (<TMPDIR>/plan-review/round-1/dyn-cursor-plan-runtime-contracts.txt.stderr-tail)

(file missing: <TMPDIR>/plan-review/round-1/dyn-cursor-plan-runtime-contracts.txt.stderr-tail)

## Launcher stderr (<TMPDIR>/plan-review/round-1/dyn-cursor-plan-runtime-contracts.txt.launch-stderr)

⏳ cursor agent: still running (1m elapsed)
⏳ cursor agent: still running (2m elapsed)
⏳ cursor agent: still running (3m elapsed)
⏳ cursor agent: still running (4m elapsed)
⏳ cursor agent: still running (5m elapsed)
⏳ cursor agent: still running (6m elapsed)
⏳ cursor agent: still running (7m elapsed)
✓ cursor agent: completed (exit code 0, output 10618 bytes)
  ```
### Warnings

- **Step design Step 3 — validate-plan-commands failed (exit 0)**:
  ```
Override accepted at the Step 3 postplan plan-command validator gate (operator-confirmed).

The plan-command validator reported 2 missing-script defects:
  DEFECT script=skills/implement/scripts/test-step-18.sh kind=missing-script
  DEFECT script=skills/implement/scripts/test-step-7a.sh kind=missing-script

Determination: FALSE POSITIVES. Both scripts exist at the cited repo paths,
verified via filesystem check from the repo root (<OPERATOR_REPO_PATH>:
  EXISTS skills/implement/scripts/test-step-18.sh
  EXISTS skills/implement/scripts/test-step-7a.sh

Root cause: the plan-review loop runs the validator from the plugin-cache cwd
rather than the consumer repo root, so the relative script paths fail to resolve.
Known recurring bug #4490 / #4509 (validator repo-root resolution). No real plan
defect: the testing-strategy fences reference real, existing harnesses.

Action: Override + resume via --postplan-operator-continue (skips re-validation,
so the spurious defect does not recur). External auto-repair (plan validator-autofix)
intentionally skipped: there is no real defect to fix, and a vendor could "resolve"
the false positive by stripping the valid `bash skills/implement/scripts/test-step-*.sh`
commands from the testing strategy.
  ```

- **Step design Step 5c — validate-plan-commands failed (exit 0)**:
  ```
Override accepted at the Step 5c publish-validation gate (operator-authorized via Gate C plan approval; same false-positive class the operator Override'd at Step 3).

The composed-plan plan-command validator reported 2 missing-script defects:
  DEFECT script=skills/implement/scripts/test-step-18.sh kind=missing-script
  DEFECT script=skills/implement/scripts/test-step-7a.sh kind=missing-script

Determination: FALSE POSITIVES. Both scripts exist in the consumer repo (verified earlier
this run). Root cause: the #4847 cwd bug recurring at the Step 5c publish site
(python/design_publish.py validation), broader than the filed #4847 report which pinned
python/plan_review.py:879. The validator resolved script paths against the plugin-cache
root rather than the consumer repo, and the 51.1.9 cache lacks the consumer-only test
harnesses test-step-18.sh / test-step-7a.sh.

Action: Override + re-run design-step5c.sh --skip-validate. VALIDATE_DEFECT_COUNT=2 and both
are the missing-script false positives, so --skip-validate bypasses no real defect. External
auto-repair intentionally skipped (no real defect; a vendor could strip the valid
bash skills/implement/scripts/test-step-*.sh testing commands).

Follow-up: augment #4847 with this Step 5c (design_publish.py) manifestation.
  ```
