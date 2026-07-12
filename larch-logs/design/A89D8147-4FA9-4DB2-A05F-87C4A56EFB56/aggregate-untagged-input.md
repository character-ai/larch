### FINDING_1:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: major
- **Focus area**: correctness
- **Location**: skills/design/references/finalize-step5.md:90-92
- **Concern**: Step 5c retry docs outside SKILL.md are not in the plan file list. Scenario: The plan adds default completed-result reattachment and a wrapper-only fresh-attempt control, and only lists `skills/design/SKILL.md` for retry wiring. Step 5 still loads `finalize-step5.md` for Step 5c driver routing; that file, plus `validator-failure.md`, `approval-gates.md`, and `decompose-panel.md`, still tell the orchestrator to re-run bare `design-step5c.sh` / `design-step5c.sh --skip-validate` after validator Fix-and-retry, Override, size Override, Gate C return, and split Override. Those retries will get `BGJOB_STATUS=DONE` from the prior refusal envelope and never launch a fresh publish.
- **Proposed resolution**: Add `### UPDATED:` rows for the four reference files (or a single shared retry-authority file they import) and pin every Step 5c re-run path to the wrapper fresh-attempt flag; keep ordinary first entry on default reattachment.

### FINDING_2:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: major
- **Focus area**: correctness
- **Location**: skills/design/scripts/design-step5c.sh:27-28
- **Concern**: Child mode still execs Python, so the wrapper cannot publish adapter merge rows. Scenario: Today child mode ends with `exec python3 ... design step5c`. The plan requires copying the Step 5c status envelope to the adapter-injected `--merge-result-env` and failing closed when required rows are missing. `exec` prevents any post-Python merge publication on pause, refusal, publish-tail, and success paths.
- **Proposed resolution**: Replace child `exec` with a normal Python invocation, then atomically publish `.design-step5c-status.env` (or equivalent rows) to the injected merge path before exiting; mirror the non-exec terminal-publish pattern planned for Step 3.

### FINDING_3:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: major
- **Focus area**: correctness
- **Location**: python/larch/design/design_step5c.py:762-764
- **Concern**: Publish result-env read failure returns without a Step 5c status envelope. Scenario: When `_step5c_safe_publish_env` fails after a publish attempt, `step5c_core` returns 1 without calling `_step5c_write_status`. The shell child then has nothing authoritative to copy into the adapter merge env, so `bgjob wait` can surface `BGJOB_RC=0` with incomplete `PUBLISH_RC` / `PLAN_WRITE_OK` rows and strand validator or refusal recovery.
- **Proposed resolution**: Extend the planned `design_step5c.py` terminal-envelope work to cover this branch: write a complete refusal/failure status envelope (including `PUBLISH_RC`, `PLAN_WRITE_OK`, `PUBLISH_OK`, `CLEANUP_ELIGIBLE=false`) before returning.

### FINDING_4:
- **Reviewer(s)**: Codex-Arch
- **Severity**: major
- **Focus area**: correctness
- **Location**: python/larch/bgjob/cli.py:83-116; python/larch/bgjob/adapt.py:336-362
- **Concern**: Session-env resolution is not propagated to the child. Scenario: Launcher calls provide only --session-env-path, while the thin wrappers no longer source it. The adapter may resolve tmpdir for its JobSpec, but the daemon child inherits no DESIGN_TMPDIR, ISSUE_NUMBER, or REPO and fails before required routing publication.
- **Proposed resolution**: Parse the trusted allowlisted session env once and export the validated child environment before daemon start, or pass equivalent explicit bindings to the child. Test launcher-style invocation with DESIGN_TMPDIR unset.

### FINDING_5:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: major
- **Focus area**: correctness
- **Location**: skills/design/scripts/design-step3-review.sh:313-345
- **Concern**: Step 3 mid-loop resume must invalidate the prior terminal bgjob result before adapt delegation. Scenario: The plan removes wrapper `rm` of `bgjob/design-step3-review.result.env` and relies on adapt default completed-result `DONE` reattachment. MAV, gate-B, and postplan bail-outs leave that file populated; resume fences call `design-step3-review.sh` with `--starting-round` / `--phase` (`approval-gates-gate-b.md`). Adapt would re-emit the stale `NEXT_ACTION=mav|gate-b|postplan-operator` envelope instead of launching a fresh loop child. `--replace-completed-result` is planned only for Step 5c retries.
- **Proposed resolution**: When `STEP3_REVIEW_HAS_RESUME_STATE=true`, delegate through `bgjob adapt` with `--replace-completed-result` (or an equivalent adapter flag). Keep default reattachment for ordinary duplicate invocations and reentry paths that already clear the result via `plan-review step3-state` / `_step3_clear_downstream_sentinels`. Extend `test-design-step3-review.sh` with a completed-result plus resume-argv case that must launch a new child.

### FINDING_6:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: major
- **Focus area**: correctness
- **Location**: skills/design/scripts/design-step3-review.sh:367-407
- **Concern**: Terminal Step 3 child failures must exit 0 after publishing orchestrator routing rows to the adapter merge env. Scenario: Round-1 accepted FINDING_4 requires child-side merge publication for scope-anchor, panel-init, and pause-race exits. The shell child still ends with `exit 1` after `prelaunch-failure` / failed normalize (`plan_review_normalize.py` returns 1 for `panel-init-failed` and `postplan-failed`). `/design` Step 3 requires `BGJOB_RC=0` before parsing `bgjob/design-step3-review.result.env`; non-zero `BGJOB_RC` routes to the failure/stall branch even when `NEXT_ACTION=final-summary:failed-judge-panel` is present.
- **Proposed resolution**: Pin in `design-step3-review.sh` / `design-step3-review.md`: after atomically writing required terminal rows (including `NEXT_ACTION=final-summary:*` when applicable) to the adapter merge path, the child must exit 0. Reserve non-zero child rc for merge-publication failures only. Add harness coverage for missing-scope-anchor and panel-init-failed paths asserting `BGJOB_RC=0` plus the expected `NEXT_ACTION` in the bgjob result env.

### FINDING_7:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: minor
- **Focus area**: risk-integration
- **Location**: skills/design/scripts/design-step3-entry.sh:37-42
- **Concern**: Re-entry result-env clearing depends on a sibling wrapper the plan does not mention. Scenario: Gate C / `--reentry` review relies on `design-step3-entry-state.sh` calling `plan-review step3-state --direct-review-entry`, which unlinks `bgjob/design-step3-review.result.env` via `_step3_clear_downstream_sentinels`. The plan removes the review wrapper’s own stale-result deletion but does not document this prerequisite. A thin `design-step3-review.sh` could regress re-run review into adapt `DONE` reattachment.
- **Proposed resolution**: Add one line to `design-step3-review.md` and `test-design-structure.sh`: reentry must still run `design-step3-entry-state.sh` (or equivalent sentinel clearing) before `bgjob adapt` so a prior terminal result cannot satisfy a fresh re-run review.

### FINDING_8:
- **Reviewer(s)**: Codex-Innovation
- **Severity**: minor
- **Focus area**: risk-integration
- **Location**: Makefile:1308-1329; scripts/residual-bash-paths.txt:96-105; agent-lint.toml:279-307
- **Concern**: New Bash harness is not fully registered. Scenario: The planned `test-design-step3b-tail.sh` may be skipped when a same-named file exists, omitted from Bash linting, or rejected by agent-lint as an unreachable skill script
- **Proposed resolution**: Add the harness to `.PHONY`, `scripts/residual-bash-paths.txt`, and the existing Makefile-only harness exclusions in `agent-lint.toml` 1. **[risk-integration]** Register the planned Step 4 harness across the repository’s test and lint surfaces. Without these entries, `make lint` or the harness target can fail, or the new adapter test can be silently skipped.

### FINDING_9:
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: major
- **Focus area**: correctness
- **Location**: skills/design/scripts/design-step3-review.sh:323-365
- **Concern**: Step 3 mid-loop resume lacks completed-result replacement when delegating to bgjob adapt. Scenario: Gate B, MAV, and postplan-operator paths re-invoke design-step3-review.sh with --starting-round and --phase after a terminal bgjob/design-step3-review.result.env already exists. Today the parent short-circuits to bgjob wait when that file is present; bgjob adapt default policy does the same. The plan only maps --replace-completed-result to Step 5c retries and removes wrapper-side result deletion. Resume then re-emits DONE with stale NEXT_ACTION=gate-b (or similar) instead of launching plan-review run with the new phase, breaking the Gate B post-apply continuation contract in approval-gates-gate-b.md step 10 and violating behave identically acceptance.
- **Proposed resolution**: In design-step3-review.sh parent mode, when STEP3_REVIEW_HAS_RESUME_STATE=true pass --replace-completed-result to bgjob adapt (wrapper-private flag, not forwarded to plan-review run). Keep default reattach for duplicate ordinary invocations. Extend test-design-step3-review.sh and test-design-structure.sh to seed a terminal result env with NEXT_ACTION=gate-b, invoke with --starting-round and --phase awaiting-continuation, and assert adapt emits STARTED (fresh child) rather than DONE reattach.

### FINDING_10:
- **Reviewer(s)**: Codex-Pragmatic
- **Severity**: major
- **Focus area**: correctness
- **Location**: skills/design/scripts/design-step3-review.sh:141-149
- **Concern**: Prior session-rehydration fix is incomplete because adapter resolution occurs after parent-only tmpdir, resume, and pause logic. Scenario: The launcher passes only `--session-env-path`; without wrapper-side resolution, `DESIGN_TMPDIR` remains empty and the wrapper exits before invoking `bgjob adapt`
- **Proposed resolution**: Add a shared trusted resolver before parent-only logic, or retain minimal parent rehydration for Steps 3 and 4

### FINDING_11:
- **Reviewer(s)**: Codex-Pragmatic
- **Severity**: major
- **Focus area**: risk-integration
- **Location**: skills/design/references/finalize-step5.md:90-92
- **Concern**: Prior Step 5c retry fix is incomplete because canonical retry references are not updated. Scenario: Validator, size, assessment, and composition recovery still invoke `design-step5c.sh` without the fresh-attempt flag, so the adapter reattaches the stale refusal result
- **Proposed resolution**: Update all retry owners, including `approval-gates.md`, `finalize-step5.md`, `decompose-panel.md`, and `validator-failure.md`, to pass the private retry control

### FINDING_13:
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: major
- **Focus area**: code-quality
- **Location**: skills/design/references/finalize-step5.md:90-92
- **Concern**: Authoritative Step 5c retry routing docs still call plain `design-step5c.sh` relaunches without the wrapper fresh-attempt flag; the plan only adds a SKILL.md bullet.. Scenario: After validator refusal, size Override, missing-composition Fix-and-retry, or Gate-C assessment repair, a completed terminal Step 5c envelope makes `bgjob adapt` emit `BGJOB_STATUS=DONE` and skip a fresh publish; the orchestrator follows `finalize-step5.md`, not the SKILL bullet alone.
- **Proposed resolution**: Add `### UPDATED:` rows for `skills/design/references/finalize-step5.md`, `skills/design/references/validator-failure.md` (autofix-ok and Fix-and-retry Step 5c paths), `skills/design/references/approval-gates.md`, and `skills/design/references/decompose-panel.md` (size Override) that pin the wrapper argv token and require it on every documented Step 5c re-run.

### FINDING_14:
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: major
- **Focus area**: architecture
- **Location**: skills/design/references/plan-review-runtime.md:63-65
- **Concern**: Step 3 runtime authority still documents wrapper-local registry/result liveness and direct `bgjob start`; the plan does not update it for `bgjob adapt` delegation.. Scenario: `/design` Step 3 loads this file before entry; stale wrapper-lifecycle instructions conflict with the new adapt-owned contract in `design-step3-review.md` and risk reintroducing deleted liveness or stale-result logic during implementation.
- **Proposed resolution**: Add `### UPDATED: skills/design/references/plan-review-runtime.md` stating parent wrappers delegate to `bgjob adapt`, completed results reattach via adapt `DONE`, fresh launch clears `.completed/step-3` only through `--clear-on-fresh`, and orchestrator continuation still requires `bgjob wait` plus `bgjob/design-step3-review.result.env` parsing.

### FINDING_15:
- **Reviewer(s)**: Codex-Requirements
- **Severity**: major
- **Focus area**: correctness
- **Location**: python/larch/state/session_env.py:969-1027
- **Concern**: Prior accepted rehydration fix remains incomplete: adapter-side resolution occurs after required wrapper parent logic. Scenario: The launcher passes `--session-env-path` but does not source it. Removing wrapper sourcing leaves `DESIGN_TMPDIR` unset before resume validation, pause handling, and delegation, so normal launches fail or skip required lifecycle work.
- **Proposed resolution**: Add one trusted pre-wrapper rehydration point, such as the launcher, so parent-only logic receives validated session values before `bgjob adapt` runs.
