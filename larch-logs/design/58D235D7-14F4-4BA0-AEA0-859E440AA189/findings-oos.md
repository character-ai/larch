### OOS_1: `build_sensitive_corpus_from_evidence` still reads only classification `FAILURE_DETAIL_LOG`
- **Description**: `build_sensitive_corpus_from_evidence` still reads only classification `FAILURE_DETAIL_LOG`. Scenario: Tier B sensitive-corpus assembly can omit truncated sidecar text when the classification env still references an oversize path. Tier A compose is fixed by this plan, but Tier B dedup/token scans may stay blind to the same evidence.
- **Reviewer**: Cursor-Arch
- **Severity**: latent
- **Focus area**: architecture
- **Location**: python/larch/state/stall_recovery.py:1575-1610
- **Phase**: design



### OOS_2: [OUT_OF_SCOPE] No regression test for prefixed generic classify ledger fallback
- **Description**: [OUT_OF_SCOPE] No regression test for prefixed generic classify ledger fallback. Scenario: `_classify_generic_from_terminal_state()` is in the firm plan, but tests only cover the implement `classify_main()` path and Tier A compose. A regression in `design-failure-*` ledger scanning would not be caught by the proposed pytest additions
- **Reviewer**: Cursor-Pragmatic
- **Severity**: latent
- **Focus area**: architecture
- **Location**: python/larch/state/stall_recovery.py
- **Phase**: design



### OOS_3: `build_sensitive_corpus_from_evidence()` still reads only classification `FAILURE_DETAIL_LOG`
- **Description**: `build_sensitive_corpus_from_evidence()` still reads only classification `FAILURE_DETAIL_LOG`. Scenario: If Tier A compose falls back to a ledger sidecar but classification still stores an oversize primary path, Tier B sensitive-corpus construction will keep omitting detail-log secrets from the corpus. Issue scope targets classify and Tier A compose only; this is a separate Tier B gap.
- **Reviewer**: Cursor-dyn-Evidence Path Correctness
- **Severity**: latent
- **Focus area**: risk-integration
- **Location**: python/larch/state/stall_recovery.py:1605-1610 python/test_stall_recovery.py:715-735
- **Phase**: design



