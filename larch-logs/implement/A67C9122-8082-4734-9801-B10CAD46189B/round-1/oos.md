### FINDING_4: [OUT_OF_SCOPE] Merge paths have inconsistent integrity-skip handling
- **Reviewer(s)**: cursor-specialist-correctness, cursor-specialist-edge-cases, cursor-specialist-testing
- **Severity**: minor
- **Concern**: Inline merge handling still fails closed for redaction-failed and recovery-failed results, while the ship path ignores all `RefreshSkip` results. The same underlying flush failure can therefore produce an error on the inline-merge path but `OK` on the ship-driver path. Document the intentional split or align the paths in a follow-up.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness: Address the concern above.
  - From cursor-specialist-edge-cases: Address the concern above.
  - From cursor-specialist-testing: Address the concern above.


Vote tally: YES=3 NO=0 JUDGE_ERROR=0 Result=accepted Fileable=false

### FINDING_5: [OUT_OF_SCOPE] Monkeypatch facade baseline references a removed test
- **Reviewer(s)**: cursor-specialist-correctness
- **Severity**: minor
- **Concern**: `python/monkeypatch-facade-binding-baseline.json` still references the removed test name `test_postmerge_flush_skip_writes_stall_shape`. Ratchet or audit tooling keyed by `qualified_symbol` may miss the renamed regression test. Update the baseline entry to `test_postmerge_flush_skip_still_completes_ok` during the next mechanical baseline refresh.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness: Address the concern above.


Vote tally: YES=3 NO=0 JUDGE_ERROR=0 Result=accepted Fileable=false

### FINDING_6: [OUT_OF_SCOPE] Existing stalled post-merge runs are not repaired
- **Reviewer(s)**: cursor-specialist-edge-cases
- **Severity**: minor
- **Concern**: The fix does not repair already-stalled post-merge runs, so operators must manually recover historical stalls such as the reported `#6900` case. Track recovery separately if needed.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases: Address the concern above.


Vote tally: YES=3 NO=0 JUDGE_ERROR=0 Result=accepted Fileable=false

### FINDING_7: [OUT_OF_SCOPE] Existing refresh-skip allowlist is not reused
- **Reviewer(s)**: cursor-specialist-edge-cases
- **Severity**: minor
- **Concern**: `REFRESH_SKIP_MERGE_OK` already provides a pre-push tolerance pattern, but post-merge handling ignores all skips unconditionally. Extend or reuse the existing allowlist instead of discarding every `RefreshSkip` in a follow-up.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases: Address the concern above.
Vote tally: YES=1 NO=2 JUDGE_ERROR=0 Result=neutral Fileable=false
