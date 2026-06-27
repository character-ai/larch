# Review Round 1

- Mode: `diff`
- 14 accepted, 0 rejected (0 neutral)

## Accepted Findings

### FINDING_1: Step 3 lacks `BAIL_REASON=recovery-out-of-scope` handling
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt, dyn-dyn-step4-composite-output.txt, dyn-dyn-skill-wires-output.txt
- **Severity**: important
- **Concern**: Step 3 composite post-parse routing omits `BAIL_REASON=recovery-out-of-scope`, which `python/implement_dispatch.py` can emit after post-checks recovery scope-check failure (`_run_step4_recovery_recompute`). A recovery run can pass pre-composite scope-check, checks-repair adds out-of-plan edits, and the composite exits non-zero with `BAIL_REASON=recovery-out-of-scope` and no `NEXT_ACTION` while checks relay shows success. The orchestrator may not bail Step 12d with `recovery-out-of-scope` per plan.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Add post-fence Step 3 rules mirroring Step 6 plus explicit branch: on BAIL_REASON=recovery-out-of-scope set IMPLEMENT_BAIL_REASON/FINAL_BAIL_REASON and bail Step 12d with STALL_STEP=2.
  - From cursor-specialist-edge-cases-output.txt: Add Step 6-parity post-fence parsing: recovery-out-of-scope to Step 12d; seed-failed and non-zero-without-NEXT_ACTION fail closed before Step 5.
  - From dyn-dyn-step4-composite-output.txt: Add an explicit Step 3 branch mirroring Step 2.4's pre-composite recovery bail: on `BAIL_REASON=recovery-out-of-scope`, set `FINAL_BAIL_REASON` / `IMPLEMENT_BAIL_REASON=recovery-out-of-scope`, `STALL_STEP=2` (or the step you intend), `STALL_TRACKING=true`, and bail to Step 12d without re-running the composite.
  - From dyn-dyn-skill-wires-output.txt: Add a Step 3 post-fence block mirroring Step 6 (~667): parse one `NEXT_ACTION=`; on `BAIL_REASON=recovery-out-of-scope`, bail Step 12d with `IMPLEMENT_BAIL_REASON=recovery-out-of-scope` and `STALL_STEP=3` (or `4`); on `seed-failed` or invalid envelope, fail closed to Step 18/12d per Step 6 parity.


### FINDING_2: Step 3 lacks Step 6-style invalid-envelope handling (`seed-failed`, non-zero without `NEXT_ACTION`)
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt, dyn-dyn-step4-composite-output.txt, dyn-dyn-skill-wires-output.txt
- **Severity**: important
- **Concern**: Step 3 says "parse the composite stdout like Step 6" but lacks Step 6 post-fence envelope rules (`seed-failed` handling, non-zero exit allowed when `NEXT_ACTION=continue`, invalid-envelope fail-closed). Claude-fallback or folded `4.r` / Step 4 `seed-failed` paths can yield composite exit 1 with `COMMIT_ROUTE_OUTCOME=seed-failed` and no `NEXT_ACTION`, or non-zero with `NEXT_ACTION=continue` on rebase conflict. Without Step 6 parity, the orchestrator may proceed to Step 5 without an implementation commit, or mis-treat valid `continue` envelopes as hard failures.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Add Step 3 post-fence paragraph matching Step 6: on seed-failed or non-zero without NEXT_ACTION treat as invalid envelope and fail closed (Step 18 or explicit stall seed).
  - From cursor-specialist-edge-cases-output.txt: Add Step 6-parity post-fence parsing: recovery-out-of-scope to Step 12d; seed-failed and non-zero-without-NEXT_ACTION fail closed before Step 5.
  - From dyn-dyn-step4-composite-output.txt: Copy the Step 6 post-fence paragraph into Step 3, adapted for `4.r` / `STALL_STEP=4`, including "parse `NEXT_ACTION` before treating exit code as invalid" and explicit `seed-failed` / non-zero-without-`NEXT_ACTION` routing.
  - From dyn-dyn-skill-wires-output.txt: Add a Step 3 post-fence block mirroring Step 6 (~667): parse one `NEXT_ACTION=`; on `BAIL_REASON=recovery-out-of-scope`, bail Step 12d with `IMPLEMENT_BAIL_REASON=recovery-out-of-scope` and `STALL_STEP=3` (or `4`); on `seed-failed` or invalid envelope, fail closed to Step 18/12d per Step 6 parity.


### FINDING_3: Step 2 telemetry sentinel written only on timing-mark success
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, codex-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt, codex-specialist-edge-cases-output.txt, dyn-dyn-dispatch-telemetry-output.txt, dyn-dyn-skill-wires-output.txt
- **Severity**: important
- **Concern**: `.step2-telemetry-marked` is written only when the timing mark returns 0, while the token mark may already have run. If the first dispatch timing mark fails transiently, the sentinel is absent; a later first dispatch without `--answers` re-runs token (and possibly timing) marking, double-counting Step 2 telemetry and breaking the once-only contract under `dispatch.lock`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Write sentinel after once-only telemetry attempt regardless of timing RC or tie token mark to the same completion predicate.
  - From codex-specialist-correctness-output.txt: Write `.step2-telemetry-marked` after the telemetry block has run under the lock, not only after timing success.
  - From cursor-specialist-edge-cases-output.txt: Write `.step2-telemetry-marked` after the full once-only mark block, independent of timing return code, or gate both marks behind the same sentinel write.
  - From codex-specialist-edge-cases-output.txt: Persist the sentinel after the first telemetry attempt or track token and timing outcomes separately so a timing-only failure does not reopen token marking.
  - From dyn-dyn-dispatch-telemetry-output.txt: Write the sentinel only after both marks complete (or treat timing failure as hard failure without spawning the child), or record partial state so token cannot re-fire on retry.
  - From dyn-dyn-skill-wires-output.txt: Write `.step2-telemetry-marked` after the first mark attempt while the lock is held (or gate token on the same success predicate), so once-only covers both token and timing.


### FINDING_4: Missing launcher tests asserting no Step 2 token mark
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt, dyn-dyn-dispatch-telemetry-output.txt
- **Severity**: important
- **Concern**: Plan-requested pytest proving `launch_codex_implement_main` / `launch_cursor_implement_main` no longer call `token mark "Step 2 — implementation"` is absent. Re-adding launcher marks would not be caught by CI while `run_dispatch_main` once-only marks could double-count Step 2 ledger rows.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Add parametrized launcher tests asserting no token mark Step 2 — implementation call.
  - From cursor-specialist-testing-output.txt: Add parametrized launch_codex_implement_main / launch_cursor_implement_main tests that spy proc.run and assert no token mark Step 2 invocation.
  - From dyn-dyn-dispatch-telemetry-output.txt: Add parametrized launcher tests that mock `proc.run` / subprocess and assert no argv contains `["token", "mark", "Step 2 — implementation"]`.


### FINDING_5: `_persist_ship_seed_context()` does not refresh blank `MANIFEST_PATH` or `TOOL_LABEL`
- **Reviewer(s)**: codex-specialist-correctness-output.txt
- **Severity**: important
- **Concern**: A tmpdir with `MANIFEST_PATH=` from bootstrap keeps the empty value, so a later successful external dispatch never records the manifest path and Step 4 can take the wrong branch.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-correctness-output.txt: Treat empty values as missing, or overwrite these keys when their current value is blank.


### FINDING_6: Recovery metadata does not exclusively gate the recovery commit branch
- **Reviewer(s)**: codex-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt, codex-specialist-edge-cases-output.txt
- **Severity**: important
- **Concern**: When `recovery-metadata.json` exists but `recovery-commit-message.txt` is missing or empty, `_run_step4_commit_leg` can fall through to the ordinary implementation branch and commit `implementation-commit-paths.nul` instead of `step2-recovery-paths-final.nul`, potentially leaving recovered Codex/Cursor edits uncommitted or committing the wrong delta.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-correctness-output.txt: Make recovery metadata dominate selection and return seed-failed if either recovery artifact is missing.
  - From cursor-specialist-edge-cases-output.txt: When recovery-metadata.json is present, require recovery message and step2-recovery-paths-final.nul; return seed-failed otherwise; never select the ordinary branch.
  - From codex-specialist-edge-cases-output.txt: Make recovery metadata select the recovery branch exclusively; if any recovery artifact is missing, return seed-failed immediately and do not consider the ordinary fallback branch.


### FINDING_8: Missing test for `_run_step4_recovery_recompute` scope-check failure path
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: important
- **Concern**: `_run_step4_recovery_recompute` scope-check failure path is untested; composite tests mock recompute to always succeed. A scope-check wiring bug could emit continue/stall instead of `recovery-out-of-scope` and allow an out-of-plan recovery commit.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Add direct or integration test with recovery-metadata present and failing scope-check; assert BAIL_REASON=recovery-out-of-scope and no NEXT_ACTION stall/continue.


### FINDING_9: Missing unit test for recovery commit branch in `_run_step4_commit_leg`
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: important
- **Concern**: `_run_step4_commit_leg` recovery commit branch has no unit coverage; only ordinary implementation pathspec is tested. Recovery selector or pathspec regression could break manifest-schema-invalid commits while ordinary-path tests pass.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Add test seeding recovery-metadata.json recovery-commit-message.txt and step2-recovery-paths-final.nul; assert commit uses recovery pathspec and message.


### FINDING_10: Missing `step2_dispatch_main --answers` no-extra-timing test
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: important
- **Concern**: Plan-required `step2_dispatch_main --answers` redispatch no-extra-timing test is absent; only `run_dispatch` telemetry is guarded. Re-adding timing mark to `step2_dispatch_main` on Q/A resume duplicates Step 2 timing rows on external redispatch.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Add step2_dispatch_main --answers test asserting zero timing mark Step 2 calls; optional structural negative grep.


### FINDING_11: Step 4 noop path drops dispatcher-committed skip breadcrumb
- **Reviewer(s)**: codex-specialist-testing-output.txt
- **Severity**: important
- **Concern**: External-manifest runs no longer print the required `⏩ 4: commit (impl) status=skip reason=dispatcher-committed ...` marker on the noop branch, so downstream orchestration loses the visible no-op signal.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-testing-output.txt: Emit the skip breadcrumb on the noop branch, either in `_run_step4_commit_leg()` or in `checks_commit_route_main()` before routing onward.


### FINDING_12: `skills/implement/SKILL.md:443` contradicts documented Cursor missing-binary fallback
- **Reviewer(s)**: codex-generalist-output.txt
- **Severity**: important
- **Concern**: Line 443 still says `coder=cursor` plus `STATUS=claude_fallback` must have failed closed before Step 2.4, but the new dispatcher contract intentionally routes missing Cursor binaries to `STATUS=claude_fallback` with edit authority. The orchestrator prompt may reject a state the Python path now succeeds into.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-generalist-output.txt: Update this paragraph to allow the documented missing-binary fallback path for Cursor, or scope the fail-closed warning only to unexpected Cursor drift cases not emitted by `run-dispatch` / `step2-dispatch`.


### FINDING_13: Successful external Codex/Cursor runs lack Step 2 token mark window boundary
- **Reviewer(s)**: dyn-dyn-dispatch-telemetry-output.txt
- **Severity**: important
- **Concern**: `run_dispatch_main` only marks when `token_eligible` (claude, or codex/cursor with missing binary). Removed launcher marks in `python/agents.py` were the only post-`check-budget` mark on the primary external path. `check_step_token_budget` resets vendor accumulation at each `mark` row, so external Step 2 spend now lacks a window boundary and cap enforcement can drift.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-dyn-dispatch-telemetry-output.txt: Restore a once-only post-`check-budget` token mark for successful external launches (e.g. gate launcher marks with `$IMPLEMENT_TMPDIR/.step2-telemetry-marked`, or move `check-budget` earlier and have `run_dispatch_main` mark codex/cursor when the binary is present, still after budget preflight and only on first dispatch).


### FINDING_14: Step 2.4 pathspec fence uses unbound `$REPO_ROOT`
- **Reviewer(s)**: dyn-dyn-skill-wires-output.txt
- **Severity**: important
- **Concern**: The Step 2.4 pathspec fence uses `$REPO_ROOT`, but SKILL never binds it. Unlike the composite (which resolves repo root inside Python), the orchestrator must supply `--repo-root` to `implement recovery-paths`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-dyn-skill-wires-output.txt: Pin a one-line prelude before the fence, e.g. `REPO_ROOT="$(git rev-parse --show-toplevel)"` with fail-closed routing if resolution fails, matching `run_dispatch_main`'s contract in `skills/implement/references/step2-dispatch.md:158`.


### FINDING_15: `checks-repair-loop.md` shows incomplete `recovery-paths` argv
- **Reviewer(s)**: dyn-dyn-skill-wires-output.txt
- **Severity**: important
- **Concern**: Step 3 repair refresh shows `python/cli.py implement recovery-paths --tmpdir "$IMPLEMENT_TMPDIR" --capture-postlaunch` only. `recovery_paths_main` requires `--repo-root`, `--prelaunch-porcelain`, `--postlaunch-porcelain`, `--prelaunch-digests`, and `--out-file`; SKILL.md:468 has the full argv.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-dyn-skill-wires-output.txt: Make line 66 match the SKILL pin (include `--repo-root "$REPO_ROOT"` and the absolute porcelain/digest/out paths), or reference the SKILL fence verbatim.


