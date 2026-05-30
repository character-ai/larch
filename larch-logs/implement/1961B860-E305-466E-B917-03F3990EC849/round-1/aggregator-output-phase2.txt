Normalizing the supplied reviewer findings into a merged structured list per the aggregator rules.
### FINDING_1: Round mode returns CODER_STATUS=applied when tracked residue remains after follow-up
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt, cursor-specialist-plan-fidelity-output.txt, cursor-specialist-security-output.txt
- **Severity**: important
- **Concern**: After the primary round commit, `review-and-fix.sh` re-checks tracked porcelain and may attempt a follow-up commit; if that commit fails or tracked dirt persists, the script still emits `CODER_STATUS=applied` (and may still print `CODER_COMMIT_SHA` for the primary commit). Step 5 / parent orchestration treat `applied` as complete while fixes may remain only in the working tree until ship-pr Option A, rebase fixup, or push recovery—masking a non-idempotent hook or failed follow-up.
- **Suggested revisions (informational for voters; coder decides)**:

### FINDING_2: Follow-up commit uses git add -A despite tracked-only residue detection
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-security-output.txt, cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: The post-commit residue gate uses `git status --porcelain --untracked-files=no`, but the follow-up path stages with `git add -A`. Untracked files created after the round commit (e.g. by a hook) can be swept into the follow-up commit even though only tracked dirt triggered the block—widening scope beyond Option A’s tracked-only model and increasing risk of committing unintended paths.
- **Suggested revisions (informational for voters; coder decides)**:

### FINDING_3: rebump_dirty_tracked_fixup duplicates large rebump fixture setup
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: `rebump_dirty_tracked_fixup` in `scripts/test-ship-pr.sh` duplicates substantial rebump fixture setup already used elsewhere. Future rebump stub edits may require parallel edits in multiple tests; a shared `_setup_rebump_bump_fixture` helper would reduce drift.
- **Suggested revisions (informational for voters; coder decides)**:

### FINDING_4: Dirty rebump integration test lacks strong bump-drop / no-stall assertions
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Severity**: important
- **Concern**: The dirty-tree rebump test can pass with fixup and `1.2.4` subjects visible while regressions skip or no-op `drop-bump-commit.sh`, reintroducing the silent stale-bump / stall class (#2852, #3209). CI does not assert that the stale bump was dropped before re-bump, that `DROPPED=true` appears in drop output, that HEAD ancestry excludes the unrebased bump subject, that stdout lacks the `DROPPED=false` stall string, or log order proving drop-before-rebump.
- **Suggested revisions (informational for voters; coder decides)**:

### FINDING_5: [OUT_OF_SCOPE] CODER_STATUS=applied docs omit post-commit residue semantics
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: `skills/review-and-fix/scripts/review-and-fix.md` line 25 documents `CODER_STATUS=applied` without post-commit residue / follow-up behavior that is only described later (e.g. line 56). Operators miss round-mode re-check and failure semantics—a pre-existing documentation gap.
- **Suggested revisions (informational for voters; coder decides)**:

### FINDING_6: ship-pr Option A has no post-fixup tracked re-check after git-commit.sh
- **Reviewer(s)**: cursor-specialist-correctness-output.txt
- **Severity**: latent
- **Concern**: Pre-rebase Option A commits tracked leftovers via `git add -u` and `git-commit.sh` but does not re-verify tracked porcelain afterward. Pre-commit hooks that modify tracked files on a successful fixup commit can leave the tree dirty; `drop-bump-commit.sh` Guard 1 then returns `DROPPED=false` and ship-pr can still stall at step 10/12—the same class as the new hook-residue test—unless a guarded second pass (re-check `--untracked-files=no`, optional second `git add -u` + commit) or explicit documented limitation is added.
- **Suggested revisions (informational for voters; coder decides)**:

### FINDING_7: Plan / acceptance text vs implemented Option B scope
- **Reviewer(s)**: cursor-specialist-correctness-output.txt
- **Severity**: nit
- **Concern**: Implemented Option B addresses hook residue only, not a full post-coder completeness scan. Partial Cursor subset commits are not repaired at `review-and-fix`; only at ship-pr rebase (Option A). Issue/acceptance text should align with the plan or `review-and-fix` should be extended if broader Option B was intended.
- **Suggested revisions (informational for voters; coder decides)**:

### FINDING_8: [OUT_OF_SCOPE] Phase-14 resume skips pre-rebase fixup block
- **Reviewer(s)**: cursor-specialist-correctness-output.txt
- **Severity**: latent
- **Concern**: Phase-14 resume paths skip the new pre-rebase fixup block. A dirty tracked tree on resume-after-conflict-resolution is not cleaned by this change; a shared fixup helper may be needed if resume can see dirty tracked trees.
- **Suggested revisions (informational for voters; coder decides)**:

### FINDING_9: [OUT_OF_SCOPE] Submodule inner dirty state blocks drop-bump under Option A
- **Reviewer(s)**: cursor-specialist-correctness-output.txt
- **Severity**: latent
- **Concern**: Submodule-internal dirty state is not cleared by `git add -u` in the superproject; submodule entries can remain in porcelain, Option A is a no-op on the index, and Guard 1 still refuses drop. Pre-existing unless submodule policy changes.
- **Suggested revisions (informational for voters; coder decides)**:

### FINDING_10: No test for staged-only dirty tree at pre-rebase fixup
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: latent
- **Concern**: There is no fixture for index-only (staged-only) tracked dirtiness before `run_rebase_rebump`. A refactor that breaks committing via `git diff --cached` could leave staged-only changes and stall at drop-bump Guard 1 without CI coverage.
- **Suggested revisions (informational for voters; coder decides)**:

### FINDING_11: No test for fixup failure fall-through to Guard 1 stall
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: latent
- **Concern**: No test stubs `git-commit.sh` failure during pre-rebase fixup and asserts best-effort Warning plus `DROPPED=false` stall when the tree stays dirty. Early exit or skipping drop on fixup failure could hide regression of warn + stall behavior.
- **Suggested revisions (informational for voters; coder decides)**:

### FINDING_12: Option B tests cover hook residue only, not partial subset commit path
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: latent
- **Concern**: `test-review-and-fix.sh` Option B coverage validates hook residue, not the #3208 partial-commit path (partial staging), which is only exercised indirectly via ship-pr Option A. Either simulate partial staging in the stub coder or document hook-only scope in the test.
- **Suggested revisions (informational for voters; coder decides)**:

### FINDING_13: No harness for applied + dirty tree after failed follow-up
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: latent
- **Concern**: Changing `CODER_STATUS` when tracked residue remains could break Step 5 without CI failure. There is no test using a non-idempotent hook or failing follow-up commit that asserts `applied` + dirty tree + warning behavior.
- **Suggested revisions (informational for voters; coder decides)**:

### FINDING_14: Hook residue test omits review-and-fix-summary.json coder_commit_sha check
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: nit
- **Concern**: The Option B hook test does not assert `.coder_commit_sha` in `review-and-fix-summary.json` matches follow-up `HEAD` / stdout `CODER_COMMIT_SHA`; summary JSON could drift without failing CI.
- **Suggested revisions (informational for voters; coder decides)**:

### FINDING_15: Option A auto-commits all tracked dirty paths without narrowing or safety gates
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: important
- **Concern**: Pre-rebase Option A auto-commits every tracked dirty path before rebase without allowlist, secret scan, or content gates—replacing Guard 1’s fail-closed stall. Malicious or mistaken uncommitted tracked changes (e.g. from a partial coder or recovery agent) can become `chore: pre-rebase working-tree fixup`, proceed through drop/rebump, and reach push with unreviewed content in history. Mitigations: narrow staging (allowlisted paths / known deltas), stall when the dirty set is broader than expected, and optionally run secret/redaction checks before `git-commit.sh`.
- **Suggested revisions (informational for voters; coder decides)**:

### FINDING_16: Follow-up commit does not re-run submodule revert/scrub
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: latent
- **Concern**: After a second hook-fired commit on the follow-up path, `post_dispatch_submodule_revert` (and fail-on-violation scrub) is not re-run. A pre-commit hook that moves a submodule pointer on the follow-up commit can be committed and still reported as applied review fixes.
- **Suggested revisions (informational for voters; coder decides)**:

### FINDING_17: [OUT_OF_SCOPE] Automated commits run consumer-repo hooks without sandbox
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: latent
- **Concern**: `git-commit.sh` runs target-repo hooks for every automated commit; this diff adds no hook sandbox. A compromised `.git/hooks` in the consumer repo can mutate the tree on each automated commit, including the new follow-up path. Trust model should be documented; hook isolation or selective `--no-verify` only where explicitly safe (not recommended globally).
- **Suggested revisions (informational for voters; coder decides)**:

### FINDING_18: Pre-rebase fixup commit consumes drop-bump --max-depth window
- **Reviewer(s)**: dyn-commit-regex-collision-output.txt
- **Severity**: important
- **Concern**: The new fixup commit is inserted immediately before `drop-bump-commit.sh --max-depth 20`, which walks `HEAD~0`…`HEAD~19`. If the real bump already sits at `HEAD~19`, fixup at `HEAD~0` pushes that bump to `HEAD~20`, outside the window. Drop then warns, returns `DROPPED=false`, and `drop_bump_no_matching_commit` treats it as benign no-op—so `run_rebase_rebump` may continue without dropping the stale bump (silent #2852 class), whereas pre-change dirty state would have stalled at Guard 1.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-commit-regex-collision-output.txt: After a successful fixup commit, call `drop-bump-commit.sh` with `--max-depth 21` (or bump the default for this call site only when a fixup was just created), or skip `HEAD` in the drop walk when its subject matches the known fixup pattern (`chore: pre-rebase working-tree fixup (#3209)`), so the bump search depth is not reduced by the fixup layer.

### FINDING_19: Option A may skip commit when index empty despite non-empty tracked porcelain
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: Option A only runs `git-commit.sh` when `git diff --cached` is non-empty after `git add -u`. Submodule-internal or similar dirty state can yield successful `add -u` with an empty index while porcelain still shows tracked paths; drop-bump Guard 1 then stalls. Should warn with paths, extend staging for remaining tracked paths, or document operator handling.
- **Suggested revisions (informational for voters; coder decides)**:

### FINDING_20: git add -u failure prevents committing already-staged changes
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: If `git add -u` fails, Option A never attempts `git-commit.sh` even when the index already has staged tracked changes (staged-only dirtiness). No fixup commit is created and drop still stalls. On `add -u` failure, still run `git-commit.sh` when the index is non-empty.
- **Suggested revisions (informational for voters; coder decides)**:

### FINDING_21: Option B CI coverage is happy-path only for residue / warn paths
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: nit
- **Concern**: `test-review-and-fix.sh` regression coverage for Option B is largely happy-path; follow-up failure, persistent hook dirtiness, and warn/status contract paths are not asserted in CI.
- **Suggested revisions (informational for voters; coder decides)**:

### FINDING_22: [OUT_OF_SCOPE] create-pr push guard uses full porcelain vs tracked-only Option B
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: `create-pr.sh` push guard uses full porcelain while Option B re-check is tracked-only. Untracked-only residue after a round commit can block push but skip follow-up. Align checks or document the intentional split (pre-existing).
- **Suggested revisions (informational for voters; coder decides)**:
