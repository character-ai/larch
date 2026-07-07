# Review Round 1

- Mode: `diff`
- 5 accepted, 1 rejected (0 neutral)

## Accepted Findings

### FINDING_1: BGJOB_RC must gate read-result-env routing
- **Reviewer(s)**: cursor-specialist-correctness, cursor-specialist-edge-cases, dyn-dyn-bgjob-step3
- **Severity**: major
- **Concern**: `--read-result-env` can still report success and derive routing keys when `BGJOB_RC` is missing or non-zero, so callers can route on loop state without proven bgjob completion.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness: `Require BGJOB_RC=0 and minimal route KVs before ok; otherwise emit missing/invalid and empty NEXT_ACTION.`
  - From cursor-specialist-edge-cases: `Fail closed when BGJOB_RC is missing or not 0; add test coverage for non-zero BGJOB_RC with complete-looking loop KVs.`
  - From dyn-dyn-bgjob-step3: `In `_step3_normalize_read_result_env`, fail closed when `BGJOB_RC` is missing or not exactly `0` (emit a non-zero CLI rc, set `READ_RESULT_ENV_STATUS` to a failure token, and suppress `NEXT_ACTION`/route KVs); add a unit test covering `BGJOB_RC=timeout` plus `STEP3_REVIEW_LOOP_STATUS=complete`.`


### FINDING_5: `skills/design/SKILL.md` should read result env after any DONE, not only BGJOB_RC=0
- **Reviewer(s)**: codex-specialist-edge-cases
- **Severity**: major
- **Concern**: The prose currently makes result-env parsing conditional on `BGJOB_RC=0`, but terminal failure routes also need to be read after DONE so the orchestrator does not miss final-summary handling.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-edge-cases: `Read the result env after any DONE; gate only normal continuation on BGJOB_RC=0 and route known terminal failure KVs on nonzero rc.`


### FINDING_6: Wrapper cleanup/truncation follows symlinks under `DESIGN_TMPDIR`
- **Reviewer(s)**: codex-specialist-edge-cases
- **Severity**: major
- **Concern**: The fresh-start cleanup path can follow symlinks and affect files outside the session if the merge env or bgjob path is replaced with a symlink.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-edge-cases: `Move cleanup into a Python helper that canonicalizes under DESIGN_TMPDIR, rejects symlinks and non-regular files, and recreates the merge env with nofollow atomic write semantics.`


### FINDING_7: Existing completed bgjob result env should not be discarded on restart
- **Reviewer(s)**: codex-specialist-edge-cases
- **Severity**: major
- **Concern**: A fresh wrapper invocation can ignore a completed bgjob result env when the registry row is already gone, then relaunch review and lose completion evidence.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-edge-cases: `Before clearing envs or starting, return existing regular non-symlink bgjob result envs through bgjob wait --max-wait-s 0 or read-result-env; clear only for an explicit new attempt.`


### FINDING_9: Empty present bgjob result env should not fall back to legacy merge input
- **Reviewer(s)**: codex-specialist-testing, dyn-dyn-bgjob-step3
- **Severity**: major
- **Concern**: When the bgjob result file exists but is empty, legacy merge data can still be revived and route on stale state instead of treating the empty primary as authoritative.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-testing: `Only fall back when the bgjob result env is absent or unreadable; keep empty present files authoritative and add a regression test.`
  - From dyn-dyn-bgjob-step3: `Treat “primary exists but has no allowed keys” as missing primary (do not fall back to legacy when the bgjob result path is present), or require legacy fallback only when the bgjob path is absent entirely; add a regression test for empty bgjob result + populated legacy on the rejoin path.`


