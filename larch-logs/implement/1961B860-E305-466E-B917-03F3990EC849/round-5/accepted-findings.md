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


### FINDING_17: Plan acceptance / persistent-hook test signal thin
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: nit
- **Concern**: Happy-path plan tests exist but persistent-hook failure-mode assertions are thin; acceptance vs failure-mode ambiguity may ship without operator-visible test signal.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Strengthen persistent-hook test or document acceptance change explicitly.


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


### FINDING_8: `review-and-fix.md` vs plan vs code exit semantics
- **Reviewer(s)**: cursor-specialist-plan-fidelity-output.txt, dyn-plan-residue-behavior-divergence-output.txt
- **Severity**: important
- **Concern**: Operators read conflicting contracts: plan failure mode #2 (warn-and-continue) vs acceptance (no `applied` with dirty tree) vs `review-and-fix.md` and committed code (fail-closed). Land Option B as one atomic change set so code, tests, and doc exit bullets agree with the chosen plan semantics.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-plan-fidelity-output.txt: Land Option B semantics as one atomic change set: code, tests, and review-and-fix.md exit bullets must agree.


