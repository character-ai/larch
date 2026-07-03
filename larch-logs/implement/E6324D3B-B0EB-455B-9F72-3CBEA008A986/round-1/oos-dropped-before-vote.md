### OOS_1: [OUT_OF_SCOPE] Step 6 cleanup still removes diagnostic artifacts before the hint is usable
- **Reviewer(s)**: cursor-specialist-correctness, cursor-specialist-edge-cases, codex-specialist-edge-cases, cursor-specialist-testing, dyn-dyn-tier-a-report
- **Severity**: latent
- **Concern**: The fallback guidance still depends on `DESIGN_TMPDIR`, but the associated tmpdir artifacts can already be deleted by Step 6 cleanup on successful runs. That leaves the investigation hint pointing at evidence that no longer exists.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness: Address the concern above.
  - From cursor-specialist-edge-cases: Address the concern above.
  - From codex-specialist-edge-cases: Address the concern above.
  - From cursor-specialist-testing: Address the concern above.
  - From dyn-dyn-tier-a-report: Address the concern above.

### OOS_2: [OUT_OF_SCOPE] no-match / lookup-failed-open still behaves like success
- **Reviewer(s)**: cursor-specialist-correctness
- **Severity**: latent
- **Concern**: The compose outcome path still treats `no-match` and `lookup-failed-open` as success, so normalization can propagate a success sentinel without ever filing an issue.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness: Address the concern above.

### OOS_3: [OUT_OF_SCOPE] append_fallback OSError still collapses to generic compose-status-missing
- **Reviewer(s)**: cursor-specialist-correctness
- **Severity**: latent
- **Concern**: If `append_fallback` hits an `OSError`, the retry path can still fall back to the generic `compose-status-missing` result instead of surfacing the real append failure.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness: Address the concern above.

### OOS_4: [OUT_OF_SCOPE] compose_report still omits status emission on issue-input paths
- **Reviewer(s)**: cursor-specialist-edge-cases, dyn-dyn-tier-a-report
- **Severity**: latent
- **Concern**: `compose_report` still leaves `STALL_RECOVERY_REPORT_STATUS` unset on plain issue-input paths, so Tier A filing status remains split across compose and backfill helpers.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases: Address the concern above.
  - From dyn-dyn-tier-a-report: Address the concern above.

### OOS_5: [OUT_OF_SCOPE] repo/title validation still relies on the bash helper boundary
- **Reviewer(s)**: cursor-specialist-edge-cases
- **Severity**: latent
- **Concern**: Repo and title values still reach the subprocess boundary without Python-side validation, so the trust boundary continues to depend on the bash helper.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases: Address the concern above.

### OOS_6: [OUT_OF_SCOPE] Retry-evidence broadening is not directly verified
- **Reviewer(s)**: cursor-specialist-testing
- **Severity**: nit
- **Concern**: The new retry-evidence behavior for non-panel escalations is only exercised indirectly. A regression in the retry append/fallback path could still sneak through without a focused assertion.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing: Address the concern above.

### OOS_7: [OUT_OF_SCOPE] generic compose-status-missing remains as a residual catch-all
- **Reviewer(s)**: cursor-specialist-testing
- **Severity**: latent
- **Concern**: Some edge cases can still end in the generic `compose-status-missing` fallback after retry evidence is present. That residual catch-all is pre-existing unless the later fix removes it.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing: Address the concern above.

### OOS_8: [OUT_OF_SCOPE] duplicate status lines can still be read with first-match semantics
- **Reviewer(s)**: cursor-specialist-testing
- **Severity**: latent
- **Concern**: `compose_env_key` is only tested on the terminal-failure path, so duplicate `STALL_RECOVERY_REPORT_STATUS` lines on append-after-compose paths can still be read stale and route to the wrong branch.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing: Address the concern above.

