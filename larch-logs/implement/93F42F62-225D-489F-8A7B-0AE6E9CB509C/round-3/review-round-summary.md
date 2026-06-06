# Review Round 3

- Mode: `diff`
- 10 accepted, 3 rejected (1 exonerated)

## Accepted Findings

### FINDING_1: MARKER_CLEARED is not fully propagated or pinned end-to-end
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-plan-fidelity-output.txt, dyn-contract-drift-output.txt
- **Severity**: latent
- **Concern**: `MARKER_CLEARED` is documented/emitted by the pause/resume route path, but the `/design` Step 0b orchestrator allowlist and tests do not fully bind or assert it, so marker-delete failures or success telemetry can be silently dropped.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Add MARKER_CLEARED to both Step 0b case arms (or remove from design-route contract) and pin in test-design-structure.sh.
  - From cursor-specialist-testing-output.txt: Add stubbed design-route or extend pause harness to assert MARKER_CLEARED on resume@ path
  - From cursor-specialist-testing-output.txt: Assert MARKER_CLEARED=true in round-trip and export-ignore success outputs
  - From cursor-specialist-plan-fidelity-output.txt: Assert MARKER_CLEARED=true on round-trip body-drift and export-ignore success load outputs.
  - From dyn-contract-drift-output.txt: Add `MARKER_CLEARED` to the Step 0b `case` allowlists in `skills/design/SKILL.md` (file-first and stdout-merge loops), echo it on the `resume@*` breadcrumb path when present, and extend `scripts/test-design-structure.sh` to pin the new key alongside existing route KVs.


### FINDING_11: Merged PR with head mismatch can be treated as fresh
- **Reviewer(s)**: dyn-resume-state-output.txt
- **Severity**: important
- **Concern**: `_resume_plan` checks PR head-ref mismatch before handling `MERGED`, so a legitimately merged PR can be routed through fresh checks and potentially duplicate PR creation.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-resume-state-output.txt: For `viewed.state == "MERGED"`, route to `merged`/`done` regardless of head-ref mismatch (optionally emit a warning), and reserve head-ref mismatch fresh-fallback for `OPEN` PRs only.


### FINDING_16: Ship resume may fall back to stale context PR_NUMBER
- **Reviewer(s)**: dyn-pr-identity-output.txt
- **Severity**: important
- **Concern**: Empty or missing `PR_NUMBER` in `ship-pr-state.sh` falls back to `ctx.pr_number`, which can resume against a stale PR identity.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-pr-identity-output.txt: Remove the `ctx_pr_number` fallback when a state file exists; require an explicit positive `PR_NUMBER` in state (or a fresh `ensure_pr` path) before any `gh.pr_view`-backed resume. If fallback is kept, only use it when `PHASE` indicates pre-PR creation.


### FINDING_17: Restore uses mutable git refs instead of one pinned snapshot SHA
- **Reviewer(s)**: dyn-pr-identity-output.txt, dyn-git-restore-output.txt
- **Severity**: important
- **Concern**: Snapshot restore uses mutable refs such as `FETCH_HEAD`, `origin/<default>`, or branch names across enumeration and blob extraction, allowing ref movement or concurrent fetches to produce wrong or internally inconsistent restores.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-pr-identity-output.txt: Resolve and use an explicit ref (`refs/remotes/origin/$LOG_RECOVERY_BRANCH` or `git rev-parse FETCH_HEAD^{commit}` captured right after the intended fetch) instead of bare `FETCH_HEAD` for enumeration and `git show`.
  - From dyn-git-restore-output.txt: Immediately after fetch/ref resolution, resolve once with `snapshot_sha=$(git -C "$REPO_TOP" rev-parse --verify "${snapshot_ref}^{commit}")` and use only that SHA for both `ls-tree` and every `git show "$snapshot_sha:$path"` call so the restored tree is a single immutable snapshot.


### FINDING_2: snapshot-not-found marker-retention path is untested
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt
- **Severity**: important
- **Concern**: The pause/resume harness does not cover `ERROR=snapshot-not-found` with marker retention, so regressions that delete or mishandle the pause marker on fetch/ref failure could ship undetected.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Add stub forcing fetch/show-ref failure; assert LOAD_OK=false ERROR=snapshot-not-found and pause marker still in issue body
  - From cursor-specialist-testing-output.txt: Add GIT_STUB_FETCH_FAIL or show-ref failure fixture expecting LOAD_OK=false ERROR=snapshot-not-found and grep pause marker still in issue body


### FINDING_20: Python merge loop can hot-spin on ci_not_ready/main_advanced
- **Reviewer(s)**: dyn-ci-loop-output.txt
- **Severity**: important
- **Concern**: `merge_pr` results `ci_not_ready` and `main_advanced` continue the merge loop without incrementing `ITERATION` or sleeping, so the ship-layer iteration cap may not bound this path.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-ci-loop-output.txt: On `ci_not_ready` / `main_advanced`, either increment `iteration` (and persist it), or sleep/backoff before the next `monitor()` call, matching `ci-wait.sh` behavior so the loop is time-bounded and does not hot-spin.


### FINDING_3: Failed restore install can leave partial DESIGN_TMPDIR state
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt, dyn-ci-loop-output.txt
- **Severity**: important
- **Concern**: `cp -R` can populate `$DESIGN_TMPDIR` before later sentinel writes or cleanup fail, producing `LOAD_OK=false` while restored files are already present and the pause marker remains retryable.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Document retry semantics or defer copying until all post-validate install steps succeed
  - From cursor-specialist-edge-cases-output.txt: On restore-install-failed after any cp, scrub DESIGN_TMPDIR or abort routing to proceed when pause marker remains and load failed
  - From dyn-ci-loop-output.txt: Treat post-`cp` sentinel cleanup as best-effort (warn on `rm`/`.resume-loaded` failure but still emit `LOAD_OK=true`), or install atomically into a staging dir and swap only after all success checks, so a late sentinel failure cannot produce “files present, load failed.”


### FINDING_4: Real-git restore test misses origin/main default path
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt
- **Severity**: important
- **Concern**: The real-git export-ignore fixture only exercises a local recovery branch, not the default `origin/main` recovery path used when `LOG_RECOVERY_BRANCH` is absent.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Add optional subshell test with snapshot on main and no LOG_RECOVERY_BRANCH in marker
  - From cursor-specialist-testing-output.txt: Add real-git subshell with snapshot on main no LOG_RECOVERY_BRANCH forcing origin/main restore and LOAD_OK=true


### FINDING_5: invalid-restored-manifest marker-retention path is untested
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: latent
- **Concern**: A corrupt restored `manifest.json` could regress to deleting the pause marker on validation failure without CI coverage.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Fixture invalid manifest assert ERROR=invalid-restored-manifest and marker retained


### FINDING_7: design-route changes are outside the declared plan file set
- **Reviewer(s)**: cursor-specialist-plan-fidelity-output.txt, dyn-contract-drift-output.txt
- **Severity**: latent
- **Concern**: `design-route.sh` / `design-route.md` were changed to relay `MARKER_CLEARED`, but those files were not listed in the plan’s file set, expanding the route-driver contract without plan amendment.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-plan-fidelity-output.txt: Add design-route files to the plan amendment or revert route changes if MARKER_CLEARED relay is not needed downstream.
  - From dyn-contract-drift-output.txt: Either fold `design-route.sh` / `design-route.md` into the plan acceptance criteria explicitly, or narrow the route diff to passthrough-only behavior already covered by loader `WARN=` lines until SKILL.md is updated.


