### FINDING_1: Preserve stored operator overrides during regeneration
- **Reviewer(s)**: Cursor-Arch, Cursor-Requirements, Cursor-dyn-Gate Integrity
- **Severity**: major
- **Concern**: Literal writer requirements could strip manually authored `operator_override` data during `--write`, reactivating the gate and losing operator decisions.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Revise writer bullets and tests: preserve matched stored operator_override verbatim; never create operator_override on rows that lacked one; add a merge test that regen with --reason keeps override unchanged
  - From Cursor-Requirements: State that merge pass-through copies operator_override only from the stored baseline row and never from live output. Clarify tests to assert preserved overrides survive --write byte-for-byte, while writer-authored overrides remain impossible.
  - From Cursor-dyn-Gate Integrity: In the UPDATED writer bullets, require pass-through of stored operator_override unchanged on identity match; restrict never create to live/--reason paths; change the test bullet to prove the writer never fabricates operator_override on rows that lacked one while still preserving operator-authored overrides across merge


### FINDING_2: Wire `REASON=` through the regeneration target
- **Reviewer(s)**: Cursor-Arch, Cursor-dyn-Gate Integrity
- **Severity**: minor
- **Concern**: The documented Makefile regeneration path still invokes `--write` without the required reason.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: In Makefile plan specify REASON= forwarding to --reason for growth regens and document that shrink-only regens may omit it; point docs/linting.md at the same contract
  - From Cursor-dyn-Gate Integrity: Document and wire REASON= (or an equivalent make variable) through regen-complexity-baseline to --write --reason, mirroring the conditional bootstrap pattern used by regen-subprocess-via-runner-baseline at 98-106


### FINDING_5: Enforce repeat-bump policy during check mode
- **Reviewer(s)**: Cursor-Innovation, Cursor-Pragmatic, Cursor-Requirements
- **Severity**: major
- **Concern**: Check mode could pass when live metrics match or are below the baseline even though committed history violates the 14-day repeat-bump rule.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Innovation: state in `_run_check` that repeat-bump runs on every loaded row from stored `history` (override-aware), independent of regression detection; add a check-mode test with violating history and live metric `<=` baseline
  - From Cursor-Pragmatic: Wire repeat-bump scanning into _run_check after baseline load (independent of find_regressions); add a check-mode test where live matches baseline but history violates the 14-day rule and main() exits 1
  - From Cursor-Requirements: Add one integration test that runs main() check mode on such a fixture and expects exit 1 with the three remediation paths, independent of --write.


### FINDING_7: Group repeat bumps by symbol across lint codes
- **Reviewer(s)**: Codex-Innovation
- **Severity**: major
- **Concern**: Including lint code in identity could allow two different complexity metrics for the same function to evade the same-symbol repeat-bump rule.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Innovation: Group gate and 30-day debt-report bump histories by `(file, qualified_symbol)` across lint codes, while retaining code details in output; add cross-code and same-name-different-file coverage.


### FINDING_8: Seed history for new baseline rows
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: major
- **Concern**: New rows with empty history would fail to record their initial metric, allowing a subsequent bump to be misclassified as the first increase.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Requirements: Add an explicit writer rule: on new identity creation require --reason and set history to a single {utc_date, metric} entry; keep append-on-growth for existing identities. Extend new-entry tests to assert that initial history entry.


### FINDING_13: Reject whitespace-only override reasons
- **Reviewer(s)**: Codex-dyn-Gate Integrity
- **Severity**: minor
- **Concern**: A whitespace-only override reason could incorrectly silence the gate.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-dyn-Gate Integrity: Require stripped nonblank override reasons and add a gate test proving whitespace-only overrides fail closed


### FINDING_14: Reject duplicate identities in debt reports
- **Reviewer(s)**: Codex-dyn-Gate Integrity
- **Severity**: minor
- **Concern**: The debt report could double-count duplicate baseline rows unless it validates identity uniqueness independently.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-dyn-Gate Integrity: Add duplicate detection to the report before rendering and test that it returns a data error without a partial report


### FINDING_1: Whitespace-only reasons are accepted
- **Reviewer(s)**: Cursor-Arch
- **Severity**: minor
- **Concern**: `--reason` and stored `reason` values may accept whitespace-only text, weakening the required audit trail.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Strip and reject whitespace-only --reason before write; update _validate_reason to use not value.strip() and add matching tests alongside the accepted override whitespace cases


### FINDING_4: History ordering for rebounds and same-day events is underspecified
- **Reviewer(s)**: Codex-Innovation
- **Severity**: major
- **Concern**: The proposed strict history ordering may reject valid post-decrease rebounds or make same-date cross-code events and override handling nondeterministic.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Innovation: Validate chronological append order without requiring metrics or dates to be strictly increasing, treat post-seed records as bumps, and define deterministic same-date cross-code event and override handling; cover both cases in tests.

