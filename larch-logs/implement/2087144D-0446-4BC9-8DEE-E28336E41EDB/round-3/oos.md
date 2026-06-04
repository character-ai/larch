### FINDING_15: [OUT_OF_SCOPE] Stall sentinel text is interpolated into SessionStart advisory context
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: latent
- **Concern**: Crafted `larch-stalled-run.txt` fields can influence SessionStart advisory JSON context before `jq --arg`; reviewer marked this pre-existing.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Address the concern above.


Vote tally: YES=1 NO=1 EXON=1 JUDGE_ERROR=0 Result=neutral

### FINDING_18: [OUT_OF_SCOPE] gh-unavailable path reinstalls instead of taking idempotent cone-ok path
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt, dyn-sparse-cone-output.txt
- **Severity**: latent
- **Concern**: When `gh` is unavailable, `already_latest_and_cone_ok` cannot run and the script falls through to unconditional reinstall even if version and cone already match.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.
  - From dyn-sparse-cone-output.txt: Address the concern above.


Vote tally: YES=2 NO=1 EXON=0 JUDGE_ERROR=0 Result=accepted

### FINDING_19: [OUT_OF_SCOPE] Skill-tool fallback can run stale installed upgrade code
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: If no cache root resolves, the release fallback may invoke the installed `/upgrade-larch` skill, which can lag the working tree in dev or no-marketplace-install scenarios.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.


Vote tally: YES=3 NO=0 EXON=0 JUDGE_ERROR=0 Result=accepted

### FINDING_20: [OUT_OF_SCOPE] HOME-less root resolution remains unguarded in pre-existing paths
- **Reviewer(s)**: dyn-bash-runtime-output.txt
- **Severity**: nit
- **Concern**: `get_installed_larch_version` and `resolve_release_step7_root` still dereference `$HOME/.claude/...` without an empty-HOME guard; reviewer marked this as pre-existing.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-bash-runtime-output.txt: Address the concern above.


Vote tally: YES=3 NO=0 EXON=0 JUDGE_ERROR=0 Result=accepted

### FINDING_21: [OUT_OF_SCOPE] SessionStart drift probe requires jq despite git being enough
- **Reviewer(s)**: dyn-bash-runtime-output.txt
- **Severity**: latent
- **Concern**: A host with git but no jq receives no sparse-drift warning; reviewer marked this outside that review’s scope.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-bash-runtime-output.txt: Address the concern above.


Vote tally: YES=0 NO=1 EXON=2 JUDGE_ERROR=0 Result=exonerated

### FINDING_22: [OUT_OF_SCOPE] Sparse-checkout comparison algorithm may be sensitive to git output drift
- **Reviewer(s)**: dyn-bash-runtime-output.txt
- **Severity**: latent
- **Concern**: The `git sparse-checkout list` versus `normalize_sparse_dirs` equality algorithm is unchanged but now exercised more often, so git output-format drift could surface more often.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-bash-runtime-output.txt: Address the concern above.


Vote tally: YES=0 NO=2 EXON=1 JUDGE_ERROR=0 Result=rejected

### FINDING_26: [OUT_OF_SCOPE] Skill-tool fallback branch is comment-only in the Bash fence
- **Reviewer(s)**: dyn-release-state-output.txt
- **Severity**: latent
- **Concern**: The fallback branch lacks mechanical in-repo capture/parse of fallback output; reviewer marked dependency on external orchestrator discipline as out of scope.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-release-state-output.txt: Address the concern above.


Vote tally: YES=2 NO=0 EXON=1 JUDGE_ERROR=0 Result=accepted

### FINDING_27: [OUT_OF_SCOPE] Source-side-effect tests do not assert fd or quiet env cleanliness
- **Reviewer(s)**: dyn-release-state-output.txt
- **Severity**: nit
- **Concern**: Tests assert sourcing avoids the production `ERR` trap, but do not assert fd 2 or `LARCH_QUIET_*` state remains unchanged.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-release-state-output.txt: Address the concern above.


Vote tally: YES=3 NO=0 EXON=0 JUDGE_ERROR=0 Result=accepted

### FINDING_28: [OUT_OF_SCOPE] Allowlist prose copies remain manually synchronized
- **Reviewer(s)**: dyn-sparse-cone-output.txt
- **Severity**: latent
- **Concern**: `lib-sparse-dirs.sh` centralizes the allowlist, but docs and test literals still contain manually synced copies; reviewer marked this as pre-existing/acknowledged.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-sparse-cone-output.txt: Address the concern above.


Vote tally: YES=0 NO=1 EXON=2 JUDGE_ERROR=0 Result=exonerated

### FINDING_31: [OUT_OF_SCOPE] Existing SessionStart git probes also assume common external tools
- **Reviewer(s)**: dyn-hook-failopen-output.txt
- **Severity**: latent
- **Concern**: Pre-existing git-state probes in the same block already rely on `sed` / `sort` / `awk` / `grep` without PATH guards; reviewer marked this as outside the new probe’s in-scope issue.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-hook-failopen-output.txt: Address the concern above.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0 Result=exonerated

### FINDING_32: [OUT_OF_SCOPE] SessionStart test PATH does not exercise stripped sed/sort behavior
- **Reviewer(s)**: dyn-hook-failopen-output.txt
- **Severity**: nit
- **Concern**: `test-sessionstart-health.sh` links `sed`, `sort`, and `tr` into the test PATH, so it does not cover stripped-PATH skip/false-positive behavior.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-hook-failopen-output.txt: Address the concern above.


Vote tally: YES=1 NO=1 EXON=1 JUDGE_ERROR=0 Result=neutral

### FINDING_33: [OUT_OF_SCOPE] Release Step 7 lacks prose fallback relative to SessionStart review scope
- **Reviewer(s)**: dyn-hook-failopen-output.txt
- **Severity**: latent
- **Concern**: Step 7 parses only `LARCH_CONE_RECONCILED=true` and lacks the planned reconcile-fragment fallback; reviewer marked this as outside the SessionStart fail-open surface.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-hook-failopen-output.txt: Address the concern above.


Vote tally: YES=1 NO=1 EXON=1 JUDGE_ERROR=0 Result=neutral

### FINDING_35: [OUT_OF_SCOPE] Unused root-resolution test helpers are dead code only
- **Reviewer(s)**: dyn-harness-hermeticity-output.txt
- **Severity**: nit
- **Concern**: The retention test’s unused cache-shape helpers are dead code, but the reviewer marked them as not a hermeticity regression because production resolver coverage is used instead.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-harness-hermeticity-output.txt: Address the concern above.

Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0 Result=exonerated

### FINDING_8: [OUT_OF_SCOPE] Missing sparse library can exit the caller shell when sourced
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, dyn-release-state-output.txt, dyn-sparse-cone-output.txt
- **Severity**: latent
- **Concern**: The missing `lib-sparse-dirs.sh` path uses `exit 1` before the sourced guard. If `upgrade-larch.sh` is sourced from release code in that state, it can terminate the orchestrator shell instead of returning an error.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Address the concern above.
  - From dyn-release-state-output.txt: Address the concern above.
  - From dyn-sparse-cone-output.txt: Address the concern above.


Vote tally: YES=3 NO=0 EXON=0 JUDGE_ERROR=0 Result=accepted

