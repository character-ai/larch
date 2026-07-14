# Review Round 1

- Mode: `diff`
- 15 accepted, 0 rejected (0 neutral)

## Accepted Findings

### FINDING_1: Hook resolves codec before eligible registry entries
- **Reviewer(s)**: cursor-specialist-correctness, codex-specialist-correctness
- **Severity**: major
- **Concern**: The hook denies background Bash when Python or the codec is unavailable even if the daemon registry is empty or contains only symlinks. Resolve the codec only after identifying an eligible registry entry.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness: Address the concern above.
  - From codex-specialist-correctness: Address the concern above.


### FINDING_2: Missing forced kv get failure harness case
- **Reviewer(s)**: cursor-specialist-edge-cases, cursor-specialist-testing, codex-specialist-testing
- **Severity**: major
- **Concern**: The hook tests Python unavailability but not kv get failure with Python available, leaving the denial path unverified.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases: Address the concern above.
  - From cursor-specialist-testing: Address the concern above.
  - From codex-specialist-testing: Address the concern above.


### FINDING_3: Lone-CR ship-state parsing regression
- **Reviewer(s)**: codex-specialist-correctness
- **Severity**: major
- **Concern**: Lone carriage returns no longer preserve prior line-boundary semantics, so state rows separated by `\r` can be parsed as one field and fail validation.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-correctness: Address the concern above.


### FINDING_4: KV-codec detector misses parser variants
- **Reviewer(s)**: codex-specialist-correctness, codex-specialist-edge-cases
- **Severity**: major
- **Concern**: The lint ratchet misses Python comprehensions and quoted or whitespace-separated shell `awk`/`cut` field-separator forms.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-correctness: Address the concern above.
  - From codex-specialist-edge-cases: Address the concern above.


### FINDING_5: Planned migrations remain hidden by the baseline
- **Reviewer(s)**: codex-specialist-correctness, codex-specialist-edge-cases, codex-specialist-testing
- **Severity**: major
- **Concern**: Generic baseline exemptions allow plan-required Python and Bash readers to remain ad hoc, preventing codec unification and baseline shrinkage.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-correctness: Address the concern above.
  - From codex-specialist-edge-cases: Address the concern above.
  - From codex-specialist-testing: Address the concern above.


### FINDING_6: Baseline identities are unstable
- **Reviewer(s)**: codex-specialist-correctness
- **Severity**: minor
- **Concern**: Line-based baseline entries churn when unrelated lines move, producing active and stale findings.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-correctness: Address the concern above.


### FINDING_7: design_core loses last-non-empty semantics
- **Reviewer(s)**: cursor-specialist-edge-cases, dyn-dyn-kv-wire
- **Severity**: major
- **Concern**: Migrated design readers let a trailing empty duplicate replace or clear an earlier non-empty value, changing terminal recovery and routing behavior.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases: Address the concern above.
  - From dyn-dyn-kv-wire: **Suggested fix:** Drop `empty_value_means_default=True` from `_read_env_value_last`, or add an explicit last-non-empty policy to the codec and use it here; add a duplicate-key fixture with a trailing empty row.


### FINDING_11: KV-codec detector produces false positives
- **Reviewer(s)**: codex-specialist-correctness, codex-specialist-edge-cases
- **Severity**: major
- **Concern**: Broad looped `split("=")` and shell delimiter detection can classify ordinary option or field parsing as environment readers.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-correctness: Address the concern above.
  - From codex-specialist-edge-cases: Address the concern above.


### FINDING_12: design_pause duplicate keys are not normalized before selection
- **Reviewer(s)**: codex-specialist-edge-cases
- **Severity**: minor
- **Concern**: Whitespace-padded duplicate keys can be selected incorrectly, violating last-wins behavior.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-edge-cases: Address the concern above.


### FINDING_13: Migrated callers lack duplicate-key regression tests
- **Reviewer(s)**: cursor-specialist-testing
- **Severity**: major
- **Concern**: Ship-state, design-router, run-context, and preflight codec policies lack plan-required duplicate-key fixtures, so routing and allowlist regressions can pass CI.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing: Address the concern above.


### FINDING_14: KV-codec lint lacks integration coverage
- **Reviewer(s)**: cursor-specialist-testing, codex-specialist-testing
- **Severity**: major
- **Concern**: Tests cover detector units but not baseline integration, stale or malformed entries, new findings, cut parsing, and migrated-reader behavior.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing: Address the concern above.
  - From codex-specialist-testing: Address the concern above.


### FINDING_15: read_kvs allowlist behavior is under-tested
- **Reviewer(s)**: cursor-specialist-testing
- **Severity**: minor
- **Concern**: Allowlisted reads, duplicates, embedded equals, carriage returns, and missing files lack targeted regression coverage.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing: Address the concern above.


### FINDING_18: Baseline regeneration can add generic exemptions
- **Reviewer(s)**: codex-specialist-edge-cases
- **Severity**: major
- **Concern**: The regeneration target can authorize new violations with a generic reason, allowing the baseline to grow instead of enforcing a shrink-only ratchet.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-edge-cases: Address the concern above.


### FINDING_19: design_core multi-value reads lose last-non-empty semantics
- **Reviewer(s)**: dyn-dyn-kv-wire
- **Severity**: major
- **Concern**: `_read_env_values` allows a trailing empty duplicate to erase an earlier non-empty value, affecting `FAILURE_OUTCOME`, `SITE`, and `TRIGGER` routing.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-dyn-kv-wire: **Suggested fix:** Preserve last-non-empty semantics explicitly (for example `duplicate_policy="all"` plus reverse scan for the first non-empty value per key, or a dedicated codec helper); add a fixture that pins `KEY=foo\nKEY=\n`.


### FINDING_20: design_publish swallows result-env read errors
- **Reviewer(s)**: dyn-dyn-kv-wire
- **Severity**: major
- **Concern**: `on_error_default=True` converts unreadable provenance files into empty data, changing the historic fail-closed error behavior.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-dyn-kv-wire: **Suggested fix:** Remove `on_error_default=True` here (or catch and re-raise), so unreadable result envs keep the historic error contract; add a test that mocks `read_kvs`/`open` failure and expects propagation.
