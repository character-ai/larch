### OOS_1: [OUT_OF_SCOPE] Sidecar selection does not correlate ledger rows to invalid primary failure-detail path
- **Reviewer(s)**: cursor-specialist-edge-cases
- **Severity**: latent
- **Concern**: Sidecar selection uses the newest ledger row by `utc`/`sequence` without correlating to the invalid primary failure-detail path. `classify` with oversize path B while the ledger only has a sidecar from an earlier escalation for path A can classify B using A's lint evidence and emit the wrong `FAILURE_CLASS` / `FAILURE_DETAIL_LOG`. When primary is set but invalid, match ledger rows to the primary path via sidecar digest (or stored source metadata) before falling back to newest-row selection.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases: Address the concern above.

### OOS_2: [OUT_OF_SCOPE] Missing regression test for classify guard when `--failure-detail-log` is omitted
- **Reviewer(s)**: cursor-specialist-edge-cases
- **Severity**: nit
- **Concern**: No regression test covers the classify guard that skips ledger sidecar fallback when `--failure-detail-log` is omitted. A future edit could accidentally enable sidecar fallback for classify without an explicit primary, reintroducing invented evidence on no-arg classify.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases: Address the concern above.

### OOS_3: [OUT_OF_SCOPE] `build_sensitive_corpus_from_evidence` omits ledger sidecar fallback
- **Reviewer(s)**: cursor-specialist-edge-cases, codex-specialist-edge-cases
- **Severity**: latent
- **Concern**: `build_sensitive_corpus_from_evidence()` still reads only the path already stored in `FAILURE_DETAIL_LOG` and does not consult the new ledger sidecar fallback. Tier B / corpus scanning can omit truncated failure-detail content that Tier A now embeds via sidecar fallback, weakening cross-surface consistency. If tier B/public-file generation runs from a stale classification file, truncated evidence is still dropped.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases: Address the concern above.
  - From codex-specialist-edge-cases: Address the concern above.

### OOS_4: [OUT_OF_SCOPE] Missing regression test for valid primary log coexisting with differing ledger sidecar
- **Reviewer(s)**: cursor-specialist-testing
- **Severity**: latent
- **Concern**: The plan lists “original detail log is valid: use it and do not consult sidecar” as an edge case, but there is no regression test where a valid primary log coexists with a ledger sidecar carrying different evidence. `_read_failure_detail_log_with_sidecar_fallback` returns early on a valid primary; the miss is coverage polish, not a demonstrated bug.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing: Address the concern above.

### OOS_5: [OUT_OF_SCOPE] Missing regression test for multiple ledger rows with distinct sidecars
- **Reviewer(s)**: cursor-specialist-testing
- **Severity**: latent
- **Concern**: “Ledger has several rows: use the newest valid sidecar” is implemented via `max(..., key=(utc, sequence))` in `_latest_failure_detail_log_sidecar`, but no test appends multiple ledger rows with distinct sidecars. Ordering logic is straightforward; failure would be latent and is not part of the plan’s acceptance commands.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing: Address the concern above.

### OOS_6: [OUT_OF_SCOPE] Missing regression tests for unsafe ledger sidecar values
- **Reviewer(s)**: cursor-specialist-testing
- **Severity**: latent
- **Concern**: Plan edge cases for unsafe ledger values (missing sidecar file, path outside tmpdir, symlink target) are guarded in `_latest_failure_detail_log_sidecar` but not exercised by tests. Behavior mirrors existing `classify_failure_detail_log` validation; gaps are defensive-path coverage, not regressions in the primary oversize→sidecar scenario this feature fixes.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing: Address the concern above.

