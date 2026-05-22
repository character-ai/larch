### FINDING_1: **Important** **correctness** `skills/implement/scripts/step2-implement.sh:299-309` — The new `main-branch-prohibited` path only runs when `read-session-env-key.sh` returns a non-empty `ISSUE_NUMBER` from `$TMPDIR_ARG/session-env.sh`. For normal `/implement`, issue identity is written to `parent-issue.md` after Step 0.5 (`post-tracking-issue.sh`), while sanctioned `session-env.sh` writers (`scripts/write-session-env.sh`, `scripts/persist-post-plan-keys.sh`) never persist `ISSUE_NUMBER`. So in the production layout that motivated #2486, `_session_issue` stays empty, the inner condition never fires, and the external implementer can still launch on `main` unless another layer (e.g. SKILL’s post-dispatch branch assertion) catches it. **Suggested fix:** Tie “issue-anchored” detection to a file that actually exists before Step 2 (e.g. parse `ISSUE_NUMBER` from `$TMPDIR_ARG/parent-issue.md` when present, with an explicit fork bypass keyed off durable fork state rather than a `session-env.sh` key `write-session-env.sh` does not emit), or add a sanctioned session-env writer for `ISSUE_NUMBER` if that is the intended contract; update Test 19 and the schema/docs to match the real on-disk contract.
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: 1. **Important** **correctness** `skills/implement/scripts/step2-implement.sh:299-309` — The new `main-branch-prohibited` path only runs when `read-session-env-key.sh` returns a non-empty `ISSUE_NUMBER` from `$TMPDIR_ARG/session-env.sh`. For normal `/implement`, issue identity is written to `parent-issue.md` after Step 0.5 (`post-tracking-issue.sh`), while sanctioned `session-env.sh` writers (`scripts/write-session-env.sh`, `scripts/persist-post-plan-keys.sh`) never persist `ISSUE_NUMBER`. So in the production layout that motivated #2486, `_session_issue` stays empty, the inner condition never fires, and the external implementer can still launch on `main` unless another layer (e.g. SKILL’s post-dispatch branch assertion) catches it. **Suggested fix:** Tie “issue-anchored” detection to a file that actually exists before Step 2 (e.g. parse `ISSUE_NUMBER` from `$TMPDIR_ARG/parent-issue.md` when present, with an explicit fork bypass keyed off durable fork state rather than a `session-env.sh` key `write-session-env.sh` does not emit), or add a sanctioned session-env writer for `ISSUE_NUMBER` if that is the intended contract; update Test 19 and the schema/docs to match the real on-disk contract.
- **Suggested revision**: Address the concern above.

### FINDING_2: **Nit** **code-quality** `skills/implement/SKILL.md:490-495` — The Phantom Untracked Probe bullet introduces a `§2.2` cross-reference; repo-facing prose elsewhere avoids the section sign for readability. **Suggested fix:** Replace `§2.2` with plain text such as “Section 2.2”.
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: 2. **Nit** **code-quality** `skills/implement/SKILL.md:490-495` — The Phantom Untracked Probe bullet introduces a `§2.2` cross-reference; repo-facing prose elsewhere avoids the section sign for readability. **Suggested fix:** Replace `§2.2` with plain text such as “Section 2.2”.
- **Suggested revision**: Address the concern above.

### FINDING_3: **Nit** **code-quality** `skills/implement/scripts/test-step2-dispatch.sh:1019` — The `fail 19` message says “healthy cursor” while the test deliberately installs a `cursor` stub that must not run, which contradicts the scenario and weakens failure triage. **Suggested fix:** Reword to state that the stubbed `cursor` must not execute (or that `cursor` is intentionally absent/broken in PATH).
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: 3. **Nit** **code-quality** `skills/implement/scripts/test-step2-dispatch.sh:1019` — The `fail 19` message says “healthy cursor” while the test deliberately installs a `cursor` stub that must not run, which contradicts the scenario and weakens failure triage. **Suggested fix:** Reword to state that the stubbed `cursor` must not execute (or that `cursor` is intentionally absent/broken in PATH).
- **Suggested revision**: Address the concern above.

### FINDING_4: correctness: skills/implement/scripts/step2-implement.sh:299-310
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [latent] main-branch-prohibited is conditional on non-empty ISSUE_NUMBER and non-fork session-env Malformed session-env with empty ISSUE_NUMBER on main still dispatches external implementer and can accumulate work on main before other rails Tighten condition or fail-closed for main/master whenever session-env exists and FORKED is not true; add regression test for empty ISSUE_NUMBER
- **Suggested revision**: Address the concern above.

### FINDING_5: risk-integration: skills/implement/scripts/step2-implement.sh:253-263
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [latent] emit_bailed exits 0 with STATUS=bailed; feature text asked for non-zero on branch-creation failure Operators or wrappers that only check $? may treat a successful bail as success Align acceptance docs with STATUS-driven contract or document $? semantics for dispatch
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

### FINDING_10: risk-integration: skills/implement/scripts/step2-implement.sh:299-310
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [latent] main-branch-prohibited is gated on session-env + ISSUE_NUMBER + not forked vs plan’s unconditional guard. Runs without session-env (or empty ISSUE_NUMBER) still launch on main until ship-pr bump guard; fork-on-main untested. Document intent next to the guard; optionally add tests for fork skip and codex path if you want parity with acceptance wording.
- **Suggested revision**: Address the concern above.

### FINDING_11: [OUT_OF_SCOPE] risk-integration: Makefile:50,74
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [nit] test-step2-dispatch is listed in two harness shards, doubling CI runtime for that file. Pre-existing shard layout; amplified slightly as the script grows. Consolidate the target to a single shard in a future CI hygiene change.
- **Suggested revision**: Address the concern above.

### FINDING_12: risk-integration: scripts/ship-pr.sh:807-819
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: [important] bump-branch-guard runs before FORKED_TARGET is read and rejects BRANCH_NAME main/master unconditionally. Forked /implement (--forked) with ship-pr state BRANCH_NAME=main reaches PHASE=bump and stalls with bump-branch-guard even though bump is documented/skipped for forked and the later forked branch would skip classify/apply. Read FORKED_TARGET (or skip the main/master clause when FORKED_TARGET=true) before applying the protected-name rule; keep branch mismatch checks if still desired for forked.
- **Suggested revision**: Address the concern above.

### FINDING_13: code-quality: skills/implement/scripts/test-step2-dispatch.sh:1013-1020
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: [nit] Test 19 failure string mentions healthy cursor while the test relies on a stub that must never run. Misleading diagnostic when the assertion fails. Reword the fail message to describe the stubbed cursor and pre-launcher bail expectation.
- **Suggested revision**: Address the concern above.

### FINDING_14: [OUT_OF_SCOPE] architecture: scripts/ship-pr.sh:807-812
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: [latent] Protected-branch guard only lists main/master. Repos whose production default is not named main/master would not get the BRANCH_NAME-based leg of the guard. Accept as known design or extend the forbidden-name set in a follow-up if product policy requires it.
- **Suggested revision**: Address the concern above.

### FINDING_15: correctness: scripts/ship-pr.sh:810-818
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [latent] Empty BRANCH_NAME and detached HEAD both normalize to empty strings so the bump-branch-guard inequality never fires. Malformed ship-pr state without BRANCH_NAME while on detached HEAD can pass the new guard and still enter bump classify/apply. Treat empty BRANCH_NAME or empty current branch as an immediate stall (or require an explicit opt-out documented in ship-pr.md).
- **Suggested revision**: Address the concern above.

### FINDING_16: risk-integration: skills/implement/scripts/step2-implement.sh:299-310
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [latent] main-branch-prohibited is conditional on session-env presence and non-empty ISSUE_NUMBER. Issue-anchored dispatch with missing/empty session keys or failed key read can still launch on main; failure moves to a later ship-pr stall only. Tighten when the guard arms or add a redundant pre-launcher check tied to a stronger invariant than ISSUE_NUMBER alone.
- **Suggested revision**: Address the concern above.

### FINDING_17: architecture: skills/implement/SKILL.md:1033-1037
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [latent] Post-dispatch branch assertion is documentation-only for the LLM orchestrator. Model non-compliance leaves a window where STATUS=complete is accepted without branch verification despite the new SKILL text. Optionally enforce via a mechanical helper on the same code path that parses dispatcher output.
- **Suggested revision**: Address the concern above.

### FINDING_18: code-quality: skills/implement/scripts/test-step2-dispatch.sh:1017-1019
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [nit] Failure message claims healthy cursor while the test uses a failing stub. Misleading regression output when the assertion fails. Reword the fail message to reflect PATH-stubbed cursor and intent to prove pre-launcher bail.
- **Suggested revision**: Address the concern above.

### FINDING_19: correctness: skills/implement/scripts/step2-implement.sh:299-310
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: [important] Guard 2 is narrower than the plan snippet and acceptance: bail only when session-env exists with non-empty ISSUE_NUMBER and FORKED_TARGET is not true. A Step 2 dispatch on main/master without that session-env file (or with empty ISSUE_NUMBER) still launches the external implementer and can commit on main, reproducing the failure mode the unconditional plan aimed to block. Align docs or acceptance with the conditional contract, or implement the unconditional guard and adjust harnesses to always provide session-env where required.
- **Suggested revision**: Address the concern above.

### FINDING_20: correctness: scripts/test-ship-pr.sh:883-896
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: [nit] Bump-branch-guard tests omit BRANCH_NAME=master despite symmetric handling in ship-pr.sh. Regression could slip if the master branch check were accidentally removed while the main check remained. Add a master-state case or parameterize tests over main and master.
- **Suggested revision**: Address the concern above.

### FINDING_21: [OUT_OF_SCOPE] architecture: feature acceptance vs plan snippet
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: [nit] Acceptance mentions non-zero exit for launcher failure while the plan uses emit_bailed (exit 0). Confusing for reviewers of the issue text only; behavior is internally consistent with emit_bailed. Update the issue acceptance wording to match dispatcher bail semantics.
- **Suggested revision**: Address the concern above.

### FINDING_22: [OUT_OF_SCOPE] architecture: implementation_plan numbered file list
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: [nit] Diff also edits codex-manifest-schema.md and test-step2-dispatch.md. None for code correctness; optional plan hygiene. Extend the tracked file list in the issue if strict traceability is required.
- **Suggested revision**: Address the concern above.

### FINDING_23: **correctness** `scripts/ship-pr.sh:807-818` — When `read_state BRANCH_NAME` yields an empty string (missing key, `BRANCH_NAME=`, or corrupted state) and the checkout is detached so `git branch --show-current` is also empty, the condition `[[ "$_bump_guard_branch" != "$_bump_guard_state_branch" ]]` is false and neither `main` nor `master` matches, so the guard does not stall and the bump phase can run without a reliable branch identity—contrary to the stated edge case that empty `BRANCH_NAME` should stall. **Suggested fix:** Extend the guard to treat an empty `BRANCH_NAME` (and/or an empty current branch when a non-empty `BRANCH_NAME` is required) as an immediate stall, and add a regression test with `BRANCH_NAME=` on a detached HEAD fixture.
- **Reviewer**: dyn-branch-guard-logic-output.txt
- **Concern**: - **correctness** `scripts/ship-pr.sh:807-818` — When `read_state BRANCH_NAME` yields an empty string (missing key, `BRANCH_NAME=`, or corrupted state) and the checkout is detached so `git branch --show-current` is also empty, the condition `[[ "$_bump_guard_branch" != "$_bump_guard_state_branch" ]]` is false and neither `main` nor `master` matches, so the guard does not stall and the bump phase can run without a reliable branch identity—contrary to the stated edge case that empty `BRANCH_NAME` should stall. **Suggested fix:** Extend the guard to treat an empty `BRANCH_NAME` (and/or an empty current branch when a non-empty `BRANCH_NAME` is required) as an immediate stall, and add a regression test with `BRANCH_NAME=` on a detached HEAD fixture.
- **Suggested revision**: Address the concern above.

### FINDING_24: [OUT_OF_SCOPE] The pre-computed diff at `<TMPDIR>/round-1/diff.txt` was empty; review used a read-only `git diff origin/main...HEAD` against the local tree instead.
- **Reviewer**: dyn-branch-guard-logic-output.txt
- **Concern**: - The pre-computed diff at `<TMPDIR>/round-1/diff.txt` was empty; review used a read-only `git diff origin/main...HEAD` against the local tree instead.
- **Suggested revision**: Address the concern above.

### FINDING_25: [OUT_OF_SCOPE] `git log "$(git merge-base HEAD main)"..HEAD --oneline` produced no lines because `HEAD` is `main` and matches the merge-base, so the single commit ahead of `origin/main` is not in that range.
- **Reviewer**: dyn-branch-guard-logic-output.txt
- **Concern**: - `git log "$(git merge-base HEAD main)"..HEAD --oneline` produced no lines because `HEAD` is `main` and matches the merge-base, so the single commit ahead of `origin/main` is not in that range.
- **Suggested revision**: Address the concern above.

### FINDING_26: [OUT_OF_SCOPE] `skills/implement/scripts/step2-implement.sh:299-310` intentionally narrows `main-branch-prohibited` to issue-anchored runs (`session-env.sh`, non-empty `ISSUE_NUMBER`, `FORKED_TARGET` not `true`); runs without `session-env.sh` can still launch on `main`, which matches the new docs and is a deliberate tradeoff rather than a regression from the stricter pseudo-code in the feature text.
- **Reviewer**: dyn-branch-guard-logic-output.txt
- **Concern**: - `skills/implement/scripts/step2-implement.sh:299-310` intentionally narrows `main-branch-prohibited` to issue-anchored runs (`session-env.sh`, non-empty `ISSUE_NUMBER`, `FORKED_TARGET` not `true`); runs without `session-env.sh` can still launch on `main`, which matches the new docs and is a deliberate tradeoff rather than a regression from the stricter pseudo-code in the feature text.
- **Suggested revision**: Address the concern above.

### FINDING_27: **risk-integration** `scripts/ship-pr.sh:1330-1574` — `run_rebase_rebump` still performs `classify-bump.sh` and `apply-bump.sh` without the new `run_bump_phase` branch guard, so the only bump entry point that enforces `read_state BRANCH_NAME` against `git branch --show-current` and rejects `main`/`master` is the initial bump path; after CI-driven rebase/re-bump, a checkout mistake or tooling regression could again apply a version bump on the wrong branch while state still names a feature branch. **Suggested fix:** Extract the bump-branch guard into a shared function (or source a tiny helper) and invoke it at the start of `run_rebase_rebump` immediately after the detached-HEAD check and before `drop-bump-commit.sh` / `apply-bump.sh`, matching `run_bump_phase` semantics.
- **Reviewer**: dyn-state-consistency-output.txt
- **Concern**: - **risk-integration** `scripts/ship-pr.sh:1330-1574` — `run_rebase_rebump` still performs `classify-bump.sh` and `apply-bump.sh` without the new `run_bump_phase` branch guard, so the only bump entry point that enforces `read_state BRANCH_NAME` against `git branch --show-current` and rejects `main`/`master` is the initial bump path; after CI-driven rebase/re-bump, a checkout mistake or tooling regression could again apply a version bump on the wrong branch while state still names a feature branch. **Suggested fix:** Extract the bump-branch guard into a shared function (or source a tiny helper) and invoke it at the start of `run_rebase_rebump` immediately after the detached-HEAD check and before `drop-bump-commit.sh` / `apply-bump.sh`, matching `run_bump_phase` semantics.
- **Suggested revision**: Address the concern above.

### FINDING_28: [OUT_OF_SCOPE] The cached diff at `<TMPDIR>/round-1/diff.txt` was empty and `git log $(git merge-base HEAD main)..HEAD` was empty because this clone’s `HEAD` is `main`; review used the current tree instead of that cache file.
- **Reviewer**: dyn-state-consistency-output.txt
- **Concern**: - The cached diff at `<TMPDIR>/round-1/diff.txt` was empty and `git log $(git merge-base HEAD main)..HEAD` was empty because this clone’s `HEAD` is `main`; review used the current tree instead of that cache file.
- **Suggested revision**: Address the concern above.

### FINDING_29: [OUT_OF_SCOPE] `read_state BRANCH_NAME` at bump time is whatever was written when the state file was first created (`write_initial_state` uses `git rev-parse --abbrev-ref HEAD` in `scripts/ship-pr.sh:244-267`); it is not refreshed on later invocations when the state file already exists (`scripts/ship-pr.sh:305-307`), which is consistent with treating the state file as the run’s contract but means operators must not splice in a mismatched `BRANCH_NAME`.
- **Reviewer**: dyn-state-consistency-output.txt
- **Concern**: - `read_state BRANCH_NAME` at bump time is whatever was written when the state file was first created (`write_initial_state` uses `git rev-parse --abbrev-ref HEAD` in `scripts/ship-pr.sh:244-267`); it is not refreshed on later invocations when the state file already exists (`scripts/ship-pr.sh:305-307`), which is consistent with treating the state file as the run’s contract but means operators must not splice in a mismatched `BRANCH_NAME`.
- **Suggested revision**: Address the concern above.

### FINDING_30: [OUT_OF_SCOPE] `skills/implement/scripts/step2-implement.sh:299-310` only emits `main-branch-prohibited` when `session-env.sh` exists and shows a non-forked issue-anchored run; if that file were missing in a real tmpdir, the Cursor path would not bail here (tests always create `session-env.sh`, e.g. `skills/implement/scripts/test-step2-dispatch.sh:986-989`). That is a narrow residual hole, not introduced by the ship-pr guard itself.
- **Reviewer**: dyn-state-consistency-output.txt
- **Concern**: - `skills/implement/scripts/step2-implement.sh:299-310` only emits `main-branch-prohibited` when `session-env.sh` exists and shows a non-forked issue-anchored run; if that file were missing in a real tmpdir, the Cursor path would not bail here (tests always create `session-env.sh`, e.g. `skills/implement/scripts/test-step2-dispatch.sh:986-989`). That is a narrow residual hole, not introduced by the ship-pr guard itself.
- **Suggested revision**: Address the concern above.

### FINDING_31: **correctness** `scripts/test-ship-pr.sh:883-897` — `run_bump_phase` rejects `BRANCH_NAME=master` as well as `main` in [`scripts/ship-pr.sh`](scripts/ship-pr.sh) (see the `master` comparison in the guard), but the new harness only rewrites state to `BRANCH_NAME=main` and never to `master`, so losing the `master` half of the condition would not fail CI. **Suggested fix:** Add a third scenario (or parameterize the existing one) that sets `BRANCH_NAME=master` via the same `sed` pattern and asserts exit code `4` and `STALL_STEP=bump-branch-guard`.
- **Reviewer**: dyn-test-coverage-output.txt
- **Concern**: - **correctness** `scripts/test-ship-pr.sh:883-897` — `run_bump_phase` rejects `BRANCH_NAME=master` as well as `main` in [`scripts/ship-pr.sh`](scripts/ship-pr.sh) (see the `master` comparison in the guard), but the new harness only rewrites state to `BRANCH_NAME=main` and never to `master`, so losing the `master` half of the condition would not fail CI. **Suggested fix:** Add a third scenario (or parameterize the existing one) that sets `BRANCH_NAME=master` via the same `sed` pattern and asserts exit code `4` and `STALL_STEP=bump-branch-guard`.
- **Suggested revision**: Address the concern above.

### FINDING_32: **correctness** `skills/implement/scripts/test-step2-dispatch.sh:970-1020` — Test 19 correctly matches [`emit_bailed`](skills/implement/scripts/step2-implement.sh) (`STATUS`, `REASON`, `TOOL`, `ORCHESTRATOR_EDIT_AUTHORITY=forbidden` on stdout), but it only builds a repo on `main`; [`step2-implement.sh`](skills/implement/scripts/step2-implement.sh) also treats `master` as a protected spawn branch with no test proving that path emits the same bail envelope. **Suggested fix:** Add a parallel case using `git init -q -b master` (same `session-env.sh` and stub launcher) and assert the same substrings as Test 19.
- **Reviewer**: dyn-test-coverage-output.txt
- **Concern**: - **correctness** `skills/implement/scripts/test-step2-dispatch.sh:970-1020` — Test 19 correctly matches [`emit_bailed`](skills/implement/scripts/step2-implement.sh) (`STATUS`, `REASON`, `TOOL`, `ORCHESTRATOR_EDIT_AUTHORITY=forbidden` on stdout), but it only builds a repo on `main`; [`step2-implement.sh`](skills/implement/scripts/step2-implement.sh) also treats `master` as a protected spawn branch with no test proving that path emits the same bail envelope. **Suggested fix:** Add a parallel case using `git init -q -b master` (same `session-env.sh` and stub launcher) and assert the same substrings as Test 19.
- **Suggested revision**: Address the concern above.

### FINDING_33: [OUT_OF_SCOPE] The pre-computed diff at `<TMPDIR>/round-1/diff.txt` was empty, so this review used the current workspace copies of the listed files instead of that artifact.
- **Reviewer**: dyn-test-coverage-output.txt
- **Concern**: - The pre-computed diff at `<TMPDIR>/round-1/diff.txt` was empty, so this review used the current workspace copies of the listed files instead of that artifact.
- **Suggested revision**: Address the concern above.

### FINDING_34: [OUT_OF_SCOPE] `write_state` / `make_repo` now agree on `feature/test-issue-7` and each bump-guard test uses a fresh `make_tmpdir` + `make_repo` pair, so the scout concern about stale `master`-based assumptions in existing assertions did not surface as a defect in the reviewed tree.
- **Reviewer**: dyn-test-coverage-output.txt
- **Concern**: - `write_state` / `make_repo` now agree on `feature/test-issue-7` and each bump-guard test uses a fresh `make_tmpdir` + `make_repo` pair, so the scout concern about stale `master`-based assumptions in existing assertions did not surface as a defect in the reviewed tree.
- **Suggested revision**: Address the concern above.

### FINDING_35: [OUT_OF_SCOPE] [`step2-implement.sh:299-309`](skills/implement/scripts/step2-implement.sh) gates `main-branch-prohibited` on session-env plus non-empty `ISSUE_NUMBER` and not `FORKED_TARGET=true`, which is narrower than the unconditional snippet in the written plan; that is a product/contract choice rather than a test-scaffolding regression, and Test 19 matches the shipped conditional.
- **Reviewer**: dyn-test-coverage-output.txt
- **Concern**: - [`step2-implement.sh:299-309`](skills/implement/scripts/step2-implement.sh) gates `main-branch-prohibited` on session-env plus non-empty `ISSUE_NUMBER` and not `FORKED_TARGET=true`, which is narrower than the unconditional snippet in the written plan; that is a product/contract choice rather than a test-scaffolding regression, and Test 19 matches the shipped conditional.
- **Suggested revision**: Address the concern above.

