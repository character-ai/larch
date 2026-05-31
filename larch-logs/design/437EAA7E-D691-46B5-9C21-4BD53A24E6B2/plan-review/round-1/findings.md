### FINDING_1:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/review-and-fix/scripts/review-and-fix.sh:564-577
- **Concern**: Follow-up commit block not updated for carryover exclusion. Scenario: After the guard fix lets the primary round commit succeed, pre-existing carryover dirt still makes git status --porcelain --untracked-files=no non-empty. The follow-up path calls stage_round_dirty_paths again; with only carryover left the manifest is empty and stage returns 1, or follow-up commit leaves carryover porcelain and lines 574-577 fail closed. CODER_STATUS=failed and return 2 after a successful primary commit — the #3272 scenario trades one false positive for another.
- **Proposed resolution**: Gate the follow-up block (564) and the post-follow-up porcelain check (574) on non-carryover tracked dirt only, reusing path_is_pre_coder_carryover with round_dir/pre-coder-head.txt. Update review-and-fix.md lines 56-57 to document carryover exclusion in the follow-up contract. Add an orchestrator regression (pre-existing dirty other.txt + coder edits src/main.py, exit 0, CODER_STATUS=applied) or extend the plan test section to require it.

### FINDING_2:
- **Reviewer(s)**: Codex-Arch, Codex-Requirements
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/review-and-fix/scripts/review-and-fix.sh:561-575
- **Concern**: Plan exempts carryover only before the first commit but leaves the post-commit residue check unchanged. Scenario: After the first round commit, the untouched pre-existing dirty path still makes git status --porcelain --untracked-files=no non-empty. The follow-up block then reruns stage_round_dirty_paths and git-commit.sh, but only carryover remains dirty, so the follow-up commit can fail and the original false-positive still ends as CODER_STATUS=failed.
- **Proposed resolution**: Apply the same carryover exclusion to the post-commit residue path: if remaining tracked dirt is only unchanged snapshotted carryover, skip the follow-up and leave it uncommitted; if manifest paths remain dirty, keep the existing follow-up commit; if genuinely-new outside-manifest dirt remains, fail closed. Add an integration-style regression around apply_findings_with_coder, not only the extracted guard.

### FINDING_3:
- **Reviewer(s)**: Codex-Edge
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/review-and-fix/scripts/review-and-fix.sh:552-557
- **Concern**: Carryover skip can commit pre-existing staged dirt. Scenario: The proposed guard skips snapshotted carryover, but git-commit.sh is invoked with no pathspec, so any pre-existing staged carryover outside coder-stage-paths.txt is included in the round commit
- **Proposed resolution**: Scope the round commit to coder-stage-paths.txt, for example via git-commit.sh --only --pathspec-from-file "$stage_manifest", or otherwise unstage/protect outside-manifest carryover before commit

### FINDING_4:
- **Reviewer(s)**: Codex-Edge, Codex-Innovation
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/review-and-fix/scripts/review-and-fix.sh:562-579
- **Concern**: Post-commit residue check still treats allowed carryover as failure. Scenario: After the first scoped coder commit, unchanged pre-existing carryover remains dirty; the existing follow-up block sees tracked porcelain, tries another stage/commit cycle, and can return CODER_STATUS=failed even though the plan intended carryover to remain uncommitted
- **Proposed resolution**: Apply the same carryover exclusion to the post-commit residue path, so follow-up commits run only for non-carryover tracked residue or manifest paths actually dirtied by hooks

### FINDING_5:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/review-and-fix/scripts/review-and-fix.sh:564-577
- **Concern**: Post-commit follow-up still fail-closes on any tracked porcelain; plan only relaxes the pre-commit guard at :552. Scenario: After carryover is skipped at the guard, the first coder commit can succeed, then `git status --porcelain --untracked-files=no` still lists unchanged carryover (e.g. `other.txt`) and lines :574-577 emit `CODER_STATUS=failed` / return `2` — #3272 still blocked in production and any orchestrator test that expects success
- **Proposed resolution**: Apply the same carryover predicate (or a small helper) in the follow-up residue check: enter follow-up only for non-carryover hook/manifest residue; treat carryover-only porcelain as warn-and-continue to `CODER_STATUS=applied`; document in `review-and-fix.md` § post-commit block

### FINDING_6:
- **Reviewer(s)**: Codex-Innovation
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/review-and-fix/scripts/review-and-fix.sh:548-557
- **Concern**: Pre-staged carryover can be committed accidentally. Scenario: If other.txt was already staged before coder dispatch, the proposed guard skips it as carryover, stage_round_dirty_paths adds only manifest paths, then git-commit.sh with no path args commits all staged changes including other.txt
- **Proposed resolution**: Constrain the round commit to manifest paths, for example git-commit.sh --only --pathspec-from-file "$stage_manifest", and add a staged-carryover regression

### FINDING_7:
- **Reviewer(s)**: Codex-Pragmatic
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/review-and-fix/scripts/review-and-fix.sh:562-570
- **Concern**: Plan exempts carryover dirt only in the pre-commit outside-manifest guard, but the post-commit residue re-check still treats the same unchanged carryover as blocking tracked porcelain.. Scenario: With pre-existing other.txt dirt and a real coder edit in src/main.py, the first commit succeeds and leaves other.txt dirty as intended. The follow-up block then sees tracked porcelain, tries to recommit manifest paths that are already committed, git commit has no staged changes, and CODER_STATUS becomes failed.
- **Proposed resolution**: Extend the same carryover exclusion to the post-commit tracked-residue check before attempting the follow-up commit, or only enter the follow-up path when non-carryover tracked residue remains. Add the regression at orchestrator/apply_findings level, not only the extracted guard predicate.

### FINDING_8:
- **Reviewer(s)**: Cursor-Requirements, Cursor-dyn-round-commit-contract
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/review-and-fix/scripts/review-and-fix.sh:564-578
- **Concern**: Post-commit follow-up still fail-closes on leftover tracked porcelain. Scenario: After the guard skips snapshotted carryover and the primary round commit succeeds, carryover paths remain in `git status --porcelain --untracked-files=no`; the #3209 follow-up block still returns `2` (empty-manifest stage failure at 565-572 or the residual check at 574-577), so the #3272 false-positive is not fixed end-to-end
- **Proposed resolution**: Apply the same carryover exclusion to the follow-up entry (564) and the post-follow-up residual check (574-577), or document and implement an explicit allowlist so unchanged carryover does not trigger failure

### FINDING_9:
- **Reviewer(s)**: Cursor-dyn-snapshot-parity
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/review-and-fix/scripts/review-and-fix.sh:564-577
- **Concern**: Post-commit tracked-porcelain follow-up ignores carryover exclusion. Scenario: After the guard fix commits only manifest paths, snapshotted unchanged carryover stays dirty; line 564 still enters follow-up and the block still fail-closes (failed follow-up stage/commit or the line 574-577 residue check), so the round can still end with CODER_STATUS=failed despite the guard fix
- **Proposed resolution**: Apply the same path_is_pre_coder_carryover filter to the follow-up trigger/residue logic (skip follow-up or treat porcelain as clean when only carryover remains), or document and test that this path is out of scope for #3272

### FINDING_10:
- **Reviewer(s)**: Codex-dyn-snapshot-parity
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/review-and-fix/scripts/review-and-fix.sh:548-557; skills/review-and-fix/scripts/review-and-fix.sh:565-568; scripts/git-commit.sh:23-24
- **Concern**: Plan skips snapshotted carryover in the guard but leaves the round commits unscoped, while git-commit.sh commits whatever is already staged when no paths are passed. Scenario: If a pre-coder dirty path was already staged, round_coder_delta_paths excludes it and the proposed guard skips it as carryover, but the subsequent unscoped git-commit.sh call commits that outside-manifest staged path anyway; this breaks the plan claim that carryover stays uncommitted
- **Proposed resolution**: Scope both the primary and follow-up round commits to coder-stage-paths.txt, for example with git-commit.sh --only --pathspec-from-file "$stage_manifest", or fail closed/unstage snapshotted staged carryover before committing; add a staged-carryover regression case so the guard and commit path are tested together

### FINDING_11:
- **Reviewer(s)**: Codex-dyn-round-commit-contract
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/review-and-fix/scripts/review-and-fix.sh:345-349, skills/review-and-fix/scripts/review-and-fix.sh:402-412, skills/review-and-fix/scripts/review-and-fix.sh:557-558, scripts/git-commit.sh:23-24
- **Concern**: 1. [correctness] Warning-only carryover exclusion can still commit pre-existing staged carryover because round commit is not pathscoped. Scenario: capture_round_tracked_paths includes cached paths, so a staged carryover path can be snapshotted and skipped by the proposed guard; stage_round_dirty_paths only adds manifest paths but does not unstage unrelated cached changes; git-commit.sh with no paths commits whatever is already staged
- **Proposed resolution**: Commit the round with the existing scoped pathspec contract, e.g. git-commit.sh --only --pathspec-from-file "$stage_manifest", and add a regression with pre-existing staged carryover proving it remains staged/uncommitted while coder delta commits

### FINDING_12:
- **Reviewer(s)**: Codex-dyn-round-commit-contract
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/review-and-fix/scripts/review-and-fix.sh:562-572, skills/review-and-fix/scripts/review-and-fix.sh:372-387, skills/review-and-fix/scripts/review-and-fix.md:56
- **Concern**: 2. [correctness] Post-commit residue re-check is still raw status-based, so unchanged carryover makes the proposed successful path fail after the primary commit. Scenario: After the primary coder commit leaves unchanged carryover dirty, git status --porcelain --untracked-files=no is still non-empty; the follow-up path reruns stage_round_dirty_paths against pre-coder-head and then attempts a follow-up commit, turning the warning-only carryover case into CODER_STATUS=failed return 2
- **Proposed resolution**: Make the post-commit residue gate carryover-aware as well: only run/fail the follow-up path for non-carryover tracked residue, and add a full round-mode regression beyond the extracted guard test

### FINDING_13:
- **Reviewer(s)**: Codex-dyn-regression-harness
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/review-and-fix/scripts/review-and-fix.sh:345-349,547-557
- **Concern**: Proposed carryover skip does not distinguish unstaged carryover from already-staged carryover. Scenario: capture_round_tracked_paths includes cached paths, and the round commit commits the whole index. If other.txt was dirty and staged before coder dispatch, the proposed guard skips it as unchanged carryover, then git-commit.sh includes it in the coder commit even though it is outside coder-stage-paths.txt.
- **Proposed resolution**: Add the minimum staged-carryover guard: do not exempt paths present in git diff --name-only --cached, or explicitly unstage skipped carryover before git-commit.sh. Add one regression fixture with pre-coder staged other.txt, snapshot present, manifest src/main.py, and assert the guard still fires.
