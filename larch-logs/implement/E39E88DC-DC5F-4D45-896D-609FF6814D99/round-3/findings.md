### FINDING_1: code-quality: scripts/ship-pr.sh:815-838
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [nit] Triplicated identical bump-branch-guard failure block Edits to stall diagnostics or keys can diverge across copies and regress one branch only Collapse to one helper or single shared failure tail with optional log tag
- **Suggested revision**: Address the concern above.

### FINDING_2: risk-integration: scripts/ship-pr.sh:829-838
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [latent] FORKED_TARGET=true exempts non-fork main/master bump when names align Mis-set FORKED_TARGET allows classify/apply bump on default branch despite incident goal Narrow trust signal or add second invariant so one flag cannot bypass protected-branch bump
- **Suggested revision**: Address the concern above.

### FINDING_3: risk-integration: skills/implement/scripts/step2-implement.sh:299-325
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [latent] main-branch-prohibited only for issue-anchored non-fork runs External Step 2 with neither session-env nor qualifying parent-issue on main still launches implementer Assert tmpdir invariants earlier or broaden guard if all external runs must be blocked on default branch
- **Suggested revision**: Address the concern above.

### FINDING_4: code-quality: scripts/test-implement-structure.sh:45-52
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [nit] Full-sentence grep pin on SKILL.md prose Minor SKILL copyedit breaks structure test though behavior unchanged Assert minimal stable tokens instead of a long prose mirror
- **Suggested revision**: Address the concern above.

### FINDING_5: code-quality: scripts/ship-pr.sh:816-837
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [nit] Identical printf for all guard failures Operators cannot see which sub-condition failed from bump capture alone Add a short reason token to the capture text while keeping STALL_STEP stable
- **Suggested revision**: Address the concern above.

### FINDING_6: [OUT_OF_SCOPE] code-quality: N/A
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [nit] merge-base HEAD..main log empty in this checkout Review used origin/main..HEAD instead None; choose correct base when HEAD is main
- **Suggested revision**: Address the concern above.

### FINDING_7: risk-integration: skills/implement/scripts/step2-implement.sh:253-263
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [latent] emit_bailed exits 0 not nonzero wrapper that treats only nonzero exit as failure may continue after main-branch-prohibited document STATUS=bailed contract or add opt-in nonzero exit for wrappers
- **Suggested revision**: Address the concern above.

### FINDING_8: code-quality: scripts/ship-pr.sh:808-838
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [nit] triplicated stall capture blocks for bump-branch-guard future edits may desynchronize three copies factor one helper for guard failure path
- **Suggested revision**: Address the concern above.

### FINDING_9: [OUT_OF_SCOPE] architecture: scripts/implement-fork-env.md:24-26
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [nit] states FORKED_TARGET not in session-env doc predates guard not introduced by this finding alone update same contract when fixing step2 fork signal source
- **Suggested revision**: Address the concern above.

### FINDING_10: risk-integration: skills/implement/SKILL.md:1038
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [latent] Guard 3 is prose plus grep-only structural test; no behavioral harness for post-dispatch branch assertion. A prompt-side orchestrator could skip the new bullet while CI stays green; wrong-branch work might continue until bump-phase stall. Add a contract/integration test that exercises the branch assertion logic or a thin wrapper script the orchestrator must call.
- **Suggested revision**: Address the concern above.

### FINDING_11: risk-integration: scripts/test-ship-pr.sh:883-935
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [nit] No test asserts bump-branch-guard on --resume-phase bump re-entry. Resume-only regression could reintroduce bump-on-wrong-branch without failing the suite. Add a resume-phase bump harness case that expects STALL_STEP=bump-branch-guard before bump stubs.
- **Suggested revision**: Address the concern above.

### FINDING_12: risk-integration: skills/implement/scripts/test-step2-dispatch.sh:968-1128
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [nit] main-branch-prohibited coverage is Cursor-only despite shared dispatcher gate. A Codex-only refactor could move or drop the gate without failing tests. Mirror one minimal case for --coder codex with a stub launcher.
- **Suggested revision**: Address the concern above.

### FINDING_13: [OUT_OF_SCOPE] risk-integration: skills/implement/scripts/run-step2-dispatch.sh:105
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [latent] Dispatcher mechanical bails use exit 0 and STATUS=bailed KV contract. Callers ignoring stdout and checking only $? mis-handle all mechanical bails; not introduced by this change. Document or harden callers if desired; out of scope for this diff.
- **Suggested revision**: Address the concern above.

### FINDING_14: [OUT_OF_SCOPE] architecture: scripts/ship-pr.sh:1354-1358
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [nit] run_rebase_rebump skips bump-branch-guard by design with an operator invariant comment. Mis-aligned checkout during rebase-rebump remains an operator footgun. Accept as documented tradeoff unless product wants guard duplication.
- **Suggested revision**: Address the concern above.

### FINDING_15: risk-integration: scripts/ship-pr.sh:829-838
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: [latent] FORKED_TARGET=true bypasses protected-name stall when symbolic ref matches BRANCH_NAME with no extra fork evidence. Mis-set or hostile state that sets FORKED_TARGET=true while aligned on main/master still permits bump classify/apply on the default branch despite the new guard for non-fork runs. Add independent fork corroboration or document explicit trust model in SECURITY.md; avoid relying on a single boolean in state.
- **Suggested revision**: Address the concern above.

### FINDING_16: risk-integration: skills/implement/scripts/step2-implement.sh:299-325
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: [latent] main-branch-prohibited only when tmpdir is issue-anchored per parent-issue or session-env presence. Step 2 can still launch an external implementer from main/master when those anchoring files are absent, leaving a narrower guard than unconditional protected-branch denial. Tighten anchoring criteria (e.g. require ISSUE_NUMBER via read-session-env-key.sh) or an explicit implement-only flag if all Step 2 entrypoints must be blocked on default branches.
- **Suggested revision**: Address the concern above.

### FINDING_17: code-quality: skills/implement/scripts/step2-implement.sh:307-309
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: [nit] Awk FS split on parent-issue ISSUE_NUMBER is less robust than read-session-env-key.sh for values containing '='. Rare formatting edge could mis-detect presence of ISSUE_NUMBER though impact is low because only emptiness is tested. Use read-session-env-key.sh for ISSUE_NUMBER extraction from parent-issue.md.
- **Suggested revision**: Address the concern above.

### FINDING_18: [OUT_OF_SCOPE] architecture: scripts/ship-pr.sh:1357-1359
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: [nit] run_rebase_rebump documents absence of bump-branch-guard; behavior is pre-existing by design. Operator must keep checkout/state aligned during rebase-rebump; not introduced by the new guard. No change required unless product wants guard parity in that path.
- **Suggested revision**: Address the concern above.

### FINDING_19: risk-integration: scripts/test-ship-pr.sh:883-905
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [important] bump_branch_guard_main/master likely hit mismatch before the non-forked default-branch prohibition. Removing or breaking the third guard in run_bump_phase (lines 829-838) could still leave tests passing while allowing a classified bump on an aligned local main when FORKED_TARGET is false. Add tests with checkout matching BRANCH_NAME=main or master and FORKED_TARGET false to assert exit 4 and bump-branch-guard via the intended code path.
- **Suggested revision**: Address the concern above.

### FINDING_20: correctness: skills/implement/scripts/step2-implement.sh:293-325
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [latent] Spawn branch uses rev-parse --abbrev-ref; detached HEAD yields SPAWN_BRANCH=HEAD so main-branch-prohibited does not run. Issue-anchored external implementer could run on detached HEAD; post-dispatch SKILL assertion may also be skipped or behave differently vs named branch. Treat HEAD spawn or symbolic-ref failure as fail-closed for issue-anchored runs or align capture with git-current-branch.sh semantics.
- **Suggested revision**: Address the concern above.

### FINDING_21: architecture: scripts/ship-pr.sh:829-832
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [latent] FORKED_TARGET=true alone unlocks bump on main/master when names align. Mis-set state allows version bump classify/apply on default branch without the non-fork stall. Add corroborating fork evidence to state or document as strict operator-only trust with runbook checks.
- **Suggested revision**: Address the concern above.

### FINDING_22: risk-integration: scripts/ship-pr.sh:1354-1360
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [latent] run_rebase_rebump omits bump-branch-guard per new comment. Wrong checkout during rebase/re-bump could reach drop-bump-commit without the new bump-phase invariants. Re-run the same guard at rebump entry or document mandatory manual checkout verification before resume.
- **Suggested revision**: Address the concern above.

### FINDING_23: code-quality: scripts/test-ship-pr.sh:883-905
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [nit] Test descriptions emphasize BRANCH_NAME=main/master while the exercised stall may be branch mismatch only. Readers and future triage may misattribute which guard clause failed. Rename or split tests once aligned-checkout coverage exists.
- **Suggested revision**: Address the concern above.

### FINDING_24: [OUT_OF_SCOPE] risk-integration: scripts/ship-pr.sh (general)
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [latent] Default branch names other than main/master are not covered by bump-branch-guard naming rule. Non-main default branches unchanged vs prior behavior. Accept or track as separate enhancement if needed.
- **Suggested revision**: Address the concern above.

### FINDING_25: correctness: scripts/ship-pr.sh:829-838
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: [important] FORKED_TARGET=true allows bump when BRANCH_NAME is main or master if checkout matches, which is absent from the plan guard snippet and contradicts the feature_description acceptance that BRANCH_NAME main or master must stall before bump. Mis-set FORKED_TARGET=true on a mistaken local main workflow can still reach version bump classify or apply, weakening the acceptance that main or master BRANCH_NAME always stalls before bump. Update the plan and acceptance to explicitly allow the fork carve-out, or remove the carve-out and require fork flows to use non-protected BRANCH_NAME or additional fork evidence beyond state alone.
- **Suggested revision**: Address the concern above.

### FINDING_26: risk-integration: skills/implement/scripts/step2-implement.sh:299-325
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: [latent] main-branch-prohibited only fires for issue-anchored tmpdirs (parent-issue ISSUE_NUMBER or session-env present) and non-forked runs, not unconditionally on main or master as in the plan Guard 2 snippet. External Step 2 on main with a tmpdir that has neither session-env nor parent-issue ISSUE_NUMBER never hits main-branch-prohibited and can still launch the implementer, leaving a gap relative to the unconditional plan guard. Match the plan with unconditional bail on main or master, or document the narrower scope in the plan and add tests for the unanchored path if it must remain allowed.
- **Suggested revision**: Address the concern above.

### FINDING_27: architecture: scripts/ship-pr.sh:812-814
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: [nit] Branch probe uses git symbolic-ref instead of the plan’s git branch --show-current. None for normal symbolic-branch checkouts; only a documentation or plan-snippet mismatch. Accept the substitution in the plan text or revert to branch --show-current if minimum Git version guarantees it.
- **Suggested revision**: Address the concern above.

### FINDING_28: architecture: scripts/test-implement-structure.sh:45-52 skills/implement/references/codex-manifest-schema.md:84 skills/implement/references/codex-manifest-schema.digest.md:33
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: [nit] Extra files beyond the plan’s enumerated list were updated for token and contract pinning. None beyond mild plan checklist drift for reviewers. Name these ancillary files in future plans when adding stable bail tokens or SKILL contract strings.
- **Suggested revision**: Address the concern above.

### FINDING_29: [OUT_OF_SCOPE] architecture: ~<TMPDIR>/round-3/diff.txt
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: [nit] Precomputed diff path was empty while origin or main contained real changes. Automated plan-fidelity workflows that only read that file would see no diff. Fix the launcher or session writer so the cached diff is populated before review.
- **Suggested revision**: Address the concern above.

### FINDING_30: **risk-integration** `scripts/ship-pr.sh:1349-1391` — `run_rebase_rebump` still skips the new `bump-branch-guard` logic (see the explicit operator-invariant comment at `scripts/ship-pr.sh:1357-1359`) yet immediately runs `drop-bump-commit.sh` and later `classify-bump.sh` / `apply-bump.sh` (`scripts/ship-pr.sh:1386-1597`), so the strong alignment enforced at `run_bump_phase` entry (`scripts/ship-pr.sh:807-839`) does not apply on CI-merge recovery paths (`scripts/ship-pr.sh:1720-1757`); a later checkout that no longer matches `read_state BRANCH_NAME` is not caught before rebump work the way resume `--resume-phase bump` is (`scripts/ship-pr.sh:1879-1894`). **Suggested fix:** Either reuse the same `git symbolic-ref` vs `read_state BRANCH_NAME` checks (including the `FORKED_TARGET` carve-out at `scripts/ship-pr.sh:829-838`) at the top of `run_rebase_rebump` before `drop-bump-commit.sh`, or tighten `scripts/ship-pr.md` with a normative recovery checklist that states this path assumes an already-correct named branch and what to do when `HEAD` drift is suspected.
- **Reviewer**: dyn-resume-path-coverage-output.txt
- **Concern**: - **risk-integration** `scripts/ship-pr.sh:1349-1391` — `run_rebase_rebump` still skips the new `bump-branch-guard` logic (see the explicit operator-invariant comment at `scripts/ship-pr.sh:1357-1359`) yet immediately runs `drop-bump-commit.sh` and later `classify-bump.sh` / `apply-bump.sh` (`scripts/ship-pr.sh:1386-1597`), so the strong alignment enforced at `run_bump_phase` entry (`scripts/ship-pr.sh:807-839`) does not apply on CI-merge recovery paths (`scripts/ship-pr.sh:1720-1757`); a later checkout that no longer matches `read_state BRANCH_NAME` is not caught before rebump work the way resume `--resume-phase bump` is (`scripts/ship-pr.sh:1879-1894`). **Suggested fix:** Either reuse the same `git symbolic-ref` vs `read_state BRANCH_NAME` checks (including the `FORKED_TARGET` carve-out at `scripts/ship-pr.sh:829-838`) at the top of `run_rebase_rebump` before `drop-bump-commit.sh`, or tighten `scripts/ship-pr.md` with a normative recovery checklist that states this path assumes an already-correct named branch and what to do when `HEAD` drift is suspected.
- **Suggested revision**: Address the concern above.

### FINDING_31: **risk-integration** `skills/implement/scripts/step2-implement.sh:311-324` — The `main-branch-prohibited` bail only runs when `SPAWN_BRANCH` is `main`/`master` **and** `_forked_target != "true"` **and** `_issue_anchored` is true, where `_issue_anchored` is derived solely from `parent-issue.md` carrying `ISSUE_NUMBER` or the mere presence of `session-env.sh` (`skills/implement/scripts/step2-implement.sh:316-321`), not from byte identity with Step 1 `BRANCH_NAME`; a tmpdir that is meant to be issue-anchored but lacks both signals could still launch the external implementer from `main`/`master`, deferring detection to later gates (`skills/implement/SKILL.md` post-dispatch assertion and `run_bump_phase`). **Suggested fix:** Narrow the condition so any durable issue-anchored marker used elsewhere in `/implement` (for example manifest presence or an explicit env key written before Step 2) also forces `_issue_anchored`, or fail closed on `main`/`master` whenever `ISSUE_NUMBER` is non-empty in any canonical source, not only those two files.
- **Reviewer**: dyn-resume-path-coverage-output.txt
- **Concern**: - **risk-integration** `skills/implement/scripts/step2-implement.sh:311-324` — The `main-branch-prohibited` bail only runs when `SPAWN_BRANCH` is `main`/`master` **and** `_forked_target != "true"` **and** `_issue_anchored` is true, where `_issue_anchored` is derived solely from `parent-issue.md` carrying `ISSUE_NUMBER` or the mere presence of `session-env.sh` (`skills/implement/scripts/step2-implement.sh:316-321`), not from byte identity with Step 1 `BRANCH_NAME`; a tmpdir that is meant to be issue-anchored but lacks both signals could still launch the external implementer from `main`/`master`, deferring detection to later gates (`skills/implement/SKILL.md` post-dispatch assertion and `run_bump_phase`). **Suggested fix:** Narrow the condition so any durable issue-anchored marker used elsewhere in `/implement` (for example manifest presence or an explicit env key written before Step 2) also forces `_issue_anchored`, or fail closed on `main`/`master` whenever `ISSUE_NUMBER` is non-empty in any canonical source, not only those two files.
- **Suggested revision**: Address the concern above.

### FINDING_32: [OUT_OF_SCOPE] The precomputed diff at `<TMPDIR>/round-3/diff.txt` was empty; review used the current tree’s `scripts/ship-pr.sh`, `skills/implement/scripts/step2-implement.sh`, and related tests. Local `HEAD` equals `main` (`46619920`), so `git diff main...HEAD` and `git log $(git merge-base HEAD main)..HEAD --oneline` show no branch-only delta versus `main`; the behavioral review above reflects what is present in the working tree, not a separate feature branch diff.
- **Reviewer**: dyn-resume-path-coverage-output.txt
- **Concern**: - The precomputed diff at `<TMPDIR>/round-3/diff.txt` was empty; review used the current tree’s `scripts/ship-pr.sh`, `skills/implement/scripts/step2-implement.sh`, and related tests. Local `HEAD` equals `main` (`46619920`), so `git diff main...HEAD` and `git log $(git merge-base HEAD main)..HEAD --oneline` show no branch-only delta versus `main`; the behavioral review above reflects what is present in the working tree, not a separate feature branch diff.
- **Suggested revision**: Address the concern above.

### FINDING_33: [OUT_OF_SCOPE] risk-integration
- **Reviewer**: dyn-resume-path-coverage-output.txt
- **Concern**: - **risk-integration** `scripts/ship-pr.sh:916-935` — `scripts/test-ship-pr.sh` exercises `forked bump allows protected default branch name when checkout matches`, documenting that `FORKED_TARGET=true` is an intentional bypass of the non-fork `main`/`master` rejection (`scripts/ship-pr.sh:829-832`); mistaken `FORKED_TARGET=true` remains a configuration foot-gun called out in-script, not a logic bug introduced without awareness.
- **Suggested revision**: Address the concern above.

