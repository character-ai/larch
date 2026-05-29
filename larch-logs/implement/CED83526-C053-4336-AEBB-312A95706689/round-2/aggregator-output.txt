### FINDING_1: Dispatch or monitor failure can still tally partial assessor outputs
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-edge-cases-output.txt, dyn-breadcrumb-pair-contract-output.txt
- **Severity**: important
- **Concern**: `assess-plan-round.sh` continues into `tally-plan-assessor.sh` after `DISPATCH_OK=false`, non-zero dispatch exit, or breadcrumb monitor failure. Partial or stale assessor files can produce a WORSE majority and Step 3.6 Continue/Stop prompt even though the panel infrastructure failed. The test harness currently reinforces this behavior in at least one case.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-edge-cases-output.txt, dyn-breadcrumb-pair-contract-output.txt: Address the concern above.

### FINDING_2: Step 3.6 skips post-Gate-B snapshot when feature-description.txt is missing
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, dyn-cursor-write-last-output.txt
- **Severity**: important
- **Concern**: `skills/design/SKILL.md` gates `snapshot-plan-round.sh write-after` on the same missing-feature-file branch as assessor dispatch. A HARD Gate B round can settle without writing `plan-after-round-N.txt`, leaving the cursor ahead of snapshots and stalling later multi-round assessor progress.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt, dyn-cursor-write-last-output.txt: Address the concern above.

### FINDING_3: Write-after failure policy is inconsistent with missing-snapshot fail-open behavior
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-edge-cases-output.txt
- **Severity**: important
- **Concern**: `write-after` failure currently exits 1 and aborts `/design`, while missing snapshots inside `assess-plan-round.sh` warn and fail open. The implementation and docs need a single policy: either fail open and skip assessment, or document and enforce a hard stop.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt, cursor-specialist-edge-cases-output.txt: Address the concern above.

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

### FINDING_6: KV parsing is duplicated and lacks a canonical helper or contract
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: Step 3, Step 3.6, and `assess-plan-round.sh` each parse KV output independently. Future contract changes require coordinated edits in multiple places.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.

### FINDING_7: Structural tests do not pin Gate B forwarding into Step 3.6
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Severity**: important
- **Concern**: `scripts/test-design-structure.sh` and related docs still allow Gate B prose or pins to bypass Step 3.6, including stale zero-findings text in `plan-review.md`. CI may block the intended doc update or miss a future bypass.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-plan-fidelity-output.txt: Address the concern above.

### FINDING_8: Cancelled assessor summary title patch is brittle
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: latent
- **Concern**: `patch_assessor_worse_title` assumes the title is line 1. A renderer layout change could break cancelled-assessor-worse titles without obvious failure.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.

### FINDING_9: Tally parser can drop valid ASSESSMENT lines
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, dyn-tally-bash32-output.txt
- **Severity**: latent
- **Concern**: `tally-plan-assessor.sh` only recognizes limited top-position/header spellings and colon separators, while dispatch accepts broader case mixes and `:` or `=`. Valid assessor outputs can pass dispatch but be treated as unparseable, changing WORSE-majority results.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt, dyn-tally-bash32-output.txt: Address the concern above.

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

### FINDING_15: Assessor reasoning can inject or bloat verdict/env output
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: important
- **Concern**: External `QUALIFICATIONS` and `REASONING` text is written into `.env` and verdict artifacts without newline/control-character sanitization or length limits. Malicious output can inject misleading KV-like lines or operator-facing rationale.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Address the concern above.

### FINDING_16: Step 3.6 surfaces untrusted assessor rationale in the operator prompt
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: important
- **Concern**: `QUALIFICATIONS_SUMMARY` from external assessors is shown in the Continue/Stop prompt without an untrusted-content contract or truncation, allowing prompt-injection-style pressure at a blocking gate.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Address the concern above.

### FINDING_17: Assessor output paths from quiet log are not confined to DESIGN_TMPDIR
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: important
- **Concern**: `assess-plan-round.sh` trusts output path KVs parsed from the quiet log, allowing a tampered log to point tally at arbitrary local files instead of constructed files under `DESIGN_TMPDIR`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Address the concern above.

### FINDING_18: Assessor prompts can expose secrets to external tools
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: latent
- **Concern**: `render-assessor-prompt.sh` includes full plan and feature text for Codex/Cursor without redaction or explicit security documentation. Secrets pasted into design artifacts can be sent to third-party APIs and retained in session bundles.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Address the concern above.

### FINDING_19: Missing-snapshot fail-open can bypass the WORSE gate under session-dir tampering
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: latent
- **Concern**: If the threat model includes mutation of files under `DESIGN_TMPDIR`, missing-snapshot and degraded paths can force NOT_WORSE/skipped behavior and avoid operator acknowledgement.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Address the concern above.

### FINDING_20: tally-plan-assessor does not validate tmpdir or output path roots
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: nit
- **Concern**: Direct invocation or future callers can pass `--*-output` paths outside the session dir because `tally-plan-assessor.sh` does not validate `DESIGN_TMPDIR` or confine inputs.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Address the concern above.

### FINDING_21: HARD assessor gate depends on jq without fallback
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: important
- **Concern**: If `jq` is unavailable, `assess-plan-round.sh` may fail to read `workflow_path` and skip the HARD quality gate while `/design` proceeds.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.

### FINDING_22: write-after snapshot preservation can leave stale after-round inputs
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: `snapshot-plan-round.sh write-after` is write-once. Re-entering the same round after `plan.txt` changes can leave `plan-after-round-N.txt` stale, so assessor comparisons use the wrong baseline.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.

### FINDING_23: Some short-circuit statuses skip Step 3.6 and may leave ambiguous baselines
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: `cap-reached` and degraded-empty-collector paths skip Step 3.6. Later Gate C re-entry may interact with old after-round files unless cursor advancement explicitly accounts for whether Step 3.6 completed.
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

### FINDING_29: [OUT_OF_SCOPE] Claude assessor dispatch is synchronous
- **Reviewer(s)**: cursor-specialist-correctness-output.txt
- **Severity**: nit
- **Concern**: Claude assessor runs synchronously before the waterfall instead of parallel with all three slots. This affects latency, not verdict correctness.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Address the concern above.

### FINDING_30: [OUT_OF_SCOPE] Dispatch failure behavior also observed by out-of-scope reviewers
- **Reviewer(s)**: cursor-specialist-testing-output.txt, dyn-tally-bash32-output.txt
- **Severity**: nit
- **Concern**: Out-of-scope review notes also observed that `assess-plan-round.sh` tallies after `DISPATCH_OK=false` and that tests currently expect partial outputs to be tallied, diverging from the written plan.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt, dyn-tally-bash32-output.txt: Address the concern above.

### FINDING_31: [OUT_OF_SCOPE] Cursor/snapshot sequencing mostly verified OK
- **Reviewer(s)**: dyn-cursor-write-last-output.txt
- **Severity**: nit
- **Concern**: The split sequencing between cursor advancement, write-after, and atomic snapshot/cursor paths appears intentional and mostly sound when the feature file is present.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-cursor-write-last-output.txt: Address the concern above.

### FINDING_32: [OUT_OF_SCOPE] Short-circuit paths skip Step 3.6 by design
- **Reviewer(s)**: dyn-cursor-write-last-output.txt
- **Severity**: nit
- **Concern**: Some degraded or cap-reached paths omit `plan-after-round-N.txt`, but Step 3’s advance-only-if-snapshot-exists rule may prevent permanent cursor drift on re-entry.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-cursor-write-last-output.txt: Address the concern above.

### FINDING_33: [OUT_OF_SCOPE] FD3 routing itself is probably not silently empty
- **Reviewer(s)**: dyn-breadcrumb-pair-contract-output.txt
- **Severity**: nit
- **Concern**: `dispatch-plan-assessors.sh` emits KVs through FD3, and under quiet init those lines should land in the quiet log. The main risks are noisy parsing and missing tests, not silent FD3 loss.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-breadcrumb-pair-contract-output.txt: Address the concern above.

### FINDING_34: [OUT_OF_SCOPE] Branch commit list was reported
- **Reviewer(s)**: dyn-breadcrumb-pair-contract-output.txt
- **Severity**: nit
- **Concern**: Reviewer reported branch commits since merge-base with `main`; this is diagnostic context, not a code finding.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-breadcrumb-pair-contract-output.txt: Address the concern above.

### FINDING_35: [OUT_OF_SCOPE] Bash 3.2 array usage appears acceptable
- **Reviewer(s)**: dyn-tally-bash32-output.txt
- **Severity**: nit
- **Concern**: Bash 3.2 portability for array constructs in `tally-plan-assessor.sh` appears consistent with repo practice; no defect was found there.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-tally-bash32-output.txt: Address the concern above.

### FINDING_36: [OUT_OF_SCOPE] strip_md_bold removes all asterisks but behaves acceptably
- **Reviewer(s)**: dyn-tally-bash32-output.txt
- **Severity**: nit
- **Concern**: `strip_md_bold` removes all `*` characters on header lines rather than paired bold markers only, but this still handles the intended bold-header cases.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-tally-bash32-output.txt: Address the concern above.

### FINDING_37: [OUT_OF_SCOPE] Pre-existing voter timing-kind drift
- **Reviewer(s)**: dyn-timing-kind-allowlist-output.txt
- **Severity**: nit
- **Concern**: The same phase-qualified timing-kind synthesis drift exists for plan voters and predates this assessor branch.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-timing-kind-allowlist-output.txt: Address the concern above.
