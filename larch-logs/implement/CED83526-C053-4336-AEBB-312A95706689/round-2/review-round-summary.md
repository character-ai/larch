# Review Round 2

- Mode: `diff`
- 18 accepted, 10 rejected (10 exonerated)

## Accepted Findings

### FINDING_1: Dispatch or monitor failure can still tally partial assessor outputs
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-edge-cases-output.txt, dyn-breadcrumb-pair-contract-output.txt
- **Severity**: important
- **Concern**: `assess-plan-round.sh` continues into `tally-plan-assessor.sh` after `DISPATCH_OK=false`, non-zero dispatch exit, or breadcrumb monitor failure. Partial or stale assessor files can produce a WORSE majority and Step 3.6 Continue/Stop prompt even though the panel infrastructure failed. The test harness currently reinforces this behavior in at least one case.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-edge-cases-output.txt, dyn-breadcrumb-pair-contract-output.txt: Address the concern above.


### FINDING_10: Base timing slugs for Codex and Cursor assessors are missing
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-edge-cases-output.txt, dyn-timing-kind-allowlist-output.txt
- **Severity**: nit
- **Concern**: `scripts/lib-timing-kinds.sh` lacks `codex-plan-assessor` and `cursor-plan-assessor` despite plan/acceptance references. Runtime may currently use phase-qualified kinds, but the allowlist is incomplete versus the documented contract unless that contract is narrowed.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-edge-cases-output.txt, dyn-timing-kind-allowlist-output.txt: Address the concern above.


### FINDING_11: Tally test matrix is incomplete
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: important
- **Concern**: `test-tally-plan-assessor.sh` lacks strict-majority, all-TIE, and zero-effective-assessor cases. Changes to WORSE/NOT_WORSE outcomes could pass CI.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.


### FINDING_12: Assess-round harness omits required skip and degraded paths
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: important
- **Concern**: `test-assess-plan-round.sh` does not cover TRIVIAL skip, missing snapshot warning paths, 0/3 effective assessor degraded-default-open behavior, or stale-file dispatch-failure regression coverage.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.


### FINDING_13: Dispatch assessor harness misses degraded-panel and regex contract coverage
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: important
- **Concern**: `test-dispatch-plan-assessors.sh` does not exercise absent Codex/Cursor scenarios, pin the exact `ASSESSMENT_PATTERN`, or compare manifest grammar with voter precedent.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.


### FINDING_14: Multi-round integration lacks assessor snapshot and cursor coverage
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: latent
- **Concern**: `test-design-multi-round-integration.sh` does not cover HARD re-entry through a second review round with assessor artifacts and cursor assertions. Unit mocks may miss end-to-end desync.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.


### FINDING_16: Step 3.6 surfaces untrusted assessor rationale in the operator prompt
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: important
- **Concern**: `QUALIFICATIONS_SUMMARY` from external assessors is shown in the Continue/Stop prompt without an untrusted-content contract or truncation, allowing prompt-injection-style pressure at a blocking gate.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Address the concern above.


### FINDING_2: Step 3.6 skips post-Gate-B snapshot when feature-description.txt is missing
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, dyn-cursor-write-last-output.txt
- **Severity**: important
- **Concern**: `skills/design/SKILL.md` gates `snapshot-plan-round.sh write-after` on the same missing-feature-file branch as assessor dispatch. A HARD Gate B round can settle without writing `plan-after-round-N.txt`, leaving the cursor ahead of snapshots and stalling later multi-round assessor progress.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt, dyn-cursor-write-last-output.txt: Address the concern above.


### FINDING_21: HARD assessor gate depends on jq without fallback
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: important
- **Concern**: If `jq` is unavailable, `assess-plan-round.sh` may fail to read `workflow_path` and skip the HARD quality gate while `/design` proceeds.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.


### FINDING_24: Dispatch KV recovery parses noisy quiet log instead of a dedicated contract stream
- **Reviewer(s)**: dyn-breadcrumb-pair-contract-output.txt
- **Severity**: important
- **Concern**: `assess-plan-round.sh` parses `DISPATCH_OK` and assessor path KVs from `LARCH_QUIET_LOG_FILE`, which can contain launcher stderr, warnings, and breadcrumbs. A spurious line can corrupt control flow.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-breadcrumb-pair-contract-output.txt: Address the concern above.


### FINDING_25: Assess-round tests do not exercise production quiet-mode monitor/KV wiring
- **Reviewer(s)**: dyn-breadcrumb-pair-contract-output.txt
- **Severity**: important
- **Concern**: The harness sets `LARCH_QUIET_DISABLE=1` and stubs monitor/dispatch, so CI does not cover the real background + breadcrumb-monitor + FD3/quiet-log path used in production.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-breadcrumb-pair-contract-output.txt: Address the concern above.


### FINDING_26: Duplicate ASSESSMENT blocks can retain stale reasoning and qualifications
- **Reviewer(s)**: dyn-tally-bash32-output.txt
- **Severity**: important
- **Concern**: On a second `ASSESSMENT:` line, the tally parser resets section flags but not accumulated reasoning or qualifications, so stale rationale can attach to the final verdict shown to the operator.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-tally-bash32-output.txt: Address the concern above.


### FINDING_27: Claude phase-qualified assessor timing kinds are missing
- **Reviewer(s)**: dyn-timing-kind-allowlist-output.txt
- **Severity**: important
- **Concern**: `dispatch-with-waterfall.sh` can emit `claude-phaseN-plan-assessor` timing kinds, especially phase-3 fallback, but the allowlist only includes unqualified `claude-plan-assessor`. Degraded assessor work can produce unknown-kind warnings and missing telemetry.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-timing-kind-allowlist-output.txt: Address the concern above.


### FINDING_28: Structural pins do not cover all assessor timing kinds
- **Reviewer(s)**: dyn-timing-kind-allowlist-output.txt
- **Severity**: important
- **Concern**: New checks only pin `claude-plan-assessor` and `codex-phase1-plan-assessor`, so CI can miss removal of other Codex/Cursor phase variants or Claude fallback kinds.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-timing-kind-allowlist-output.txt: Address the concern above.


### FINDING_4: Assessor documentation is too thin for the new orchestration contract
- **Reviewer(s)**: cursor-specialist-structure-output.txt, dyn-breadcrumb-pair-contract-output.txt
- **Severity**: nit
- **Concern**: `assess-plan-round.md` does not fully describe argv/KV behavior, dispatch failure policy, or the intentional background-monitor asymmetry versus foreground voter dispatch. This creates drift risk for future maintainers.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt, dyn-breadcrumb-pair-contract-output.txt: Address the concern above.


### FINDING_5: Snapshot harness lacks idempotence, failure, and atomic-write coverage
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-testing-output.txt
- **Severity**: important
- **Concern**: `test-snapshot-plan-round.sh` does not cover interrupted atomic rename behavior, write-after idempotence/preservation, write-after failure, argv validation, or cursor/snapshot desync cases. Regressions in snapshot integrity could pass CI.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt, cursor-specialist-testing-output.txt: Address the concern above.


### FINDING_7: Structural tests do not pin Gate B forwarding into Step 3.6
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Severity**: important
- **Concern**: `scripts/test-design-structure.sh` and related docs still allow Gate B prose or pins to bypass Step 3.6, including stale zero-findings text in `plan-review.md`. CI may block the intended doc update or miss a future bypass.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-plan-fidelity-output.txt: Address the concern above.


### FINDING_9: Tally parser can drop valid ASSESSMENT lines
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, dyn-tally-bash32-output.txt
- **Severity**: latent
- **Concern**: `tally-plan-assessor.sh` only recognizes limited top-position/header spellings and colon separators, while dispatch accepts broader case mixes and `:` or `=`. Valid assessor outputs can pass dispatch but be treated as unparseable, changing WORSE-majority results.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt, dyn-tally-bash32-output.txt: Address the concern above.


