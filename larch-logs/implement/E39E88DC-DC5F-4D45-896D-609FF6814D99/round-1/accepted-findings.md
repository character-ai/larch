### FINDING_1: **Important** **correctness** `skills/implement/scripts/step2-implement.sh:299-309` — The new `main-branch-prohibited` path only runs when `read-session-env-key.sh` returns a non-empty `ISSUE_NUMBER` from `$TMPDIR_ARG/session-env.sh`. For normal `/implement`, issue identity is written to `parent-issue.md` after Step 0.5 (`post-tracking-issue.sh`), while sanctioned `session-env.sh` writers (`scripts/write-session-env.sh`, `scripts/persist-post-plan-keys.sh`) never persist `ISSUE_NUMBER`. So in the production layout that motivated #2486, `_session_issue` stays empty, the inner condition never fires, and the external implementer can still launch on `main` unless another layer (e.g. SKILL’s post-dispatch branch assertion) catches it. **Suggested fix:** Tie “issue-anchored” detection to a file that actually exists before Step 2 (e.g. parse `ISSUE_NUMBER` from `$TMPDIR_ARG/parent-issue.md` when present, with an explicit fork bypass keyed off durable fork state rather than a `session-env.sh` key `write-session-env.sh` does not emit), or add a sanctioned session-env writer for `ISSUE_NUMBER` if that is the intended contract; update Test 19 and the schema/docs to match the real on-disk contract.
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: 1. **Important** **correctness** `skills/implement/scripts/step2-implement.sh:299-309` — The new `main-branch-prohibited` path only runs when `read-session-env-key.sh` returns a non-empty `ISSUE_NUMBER` from `$TMPDIR_ARG/session-env.sh`. For normal `/implement`, issue identity is written to `parent-issue.md` after Step 0.5 (`post-tracking-issue.sh`), while sanctioned `session-env.sh` writers (`scripts/write-session-env.sh`, `scripts/persist-post-plan-keys.sh`) never persist `ISSUE_NUMBER`. So in the production layout that motivated #2486, `_session_issue` stays empty, the inner condition never fires, and the external implementer can still launch on `main` unless another layer (e.g. SKILL’s post-dispatch branch assertion) catches it. **Suggested fix:** Tie “issue-anchored” detection to a file that actually exists before Step 2 (e.g. parse `ISSUE_NUMBER` from `$TMPDIR_ARG/parent-issue.md` when present, with an explicit fork bypass keyed off durable fork state rather than a `session-env.sh` key `write-session-env.sh` does not emit), or add a sanctioned session-env writer for `ISSUE_NUMBER` if that is the intended contract; update Test 19 and the schema/docs to match the real on-disk contract.
- **Suggested revision**: Address the concern above.


### FINDING_10: risk-integration: skills/implement/scripts/step2-implement.sh:299-310
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [latent] main-branch-prohibited is gated on session-env + ISSUE_NUMBER + not forked vs plan’s unconditional guard. Runs without session-env (or empty ISSUE_NUMBER) still launch on main until ship-pr bump guard; fork-on-main untested. Document intent next to the guard; optionally add tests for fork skip and codex path if you want parity with acceptance wording.
- **Suggested revision**: Address the concern above.


### FINDING_12: risk-integration: scripts/ship-pr.sh:807-819
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: [important] bump-branch-guard runs before FORKED_TARGET is read and rejects BRANCH_NAME main/master unconditionally. Forked /implement (--forked) with ship-pr state BRANCH_NAME=main reaches PHASE=bump and stalls with bump-branch-guard even though bump is documented/skipped for forked and the later forked branch would skip classify/apply. Read FORKED_TARGET (or skip the main/master clause when FORKED_TARGET=true) before applying the protected-name rule; keep branch mismatch checks if still desired for forked.
- **Suggested revision**: Address the concern above.


### FINDING_13: code-quality: skills/implement/scripts/test-step2-dispatch.sh:1013-1020
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: [nit] Test 19 failure string mentions healthy cursor while the test relies on a stub that must never run. Misleading diagnostic when the assertion fails. Reword the fail message to describe the stubbed cursor and pre-launcher bail expectation.
- **Suggested revision**: Address the concern above.


### FINDING_15: correctness: scripts/ship-pr.sh:810-818
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [latent] Empty BRANCH_NAME and detached HEAD both normalize to empty strings so the bump-branch-guard inequality never fires. Malformed ship-pr state without BRANCH_NAME while on detached HEAD can pass the new guard and still enter bump classify/apply. Treat empty BRANCH_NAME or empty current branch as an immediate stall (or require an explicit opt-out documented in ship-pr.md).
- **Suggested revision**: Address the concern above.


### FINDING_16: risk-integration: skills/implement/scripts/step2-implement.sh:299-310
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [latent] main-branch-prohibited is conditional on session-env presence and non-empty ISSUE_NUMBER. Issue-anchored dispatch with missing/empty session keys or failed key read can still launch on main; failure moves to a later ship-pr stall only. Tighten when the guard arms or add a redundant pre-launcher check tied to a stronger invariant than ISSUE_NUMBER alone.
- **Suggested revision**: Address the concern above.


### FINDING_18: code-quality: skills/implement/scripts/test-step2-dispatch.sh:1017-1019
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [nit] Failure message claims healthy cursor while the test uses a failing stub. Misleading regression output when the assertion fails. Reword the fail message to reflect PATH-stubbed cursor and intent to prove pre-launcher bail.
- **Suggested revision**: Address the concern above.


### FINDING_19: correctness: skills/implement/scripts/step2-implement.sh:299-310
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: [important] Guard 2 is narrower than the plan snippet and acceptance: bail only when session-env exists with non-empty ISSUE_NUMBER and FORKED_TARGET is not true. A Step 2 dispatch on main/master without that session-env file (or with empty ISSUE_NUMBER) still launches the external implementer and can commit on main, reproducing the failure mode the unconditional plan aimed to block. Align docs or acceptance with the conditional contract, or implement the unconditional guard and adjust harnesses to always provide session-env where required.
- **Suggested revision**: Address the concern above.


### FINDING_2: **Nit** **code-quality** `skills/implement/SKILL.md:490-495` — The Phantom Untracked Probe bullet introduces a `§2.2` cross-reference; repo-facing prose elsewhere avoids the section sign for readability. **Suggested fix:** Replace `§2.2` with plain text such as “Section 2.2”.
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: 2. **Nit** **code-quality** `skills/implement/SKILL.md:490-495` — The Phantom Untracked Probe bullet introduces a `§2.2` cross-reference; repo-facing prose elsewhere avoids the section sign for readability. **Suggested fix:** Replace `§2.2` with plain text such as “Section 2.2”.
- **Suggested revision**: Address the concern above.


### FINDING_20: correctness: scripts/test-ship-pr.sh:883-896
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: [nit] Bump-branch-guard tests omit BRANCH_NAME=master despite symmetric handling in ship-pr.sh. Regression could slip if the master branch check were accidentally removed while the main check remained. Add a master-state case or parameterize tests over main and master.
- **Suggested revision**: Address the concern above.


### FINDING_23: **correctness** `scripts/ship-pr.sh:807-818` — When `read_state BRANCH_NAME` yields an empty string (missing key, `BRANCH_NAME=`, or corrupted state) and the checkout is detached so `git branch --show-current` is also empty, the condition `[[ "$_bump_guard_branch" != "$_bump_guard_state_branch" ]]` is false and neither `main` nor `master` matches, so the guard does not stall and the bump phase can run without a reliable branch identity—contrary to the stated edge case that empty `BRANCH_NAME` should stall. **Suggested fix:** Extend the guard to treat an empty `BRANCH_NAME` (and/or an empty current branch when a non-empty `BRANCH_NAME` is required) as an immediate stall, and add a regression test with `BRANCH_NAME=` on a detached HEAD fixture.
- **Reviewer**: dyn-branch-guard-logic-output.txt
- **Concern**: - **correctness** `scripts/ship-pr.sh:807-818` — When `read_state BRANCH_NAME` yields an empty string (missing key, `BRANCH_NAME=`, or corrupted state) and the checkout is detached so `git branch --show-current` is also empty, the condition `[[ "$_bump_guard_branch" != "$_bump_guard_state_branch" ]]` is false and neither `main` nor `master` matches, so the guard does not stall and the bump phase can run without a reliable branch identity—contrary to the stated edge case that empty `BRANCH_NAME` should stall. **Suggested fix:** Extend the guard to treat an empty `BRANCH_NAME` (and/or an empty current branch when a non-empty `BRANCH_NAME` is required) as an immediate stall, and add a regression test with `BRANCH_NAME=` on a detached HEAD fixture.
- **Suggested revision**: Address the concern above.


### FINDING_3: **Nit** **code-quality** `skills/implement/scripts/test-step2-dispatch.sh:1019` — The `fail 19` message says “healthy cursor” while the test deliberately installs a `cursor` stub that must not run, which contradicts the scenario and weakens failure triage. **Suggested fix:** Reword to state that the stubbed `cursor` must not execute (or that `cursor` is intentionally absent/broken in PATH).
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: 3. **Nit** **code-quality** `skills/implement/scripts/test-step2-dispatch.sh:1019` — The `fail 19` message says “healthy cursor” while the test deliberately installs a `cursor` stub that must not run, which contradicts the scenario and weakens failure triage. **Suggested fix:** Reword to state that the stubbed `cursor` must not execute (or that `cursor` is intentionally absent/broken in PATH).
- **Suggested revision**: Address the concern above.


### FINDING_31: **correctness** `scripts/test-ship-pr.sh:883-897` — `run_bump_phase` rejects `BRANCH_NAME=master` as well as `main` in [`scripts/ship-pr.sh`](scripts/ship-pr.sh) (see the `master` comparison in the guard), but the new harness only rewrites state to `BRANCH_NAME=main` and never to `master`, so losing the `master` half of the condition would not fail CI. **Suggested fix:** Add a third scenario (or parameterize the existing one) that sets `BRANCH_NAME=master` via the same `sed` pattern and asserts exit code `4` and `STALL_STEP=bump-branch-guard`.
- **Reviewer**: dyn-test-coverage-output.txt
- **Concern**: - **correctness** `scripts/test-ship-pr.sh:883-897` — `run_bump_phase` rejects `BRANCH_NAME=master` as well as `main` in [`scripts/ship-pr.sh`](scripts/ship-pr.sh) (see the `master` comparison in the guard), but the new harness only rewrites state to `BRANCH_NAME=main` and never to `master`, so losing the `master` half of the condition would not fail CI. **Suggested fix:** Add a third scenario (or parameterize the existing one) that sets `BRANCH_NAME=master` via the same `sed` pattern and asserts exit code `4` and `STALL_STEP=bump-branch-guard`.
- **Suggested revision**: Address the concern above.


### FINDING_32: **correctness** `skills/implement/scripts/test-step2-dispatch.sh:970-1020` — Test 19 correctly matches [`emit_bailed`](skills/implement/scripts/step2-implement.sh) (`STATUS`, `REASON`, `TOOL`, `ORCHESTRATOR_EDIT_AUTHORITY=forbidden` on stdout), but it only builds a repo on `main`; [`step2-implement.sh`](skills/implement/scripts/step2-implement.sh) also treats `master` as a protected spawn branch with no test proving that path emits the same bail envelope. **Suggested fix:** Add a parallel case using `git init -q -b master` (same `session-env.sh` and stub launcher) and assert the same substrings as Test 19.
- **Reviewer**: dyn-test-coverage-output.txt
- **Concern**: - **correctness** `skills/implement/scripts/test-step2-dispatch.sh:970-1020` — Test 19 correctly matches [`emit_bailed`](skills/implement/scripts/step2-implement.sh) (`STATUS`, `REASON`, `TOOL`, `ORCHESTRATOR_EDIT_AUTHORITY=forbidden` on stdout), but it only builds a repo on `main`; [`step2-implement.sh`](skills/implement/scripts/step2-implement.sh) also treats `master` as a protected spawn branch with no test proving that path emits the same bail envelope. **Suggested fix:** Add a parallel case using `git init -q -b master` (same `session-env.sh` and stub launcher) and assert the same substrings as Test 19.
- **Suggested revision**: Address the concern above.


### FINDING_4: correctness: skills/implement/scripts/step2-implement.sh:299-310
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [latent] main-branch-prohibited is conditional on non-empty ISSUE_NUMBER and non-fork session-env Malformed session-env with empty ISSUE_NUMBER on main still dispatches external implementer and can accumulate work on main before other rails Tighten condition or fail-closed for main/master whenever session-env exists and FORKED is not true; add regression test for empty ISSUE_NUMBER
- **Suggested revision**: Address the concern above.


### FINDING_6: code-quality: skills/implement/scripts/test-step2-dispatch.sh:1019
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [nit] Failure message claims healthy cursor though stub must never run Confusing CI/debug output when assertion fails Rewrite fail message to match the test intent (main + stub not invoked)
- **Suggested revision**: Address the concern above.


### FINDING_7: code-quality: skills/implement/SKILL.md:490-495
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [nit] New cross-reference uses §2.2 Rendering/accessibility friction in some clients Spell out Section 2.2 or use a plain markdown link
- **Suggested revision**: Address the concern above.


### FINDING_8: risk-integration: skills/implement/SKILL.md:1038
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [important] Post-dispatch branch assertion is SKILL-only; no CI asserts git-current-branch.sh vs BRANCH_NAME or stall tokens. Orchestrator can skip the new step; regression in SKILL text or implementer behavior would not fail CI while acceptance claims machine-visible stall. Add a minimal harness or scripted contract test for the documented shell checks and stall markers, or narrow acceptance to human-enforced steps only.
- **Suggested revision**: Address the concern above.


### FINDING_9: risk-integration: scripts/test-ship-pr.sh:883-896
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [nit] Bump-branch guard tests cover BRANCH_NAME=main and mismatch but not BRANCH_NAME=master. A future edit removing the master conjunct in ship-pr.sh would leave tests green. Mirror the main-state test with BRANCH_NAME=master and identical stall/rc expectations.
- **Suggested revision**: Address the concern above.


