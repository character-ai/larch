Normalizing the 41 reviewer inputs into merged findings with severity rules and verbatim revision bullets.


### FINDING_1: Option B follow-up staging scope (`git add -u` vs `git add -A`)
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-security-output.txt, cursor-specialist-edge-cases-output.txt, cursor-specialist-plan-fidelity-output.txt, dyn-plan-residue-behavior-divergence-output.txt
- **Severity**: important
- **Concern**: Follow-up commit staging in `review-and-fix.sh` does not match a single contract: the plan and primary round use `git add -A`, while committed follow-up uses `git add -u`. Reviewers disagree on the fix—`-A` matches plan/primary but may sweep untracked files past a tracked-only porcelain gate; `-u` matches tracked-only triggers but diverges from plan wording and primary staging. Staging drift across Option A, primary round, and follow-up increases inconsistent commit contents and hook-residue handling risk.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Change follow-up to git add -A to match the primary block and plan.
  - From cursor-specialist-security-output.txt: Use git add -u (or path-scoped staging) in follow-up to match trigger scope; add test with untracked fixture present.
  - From cursor-specialist-edge-cases-output.txt: Prefer git add -u for follow-up or test/document -A scope.
  - From cursor-specialist-plan-fidelity-output.txt: Use git add -A on the follow-up path (as in uncommitted tree) and add a test if untracked hook output is possible.
  - From dyn-plan-residue-behavior-divergence-output.txt: Use `git add -A` for the follow-up (with submodule revert already done upstream), or document tracked-only scope explicitly in `review-and-fix.md` and justify why it differs from the primary round commit.

### FINDING_2: Option A pre-rebase fixup needs multi-pass hook handling
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: important
- **Concern**: Pre-rebase fixup in `ship-pr.sh` is single-pass; pre-commit hooks can re-dirty the tree after the fixup commit (same class as Option B hook tests). One pass can leave tracked porcelain non-empty so `drop-bump-commit` Guard 1 returns `DROPPED=false` and `exit_stall` 10 (#3209 failure class at rebase time).
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Add a two-pass fixup loop (as in local working-tree edits), document in ship-pr.md, and add a rebump test with a pre-commit hook.

### FINDING_3: Duplicated dirty-tree commit logic across ship-pr and review-and-fix
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: latent
- **Concern**: Dirty-tree commit logic is duplicated in `ship-pr.sh` and `review-and-fix.sh` with diverging `git add` flags and pass counts. Future fixes at one site (multi-pass, staging scope) may not propagate, reintroducing stalls or inconsistent commit contents.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Keep staging flags aligned within each script; extract a shared helper if a third callsite appears.

### FINDING_4: Rebump / fix-loop tests lack pre-commit hook re-dirty coverage
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt
- **Severity**: important
- **Concern**: Rebump and related harness cases do not install a pre-commit hook that re-dirties after the first fixup commit. Regression in fixup pass count or hook handling would not fail CI despite reproducing the #3209 stall class at rebase time; Option A two-pass behavior is untested when hooks re-modify tracked files.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Add rebump fixture with idempotent pre-commit hook asserting exit 0 and clean tracked tree.
  - From cursor-specialist-correctness-output.txt: Add hook fixture asserting no stall and clean or double-fixup behavior
  - From cursor-specialist-testing-output.txt: Add test-ship-pr fix-loop case with per-commit pre-commit hook.

### FINDING_5: Option B persistent tracked residue vs `CODER_STATUS` / plan contract
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-security-output.txt, cursor-specialist-edge-cases-output.txt, cursor-specialist-plan-fidelity-output.txt, dyn-plan-residue-behavior-divergence-output.txt
- **Severity**: important
- **Concern**: After follow-up, persistent tracked porcelain from non-idempotent hooks conflicts with plan acceptance, failure-mode prose, and shipped behavior. Reviewers report warn-and-continue (`CODER_STATUS=applied`, exit 0) vs fail-closed (`CODER_STATUS=failed`, return 2); dynamic review notes committed `HEAD` is fail-closed while the plan still contains contradictory warn-and-continue vs acceptance bullets. Step 5 may report success with stale `CODER_COMMIT_SHA`, block `/implement` before ship-pr Option A, or defer cleanup to rebase—operators and automation need one aligned contract across code, tests, docs, and plan.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Fail-closed (CODER_STATUS=failed return 2) when porcelain remains after follow-up or update acceptance to match warn-and-continue
  - From cursor-specialist-testing-output.txt: Align acceptance with warn-and-continue or return 2 / CODER_STATUS=failed when porcelain remains after follow-up.
  - From cursor-specialist-security-output.txt: Return 2 / CODER_STATUS=failed when tracked porcelain remains after follow-up.
  - From cursor-specialist-edge-cases-output.txt: Emit failed/return 2 when porcelain remains after follow-up; or omit CODER_COMMIT_SHA and avoid applied on incomplete commits.
  - From cursor-specialist-plan-fidelity-output.txt: Resolve the plan contradiction: either update acceptance to allow warn-and-continue with documented Option A backstop, or keep fail-closed return 2 (HEAD) and align tests/docs.
  - From dyn-plan-residue-behavior-divergence-output.txt: Pick one contract and align all three surfaces—either update the plan/issue acceptance text to document intentional fail-closed Step 5 blocking, or restore warn-and-continue in code to match the plan and rely on Option A as the sole backstop for non-idempotent hooks.
  - From dyn-plan-residue-behavior-divergence-output.txt: Amend the plan artifact (and `review-and-fix.md` exit-code section if needed) so failure-mode and acceptance prose describe the same semantics; do not leave implementers choosing between two authoritative plan statements.
  - From dyn-plan-residue-behavior-divergence-output.txt: If the team reverts to warn-and-continue per plan, change this test to expect exit `0` / `CODER_STATUS=applied` and add a separate assertion that tracked porcelain is non-empty; if fail-closed stays, update the plan text only—tests already encode the stricter contract.

### FINDING_6: `persistent-hook-residue` test does not assert dirty tree / warnings
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt
- **Severity**: important
- **Concern**: The persistent-hook regression test does not assert that the tree stays dirty, that warnings appear, or that `CODER_COMMIT_SHA` mismatches the working tree. A regression to fail-closed, accidental clean tree, or dropped warnings would not fail CI.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Add git status --porcelain --untracked-files=no non-empty assertion (and optional warning grep)
  - From cursor-specialist-testing-output.txt: Assert non-empty tracked porcelain (or documented SHA mismatch) and warn substrings.

### FINDING_7: Pre-rebase fixup `continue` on empty index with dirty porcelain
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: When `git add -u` leaves an empty index but porcelain remains dirty (e.g. skip-worktree or unstagable tracked state), the loop continues through both passes and still hits drop-bump Guard 1 stall without fixup context; Option A may not improve over single-pass stall.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Break after no-op pass or document; optional early warning
  - From cursor-specialist-edge-cases-output.txt: Log unstagable residue; consider one git add -A attempt or explicit operator message before drop-bump.

### FINDING_8: `review-and-fix.md` vs plan vs code exit semantics
- **Reviewer(s)**: cursor-specialist-plan-fidelity-output.txt, dyn-plan-residue-behavior-divergence-output.txt
- **Severity**: important
- **Concern**: Operators read conflicting contracts: plan failure mode #2 (warn-and-continue) vs acceptance (no `applied` with dirty tree) vs `review-and-fix.md` and committed code (fail-closed). Land Option B as one atomic change set so code, tests, and doc exit bullets agree with the chosen plan semantics.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-plan-fidelity-output.txt: Land Option B semantics as one atomic change set: code, tests, and review-and-fix.md exit bullets must agree.

### FINDING_9: `ship-pr.md` omits two-pass pre-rebase fixup loop
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Severity**: nit
- **Concern**: Documentation describes single-pass pre-rebase fixup while implementation (including uncommitted two-pass loop) can run two passes when hooks re-dirty after the first fixup commit; operators miss the behavior when diagnosing duplicate fixup commits.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Document two-pass behavior per ship-pr.sh:2856-2875
  - From cursor-specialist-edge-cases-output.txt: Update ship-pr.md to describe two-pass hook handling.
  - From cursor-specialist-plan-fidelity-output.txt: Document the two-pass loop in ship-pr.md or revert to single-pass if minimal plan scope is required.

### FINDING_10: Asymmetric retry depth (ship-pr two-pass vs review-and-fix one follow-up)
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: `ship-pr` may run two pre-rebase fixup passes while round mode has only one follow-up; hook re-dirties on every commit can leave residue and `applied` long before rebase Option A runs.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Add second follow-up in round mode or enforce earlier tracked cleanup before push.

### FINDING_11: `run_rebase_rebump` auto-commits all dirty tracked files before drop-bump
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: important
- **Concern**: Partial or unreviewed tracked edits can be silently committed under a generic chore subject and proceed toward rebase/force-push instead of stalling.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Log staged paths; restrict fixup paths or run checks before push; stall when fixup touches non-log paths.

### FINDING_12: Follow-up commit does not re-run submodule revert/scrub
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: latent
- **Concern**: A hook re-touching submodule paths after primary revert could allow submodule changes into the follow-up commit when staging with `git add -A` or broad adds.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Re-run submodule revert before follow-up or stage with git add -u excluding submodule paths.

### FINDING_13: No test for staged-only dirty tree at rebase drop site
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: latent
- **Concern**: `git add -u` / index-only dirty state could skip fixup while porcelain guard still fires, causing stall without regression signal in CI.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Add staged-only fixture and assert fixup commit + exit 0.

### FINDING_14: Rebump version-fixture setup duplicated in tests
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: ~130 lines of rebump version-fixture setup duplicate `rebump_changelog_commit_shape`, increasing maintenance and copy-paste risk when bump/changelog fixtures change.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Extract _make_rebump_version_fixture helper parameterized by version and optional dirty file.

### FINDING_15: `rebump_fixup_commit_fail_stalls` omits stale bump on branch
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: Test validates Guard 1 dirty-tree stall only, not the combined stale-bump + dirty-tree production scenario from #3208.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Reuse bump-on-branch setup from rebump_dirty_tracked_fixup; stub git-commit.sh fixup failure only.

### FINDING_16: `rebump_fixup_commit_fail_stalls` fragile log grep assertions
- **Reviewer(s)**: dyn-stall-exit-code-trace-output.txt
- **Severity**: important
- **Concern**: Exit 4 / `STALL_STEP=10` are reachable and correct, but the follow-on grep searches only stdout and the first `ship-pr-fail-rebase-*.log` while fixup failure and Guard-1 text may land in later captures or `execution-issues.md`, so the case can fail `ok` even when stall behavior is correct.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-stall-exit-code-trace-output.txt: Drop the fragile dual-grep or scan all `$tmp/ship-pr-fail-rebase-*.log` (and/or `$tmp/execution-issues.md`); keep `assert_rc 4`, `STALL_STEP=10`, `EXIT_CODE=4`, and optionally stdout `⛔ ship-pr: stalled at step 10`.

### FINDING_17: Plan acceptance / persistent-hook test signal thin
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: nit
- **Concern**: Happy-path plan tests exist but persistent-hook failure-mode assertions are thin; acceptance vs failure-mode ambiguity may ship without operator-visible test signal.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Strengthen persistent-hook test or document acceptance change explicitly.

### FINDING_18: `make lint` / relevant-checks not verified for merge
- **Reviewer(s)**: cursor-specialist-plan-fidelity-output.txt
- **Severity**: latent
- **Concern**: Reviewer did not run `bash scripts/relevant-checks.sh`; merge may fail CI or pre-commit despite plan-complete implementation.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-plan-fidelity-output.txt: Run bash scripts/relevant-checks.sh before merge.

### OOS_1: [OUT_OF_SCOPE] Pre-existing rebump fixture duplication before this branch
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: Pre-existing rebump tests already duplicate large fixture blocks before this change; pattern predates #3209 work—not introduced by this branch.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Consider broader fixture extraction separately from this PR.

### OOS_2: [OUT_OF_SCOPE] Fix-loop harness section CI duration / flake risk
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: nit
- **Concern**: Fix-loop harness section is already large; new cases add shard 14 time and may slow or flake shared runners.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Monitor harness-timer; split section if duration regresses.

### OOS_3: [OUT_OF_SCOPE] Primary round `git add -A` untracked-sweep class pre-existing
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: latent
- **Concern**: Primary round commit already used `git add -A`; same untracked-sweep class as follow-up; pre-existing on branch.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Align primary and follow-up staging policy in a separate change if desired.

### OOS_4: [OUT_OF_SCOPE] Uncommitted WIP reverts Option B to warn-and-continue
- **Reviewer(s)**: dyn-plan-residue-behavior-divergence-output.txt
- **Severity**: important
- **Concern**: Uncommitted working-tree edits (not in precomputed `diff.txt` / `HEAD`) revert Option B to warn-and-continue while `HEAD` is fail-closed—aligns with one plan bullet but violates acceptance and leaves doc/code/test inconsistent with WIP; resolve before merge.
- **Suggested revisions (informational for voters; coder decides)**:
  - (dyn-plan-residue-behavior-divergence-output.txt provided concern only; no separate fix bullet beyond resolving before merge.)

### OOS_5: [OUT_OF_SCOPE] Uncommitted two-pass `ship-pr.sh` not in precomputed diff
- **Reviewer(s)**: dyn-plan-residue-behavior-divergence-output.txt
- **Severity**: latent
- **Concern**: Uncommitted `scripts/ship-pr.sh` adds a two-pass pre-rebase fixup loop; `HEAD`/diff has single pass—reasonable for idempotent hooks but undocumented on branch and outside precomputed diff.
- **Suggested revisions (informational for voters; coder decides)**:
  - (dyn-plan-residue-behavior-divergence-output.txt provided concern only; document or land with FINDING_9 work.)

### OOS_6: [OUT_OF_SCOPE] Option A on `HEAD` — no additional architecture findings
- **Reviewer(s)**: dyn-plan-residue-behavior-divergence-output.txt
- **Severity**: nit
- **Concern**: Option A on `HEAD` matches plan best-effort / fall-through-to-Guard-1 design; dirty-tree and fixup-fail stall tests are consistent—no further architecture findings for that layer.
- **Suggested revisions (informational for voters; coder decides)**:
  - (No fix direction; informational scout closure only.)
