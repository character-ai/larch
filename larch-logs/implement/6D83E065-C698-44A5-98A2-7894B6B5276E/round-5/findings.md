### FINDING_1: Design OOS path resolution is duplicated and can miss design-export files
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-testing-output.txt
- **Severity**: important
- **Concern**: Design OOS path resolution is implemented in multiple places and lacks regression coverage for stale `DESIGN_TMPDIR` versus design-export fallback. Divergence can reopen the design-export miss class and cause checkpoint gates to count the wrong files.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt, cursor-specialist-testing-output.txt: Address the concern above.

### FINDING_2: OOS ndjson discovery diverges across shell, checkpoint, and Python paths
- **Reviewer(s)**: cursor-specialist-structure-output.txt, dyn-oos-flow-output.txt, dyn-python-parity-output.txt
- **Severity**: important
- **Concern**: `oos-issues.ndjson` discovery is duplicated and inconsistent across ship drivers and checkpoint code. Missing or ambiguous `RUN_ID` handling can either block valid OOS disposition or attach evidence from the wrong run.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt, dyn-oos-flow-output.txt, dyn-python-parity-output.txt: Address the concern above.

### FINDING_3: OOS pipeline docs omit security sidecar and checkpoint stall semantics
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-edge-cases-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Severity**: important
- **Concern**: Canonical OOS pipeline documentation does not fully describe `security-oos-observations.md`, private security handling, or the checkpoint behavior that refuses all-clear while that sidecar remains non-empty.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt, cursor-specialist-edge-cases-output.txt, cursor-specialist-plan-fidelity-output.txt: Address the concern above.

### FINDING_4: Public OOS redaction is not centralized or mechanically enforced
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-security-output.txt
- **Severity**: important
- **Concern**: Public OOS redaction is partly prompt-enforced and partly reimplemented locally. Token drift or missed orchestration steps could leak internal URLs or secrets into public issue bodies.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt, cursor-specialist-security-output.txt: Address the concern above.

### FINDING_5: `write_description` subshell loop repeats description prefixes
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: important
- **Concern**: `write_description` uses a piped `while` loop whose state changes occur in a subshell, so multi-line descriptions can receive repeated `- **Description**:` prefixes and mis-parse at filing time.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.

### FINDING_6: Tool failure appending can duplicate or miss entries
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: latent
- **Concern**: `_append_execution_tool_failure` can append manually even after `append-tool-failure.sh` succeeds if substring matching misses, creating duplicate or inconsistent Tool Failures state.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.

### FINDING_7: Scoped load-directive tests rely on fragile awk windows
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-testing-output.txt
- **Severity**: latent
- **Concern**: Load-directive tests use proximity windows that can pass despite separating mandatory load lines from their entry points, allowing future SKILL.md edits to silently drop CI protection.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt, cursor-specialist-testing-output.txt: Address the concern above.

### FINDING_8: Materializer is invoked twice per site unnecessarily
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: Step 2 and PR prep run the materializer once for `--count-only` and again for full output, duplicating manifest parsing and jq work.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.

### FINDING_9: Documented OOS dedup order differs from checkpoint order
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: The documented cross-phase dedup order does not match the checkpoint accepted-file order, creating possible precedence confusion for implementers.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.

### FINDING_10: Python materialization persists `OOS_PENDING=true` too early
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt
- **Severity**: important
- **Concern**: `_materialize_manifest_oos` writes `OOS_PENDING=true` before materialization succeeds and may not clear it on success, causing persisted state to block later ship or PR-create paths even after disposition is satisfied.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt: Address the concern above.

### FINDING_11: [OUT_OF_SCOPE] Python OOS tests encode or obscure the wrong post-disposition behavior
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-edge-cases-output.txt, cursor-specialist-plan-fidelity-output.txt, dyn-oos-flow-output.txt, dyn-python-parity-output.txt
- **Severity**: important
- **Concern**: Tests named as if PR creation is allowed after disposition assert `NEEDS_USER_INPUT` instead, and related design-export tests do not verify resolved accepted-file paths. This bakes in or obscures the post-Step-9a.1 resume regression.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-edge-cases-output.txt, cursor-specialist-plan-fidelity-output.txt, dyn-oos-flow-output.txt, dyn-python-parity-output.txt: Address the concern above.

### FINDING_12: Step 2 lacks fail-closed test coverage for materializer failure
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: important
- **Concern**: No test asserts that Step 2 bails out when the manifest has OOS observations but the materialization helper fails, risking a false `complete` status with no file triggers for Step 9a.1.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.

### FINDING_13: `ship-pr.sh` lacks runtime coverage for materializer failure forcing `OOS_PENDING`
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: important
- **Concern**: After removal of prior ship-pr tests, materialize failure behavior is only grep-order covered; a non-empty manifest plus helper failure could skip `OOS_PENDING` and reach PR creation.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.

### FINDING_14: Security sidecar checkpoint blocking lacks regression coverage
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: important
- **Concern**: The new `security-oos-observations.md` checkpoint block and Python pre-PR block lack regression tests, so security-routed manifest OOS could pass to PR creation or all-clear without SECURITY.md disposition.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.

### FINDING_15: Manifest security routing under-detects title and prose-only security signals
- **Reviewer(s)**: cursor-specialist-security-output.txt, dyn-public-redaction-output.txt
- **Severity**: important
- **Concern**: Manifest OOS routing only reliably keys off structured focus-area signals, so security-sensitive content in title or prose-only description markers can be materialized into public accepted-OOS artifacts and issue bodies.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt, dyn-public-redaction-output.txt: Address the concern above.

### FINDING_16: Accepted-OOS size checks can loop forever after Step 9a.1
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt, cursor-specialist-plan-fidelity-output.txt, dyn-oos-flow-output.txt, dyn-shell-state-output.txt, dyn-python-parity-output.txt
- **Severity**: important
- **Concern**: Python and bash paths treat non-empty accepted-OOS markdown as requiring filing before checking whether disposition is already satisfied. Because accepted files remain after Step 9a.1, reinvocation can repeatedly return OOS filing or bounce between phases instead of reaching PR creation.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt, cursor-specialist-plan-fidelity-output.txt, dyn-oos-flow-output.txt, dyn-shell-state-output.txt, dyn-python-parity-output.txt: Address the concern above.

### FINDING_17: [OUT_OF_SCOPE] Description-body `focus-area` scanning can mis-route manifest OOS
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt, dyn-oos-flow-output.txt, dyn-shell-state-output.txt
- **Severity**: latent
- **Concern**: `security_signal` scans description text for focus-area-shaped lines, so quoted or narrative `- **focus-area**: security` text can route otherwise non-security observations to the private sidecar and stall shipping.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt, dyn-oos-flow-output.txt, dyn-shell-state-output.txt: Address the concern above.

### FINDING_18: Materializer contract markdown is not covered by header tests
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: nit
- **Concern**: `materialize-manifest-oos.md` contract headers are not included in the reference-header test glob, so contract triplet drift can go unnoticed.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.

### FINDING_19: Manifest security classification uses raw or inconsistently normalized fields
- **Reviewer(s)**: dyn-public-redaction-output.txt
- **Severity**: important
- **Concern**: Security routing classifies raw `focus_area` and description strings before the same normalization/sanitization used for public writes. Leading whitespace or documentation mismatch can cause security-marked observations to bypass the private sidecar.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-public-redaction-output.txt: Address the concern above.

### FINDING_20: Python `_oos_gate` does not enforce checkpoint ndjson preconditions
- **Reviewer(s)**: dyn-python-parity-output.txt
- **Severity**: important
- **Concern**: Python calls `oos.disposition_ok` without enforcing the checkpoint rule that non-security accepted OOS requires a resolved `oos-issues.ndjson`, allowing Python-only disposition success paths that bash would fail closed.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-python-parity-output.txt: Address the concern above.

### FINDING_21: [OUT_OF_SCOPE] SECURITY.md does not clearly cross-link manifest routing asymmetry
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: nit
- **Concern**: SECURITY.md and manifest OOS use different security discrimination rules, which can mislead operators unless the asymmetry and manifest predicate are explicitly cross-linked.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Address the concern above.

### FINDING_22: [OUT_OF_SCOPE] Checkpoint ndjson requirement may reject inline-triage-only coverage
- **Reviewer(s)**: dyn-oos-flow-output.txt
- **Severity**: latent
- **Concern**: Requiring `oos-issues.ndjson` whenever non-security accepted OOS exists can prevent checkpoint success for inline-triage-only coverage if accepted markdown remains without ndjson.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-oos-flow-output.txt: Address the concern above.

### FINDING_23: [OUT_OF_SCOPE] Count-only materializer failure can stall zero-OOS manifests
- **Reviewer(s)**: dyn-shell-state-output.txt
- **Severity**: latent
- **Concern**: If count-only materialization fails on a manifest with zero OOS observations, the failure branch still sets `OOS_PENDING=true`, conservatively stalling shipping for infrastructure or schema errors unrelated to actual OOS.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-shell-state-output.txt: Address the concern above.

### FINDING_24: [OUT_OF_SCOPE] Python `_oos_gate` remains architecturally behind checkpoint parity
- **Reviewer(s)**: dyn-shell-state-output.txt
- **Severity**: latent
- **Concern**: Beyond the direct PR-create path, `_oos_gate` does not fully apply checkpoint preconditions such as ndjson validation or security sidecar blocking for future direct callers.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-shell-state-output.txt: Address the concern above.

### FINDING_25: [OUT_OF_SCOPE] Python ship driver lacks phase-aware resume support
- **Reviewer(s)**: dyn-python-parity-output.txt
- **Severity**: latent
- **Concern**: Python has no `--resume-phase` or phase-aware entry point, so every invocation reruns the full sequence rather than matching bash resume semantics.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-python-parity-output.txt: Address the concern above.

### FINDING_26: [OUT_OF_SCOPE] Security sidecar redaction branch lacks direct tests
- **Reviewer(s)**: dyn-public-redaction-output.txt
- **Severity**: latent
- **Concern**: Redaction tests cover public accepted-OOS output but not `security-oos-observations.md`, even though the security-routed branch also passes through sanitization.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-public-redaction-output.txt: Address the concern above.

### FINDING_27: [OUT_OF_SCOPE] Step 9a.1 combine and issue redaction remain prompt-level
- **Reviewer(s)**: dyn-public-redaction-output.txt
- **Severity**: latent
- **Concern**: Combine, `/issue`, and larch-log redaction still depend on orchestrator prompt instructions rather than a mechanical enforcement hook beyond the new materializer.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-public-redaction-output.txt: Address the concern above.
