### FINDING_1:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: python/larch/implement/ship.py:688-700
- **Concern**: Refresh gate should use staged_assessment_present not staged path is_file. Scenario: The plan gates refresh on staged artifacts existing but ship already computes staged_present via staged_assessment_present while the pin attempt uses staged_assessment_path.is_file(). On partial or symlink-corrupt artifact sets pin fails yet is_file can still be true so ship may call refresh that always returns False because the helper requires STATUS=present and regular non-symlink sidecar files
- **Proposed resolution**: In _pin_and_load_guidelines_note call refresh only when staged_assessment_present(tmpdir) is true and align the pin attempt guard with that same predicate instead of is_file alone



### FINDING_2:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/test_ship.py:4395-4411
- **Concern**: Drift recovery tests omit warning suppression contract. Scenario: The plan requires logging the pin-skip warning only after refresh and retry both fail. Without an assertion that execution-issues.md lacks that warning on the successful recovery path a regression can still emit the false alarm that drives the 87% drop investigation noise even when the note is delivered
- **Proposed resolution**: Add to the drift recovery test an assertion that execution-issues.md does not contain architectural-guidelines pin-note-from-staged skipped or failed fingerprint validation after refresh succeeds and the consumable note is returned



### FINDING_3:
- **Reviewer(s)**: Codex-Generic
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/larch/core/architectural_guidelines.py:435-480
- **Concern**: Refresh path can bypass the staged fingerprint guard. Scenario: The plan lets refresh require only regular staged assessment and sidecar files with STATUS=present before rewriting artifacts. If the original materialized diff snapshot is missing or no longer hashes to the stored DIFF_FINGERPRINT, a note that pin_note_from_staged correctly rejects today can be re-fingerprinted against the live diff and pinned on retry.
- **Proposed resolution**: Before rewriting, require the existing MATERIALIZED_DIFF to be a regular non-symlink file and require diff_fingerprint(old_snapshot) to equal the stored DIFF_FINGERPRINT. Return False otherwise and add the matching failure test.



