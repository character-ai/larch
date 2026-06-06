### FINDING_1: Scope-anchor terminal gating is duplicated/incomplete across handoff layers
- **Reviewer(s)**: cursor-specialist-structure-output.txt, dyn-scope-flow-output.txt, dyn-ship-cutover-output.txt
- **Severity**: important
- **Concern**: Loop, Step 3 driver, orchestrator prose, and recovery fallback paths each own part of the `SCOPE_ANCHOR_FILE` terminal-gating contract. Drift or missing clearing can leave durable handoff envs, stdout parsing, or fallback recovery disagreeing about whether an anchor is valid on `tally-error` / `panel-failed`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.
  - From dyn-scope-flow-output.txt: Address the concern above.
  - From dyn-ship-cutover-output.txt: Address the concern above.

### FINDING_2: Scope-anchor path validators have inconsistent containment contracts
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-security-output.txt, dyn-bash-contracts-output.txt
- **Severity**: important
- **Concern**: Voter, aggregator, and plan-review renderers validate anchor paths with different allowed-root policies. The voter validator is both too broad for repo-local files and too narrow for custom `TMPDIR` sessions, risking either unintended prompt inclusion or broken valid design runs.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.
  - From cursor-specialist-security-output.txt: Address the concern above.
  - From dyn-bash-contracts-output.txt: Address the concern above.

### FINDING_3: Assessor scope-anchor path validation is weaker than other consumers
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-security-output.txt
- **Severity**: important
- **Concern**: Assessor dispatch/rendering hardens feature content but does not consistently enforce the staged-anchor path contract before reading it. Legacy fallback or symlinked staged-anchor paths can bypass symlink, size, CR/LF, or containment checks used elsewhere.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.
  - From cursor-specialist-security-output.txt: Address the concern above.

### FINDING_4: Literal-redacted untrusted-block rendering is duplicated and inconsistent
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Severity**: important
- **Concern**: Multiple scripts reimplement untrusted block emission, redaction, escaping, or framing attributes instead of using one helper. Subprocess context blocks also lack the same `encoding="literal-redacted"` contract used by other surfaces.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.
  - From cursor-specialist-correctness-output.txt: Address the concern above.
  - From cursor-specialist-plan-fidelity-output.txt: Address the concern above.

### FINDING_5: [OUT_OF_SCOPE] Scope-reduction dedup logic is embedded and duplicated
- **Reviewer(s)**: cursor-specialist-structure-output.txt, dyn-ship-cutover-output.txt
- **Severity**: latent
- **Concern**: Plan-review dedup now has large inline Python and multiple overlapping implementations of marker/problem-text normalization, making the god-script harder to test and easier to drift from the marker helper.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.
  - From dyn-ship-cutover-output.txt: Address the concern above.

### FINDING_6: Dedup bracket stripping diverges from marker normalization
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-edge-cases-output.txt
- **Severity**: important
- **Concern**: `comparison_text()` strips arbitrary leading bracket tags while marker detection strips a narrower set. Custom focus/severity prefixes can therefore be preserved by one path but deduped or merged by another, potentially dropping distinct findings.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.
  - From cursor-specialist-correctness-output.txt: Address the concern above.
  - From cursor-specialist-testing-output.txt: Address the concern above.
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.

### FINDING_7: Duplicate Makefile harness target
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: `test-check-scope-reduction-marker` runs in two harness shards, wasting CI/full-lint time.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.

### FINDING_8: [OUT_OF_SCOPE] Branch bundles unrelated scope-anchor and Python ship-default work
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Severity**: important
- **Concern**: The branch mixes plan-review scope-anchor changes with Python ship-default and other initiatives, making regressions, review traceability, and reverts harder to isolate.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.
  - From cursor-specialist-plan-fidelity-output.txt: Address the concern above.

### FINDING_9: [OUT_OF_SCOPE] Scout/read-tools scope context lacks inline literal-redacted hardening
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: latent
- **Concern**: Scout scope context does not use the same inline literal-redacted block framing as other prompt surfaces, so untrusted issue prose can influence archetype selection with weaker delimiter hardening.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.

### FINDING_10: Round summaries persist ungated SCOPE_ANCHOR_FILE on failed terminals
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt, cursor-specialist-plan-fidelity-output.txt, dyn-scope-flow-output.txt, dyn-bash-contracts-output.txt, dyn-docs-contracts-output.txt
- **Severity**: important
- **Concern**: `_write_round_summary` records the materialized anchor path even when normalized stdout and Step 3 result envs omit it on `tally-error` / `panel-failed`. This creates conflicting durable artifacts and can mislead forensic consumers or automation.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Address the concern above.
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.
  - From cursor-specialist-plan-fidelity-output.txt: Address the concern above.
  - From dyn-scope-flow-output.txt: Address the concern above.
  - From dyn-bash-contracts-output.txt: Address the concern above.
  - From dyn-docs-contracts-output.txt: Address the concern above.

### FINDING_11: Marker consolidation changed scope-reduction detection case sensitivity
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt, cursor-specialist-plan-fidelity-output.txt, dyn-bash-contracts-output.txt
- **Severity**: important
- **Concern**: Consolidation changed marker detection from uppercase/case-sensitive semantics to case-insensitive matching. Lowercase `[scope-reduction]` can now classify as present where prior behavior returned absent.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Address the concern above.
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.
  - From cursor-specialist-plan-fidelity-output.txt: Address the concern above.
  - From dyn-bash-contracts-output.txt: Address the concern above.

### FINDING_12: [OUT_OF_SCOPE] Legacy single-pass tally errors keep LOOP_STATUS=complete
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: Legacy single-pass tally failures keep `LOOP_STATUS=complete` while multi-round failures use `tally-error`, so orchestrator short-circuit logic can diverge between paths.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Address the concern above.
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.

### FINDING_13: Scope-anchor validation gates lack negative regression coverage
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: important
- **Concern**: New oversize, disallowed-path, and CR/LF anchor validation behavior is not fully pinned by executable harnesses, so invalid anchors could be silently accepted or leak if relay guards regress.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.

### FINDING_14: Re-tally scope-anchor refresh is prose-only
- **Reviewer(s)**: cursor-specialist-testing-output.txt, dyn-scope-flow-output.txt
- **Severity**: important
- **Concern**: MainAgent re-tally refresh of `SCOPE_ANCHOR_FILE` handoff state depends on prompt/orchestrator discipline rather than a script helper. A sloppy `tally-error` refresh could leave stale anchor keys in one or both Step 3 env files.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.
  - From dyn-scope-flow-output.txt: Address the concern above.

### FINDING_15: relevant-checks can soft-skip Python checks when Python files changed
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: important
- **Concern**: Local `relevant-checks` no longer fail closed when `python/*.py` changes but Python tools are missing, allowing large Python driver changes to bypass local py-lint/py-test.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.

### FINDING_16: Python support policy is unclear after CI narrows to 3.12
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: latent
- **Concern**: CI now runs Python 3.12 only, while contributors on 3.11 may still believe that version is supported.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.

### FINDING_17: [OUT_OF_SCOPE] Assessor plan snapshots remain raw markdown fences
- **Reviewer(s)**: cursor-specialist-security-output.txt, cursor-specialist-edge-cases-output.txt, dyn-docs-contracts-output.txt
- **Severity**: latent
- **Concern**: Assessor feature blocks are hardened, but plan snapshot sections are still raw-catted into markdown fences. Malicious plan content can break prompt framing and inject assessor-steering text.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Address the concern above.
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.
  - From dyn-docs-contracts-output.txt: Address the concern above.

### FINDING_18: [OUT_OF_SCOPE] Python ship default proceeds despite documented security/parity gaps
- **Reviewer(s)**: cursor-specialist-security-output.txt, dyn-ship-cutover-output.txt
- **Severity**: latent
- **Concern**: `python/ship.py` is default Step 8+ while SECURITY/docs still describe unresolved review/parity gaps, exposing operators to a less-reviewed publication/merge path.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Address the concern above.
  - From dyn-ship-cutover-output.txt: Address the concern above.

### FINDING_19: Aggregator silently omits invalid scope anchors
- **Reviewer(s)**: cursor-specialist-security-output.txt, cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: Invalid or stale aggregator scope-anchor paths fail validation by omitting the anchor block without warning, leaving operators unaware that aggregation ran without scope context.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Address the concern above.
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.

### FINDING_20: [OUT_OF_SCOPE] Raw reviewer findings are inlined without escaping
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: latent
- **Concern**: Aggregator inputs still inline raw reviewer prose without the literal-redacted untrusted block contract, allowing findings prose to inject instructions adjacent to hardened scope-anchor content.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Address the concern above.

### FINDING_21: [OUT_OF_SCOPE] Docs still mention voter --scope-anchor-file argv
- **Reviewer(s)**: cursor-specialist-security-output.txt, dyn-ship-cutover-output.txt
- **Severity**: nit
- **Concern**: Skill prose still references voter `--scope-anchor-file` argv even though the tally contract uses env/staged-anchor handoff and rejected argv plumbing.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Address the concern above.
  - From dyn-ship-cutover-output.txt: Address the concern above.

### FINDING_22: Step 3 recovery accepts zero-byte staged anchors
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: `recover_main_agent_scope_anchor` can recover an empty staged anchor into `SCOPE_ANCHOR_FILE`, causing MainAgent voting with empty scope evidence instead of failing/panel-failed.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.

### FINDING_23: Missing focused harness for absent SCOPE_ANCHOR_FILE fallback
- **Reviewer(s)**: cursor-specialist-plan-fidelity-output.txt
- **Severity**: nit
- **Concern**: The plan requested an explicit missing-KV fallback test, but current coverage is implicit and bundled with other assertions.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-plan-fidelity-output.txt: Address the concern above.

### FINDING_24: Aggregator hardening lacks clear plan/PR traceability
- **Reviewer(s)**: cursor-specialist-plan-fidelity-output.txt
- **Severity**: latent
- **Concern**: Aggregator scope-anchor hardening was added outside the primary implementation flow, while SECURITY treats aggregator as a scope-anchor consumer. Reviewers may miss the dependency without explicit traceability.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-plan-fidelity-output.txt: Address the concern above.

### FINDING_25: [OUT_OF_SCOPE] Relay terminal matrix excludes converged/cap-hit from env handoff
- **Reviewer(s)**: dyn-scope-flow-output.txt
- **Severity**: latent
- **Concern**: `_scope_anchor_handoff_value` excludes `converged` / `cap-hit`, matching current plan semantics, but future consumers may wrongly expect `SCOPE_ANCHOR_FILE` in Step 3 result envs on those terminals.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-scope-flow-output.txt: Address the concern above.

### FINDING_26: [OUT_OF_SCOPE] Multi-round stdout parsing can keep stale first-wins KVs
- **Reviewer(s)**: dyn-scope-flow-output.txt
- **Severity**: latent
- **Concern**: Multi-round loop stdout can include intermediate tally KVs before terminal KVs, while orchestrator parsing is first-wins per key. Later rounds may not override stale earlier values.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-scope-flow-output.txt: Address the concern above.

### FINDING_27: Python ship state filter drops durable bash-contract keys
- **Reviewer(s)**: dyn-ship-cutover-output.txt
- **Severity**: important
- **Concern**: `_ALLOWED_SHIP_STATE_KEYS` omits durable keys that bash helpers still treat as cross-driver state. Python default runs can drop seeded booleans such as `NO_LOGS_COMMIT`, causing later helpers to commit logs or reconstruct finalize state incorrectly.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-ship-cutover-output.txt: Address the concern above.

### FINDING_28: [OUT_OF_SCOPE] Python ship cold resume phase14 remains weaker than bash
- **Reviewer(s)**: dyn-ship-cutover-output.txt
- **Severity**: latent
- **Concern**: Cold resume with `RESUME_PHASE=ship-pr-rrr-phase14` still routes to an unsupported continuation when the phase14 flag cannot be created, unlike the bash opt-in path.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-ship-cutover-output.txt: Address the concern above.

### FINDING_29: Scope-anchor docs point operators at feature-description instead of staged anchor
- **Reviewer(s)**: dyn-docs-contracts-output.txt
- **Severity**: latent
- **Concern**: Several docs still describe `feature-description.txt` as the authoritative Step 3/assessor scope source, even though runtime materializes and binds dispatch to `plan-review-scope-anchor.txt` first.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-docs-contracts-output.txt: Address the concern above.

### FINDING_30: Handoff docs omit the LOOP_STATUS half of the dual gate
- **Reviewer(s)**: dyn-docs-contracts-output.txt
- **Severity**: latent
- **Concern**: Normative docs describe relay as gated only on tally terminals, while runtime also requires compatible `LOOP_STATUS`. Operators may expect anchor persistence on `panel-failed` plus successful tally.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-docs-contracts-output.txt: Address the concern above.

### FINDING_31: SECURITY.md understates subprocess context hardening
- **Reviewer(s)**: dyn-docs-contracts-output.txt
- **Severity**: latent
- **Concern**: The canonical Claude review subprocess security bullet does not match newer docs claiming redaction, XML escaping, untrusted framing, and path-attribute escaping.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-docs-contracts-output.txt: Address the concern above.

### FINDING_32: [OUT_OF_SCOPE] read-tools staged-context carve-out is underdocumented
- **Reviewer(s)**: dyn-docs-contracts-output.txt
- **Severity**: nit
- **Concern**: Launch-subprocess docs describe context bodies as framed/redacted, but the `--read-tools` scout path stages files instead of prompt-inlining them and needs an explicit carve-out.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-docs-contracts-output.txt: Address the concern above.
