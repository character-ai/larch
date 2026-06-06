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

### FINDING_2: snapshot-not-found marker-retention path is untested
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt
- **Severity**: important
- **Concern**: The pause/resume harness does not cover `ERROR=snapshot-not-found` with marker retention, so regressions that delete or mishandle the pause marker on fetch/ref failure could ship undetected.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Add stub forcing fetch/show-ref failure; assert LOAD_OK=false ERROR=snapshot-not-found and pause marker still in issue body
  - From cursor-specialist-testing-output.txt: Add GIT_STUB_FETCH_FAIL or show-ref failure fixture expecting LOAD_OK=false ERROR=snapshot-not-found and grep pause marker still in issue body

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

### FINDING_6: Restore path handling may execute unsafe tree path content
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: important
- **Concern**: Per-file restore uses git tree paths in shell contexts without a strict safe-character validation step, raising a command-substitution risk from malicious snapshot path names.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Validate each relative path against a strict safe-character allowlist before any double-quoted use, or restore via git checkout-index/read-tree without per-path shell expansion; add a regression test with a committed $(…) path component.

### FINDING_7: design-route changes are outside the declared plan file set
- **Reviewer(s)**: cursor-specialist-plan-fidelity-output.txt, dyn-contract-drift-output.txt
- **Severity**: latent
- **Concern**: `design-route.sh` / `design-route.md` were changed to relay `MARKER_CLEARED`, but those files were not listed in the plan’s file set, expanding the route-driver contract without plan amendment.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-plan-fidelity-output.txt: Add design-route files to the plan amendment or revert route changes if MARKER_CLEARED relay is not needed downstream.
  - From dyn-contract-drift-output.txt: Either fold `design-route.sh` / `design-route.md` into the plan acceptance criteria explicitly, or narrow the route diff to passthrough-only behavior already covered by loader `WARN=` lines until SKILL.md is updated.

### FINDING_8: [OUT_OF_SCOPE] Python ship-driver work is bundled with pause/resume changes
- **Reviewer(s)**: cursor-specialist-plan-fidelity-output.txt, dyn-git-restore-output.txt, dyn-contract-drift-output.txt
- **Severity**: important
- **Concern**: The branch includes substantial `python/ship.py` / `python/run_logs.py` work from a separate issue, making pause/resume review scope and regression attribution ambiguous.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-plan-fidelity-output.txt: Keep pause/resume review scoped to commit 5ccd6e3e8 plus review follow-ups on the nine planned paths.
  - From dyn-contract-drift-output.txt: Split the Python ship resume FSM into its own PR/issue authority (or rebase the pause/resume branch onto `main` without #3448), and keep #3529 to the nine shell/doc/test files the plan names.

### FINDING_9: [OUT_OF_SCOPE] body-drift docs may overstate marker persistence
- **Reviewer(s)**: cursor-specialist-plan-fidelity-output.txt
- **Severity**: nit
- **Concern**: The body-drift documentation says the marker remains authoritative without clarifying that successful loads delete it afterward.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-plan-fidelity-output.txt: Clarify that authority applies during validation only; successful install still clears the marker per WI3.

### FINDING_10: [OUT_OF_SCOPE] Fresh fallback can reset persisted ship loop counters
- **Reviewer(s)**: dyn-resume-state-output.txt, dyn-ci-loop-output.txt
- **Severity**: important
- **Concern**: When ship resume falls back to `start=="fresh"`, persisted CI loop counters can be written and then reset to zero at merge-loop entry, potentially bypassing loop caps after a transient mis-route.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-resume-state-output.txt: When entering the merge loop after a fresh fallback, seed `iteration` / `rebase_count` / `fix_attempts` / `transient_retries` from `resume.*` (the same values already persisted in `ship-pr-state.sh`), or refuse fresh fallback when `PHASE=ci-initial` and counters indicate an in-progress merge loop unless an explicit operator reset flag is set.

### FINDING_11: Merged PR with head mismatch can be treated as fresh
- **Reviewer(s)**: dyn-resume-state-output.txt
- **Severity**: important
- **Concern**: `_resume_plan` checks PR head-ref mismatch before handling `MERGED`, so a legitimately merged PR can be routed through fresh checks and potentially duplicate PR creation.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-resume-state-output.txt: For `viewed.state == "MERGED"`, route to `merged`/`done` regardless of head-ref mismatch (optionally emit a warning), and reserve head-ref mismatch fresh-fallback for `OPEN` PRs only.

### FINDING_12: [OUT_OF_SCOPE] Corrupt ship resume counters silently reset to zero
- **Reviewer(s)**: dyn-resume-state-output.txt, dyn-ci-loop-output.txt
- **Severity**: important
- **Concern**: `read_resume_counters` maps non-numeric counter values to `0`, which can silently reset budgets from a damaged `ship-pr-state.sh`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-resume-state-output.txt: Treat non-numeric counter fields as a blocked resume (similar to invalid `BRANCH_NAME` / `PR_URL` handling in `_resume_plan`) or emit a loud parse warning and refuse `open-pr` resume until state is repaired.

### FINDING_13: Marker-delete failure after successful restore can reintroduce stale-marker resume loops
- **Reviewer(s)**: dyn-resume-state-output.txt, dyn-pr-identity-output.txt
- **Severity**: important
- **Concern**: If restore succeeds but pause-marker deletion fails, `LOAD_OK=true` / `MARKER_CLEARED=false` still allows `ROUTE=resume@*`, leaving GitHub issue state stale and enabling later invocations to re-load old snapshots.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-resume-state-output.txt: Either treat post-success marker-delete failure as a hard operator gate (`LOAD_OK=false` with a dedicated `ERROR=marker-delete-failed` while keeping restored files), or have `design-route.sh` skip re-load when `.resume-loaded` is already present in the active tmpdir and the marker still exists.
  - From dyn-pr-identity-output.txt: Treat `MARKER_CLEARED=false` as a hard integration gate before `ROUTE=resume@*` (fail closed with a loud operator-visible warning and manual marker-repair instructions), or have `design-route.sh` retry `clear_pause_marker` once before routing; at minimum, surface `**⚠ ... marker-delete-failed; clear larch:design-pause manually before continuing**` in the orchestrator resume path.

### FINDING_14: [OUT_OF_SCOPE] terminal ship failures now always persist PHASE=stalled
- **Reviewer(s)**: dyn-resume-state-output.txt
- **Severity**: latent
- **Concern**: `_write_terminal_state` always writes `PHASE=stalled` on failure, which may remove a `postmerge` signal used by gh-skipped merged detection.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-resume-state-output.txt: worth monitoring in forked/`repo_unavailable` runs.

### FINDING_15: [OUT_OF_SCOPE] Restore does not enforce cwd worktree matches --repo
- **Reviewer(s)**: dyn-pr-identity-output.txt, dyn-git-restore-output.txt
- **Severity**: important
- **Concern**: `design-pause-load.sh` reads git snapshots from the caller’s cwd while `--repo` only affects GitHub issue operations, so a repo/worktree mismatch can restore the wrong snapshot or fail misleadingly.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-pr-identity-output.txt: After resolving `CURRENT_REPO`, compare it to the slug for `REPO_TOP`’s `origin` (or `git -C "$REPO_TOP" remote get-url origin` normalized) and fail with a dedicated `ERROR=repo-worktree-mismatch` when they diverge; document that restore always uses the cwd worktree, not `--repo`.

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

### FINDING_18: [OUT_OF_SCOPE] ship state writer does not validate REPO on write
- **Reviewer(s)**: dyn-pr-identity-output.txt
- **Severity**: latent
- **Concern**: `_write_ship_state()` validates several fields but not `REPO`, allowing corrupt values to persist until later resume validation.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-pr-identity-output.txt: worth hardening but not introduced by the pause/resume shell changes.

### FINDING_19: [OUT_OF_SCOPE] marker-delete failure diagnostics are suppressed
- **Reviewer(s)**: dyn-pr-identity-output.txt
- **Severity**: nit
- **Concern**: `clear_pause_marker` discards `named-block-write.sh` output, so `WARN=marker-delete-failed` lacks the underlying API or command failure reason.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-pr-identity-output.txt: diagnostic emission would help operators without changing control flow.

### FINDING_20: Python merge loop can hot-spin on ci_not_ready/main_advanced
- **Reviewer(s)**: dyn-ci-loop-output.txt
- **Severity**: important
- **Concern**: `merge_pr` results `ci_not_ready` and `main_advanced` continue the merge loop without incrementing `ITERATION` or sleeping, so the ship-layer iteration cap may not bound this path.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-ci-loop-output.txt: On `ci_not_ready` / `main_advanced`, either increment `iteration` (and persist it), or sleep/backoff before the next `monitor()` call, matching `ci-wait.sh` behavior so the loop is time-bounded and does not hot-spin.

### FINDING_21: Restore destination lacks canonical containment check
- **Reviewer(s)**: dyn-git-restore-output.txt
- **Severity**: important
- **Concern**: The per-file restore assembles destination paths manually and filters obvious traversal, but does not prove canonical parent containment under the staging directory.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-git-restore-output.txt: After building `dest`, reject unless `realpath`/`pwd -P` containment proves the resolved parent directory stays under `$restore_tmp`, mirroring the publish-side ancestor guard.

### FINDING_22: [OUT_OF_SCOPE] Python ship resume contract documentation is missing or incomplete
- **Reviewer(s)**: dyn-contract-drift-output.txt
- **Severity**: important
- **Concern**: The Python ship-driver resume/state-machine surface expanded without a sibling normative contract documenting resume tokens, persisted counters, merge-signal rules, and output envelopes.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-contract-drift-output.txt: Add a `python/ship.md` (or extend `python/README.md` with an explicit resume/state KV section) documenting `ResumePlan.start` values, persisted counter keys, merge-signal thresholds, and stdout/JSON envelope fields; cross-link from SECURITY.md’s Python ship-pr paragraph.

### FINDING_23: [OUT_OF_SCOPE] committed implement run logs inflate review surface
- **Reviewer(s)**: dyn-contract-drift-output.txt
- **Severity**: nit
- **Concern**: The branch includes a full `larch-logs/implement/…` run tree that is normal `/implement` output but unrelated to pause/resume semantics.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-contract-drift-output.txt: Address the concern above.
