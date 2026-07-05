### OOS_1: [OUT_OF_SCOPE] classifier mismatch in non-security OOS counting
- **Reviewer(s)**: cursor-specialist-correctness
- **Severity**: latent
- **Concern**: `_non_security_oos_count()` still classifies via temp-file `voting.is_security_block`, while the plan-review tally now uses `voting.is_security_block_text` on restored attribution text. That leaves `/implement` able to diverge from `/design` on edge-case security tagging.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness: route `_non_security_oos_count` through the same text classifier on block bodies when consolidating classifiers repo-wide.

### OOS_2: [OUT_OF_SCOPE] emit-tally parent-copy path untested
- **Reviewer(s)**: cursor-specialist-correctness, cursor-specialist-edge-cases
- **Severity**: latent
- **Concern**: The session-env test stubs `_emit_tally`, so it verifies forwarding and `_copy_to_parent` wiring but not the real `emit-tally` preserve/serialize/finalize chain or the parent `oos-accepted-review.md` bytes after pool promotion.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness: add one integration test that runs the real `emit-tally` helper with `--session-env-path` and asserts parent `oos-accepted-review.md` bytes after pool promotion.
  - From cursor-specialist-edge-cases: Stub only command dispatch and run emit_tally against a real tmpdir layout.

### OOS_3: [OUT_OF_SCOPE] missing fail-closed read/decode regression
- **Reviewer(s)**: cursor-specialist-correctness, cursor-specialist-testing
- **Severity**: latent
- **Concern**: Fail-closed coverage only exercises classifier failure; the strict read/decode seam at `_artifact_text_for_item` still lacks a regression for `UnicodeDecodeError` or invalid UTF-8.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness: add a test that makes Path.read_text raise UnicodeDecodeError and assert tally aborts without writing public OOS pools.
  - From cursor-specialist-testing: Add invalid-UTF-8 or mocked read-failure regression asserting non-zero tally exit and empty public OOS sinks.
  - From cursor-specialist-testing: Add a test forcing read/decode failure at _artifact_text_for_item and assert non-zero exit with no public OOS pool artifacts

### OOS_4: [OUT_OF_SCOPE] stale OOS sink can mask fresher oos.md
- **Reviewer(s)**: cursor-specialist-edge-cases
- **Severity**: latent
- **Concern**: Over-count sink preservation has no regression for stale sink masking fresher oos.md; promoted or stale sinks with count >= tally can skip serialization of newer round-local OOS.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases: Add test where sink_count > OOS_ACCEPTED_COUNT and oos.md differs, documenting expected authority.

### OOS_5: [OUT_OF_SCOPE] parent copy OSError is silently suppressed
- **Reviewer(s)**: cursor-specialist-testing
- **Severity**: latent
- **Concern**: `_copy_to_parent` suppresses `OSError`, so parent-copy failure remains silent; the reviewer notes it is pre-existing and not introduced or amplified here.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing: Separate hardening if desired; out of scope for this PR.

### OOS_6: [OUT_OF_SCOPE] security pool routing traceability gap
- **Reviewer(s)**: cursor-specialist-testing
- **Severity**: nit
- **Concern**: Security pool routing still relies on `test_plan_review.py`, which is only a traceability gap.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing: No change required for this PR unless consolidating security tests

### OOS_7: [OUT_OF_SCOPE] Codex jsonl sidecar path untested
- **Reviewer(s)**: cursor-specialist-testing
- **Severity**: nit
- **Concern**: The lazy sidecar test covers Cursor `.tsv` only, so Codex `.jsonl` lazy materialization remains unverified.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing: Add a jsonl-path test if Codex lanes matter in CI

### OOS_8: [OUT_OF_SCOPE] emit-tally subprocess return code is ignored
- **Reviewer(s)**: dyn-dyn-oos-reentry-codex
- **Severity**: important
- **Concern**: `_emit_tally` ignores the `emit-tally` subprocess return code, so caller code can continue and copy local artifacts to the parent session after a partial OOS sink is rejected.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-dyn-oos-reentry-codex: Return or raise on non-zero `emit-tally` results, and make callers stop before parent copy.

