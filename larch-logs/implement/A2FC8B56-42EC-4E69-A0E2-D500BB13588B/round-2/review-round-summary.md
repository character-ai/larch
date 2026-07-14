# Review Round 2

- Mode: `diff`
- 16 accepted, 7 rejected (1 neutral)

## Accepted Findings

### FINDING_1: Partial KV reads drop defaults
- **Reviewer(s)**: cursor-specialist-correctness, codex-specialist-correctness, codex-specialist-edge-cases, dyn-dyn-kv-wire
- **Severity**: major
- **Concern**: Successful partial KV reads discard fallback defaults, causing terminal recovery and other migrated readers to raise `KeyError` for omitted keys.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness: Address the concern above.
  - From codex-specialist-correctness: Address the concern above.
  - From codex-specialist-edge-cases: Address the concern above.
  - From dyn-dyn-kv-wire: Address the concern above.


### FINDING_2: KV lint misses grep/cut readers
- **Reviewer(s)**: codex-specialist-correctness
- **Severity**: major
- **Concern**: The cut detector does not flag KEY-prefix grep or cut pipelines lacking selected keywords, allowing ad-hoc readers to bypass lint.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-correctness: Address the concern above.


### FINDING_3: Baseline exempts planned migrations
- **Reviewer(s)**: codex-specialist-correctness, cursor-specialist-edge-cases, codex-specialist-edge-cases, codex-specialist-testing
- **Severity**: major
- **Concern**: Generic baseline rows grandfather plan-listed Python and Bash readers, weakening the shrink-only ratchet while divergent parsers remain.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-correctness: Address the concern above.
  - From cursor-specialist-edge-cases: Address the concern above.
  - From codex-specialist-edge-cases: Address the concern above.
  - From codex-specialist-testing: Address the concern above.


### FINDING_4: Hook test utility setup masks failures
- **Reviewer(s)**: codex-specialist-correctness
- **Severity**: minor
- **Concern**: Hook tests remove `cat` and `dirname` while testing Python/KV failures, so they can deny malformed input before exercising the intended failure paths.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-correctness: Address the concern above.


### FINDING_5: Clarify readers remain ad hoc
- **Reviewer(s)**: cursor-specialist-edge-cases
- **Severity**: major
- **Concern**: Plan-listed clarify publish/rename readers still use split loops, leaving duplicate-key and CR semantics inconsistent with the shared codec.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases: Address the concern above.


### FINDING_6: Terminal env scans remain ad hoc
- **Reviewer(s)**: cursor-specialist-edge-cases
- **Severity**: major
- **Concern**: Design-terminal environment scans retain legacy parsing, so state recovery can disagree with codec-based ship/design paths.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases: Address the concern above.


### FINDING_7: Step 8 ship parsing bypasses the codec
- **Reviewer(s)**: cursor-specialist-edge-cases
- **Severity**: major
- **Concern**: Step 8 still reads ship state through grep/tail/cut, leaving Bash and Python ship-state parsing semantics inconsistent.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases: Address the concern above.


### FINDING_8: Hook KV failure path is untested
- **Reviewer(s)**: cursor-specialist-edge-cases, cursor-specialist-testing, dyn-dyn-kv-wire
- **Severity**: major
- **Concern**: The harness does not test a working Python interpreter with an eligible registry whose `kv get` invocation fails, so fail-closed denial may be unverified.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases: Address the concern above.
  - From cursor-specialist-testing: Address the concern above.
  - From dyn-dyn-kv-wire: Address the concern above.


### FINDING_9: KV lint lacks integration coverage
- **Reviewer(s)**: cursor-specialist-edge-cases, cursor-specialist-testing
- **Severity**: major
- **Concern**: Integration tests do not cover new findings, stale baseline rows, malformed entries, or strict baseline enforcement.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases: Address the concern above.
  - From cursor-specialist-testing: Address the concern above.


### FINDING_10: Shell lint findings lack stable anchors
- **Reviewer(s)**: cursor-specialist-edge-cases
- **Severity**: minor
- **Concern**: Shell baseline identities are line-keyed rather than anchor-keyed, causing unrelated edits to churn baseline rows.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases: Address the concern above.


### FINDING_14: Lone-CR parsing changes value semantics
- **Reviewer(s)**: codex-specialist-edge-cases, dyn-dyn-kv-wire
- **Severity**: major
- **Concern**: `splitlines()` treats lone carriage returns as row separators, changing embedded-CR values and potentially producing empty values.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-edge-cases: Address the concern above.
  - From dyn-dyn-kv-wire: Address the concern above.


### FINDING_17: Session codec policy tests are missing
- **Reviewer(s)**: cursor-specialist-testing
- **Severity**: major
- **Concern**: Session tests do not pin first-match, duplicate-key, or empty-value behavior for `_session_get`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing: Address the concern above.


### FINDING_18: Ship-state edge-case coverage is incomplete
- **Reviewer(s)**: cursor-specialist-testing
- **Severity**: major
- **Concern**: Ship-state tests omit allowlists, embedded equals, and wrapped read failures, leaving routing and parsing regressions undetected.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing: Address the concern above.


### FINDING_19: SessionStart readers remain ad hoc
- **Reviewer(s)**: cursor-specialist-testing
- **Severity**: major
- **Concern**: Plan-listed SessionStart `awk` readers remain outside `kv get`, preserving dual parsing semantics without harness coverage.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing: Address the concern above.


### FINDING_23: `read_kvs` overload omits last-non-empty
- **Reviewer(s)**: codex-specialist-testing
- **Severity**: major
- **Concern**: The scalar overload does not admit `last-non-empty`, causing a production Pyright failure in `design_core.py`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-testing: Address the concern above.


### FINDING_24: Run-context codec regressions lack tests
- **Reviewer(s)**: codex-specialist-testing
- **Severity**: minor
- **Concern**: Run-context tests do not cover empty values, CR decoding, read failures, allowlists, embedded equals, or KV match handling.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-testing: Address the concern above.
