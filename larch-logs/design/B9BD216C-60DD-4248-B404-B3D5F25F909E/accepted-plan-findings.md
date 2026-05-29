### FINDING_1: Retained-set fill can keep nine cached versions
- **Reviewer(s)**: Cursor-Edge
- **Severity**: important
- **Concern**: Seeding `ACTUAL_VERSION` and then filling from the sorted version list without skipping versions already retained can exceed the intended eight cached directories when the target is already among the newest eight.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Edge: Specify skip-if-already-retained while filling to KEEP_VERSIONS=8; add a harness case that asserts exactly eight dirs remain when ACTUAL_VERSION is already among the newest eight


### FINDING_2: Missing actual-version cache entry can consume retention budget
- **Reviewer(s)**: Codex-Edge
- **Severity**: important
- **Concern**: Counting `ACTUAL_VERSION` toward the eight-entry retention budget before confirming its cache directory exists can leave only seven real cached rollback candidates after pruning.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Edge: Only count ACTUAL_VERSION toward KEEP_VERSIONS when $LARCH_CACHE_DIR/$ACTUAL_VERSION is an existing cached dir; otherwise fill from real cached entries up to 8 and add an absent-target regression case


### FINDING_5: Upgrade prune drops required recent-version retention window
- **Reviewer(s)**: Cursor-Requirements, Codex-Requirements
- **Severity**: important
- **Concern**: Changing `/upgrade-larch` to a hard maximum of eight install-stamped versions contradicts the requirement that the last eight installed versions are only a floor and that recent versions within the retention window must also be kept.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Requirements, Codex-Requirements: Revise the plan to keep the union of last 8 installed and versions within the /upgrade-larch retention window; decide and document install-age versus activity signal, and add prune tests for young outside-top-8 kept and old outside-top-8 deleted.

