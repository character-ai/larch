Aggregating the supplied reviewer slots into merged findings with stable IDs (first-seen by minimum original finding number). Read-only: structured output only.

---

### FINDING_1: Unused `checks-step10` branch in recovery waterfall
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-edge-cases-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Concern**: `run_recovery_waterfall` defines a `verify_kind=checks-step10` path that no caller passes; tests never hit it. Same dead arm noted as maintenance/confusion risk and as plan-fidelity dead code; risks false assumptions about step10 recovery parity with step6-style checks.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-edge-cases-output.txt: Remove the dead case arm or wire a real call site with a contract comment
  - From cursor-specialist-plan-fidelity-output.txt: Remove checks-step10 or add a real call site if step10 coverage is intended.

### FINDING_2: Divergent bump vs non-bump classification
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Concern**: Parallel logic between `ship_pr_vendor_conflict_csv_is_non_bump_only`, the deterministic rebase loop CSV gate, and the waterfall can disagree after partial edits, so the waterfall may run on paths the loop classifies differently (bump-only vs non-bump) or vice versa.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Share one classification helper or document a single source of truth with cross-callsite tests

### FINDING_3: Inconsistent stderr redirection across Cursor vs other tiers
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-edge-cases-output.txt
- **Concern**: Cursor tier stderr is sent to `wf_log` with truncate (`2>`) while Codex/Claude append (`2>>`), making combined tier diagnostics harder to read when debugging waterfall failures and dropping earlier stderr context on Cursor failure.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Normalize stderr redirection across tiers
  - From cursor-specialist-testing-output.txt: Standardize on 2>> for all tiers
  - From cursor-specialist-edge-cases-output.txt: Use 2>> append like other tiers

### FINDING_4: `with_transient_retry` passes unused `fail_file` to predicates
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Concern**: `fail_file` is passed into envelope predicates but unused, so readers may assume fail-file-aware behavior that never runs.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Align signature and comment (drop arg or use it)

### FINDING_5: [OUT_OF_SCOPE] Unrelated ast-grep contributor doc bundled with ship-pr work
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-security-output.txt, cursor-specialist-edge-cases-output.txt
- **Concern**: `docs/installation-and-setup.md` (ast-grep section) is unrelated to ship-pr automation; reviewers must split attention across unrelated concerns in one PR; several slots mark as scope/triage only (no ship-pr logic change).
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Split doc change to its own PR or branch
  - From cursor-specialist-correctness-output.txt: None (scope/triage only)
  - From cursor-specialist-testing-output.txt: None required for this review
  - From cursor-specialist-security-output.txt: No change required for ship-pr security review
  - From cursor-specialist-edge-cases-output.txt: None for this review

### FINDING_6: [OUT_OF_SCOPE] Launchers exit 0; recovery relies on verifier not rc
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Concern**: `scripts/launch-*-ci.sh` pattern (grep `LAUNCHER_EXIT`; exit 0) is described as pre-existing on main, not introduced by this PR; no change required for this PR scope.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: No change required for this PR scope

### FINDING_7: [OUT_OF_SCOPE] `exit_transient_net` outside `with_transient_retry` for rebase / ci-wait bail
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt
- **Concern**: Same structural pattern as on main before branch (`exit_transient_net` outside `with_transient_retry` body at cited bail sites). One slot: no change unless product tightens acceptance #11 globally. Other slot: strict reading of plan acceptance #11 conflicts with legacy call sites; refactor into WTR or relax/document acceptance #11 scope.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: No change required unless product wants to tighten acceptance #11 globally
  - From cursor-specialist-correctness-output.txt: Refactor into WTR or relax/document acceptance #11 scope

### FINDING_8: `commit_post_waterfall_checks_fix_or_stall` may miss untracked-only recovery work
- **Reviewer(s)**: cursor-specialist-correctness-output.txt
- **Concern**: Uses `git diff` without untracked detection; if recovery produces only untracked fixes, both diffs can be quiet, function returns 0 without add/commit/push, phase advances with dirty tree and no failure record.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Use git status --porcelain (or existing dirty capture) for early-out; only skip when truly clean

### FINDING_9: Awk KV extract for `BAIL_REASON` / `ERROR` is first-line only
- **Reviewer(s)**: cursor-specialist-correctness-output.txt
- **Concern**: Multi-line or wrapped envelope values can miss transient tokens; `with_transient_retry` may return 0 then bail path `exit_transient_net` fires without intended retries.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Match kv_value semantics or forbid multiline KV in helpers; add harness for multiline envelope

### FINDING_10: `usage()` omits `--failure-log` in `launch-cursor-ci.sh`
- **Reviewer(s)**: cursor-specialist-correctness-output.txt
- **Concern**: Operators copying argv from usage-only help miss implemented flags.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Update usage string to mirror implemented argv

### FINDING_11: [OUT_OF_SCOPE] Design run log artifacts co-present in diff
- **Reviewer(s)**: cursor-specialist-correctness-output.txt
- **Concern**: `larch-logs/design/...` noise in diff; not ship-pr runtime; policy-expected.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: None (policy-expected noise)

### FINDING_12: Tier success conflation: `LAUNCHER_EXIT` vs process exit / discarded launcher stdout
- **Reviewer(s)**: cursor-specialist-testing-output.txt, cursor-specialist-security-output.txt
- **Concern**: `launch-claude-ci.sh` exits 0 even when `LAUNCHER_EXIT` is non-zero; ship-pr recovery waterfall uses shell exit for `tier_rc`, so Claude timeout/failure can yield rc 0 and tier looks launched OK until verify; with `>/dev/null` on launcher output, failed vendor runs can still look like successful tiers and skip immediate post-launcher rollback, behavior depending on verifier gaps.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Propagate LAUNCHER_EXIT (exit non-zero on failure) to match other CI launchers
  - From cursor-specialist-security-output.txt: Omit >/dev/null and parse LAUNCHER_EXIT or exit non-zero from launcher when LAUNCHER_EXIT!=0

### FINDING_13: Missing Acceptance #12 rollback harness tests (only grep pins)
- **Reviewer(s)**: cursor-specialist-testing-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Concern**: Plan AC#12 names rollback harness cases not present in `scripts/`; structural grep can pass while rollback behavior (ordering, spaces, globs, staged restore) regresses.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Add recovery_waterfall_rollback_handles_paths_with_spaces_and_globs and recovery_waterfall_rollback_restores_staged_changes_via_git_restore_staged to test-ship-pr.sh
  - From cursor-specialist-plan-fidelity-output.txt: Add recovery_waterfall_rollback_handles_paths_with_spaces_and_globs and recovery_waterfall_rollback_restores_staged_changes_via_git_restore_staged to scripts/test-ship-pr.sh (or alias existing tests to those names).

### FINDING_14: Brittle negative grep in `test-launch-claude-ci.sh`
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Concern**: Negative grep for subprocess marker couples test to unrelated text drift (false pass/fail).
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Use a stable positive writer-preamble sentinel assertion

### FINDING_15: Makefile `test-harnesses-2` shard timing risk
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Concern**: Second launcher harness added to shard 2 without shown timing rebalance; possible CI shard wall-time regression.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Rebalance harness shards if CI shows shard 2 slowdown

### FINDING_16: Redaction pipeline fail-open: raw `head -c` on redactor failure
- **Reviewer(s)**: cursor-specialist-security-output.txt, cursor-specialist-edge-cases-output.txt
- **Concern**: Redact pipe falls back to raw `head -c` when `redact-secrets.sh` errors or is missing; up to ~4KB unredacted (or unredacted excerpt) can reach external model prompts.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Fail closed: drop excerpt or substitute fixed text and surface error; do not fall back to raw bytes
  - From cursor-specialist-edge-cases-output.txt: Fail close omit excerpt or non-zero exit when redaction fails

### FINDING_17: Symlinked `--failure-log` may bypass tmp containment intent
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Concern**: Symlinked `--failure-log` could steer `head -c` reads while passing prefix checks; same-user tmp races could read sensitive paths.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Validate no symlink / copy to mktemp before read

### FINDING_18: `merge-pr` transient predicate scans only first `MERGE_RESULT`/`ERROR` pair
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Concern**: Stale first lines could misclassify envelopes and change retry vs stall.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Parse last matching envelope or tighten log shape contract

### FINDING_19: Recovery commit + failed verify leaves HEAD off baseline; later tiers skipped
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Concern**: If a recovery tier creates a commit and verification fails, HEAD no longer matches baseline; remaining waterfall tiers are skipped and run aborts as total failure though other tiers were never tried.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Reset HEAD to baseline after failed verify or adjust baseline policy document harness-only env

### FINDING_20: Sourcing `ship-pr.sh` runs `larch_quiet_init` outside `main`
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Concern**: Sourcing without `LARCH_QUIET_DISABLE` can redirect stdout/stderr and touch disk, conflicting with strict zero side-effect wording.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Defer quiet init to main or document required env

### FINDING_21: Plan vs shipped verifier naming (`run-relevant-checks-captured.sh` vs `pr-prep-oos`)
- **Reviewer(s)**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: Pasted plan lists `run-relevant-checks-captured.sh` as pr-prep verifier; code uses `pr-prep-oos` (OOS gate); future audits may false-flag mismatch though OOS-gate rerun may match stall domain.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-plan-fidelity-output.txt: Reconcile plan text with shipped ship-pr.md + verify_kind naming (document OOS verifier for pr-prep explicitly).

### FINDING_22: `ship-pr.md` lacks explicit `RESUME_PHASE` / `CALLER_KIND` mapping example
- **Reviewer(s)**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: Acceptance #4 explicit `RESUME_PHASE=bump` + `CALLER_KIND=step8_apply_bump_same_version` vs wrong `RESUME_PHASE` token not spelled in `ship-pr.md`; orchestrator-facing doc may mislead.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-plan-fidelity-output.txt: Add a one-line explicit mapping example to ship-pr.md (and keep docs/linting.md aligned).

### FINDING_23: [OUT_OF_SCOPE] Stale `skills/implement/SKILL.md` exit 5 orchestration vs absorbed paths
- **Reviewer(s)**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: `SKILL.md` still documents ship-pr exit 5 while ship-pr no longer emits exit 5 for absorbed paths; operators following stale guidance may mishandle exit 4 stall streams after this lands.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-plan-fidelity-output.txt: Follow-up SKILL.md + reference doc edits to match exit 4 / waterfall contracts.

---

**Note:** `FINDING_6` (launchers exit 0, OOS) was **not** merged with `FINDING_12` (`LAUNCHER_EXIT` propagation / waterfall tier_rc): same broad theme but incompatible triage (no PR change vs explicit fix), different fixes, and different primary code paths called out.

Because this output contains one or more `### FINDING_N:` blocks, **`LARCH_AGGREGATOR_EMPTY_MERGE_ATTESTED` must not appear** anywhere in this response.
