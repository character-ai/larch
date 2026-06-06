### FINDING_1: [OUT_OF_SCOPE] Duplicate skipped-findings security classifier call
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt, dyn-bash-portability-output.txt
- **Severity**: important
- **Concern**: Skipped-OOS/security routing in `review-and-fix.sh` calls `is_security_block` twice for non-security blocks and includes confusing or unreachable branching. This is inefficient and obscures the classifier failure contract; one source treats it as out-of-scope for portability.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.
  - From cursor-specialist-correctness-output.txt: Address the concern above.
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.
  - From dyn-bash-portability-output.txt: Address the concern above.

### FINDING_2: Legacy accumulated OOS seed can collide or stay gate-invisible
- **Reviewer(s)**: cursor-specialist-correctness-output.txt
- **Severity**: latent
- **Concern**: `OOS_WRITE_SEQ` seeding ignores bare `FINDING_` headers already present in `accumulated-oos.md`, so resumed runs can leave legacy OOS gate-invisible or assign colliding `OOS_` IDs.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Address the concern above.

### FINDING_3: Coder in-scope filter misses `[OOS]` shorthand
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt
- **Severity**: important
- **Concern**: The coder in-scope filter strips `[OUT_OF_SCOPE]` but not `[OOS]`, while tally treats `[OOS]` as out-of-scope. `[OOS]` findings that reach `accepted-findings.md` may be sent to the coder as in-scope.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Address the concern above.
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.

### FINDING_4: Security routing classifier is duplicated across surfaces
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-security-output.txt, cursor-specialist-edge-cases-output.txt, dyn-bash-portability-output.txt, dyn-parity-output.txt
- **Severity**: latent
- **Concern**: Security routing/classification logic is duplicated across tally, serializer, Python, and gate-counting paths, with slightly different rules and failure handling. Future drift could make one layer hold/filter a security block while another counts or serializes it publicly.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Address the concern above.
  - From cursor-specialist-security-output.txt: Address the concern above.
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.
  - From dyn-bash-portability-output.txt: Address the concern above.
  - From dyn-parity-output.txt: Address the concern above.

### FINDING_5: [OUT_OF_SCOPE] Serializer ignores direct `### OOS_N:` blocks
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, dyn-bash-portability-output.txt, dyn-oos-pipeline-output.txt, dyn-parity-output.txt
- **Severity**: latent
- **Concern**: `oos-serialize.sh` only splits on `### FINDING_N:` headings and ignores direct `### OOS_N:` headings. Some sources mark this pre-existing/out-of-scope, but one in-scope source notes the new desync rebuild path may now depend on this serializer and stall review/ship when `oos.md` contains direct OOS ballots.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Address the concern above.
  - From dyn-bash-portability-output.txt: Address the concern above.
  - From dyn-oos-pipeline-output.txt: Address the concern above.
  - From dyn-parity-output.txt: Address the concern above.

### FINDING_6: Checkpoint harness lacks legacy FINDING disposition-gap coverage
- **Reviewer(s)**: cursor-specialist-testing-output.txt, dyn-harness-wiring-output.txt
- **Severity**: latent
- **Concern**: Gate-level legacy-header cases exist, but checkpoint disposition-gap tests still use only `### OOS_1:`. A regression in legacy counting on the checkpoint path could let Step 8+ proceed incorrectly.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.
  - From dyn-harness-wiring-output.txt: Address the concern above.

### FINDING_7: Missing mixed security plus public OOS tally round test
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: latent
- **Concern**: There is no test for a round containing both security-held and public accepted OOS. A regression could mis-set public OOS counts or leak security-routed blocks into public sinks.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.

### FINDING_8: Missing awk/Python parity coverage for legacy OOS counting
- **Reviewer(s)**: cursor-specialist-testing-output.txt, dyn-parity-output.txt, dyn-harness-wiring-output.txt
- **Severity**: latent
- **Concern**: Legacy header counting was extended in both awk and Python, but tests assert most cases separately rather than mechanically comparing both counters on the same fixtures. Regex drift could pass isolated suites while ship/gate behavior diverges.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.
  - From dyn-parity-output.txt: Address the concern above.
  - From dyn-harness-wiring-output.txt: Address the concern above.

### FINDING_9: Missing issue filing regression for normalized OOS sinks
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: latent
- **Concern**: Normalized OOS headers may parse and pass gates but still fail in `/issue` batch/combine/cap/dependency paths, yielding `OOS filed: 0` at runtime.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.

### FINDING_10: Missing emit-tally serialize-failure harness
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: nit
- **Concern**: `emit-tally` now propagates `oos-serialize` failures, but there is no harness proving failure propagation when `OOS_ACCEPTED_COUNT=0`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.

### FINDING_11: [OUT_OF_SCOPE] Review-core stubs cannot test production tally-to-emit chain
- **Reviewer(s)**: cursor-specialist-testing-output.txt, dyn-harness-wiring-output.txt
- **Severity**: latent
- **Concern**: `test-review-core.sh` stubs the production emit path, so production tally-to-emit overwrite bugs must remain covered by dedicated harnesses instead of review-core tests.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.
  - From dyn-harness-wiring-output.txt: Address the concern above.

### FINDING_12: [OUT_OF_SCOPE] Design tally tests lack expanded security-routing fixtures
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: latent
- **Concern**: Design-path tally integration tests were not updated for expanded security routing forms, leaving design tally regression coverage behind the shared library behavior.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.

### FINDING_13: Public filing can expose accepted OOS vulnerability details without security tokens
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: latent
- **Concern**: Accepted legacy/scope-drift OOS blocks without explicit security-routing tokens are now normalized and filed publicly. A vulnerability-shaped OOS finding without `focus-area: security` or `[security]` heading could become a public GitHub issue.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Address the concern above.

### FINDING_14: Gate counter misses prose-only security markers
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: latent
- **Concern**: `oos-non-security-block-count.awk` excludes only some security forms and may count accepted OOS with unfenced `focus-area = security` prose as non-security if producer screening is bypassed.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Address the concern above.

### FINDING_15: Serializer now hard-depends on python3 on fallback paths
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt, dyn-bash-portability-output.txt
- **Severity**: important
- **Concern**: `oos-serialize.sh` now requires `python3`, and `emit-tally` no longer ignores serializer failures. Standalone or zero-OOS/fallback paths that used to be awk-only can now hard-fail if `python3` is unavailable or broken.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.
  - From dyn-bash-portability-output.txt: Address the concern above.

### FINDING_16: Emit-tally desync rebuild can lose or fail on normalized/scope-drift OOS
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt, cursor-specialist-plan-fidelity-output.txt, dyn-oos-pipeline-output.txt
- **Severity**: latent
- **Concern**: `emit-tally` preserves tally output only when sink count equals `OOS_ACCEPTED_COUNT`; otherwise it rebuilds from `oos.md`. Scope-drift or normalized sink-only OOS may not be reproducible from `oos.md`, causing loss, destructive overwrite, or fail-closed behavior.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.
  - From cursor-specialist-plan-fidelity-output.txt: Address the concern above.
  - From dyn-oos-pipeline-output.txt: Address the concern above.

### FINDING_17: [OUT_OF_SCOPE] Final zero-OOS round can clobber accumulated review OOS mirror
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt, dyn-oos-pipeline-output.txt
- **Severity**: important
- **Concern**: In multi-round runs, a later round with no accepted/skipped OOS can overwrite the parent `oos-accepted-review.md` with an empty file while durable OOS remain only in `accumulated-oos.md`, making gate input empty.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.
  - From dyn-oos-pipeline-output.txt: Address the concern above.

### FINDING_18: [OUT_OF_SCOPE] Design OOS producers still emit legacy headers
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: Design-path OOS producers were not normalized, so legacy `FINDING` headers in `oos-accepted-design.md` can still be dropped by counters/gates in mixed design+review runs.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.

### FINDING_19: [OUT_OF_SCOPE] Legacy OOS tag matching is case-sensitive
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: Variant casings such as `[out_of_scope]` can bypass normalization paths and still count as zero at the gate.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.

### FINDING_20: Plan scope does not cover security-classifier changes
- **Reviewer(s)**: cursor-specialist-plan-fidelity-output.txt
- **Severity**: important
- **Concern**: The plan forbids vote-tally logic changes, but the branch rewrites `is_security_block` and updates related security/voting docs outside the planned file list. This changes security routing without an explicit plan amendment.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-plan-fidelity-output.txt: Address the concern above.

### FINDING_21: Plan scope does not cover serializer normalization/classification changes
- **Reviewer(s)**: cursor-specialist-plan-fidelity-output.txt
- **Severity**: important
- **Concern**: The plan limited normalization to tally and review-and-fix and said `oos-serialize` stays unchanged on the tally-wrote path, but the serializer now normalizes and uses Python security classification on fallback paths.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-plan-fidelity-output.txt: Address the concern above.

### FINDING_22: Reader regex behavior exceeds documented plan literals
- **Reviewer(s)**: cursor-specialist-plan-fidelity-output.txt
- **Severity**: nit
- **Concern**: Reader backstops match `[OOS]` shorthand and trailing OUT_OF_SCOPE tags beyond the plan’s literal `FINDING_N: [OUT_OF_SCOPE]` form, making plan-to-code traceability incomplete.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-plan-fidelity-output.txt: Address the concern above.

### FINDING_23: Serializer classifier read errors can be treated as non-security
- **Reviewer(s)**: dyn-bash-portability-output.txt
- **Severity**: important
- **Concern**: The duplicate Python classifier in `oos-serialize.sh` lacks the hardened `OSError` handling contract. A read failure may exit with status 1, which `flush_block` treats as non-security, allowing security-tagged content into the public accepted-OOS sink.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-bash-portability-output.txt: Address the concern above.

### FINDING_24: Serializer writes output non-atomically and can leave partial public sinks
- **Reviewer(s)**: dyn-bash-portability-output.txt
- **Severity**: latent
- **Concern**: `flush_block` writes incrementally to `$OUTPUT_FILE` and exits on classifier failure. A mid-file failure after earlier blocks can leave a partially written public sink.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-bash-portability-output.txt: Address the concern above.

### FINDING_25: [OUT_OF_SCOPE] Normalized temp OOS blocks are not deleted
- **Reviewer(s)**: dyn-bash-portability-output.txt
- **Severity**: nit
- **Concern**: `tally-code-votes.sh` writes normalized temporary OOS block files and never deletes them. This is harmless for typical rounds and unrelated to the reviewed portability surface.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-bash-portability-output.txt: Address the concern above.

### FINDING_26: [OUT_OF_SCOPE] Degraded-panel retry can duplicate accumulated OOS
- **Reviewer(s)**: dyn-oos-pipeline-output.txt
- **Severity**: latent
- **Concern**: Degraded-panel retry calls `append_round_oos_artifact` before and after retry, which can duplicate the same round’s accepted OOS in `accumulated-oos.md` and inflate gate counts.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-oos-pipeline-output.txt: Address the concern above.

### FINDING_27: [OUT_OF_SCOPE] OOS pipeline docs disagree on accumulated versus mirror authority
- **Reviewer(s)**: dyn-oos-pipeline-output.txt
- **Severity**: latent
- **Concern**: Step 9a.1 guidance and normative OOS pipeline references disagree about whether accumulated review OOS or `$IMPLEMENT_TMPDIR/oos-accepted-review.md` is authoritative, which can still drop review OOS when mirrors are empty.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-oos-pipeline-output.txt: Address the concern above.

### FINDING_28: Emit-to-ship tests do not compare awk and Python counts on final sinks
- **Reviewer(s)**: dyn-parity-output.txt
- **Severity**: latent
- **Concern**: The review→ship path now has separate awk and Python counting authorities, but chained emit-tally tests do not compare both counts on final `oos-accepted-review.md` artifacts before ship.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-parity-output.txt: Address the concern above.

### FINDING_29: Emit-tally tests miss malformed or missing `OOS_ACCEPTED_COUNT`
- **Reviewer(s)**: dyn-harness-wiring-output.txt
- **Severity**: latent
- **Concern**: `emit-tally` coerces absent or non-numeric `OOS_ACCEPTED_COUNT` to zero, which can route through serialize/truncate and wipe a pre-populated normalized sink. Tests only cover clean integer counts.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-harness-wiring-output.txt: Address the concern above.

### FINDING_30: Canonical-header tests use file-wide `FINDING` greps that can false-fail body citations
- **Reviewer(s)**: dyn-harness-wiring-output.txt
- **Severity**: latent
- **Concern**: Several regression checks use file-wide `grep -Eq '^### FINDING_'` to prove canonical headers, but normalization intentionally preserves `### FINDING_N:` citations inside block bodies. Valid fixtures could therefore fail CI.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-harness-wiring-output.txt: Address the concern above.

### FINDING_31: [OUT_OF_SCOPE] Issue parser lacks legacy FINDING fixture
- **Reviewer(s)**: dyn-harness-wiring-output.txt
- **Severity**: latent
- **Concern**: `/issue` parsing still keys batch parsing on `### OOS_N:` only and lacks a legacy `FINDING` fixture. The source marks this pre-existing and deferred to producer normalization.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-harness-wiring-output.txt: Address the concern above.
