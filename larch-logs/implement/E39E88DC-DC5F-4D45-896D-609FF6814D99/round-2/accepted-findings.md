### FINDING_1: code-quality: scripts/ship-pr.md:72
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [important] bump-branch-guard prose omits FORKED_TARGET carve-out present in ship-pr.sh. Readers assume forked runs cannot use default branch names; runbooks diverge from tested ship-pr.sh behavior. Document fork exception alongside mismatch/empty rules.
- **Suggested revision**: Address the concern above.


### FINDING_11: risk-integration: scripts/ship-pr.sh:827-833
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [latent] FORKED_TARGET=true allows bump phase on default branch name Wrong FORKED_TARGET in state allows version bump work on main Extra validation or document trust model for FORKED_TARGET carve-out
- **Suggested revision**: Address the concern above.


### FINDING_13: risk-integration: scripts/ship-pr.md:72
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [important] bump-branch-guard docs omit FORKED_TARGET=true exception present in ship-pr.sh Forked workflow on default branch name matches state and checkout but readers of ship-pr.md believe bump always stalls on main/master Document fork exception when BRANCH_NAME is main/master and FORKED_TARGET=true matches implementation
- **Suggested revision**: Address the concern above.


### FINDING_14: risk-integration: skills/implement/references/codex-manifest-schema.md:84
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [important] main-branch-prohibited bail description mismatches step2-implement.sh (parent-issue path; session-env presence) Integrators or tooling encode wrong preconditions; test 19b behavior contradicts published contract Rewrite bullet to match code: main/master spawn; not forked; parent-issue ISSUE_NUMBER or session-env file present
- **Suggested revision**: Address the concern above.


### FINDING_15: risk-integration: skills/implement/scripts/step2-implement.md:61
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [important] Same contract drift as codex-manifest-schema for main-branch-prohibited Operators rely on step2-implement.md and mis-configure harnesses or diagnostics Align prose with step2-implement.sh and reference test 19b
- **Suggested revision**: Address the concern above.


### FINDING_16: risk-integration: skills/implement/references/codex-manifest-schema.digest.md:33
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [important] Digest summary wrong for main-branch-prohibited vs implementation Short schema used for quick audits spreads incorrect rule Mirror corrected full-schema wording
- **Suggested revision**: Address the concern above.


### FINDING_18: risk-integration: skills/implement/scripts/test-step2-dispatch.sh:916-931
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [latent] No step2 harness proving FORKED_TARGET=true allows main/master spawn Fork bypass could be removed or inverted without test failure Add forked spawn test mirroring bump_forked_main_ok semantics for step2
- **Suggested revision**: Address the concern above.


### FINDING_19: code-quality: skills/implement/scripts/test-step2-dispatch.md:36
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [nit] Numbered test spec bullet 19 omits 19a/19b scenarios documented only in shell comments Future editors may drop 19a/19b coverage thinking it is unspecified Extend markdown bullet list to cover master and parent-issue cases
- **Suggested revision**: Address the concern above.


### FINDING_2: code-quality: skills/implement/scripts/step2-implement.sh:299-324;skills/implement/scripts/step2-implement.md:61;skills/implement/references/codex-manifest-schema.md:84;skills/implement/references/codex-manifest-schema.digest.md:33
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [important] Dispatcher issue-anchoring predicate (session-env file OR parent-issue ISSUE_NUMBER) and parent-issue-only path disagree with normative bail-token text requiring session-env ISSUE_NUMBER. Schema/dispatcher docs mis-state when main-branch-prohibited fires; digest readers under-test the real predicate. Align all three docs with code and test 19b.
- **Suggested revision**: Address the concern above.


### FINDING_21: risk-integration: skills/implement/scripts/step2-implement.md:61; skills/implement/references/codex-manifest-schema.md:84; skills/implement/references/codex-manifest-schema.digest.md:33
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [important] Docs and digest describe main-branch-prohibited as requiring non-empty ISSUE_NUMBER in session-env, but step2-implement.sh treats any present session-env.sh (or parent-issue ISSUE_NUMBER) as issue-anchored; test 19b exercises parent-issue without session ISSUE_NUMBER. Consumers read schema/docs and believe bail cannot happen when ISSUE_NUMBER is absent from session-env, or miss that parent-issue alone triggers it; debugging and harness design diverge from runtime. Update step2-implement.md, codex-manifest-schema.md, and digest.md so the bail predicate matches step2-implement.sh and the tests.
- **Suggested revision**: Address the concern above.


### FINDING_25: **correctness** `scripts/ship-pr.sh:812` — The bump guard resolves the checked-out branch with `git branch --show-current`, which only exists in Git 2.22+; on older Git the command fails, stderr is discarded, and `|| echo ""` forces an empty current name so the first guard (`-z "$_bump_guard_branch"`) always stalls as `bump-branch-guard`, which is easy to misread as detached HEAD or bad state rather than an unsupported Git probe. The same repo already standardizes on `git symbolic-ref --short HEAD` in `scripts/git-current-branch.sh` for broader Git compatibility. **Suggested fix:** Replace the probe with `git symbolic-ref -q --short HEAD 2>/dev/null || echo ""` (or shell out to `git-current-branch.sh` and parse `BRANCH=`) so the guard matches that contract and fails only for real detached/invalid worktrees.
- **Reviewer**: dyn-bash-portability-output.txt
- **Concern**: - **correctness** `scripts/ship-pr.sh:812` — The bump guard resolves the checked-out branch with `git branch --show-current`, which only exists in Git 2.22+; on older Git the command fails, stderr is discarded, and `|| echo ""` forces an empty current name so the first guard (`-z "$_bump_guard_branch"`) always stalls as `bump-branch-guard`, which is easy to misread as detached HEAD or bad state rather than an unsupported Git probe. The same repo already standardizes on `git symbolic-ref --short HEAD` in `scripts/git-current-branch.sh` for broader Git compatibility. **Suggested fix:** Replace the probe with `git symbolic-ref -q --short HEAD 2>/dev/null || echo ""` (or shell out to `git-current-branch.sh` and parse `BRANCH=`) so the guard matches that contract and fails only for real detached/invalid worktrees.
- **Suggested revision**: Address the concern above.


### FINDING_29: **correctness** `scripts/ship-pr.md:72-72` — The `bump-branch-guard` invariant says bump stalls whenever `BRANCH_NAME` is `main` or `master` or differs from the current branch, but `run_bump_phase` in `scripts/ship-pr.sh` only treats `main`/`master` in state as fatal when `read_state FORKED_TARGET` is not `true` (after empty-name and mismatch checks), so forked runs can still pass the bump phase with `BRANCH_NAME` and checkout both on the default branch, as exercised by `scripts/test-ship-pr.sh` around the `bump_forked_main_ok` case. **Suggested fix:** Amend the bullet to state explicitly that the `main`/`master` `BRANCH_NAME` rule is waived when `FORKED_TARGET=true` and the current branch still matches `BRANCH_NAME`, so the doc matches the state machine and tests.
- **Reviewer**: dyn-stall-contract-output.txt
- **Concern**: - **correctness** `scripts/ship-pr.md:72-72` — The `bump-branch-guard` invariant says bump stalls whenever `BRANCH_NAME` is `main` or `master` or differs from the current branch, but `run_bump_phase` in `scripts/ship-pr.sh` only treats `main`/`master` in state as fatal when `read_state FORKED_TARGET` is not `true` (after empty-name and mismatch checks), so forked runs can still pass the bump phase with `BRANCH_NAME` and checkout both on the default branch, as exercised by `scripts/test-ship-pr.sh` around the `bump_forked_main_ok` case. **Suggested fix:** Amend the bullet to state explicitly that the `main`/`master` `BRANCH_NAME` rule is waived when `FORKED_TARGET=true` and the current branch still matches `BRANCH_NAME`, so the doc matches the state machine and tests.
- **Suggested revision**: Address the concern above.


### FINDING_30: **correctness** `skills/implement/scripts/step2-implement.md:61-61` — The bail description ties `main-branch-prohibited` to `session-env.sh` existing with non-empty `ISSUE_NUMBER`, but `step2-implement.sh` sets `_issue_anchored` from a non-empty `ISSUE_NUMBER` in `parent-issue.md` even when `session-env.sh` is absent, and treats the mere presence of `session-env.sh` as sufficient without verifying `ISSUE_NUMBER` is non-empty. **Suggested fix:** Rewrite the sentence to match the real predicates (`parent-issue.md` `ISSUE_NUMBER` **or** `session-env.sh` present, `FORKED_TARGET` not `true`, spawn branch `main`/`master`) or tighten the script to match the documented stricter session-env rule.
- **Reviewer**: dyn-stall-contract-output.txt
- **Concern**: - **correctness** `skills/implement/scripts/step2-implement.md:61-61` — The bail description ties `main-branch-prohibited` to `session-env.sh` existing with non-empty `ISSUE_NUMBER`, but `step2-implement.sh` sets `_issue_anchored` from a non-empty `ISSUE_NUMBER` in `parent-issue.md` even when `session-env.sh` is absent, and treats the mere presence of `session-env.sh` as sufficient without verifying `ISSUE_NUMBER` is non-empty. **Suggested fix:** Rewrite the sentence to match the real predicates (`parent-issue.md` `ISSUE_NUMBER` **or** `session-env.sh` present, `FORKED_TARGET` not `true`, spawn branch `main`/`master`) or tighten the script to match the documented stricter session-env rule.
- **Suggested revision**: Address the concern above.


### FINDING_31: **correctness** `skills/implement/references/codex-manifest-schema.md:84-84` — The `main-branch-prohibited` token description only mentions `session-env.sh` with non-empty `ISSUE_NUMBER` and omits the `parent-issue.md` path and the “session-env file exists” predicate that does not actually require a non-empty `ISSUE_NUMBER`. **Suggested fix:** Mirror the authoritative conditions from `step2-implement.sh` (same as above) so schema consumers do not mis-parse when the bail fires from parent-issue-only or from an empty-`ISSUE_NUMBER` session-env file.
- **Reviewer**: dyn-stall-contract-output.txt
- **Concern**: - **correctness** `skills/implement/references/codex-manifest-schema.md:84-84` — The `main-branch-prohibited` token description only mentions `session-env.sh` with non-empty `ISSUE_NUMBER` and omits the `parent-issue.md` path and the “session-env file exists” predicate that does not actually require a non-empty `ISSUE_NUMBER`. **Suggested fix:** Mirror the authoritative conditions from `step2-implement.sh` (same as above) so schema consumers do not mis-parse when the bail fires from parent-issue-only or from an empty-`ISSUE_NUMBER` session-env file.
- **Suggested revision**: Address the concern above.


### FINDING_32: **architecture** `scripts/ship-pr.sh:1343-1587` — `run_rebase_rebump` still runs `drop-bump-commit.sh`, `rebase-push.sh`, `git-sync-local-main.sh`, and then `classify-bump.sh` / `apply-bump.sh` without reusing the `run_bump_phase` branch gate at `scripts/ship-pr.sh:807-833`, so the deliberate “no guard in `run_rebase_rebump`” split leaves one CI-rebump path where a mistaken checkout (still a symbolic ref, so not caught by the detached-HEAD check at `scripts/ship-pr.sh:1361-1368`) could diverge from `read_state BRANCH_NAME` without the early `bump-branch-guard` failure mode that now exists for the primary bump entry. **Suggested fix:** Factor the `run_bump_phase` opening checks into a small shared helper and call it at the start of `run_rebase_rebump` before `drop-bump-commit.sh`, or document this as an accepted operator-only invariant and add a one-line comment next to the re-bump block pointing at `run_bump_phase`’s guard as the canonical policy.
- **Reviewer**: dyn-guard-bypass-output.txt
- **Concern**: - **architecture** `scripts/ship-pr.sh:1343-1587` — `run_rebase_rebump` still runs `drop-bump-commit.sh`, `rebase-push.sh`, `git-sync-local-main.sh`, and then `classify-bump.sh` / `apply-bump.sh` without reusing the `run_bump_phase` branch gate at `scripts/ship-pr.sh:807-833`, so the deliberate “no guard in `run_rebase_rebump`” split leaves one CI-rebump path where a mistaken checkout (still a symbolic ref, so not caught by the detached-HEAD check at `scripts/ship-pr.sh:1361-1368`) could diverge from `read_state BRANCH_NAME` without the early `bump-branch-guard` failure mode that now exists for the primary bump entry. **Suggested fix:** Factor the `run_bump_phase` opening checks into a small shared helper and call it at the start of `run_rebase_rebump` before `drop-bump-commit.sh`, or document this as an accepted operator-only invariant and add a one-line comment next to the re-bump block pointing at `run_bump_phase`’s guard as the canonical policy.
- **Suggested revision**: Address the concern above.


### FINDING_33: **architecture** `skills/implement/scripts/step2-implement.sh:164-193` vs `skills/implement/scripts/step2-implement.sh:293-324` and `skills/implement/SKILL.md:1038-1040` — `STATUS=claude_fallback` is emitted and the script exits before `REPO_ROOT` resolution and before `SPAWN_BRANCH_FILE` / `main-branch-prohibited` logic, and §2.2’s `git-current-branch.sh` vs `BRANCH_NAME` assertion is explicitly scoped to `STATUS=complete` only, so the Cursor/Codex-style “fail before external work” and “fail right after external `complete`” gates never run on the Claude-fallback path; wrong-branch work is only forced to fail at `ship-pr` bump time via `scripts/ship-pr.sh:807-833` if state `BRANCH_NAME` stayed correct. **Suggested fix:** Add a documented pre–Step 3 (or pre–Step 4) branch assertion for `claude_fallback` mirroring §2.2 so wrong-branch edits are rejected before the implementation commit, or explicitly state in `skills/implement/SKILL.md` that bump-phase enforcement is the sole backstop for `claude_fallback`.
- **Reviewer**: dyn-guard-bypass-output.txt
- **Concern**: - **architecture** `skills/implement/scripts/step2-implement.sh:164-193` vs `skills/implement/scripts/step2-implement.sh:293-324` and `skills/implement/SKILL.md:1038-1040` — `STATUS=claude_fallback` is emitted and the script exits before `REPO_ROOT` resolution and before `SPAWN_BRANCH_FILE` / `main-branch-prohibited` logic, and §2.2’s `git-current-branch.sh` vs `BRANCH_NAME` assertion is explicitly scoped to `STATUS=complete` only, so the Cursor/Codex-style “fail before external work” and “fail right after external `complete`” gates never run on the Claude-fallback path; wrong-branch work is only forced to fail at `ship-pr` bump time via `scripts/ship-pr.sh:807-833` if state `BRANCH_NAME` stayed correct. **Suggested fix:** Add a documented pre–Step 3 (or pre–Step 4) branch assertion for `claude_fallback` mirroring §2.2 so wrong-branch edits are rejected before the implementation commit, or explicitly state in `skills/implement/SKILL.md` that bump-phase enforcement is the sole backstop for `claude_fallback`.
- **Suggested revision**: Address the concern above.


### FINDING_4: code-quality: scripts/test-implement-structure.sh:45-48
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [nit] Brittle substring greps over SKILL.md orchestration prose. Rewording Step 2.2 breaks CI without functional change. Use stable sentinels or anchor on script identifiers plus minimal tokens.
- **Suggested revision**: Address the concern above.


### FINDING_5: risk-integration: scripts/ship-pr.sh:827-832
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [latent] FORKED_TARGET=true bypasses protected BRANCH_NAME check when names match. Mis-set FORKED_TARGET could again permit bump/commits on default branch. Document threat model; optionally require additional fork-only evidence before bypass.
- **Suggested revision**: Address the concern above.


### FINDING_7: correctness: skills/implement/references/codex-manifest-schema.md:84 (+ digest.md:33, step2-implement.md:61)
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [important] Schema/digest/step2-implement.md mis-describe main-branch-prohibited vs step2-implement.sh:311-324 Operator or generator trusts schema: expects session-env ISSUE_NUMBER and no bail with only parent-issue.md; or expects no bail when session-env lacks ISSUE_NUMBER despite file existing Rewrite bail docs to match code: parent-issue ISSUE_NUMBER= OR session-env file exists; FORKED_TARGET from session-env when present
- **Suggested revision**: Address the concern above.


### FINDING_8: correctness: scripts/ship-pr.md:72
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [important] Doc says main/master BRANCH_NAME always stalls; code exempts FORKED_TARGET=true Reader mis-configures or mis-diagnoses forked bump on default branch name Doc: add unless FORKED_TARGET=true to match ship-pr.sh:827-833
- **Suggested revision**: Address the concern above.


### FINDING_9: code-quality: skills/implement/scripts/test-step2-dispatch.md:36
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [nit] Test catalog bullet 19 omits 19a/19b coverage Future contributors may not know master and parent-issue paths are pinned Extend bullet 19 to document 19a and 19b
- **Suggested revision**: Address the concern above.


