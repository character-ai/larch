### FINDING_1: Outcome validators are not updated in their owning module
- **Reviewer(s)**: Cursor-Arch, Cursor-Pragmatic, Cursor-Requirements, Cursor-dyn-State Compatibility Auditor
- **Severity**: major
- **Concern**: The outcome JSON validators that gate run-log batch writes and audit scans live in `python/larch/core/architectural_guidelines.py`, but the plan assigns the validator work to `ship_guidelines.py`. Without explicit schema-v1 combination rules, new `deterministic-clean` and `unavailable` outcomes will be rejected after classification succeeds.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Add explicit plan steps to extend validate_guideline_ship_outcome_record and validate_invariant_ship_outcome_record for the new reason and assessment_kind combinations and add matching tests in test_architectural_guidelines.py or test_ship.py
  - From Cursor-Pragmatic: Add ### UPDATED: python/larch/core/architectural_guidelines.py steps to extend both validate_* functions (clean branch for REASON_DETERMINISTIC_CLEAN; dropped branch for REASON_UNAVAILABLE; reject unavailable+violation and deterministic-clean+deviation/violation). Keep ship_guidelines.py limited to reason-token sets and _classify_* mapping.
  - From Cursor-Requirements: Add validator updates to the ### UPDATED: python/larch/core/architectural_guidelines.py section: allow guideline clean+deterministic-clean+clean kind, dropped+unavailable+empty kind, and matching invariant combinations; extend python/tests/core/test_architectural_guidelines.py alongside test_ship.py.
  - From Cursor-dyn-State Compatibility Auditor: Add explicit ### UPDATED tasks for validate_guideline_ship_outcome_record and validate_invariant_ship_outcome_record: accept deterministic-clean and unavailable combinations per docs/run-log-batches.md and reject invalid pairings named in test_ship.py


### FINDING_2: Incremental coverage advancement is not wired into consumption
- **Reviewer(s)**: Cursor-Arch, Cursor-Pragmatic, Cursor-dyn-State Compatibility Auditor
- **Severity**: major
- **Concern**: Adding a standalone advancement helper and changing the staleness comparison is insufficient unless `note_consumable` and `invariant_note_consumable` invoke it on HEAD drift, persist the advanced covered identity, and then perform the covered-fingerprint check. Otherwise safe docs-only or `larch-logs`-only commits leave notes stale and force reassessment.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Specify that note_consumable or invariant_note_consumable invokes the advancement helper before returning true on HEAD drift and before note_fingerprint_stale runs and add an integration test mirroring test_log_only_head_advance for docs-only increments
  - From Cursor-Pragmatic: Specify that note_consumable / invariant_note_consumable call the advancement helper when HEAD differs, Git increment paths are all clearly out of scope, and covered identity validates; only then return not note_fingerprint_stale using COVERED_DIFF_FINGERPRINT.
  - From Cursor-Pragmatic: On successful advancement, atomically update HEAD_SHA (and COVERED_DIFF_FINGERPRINT) to the current head; add a chained-increment test (assess → docs-only → logs-only).
  - From Cursor-dyn-State Compatibility Auditor: Wire note_consumable and invariant_note_consumable (and shared callers such as _compose_precheck_result) to invoke the advancement helper on HEAD drift: persist safe advances before returning consumable, leave state unchanged when increment intersects or Git/parsing is unsafe


### FINDING_4: Missing or empty fingerprints can pass consumption checks
- **Reviewer(s)**: Cursor-dyn-State Compatibility Auditor
- **Severity**: major
- **Concern**: The HEAD-match early return and empty-fingerprint behavior allow metadata with missing or empty covered identities to be treated as consumable, weakening the required fail-closed and prior-format compatibility semantics.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-dyn-State Compatibility Auditor: Remove or narrow the unconditional HEAD-match return; require resolved COVERED_DIFF_FINGERPRINT (with prior-format fallback), optional AUTHORED identity, and live covered-input validation even when HEAD_SHA matches
  - From Cursor-dyn-State Compatibility Auditor: Treat missing covered/authored fingerprint as stale or unconsumable (fail closed); align note_fingerprint_stale and invariant_note_fingerprint_stale with COVERED_DIFF_FINGERPRINT and add regression coverage


### FINDING_8: Rename handling can misclassify an unsafe increment as out of scope
- **Reviewer(s)**: Codex-Pragmatic
- **Severity**: major
- **Concern**: A rename may expose only its destination under the chosen `git diff --name-only` form. Renaming a code or knowledge file into `docs/**/*.md` or `larch-logs/**` could therefore be incorrectly classified as safe and advance coverage without reassessment.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Pragmatic: Use a diff form that exposes both sides, such as `--no-renames --name-only -z`, or strictly parse `--name-status -z` and classify every source and destination path. Add a focused code-to-allowed-path rename test.


### FINDING_1: Incremental coverage advancement contract is incomplete
- **Reviewer(s)**: Cursor-Arch, Cursor-Pragmatic
- **Severity**: major
- **Concern**: The planned incremental advancement path does not fully specify how safe post-assessment HEAD drift is detected, how covered identity is recomputed, or how snapshot artifacts stay aligned. Without an explicit stored-HEAD..current-HEAD incremental check, implementers may diff from base or replay the full materialized diff and misclassify pre-assessment paths as new increments. Without full-diff fingerprint recomputation and atomic snapshot refresh during advancement, safe docs-only or larch-logs-only advances can leave `COVERED_DIFF_FINGERPRINT`, `DIFF_SNAPSHOT`, and live consumption checks inconsistent, forcing reassessment despite the once-per-run pre-filter intent.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: State explicitly that the rename-safe incremental check runs git diff --no-renames --name-only -z <stored HEAD_SHA>..<current HEAD>, using the durable metadata HEAD_SHA written at the last successful coverage update as the old revision.
  - From Cursor-Pragmatic: In the shared advancement helper, re-materialize the full base..HEAD implementation diff at the new HEAD, atomically update the snapshot file plus `DIFF_SNAPSHOT`, `COVERED_DIFF_FINGERPRINT`, and `HEAD_SHA` together, and add tests that a docs-only or log-only advance leaves snapshot bytes and covered identity consistent.
  - From Cursor-Pragmatic: After incremental paths pass classification, materialize the full implementation diff at the new HEAD, set `COVERED_DIFF_FINGERPRINT` to that full-diff fingerprint (keeping `AUTHORED_DIFF_FINGERPRINT` unchanged), and test chained docs-only then log-only advances against live full-diff consumption.


