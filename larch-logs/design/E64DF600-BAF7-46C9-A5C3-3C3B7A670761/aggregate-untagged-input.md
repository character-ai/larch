### FINDING_1:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: major
- **Focus area**: correctness
- **Location**: python/larch/core/architectural_guidelines.py:1285-1307
- **Concern**: Incremental safety check must diff stored HEAD_SHA to current HEAD, not base to HEAD. Scenario: The plan says diff between persisted covered input and current HEAD but never names the old git endpoint. An implementer can diff BASE_REF..HEAD or replay the full materialized diff. That treats pre-assessment code paths as new increments, blocks safe docs-only or larch-logs-only advances, and forces reassessment after the once-per-run pre-filter should have kept coverage.
- **Proposed resolution**: State explicitly that the rename-safe incremental check runs git diff --no-renames --name-only -z <stored HEAD_SHA>..<current HEAD>, using the durable metadata HEAD_SHA written at the last successful coverage update as the old revision.

### FINDING_2:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: major
- **Focus area**: correctness
- **Location**: python/larch/core/architectural_guidelines.py:1434-1457
- **Concern**: Compose precheck still bypasses unified consumption and advancement. Scenario: `_compose_precheck_result` and `_invariant_compose_precheck_result` call `note_consumable` / `invariant_note_consumable` without `repo_root` or `base_ref`, then run a separate `note_fingerprint_stale` gate. After the plan removes HEAD-match-only consumability and requires live identity validation plus advancement on drift, this split path cannot advance coverage or return `status=current` during compose even when a safe docs-only or log-only commit landed.
- **Proposed resolution**: Refactor both precheck helpers to pass resolved `repo_root` and `BASE_REF` into the consumption helpers, rely on the unified consumable result only, and delete the redundant parallel fingerprint-stale branch. Add compose-precheck tests that prove safe HEAD drift returns `status=current` without rematerialization.

### FINDING_3:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: major
- **Focus area**: risk-integration
- **Location**: python/larch/implement/ship.py:451-476
- **Concern**: Violation preservation is not enforceable with unconditional sidecar clear. Scenario: Acceptance requires that unavailable never erases a blocking invariant violation. The plan adds classification precedence only in `ship_guidelines.py`, but `_invariants_gate_before_pr` always clears the invariant outcome sidecar before gate evaluation and `write_invariant_ship_outcome` always rewrites it. A later unavailable refresh therefore drops a persisted `violation` outcome before classification can preserve it, even if the durable violation note still exists.
- **Proposed resolution**: Specify and test a no-clobber write contract: read the existing invariant outcome sidecar (and authored violation durable note) before clear/write; when the new gate resolves to unavailable, keep the existing violation outcome and skip unavailable downgrade. Document the touch point (`ship.py` gate and/or `write_invariant_ship_outcome`) in the firm plan files.

### FINDING_4:
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: major
- **Focus area**: correctness
- **Location**: python/larch/core/architectural_guidelines.py:1447-1457
- **Concern**: Compose precheck still bypasses advancement and live validation. Scenario: `_compose_precheck_result` and `_invariant_compose_precheck_result` call `note_consumable` / `invariant_note_consumable` without `repo_root` or `base_ref`, and return `status=current` when `root is None`. After the HEAD-match shortcut is removed, safe docs-only or log-only advances never run here and reuse either fails closed or skips fingerprint validation, breaking once-per-run compose reuse despite round-1 consumption wiring.
- **Proposed resolution**: Pass `repo_root=root` and the resolved `base_ref` into consumable checks, delete the `root is None → current` branch, and rely on the shared advancement plus covered-fingerprint validation inside consumable before returning `status=current`.

### FINDING_5:
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: major
- **Focus area**: correctness
- **Location**: python/larch/core/architectural_guidelines.py:1434-1576
- **Concern**: Coverage advancement omits diff snapshot refresh. Scenario: The plan updates `COVERED_DIFF_FINGERPRINT` and `HEAD_SHA` on safe advance and adds use-time validation that snapshot content matches the declared fingerprint, but it never requires rewriting `DIFF_SNAPSHOT` (or the referenced diff artifact) during advancement. A safe post-assessment commit would leave a stale snapshot paired with a new covered identity, so the next consumption check fails and forces reassessment anyway.
- **Proposed resolution**: In the shared advancement helper, re-materialize the full base..HEAD implementation diff at the new HEAD, atomically update the snapshot file plus `DIFF_SNAPSHOT`, `COVERED_DIFF_FINGERPRINT`, and `HEAD_SHA` together, and add tests that a docs-only or log-only advance leaves snapshot bytes and covered identity consistent.

### FINDING_6:
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: major
- **Focus area**: correctness
- **Location**: python/larch/core/architectural_guidelines.py:1285-1307
- **Concern**: Advancement must recompute covered identity from full materialized diff. Scenario: The shared advancement helper is specified to validate an incremental path set, but it does not state that the persisted `COVERED_DIFF_FINGERPRINT` must be the fingerprint of the full materialized implementation diff at the new HEAD (same contract as authorship). Fingerprinting only the increment would disagree with later live consumption checks against full base..HEAD materialization and keep notes stale after otherwise safe advances.
- **Proposed resolution**: After incremental paths pass classification, materialize the full implementation diff at the new HEAD, set `COVERED_DIFF_FINGERPRINT` to that full-diff fingerprint (keeping `AUTHORED_DIFF_FINGERPRINT` unchanged), and test chained docs-only then log-only advances against live full-diff consumption.

### FINDING_7:
- **Reviewer(s)**: Codex-Pragmatic
- **Severity**: major
- **Focus area**: correctness
- **Location**: python/larch/core/architectural_guidelines.py:1217-1278
- **Concern**: Unavailable-note identity rules conflict with universal consumption requirements. Scenario: The plan permits unavailable notes without fingerprints, but requires every consumed note to have a non-empty covered identity. The ship loader checks consumability before reading NOTE_STATE, so such an unavailable note cannot reach unavailable outcome classification and instead repeatedly requests reassessment or emits the existing materialization-failed result.
- **Proposed resolution**: Define a state-specific terminal path for unavailable artifacts that emits the unavailable outcome without claiming reusable coverage, or require every unavailable note intended for normal consumption to carry a validated covered identity. Add the corresponding loader behavior to the firm plan.
