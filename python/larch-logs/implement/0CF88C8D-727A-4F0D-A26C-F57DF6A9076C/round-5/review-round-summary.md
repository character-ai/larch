# Review Round 5

- Mode: `diff`
- 10 accepted, 10 rejected (10 exonerated)

## Accepted Findings

### FINDING_10: Missing emit-tally serialize-failure harness
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: nit
- **Concern**: `emit-tally` now propagates `oos-serialize` failures, but there is no harness proving failure propagation when `OOS_ACCEPTED_COUNT=0`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.


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


### FINDING_2: Legacy accumulated OOS seed can collide or stay gate-invisible
- **Reviewer(s)**: cursor-specialist-correctness-output.txt
- **Severity**: latent
- **Concern**: `OOS_WRITE_SEQ` seeding ignores bare `FINDING_` headers already present in `accumulated-oos.md`, so resumed runs can leave legacy OOS gate-invisible or assign colliding `OOS_` IDs.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Address the concern above.


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


### FINDING_23: Serializer classifier read errors can be treated as non-security
- **Reviewer(s)**: dyn-bash-portability-output.txt
- **Severity**: important
- **Concern**: The duplicate Python classifier in `oos-serialize.sh` lacks the hardened `OSError` handling contract. A read failure may exit with status 1, which `flush_block` treats as non-security, allowing security-tagged content into the public accepted-OOS sink.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-bash-portability-output.txt: Address the concern above.


### FINDING_3: Coder in-scope filter misses `[OOS]` shorthand
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt
- **Severity**: important
- **Concern**: The coder in-scope filter strips `[OUT_OF_SCOPE]` but not `[OOS]`, while tally treats `[OOS]` as out-of-scope. `[OOS]` findings that reach `accepted-findings.md` may be sent to the coder as in-scope.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Address the concern above.
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.


### FINDING_30: Canonical-header tests use file-wide `FINDING` greps that can false-fail body citations
- **Reviewer(s)**: dyn-harness-wiring-output.txt
- **Severity**: latent
- **Concern**: Several regression checks use file-wide `grep -Eq '^### FINDING_'` to prove canonical headers, but normalization intentionally preserves `### FINDING_N:` citations inside block bodies. Valid fixtures could therefore fail CI.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-harness-wiring-output.txt: Address the concern above.


### FINDING_6: Checkpoint harness lacks legacy FINDING disposition-gap coverage
- **Reviewer(s)**: cursor-specialist-testing-output.txt, dyn-harness-wiring-output.txt
- **Severity**: latent
- **Concern**: Gate-level legacy-header cases exist, but checkpoint disposition-gap tests still use only `### OOS_1:`. A regression in legacy counting on the checkpoint path could let Step 8+ proceed incorrectly.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.
  - From dyn-harness-wiring-output.txt: Address the concern above.


