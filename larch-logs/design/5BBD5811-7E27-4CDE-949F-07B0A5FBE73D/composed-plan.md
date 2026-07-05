## Plan

## Approach

Add a small durable run-log artifact for implement Step 8 guideline outcomes.

Use one JSON replace-mode batch `architectural-guideline-outcome.json` with schema version 1:

- `schema_version`: always `1`
- `phase`: `implement`
- `step`: `8`
- `outcome`: `pinned`, `clean`, or `dropped`
- `reason`: stable token from a bounded set (defined in ship_guidelines.py)
- `detail`: redacted bounded diagnostic, when useful
- `guidelines_status`: `present`, `absent`, or `invalid` — always sourced from materialized compose metadata
- `head_sha`
- `base_ref`
- `assessment_kind`: `clean`, `deviation`, or empty

**Classification rules (always use materialized `guidelines_status`, not note emptiness):**
- `outcome=pinned`: `guidelines_status=present` and a redacted note is returned and passed to PR body.
- `outcome=clean`: `guidelines_status=absent` or `invalid` (missing/invalid guidelines), OR `guidelines_status=present` and the note is the CLEAN_PRESENTATION_NOTE.
- `outcome=dropped`: `guidelines_status=present` and note cannot be shipped (materialization, read, redaction, fingerprint, or stale artifact failure).
- `needs_assessment=True`: skip sidecar write; no durable outcome until a terminal resolution.

Thread `guidelines_status` (and `assessment_kind` when known) from `prepare_compose_assessment` / `read_guidelines` into `GuidelinesShipOutcome` construction. Classify `outcome=clean` for absent/invalid before evaluating present-guideline drop reasons. Never infer `guidelines_status` from note emptiness.

Reserve `dropped` exclusively for `guidelines_status=present` failures. Absent or invalid guidelines map to `outcome=clean`.

**Sidecar write and flush contract:**
1. Clear any prior `GUIDELINE_SHIP_OUTCOME_SIDECAR` file at the start of each compose outcome attempt (before classifying) to prevent stale ambient artifacts from being staged on a skip path.
2. After `load_or_prepare_guidelines_note` resolves to a terminal outcome (pinned, clean, or dropped), write the outcome sidecar unconditionally. The `warning_logged` flag does not guard the write.
3. In non-`--no-logs-commit` mode: treat sidecar write failure or verification failure as a pre-PR stall (same class as flush failure). Best-effort continuation applies only to the human-readable warning append path.
4. Call `flush_logs_pre` once after writing the sidecar, before `pr.ensure_pr`. Both initial PR-create and `_refresh_guidelines_gate_after_rebase` share this same flush contract through a single helper.
5. If `flush_logs_pre` returns volatile-only: stall before PR creation unless the committed `architectural-guideline-outcome.json` already exists for the run and matches the tmpdir sidecar. A matching committed artifact is acceptable.
6. `--no-logs-commit`: write the sidecar to tmpdir, skip the pre-PR flush, do not stall.
7. `needs_assessment=True` (unresolved): skip sidecar write and flush entirely.

After a log-only flush advances HEAD (larch-logs changes only), the diff fingerprint is unchanged. Pick one approach: teach `note_consumable` to accept fingerprint-stable notes after larch-logs-only commits. Test only this path.

**Feature-era floor:** Add a single `GUIDELINE_SHIP_OUTCOME_MIN_LARCH_VERSION` Final in `config.py`. Both the audit scan and fluff-analysis compare `manifest.json::larch_version` against this cutover. Below cutover with absent artifact: `informational`. At or above cutover with step8-eligible and absent artifact: `fail`.

Keep the existing warning-append path for human-readable diagnostics in `execution-issues.ndjson`.

Do not add `architectural-guideline-outcome.json` to the generic step8 condition in `docs/run-logs-required-files.tsv`.

## Files to modify/create

### UPDATED: python/larch/implement/ship_guidelines.py

Add a frozen dataclass `GuidelinesShipOutcome` for the durable outcome record.

Define a bounded set of stable `reason` tokens as module-level constants or an enum. Use only tokens from this set when writing the outcome JSON; do not construct reason strings ad hoc.

Add the shared outcome-write helper that:
1. Clears the prior `GUIDELINE_SHIP_OUTCOME_SIDECAR` file before classifying (prevent stale ambient artifact).
2. Classifies the outcome using materialized `guidelines_status` from compose metadata (not note emptiness).
3. Writes the outcome sidecar using atomic JSON output; sanitizes all diagnostic strings before writing.
4. Returns success or failure; the caller stalls in non-`--no-logs-commit` mode when write fails.
5. Skips write when `needs_assessment=True`.

Extend `GuidelinesGateResult` to carry the pre-computed `guidelines_status` and `assessment_kind` from compose metadata so classification can use them directly.

Write the outcome sidecar before optional warning append. Keep warning append for human-readable drop diagnostics (best-effort only).

### UPDATED: python/larch/core/architectural_guidelines.py

Add `GUIDELINE_SHIP_OUTCOME_SIDECAR = "architectural-guideline-outcome.json"` alongside `DROPPED_NOTE_ARTIFACT`, `DURABLE_NOTE`, etc.

### UPDATED: python/larch/implement/ship.py

Replace `_flush_guidelines_warning_before_pr` with a guideline-outcome flush hook that is called from inside `_guidelines_gate_before_pr` (shared single helper).

The hook:
- Always invokes the outcome write+flush helper for every terminal gate result; never guards on `warning_logged`.
- Invoked from both initial PR-create and `_refresh_guidelines_gate_after_rebase` through the same shared path.
- Stalls before PR creation when sidecar write or flush fails (non-`--no-logs-commit` mode).
- Accepts volatile-only only when committed artifact already exists and matches.
- Skips flush on `--no-logs-commit`; does not stall.
- Updates function name and stall diagnostic text to reflect all-outcome flush purpose.

After log-only flush, teach `note_consumable` to accept fingerprint-stable notes across larch-logs-only commits (single approach, no dual-strategy).

### UPDATED: python/larch/core/config.py

Add:
- `RUN_LOG_BATCH_GUIDELINE_SHIP_OUTCOME: Final = "architectural-guideline-outcome"` per G-Cfg-1.
- `GUIDELINE_SHIP_OUTCOME_MIN_LARCH_VERSION: Final = "<shipping-release>"` for feature-era cutover.

### UPDATED: python/larch/report/run_log_batch.py

Register `architectural-guideline-outcome` (via `RUN_LOG_BATCH_GUIDELINE_SHIP_OUTCOME`) as replace-mode JSON with `json-object` sanitizer.

### UPDATED: python/larch/report/run_log_flush.py

Stage the guideline outcome sidecar during `_stage_pre_commit`. Read path via `architectural_guidelines.GUIDELINE_SHIP_OUTCOME_SIDECAR`. If absent, do nothing. If present, write the new batch into `larch-logs/implement/<RUN_ID>/`.

### UPDATED: python/larch/report/gc_run_logs.py

Add `architectural-guideline-outcome.json` to the implement `SKILL_KEEP` set.

### UPDATED: python/larch/issue/audit_runs.py

Extract `implement_step8_reachable(run_dir: Path, manifest: dict) -> bool` from `_scan_required` step8 cond logic and expose it as a module-level helper. Use it from both `_scan_required` (existing step8 gating) and `_guideline_ship_outcome_scan_obj` (new scan). This ensures audit and required-files stay aligned on bail-signal and empty-manifest edge cases.

Add `_guideline_ship_outcome_scan_obj` handler:
- Calls `implement_step8_reachable` to determine step8 eligibility.
- Reads `manifest.json::larch_version` and compares to `config.GUIDELINE_SHIP_OUTCOME_MIN_LARCH_VERSION`.
- Below cutover or not step8-eligible: returns `informational`.
- At or above cutover, step8-eligible, artifact absent/symlink/empty/malformed: returns `fail`.
- Validates `schema_version=1`, `outcome` (pinned/clean/dropped), `guidelines_status` (present/absent/invalid), `head_sha`, and `reason` (must be from bounded set).
- When `gc-slimmed` marker is present and artifact absent: returns `informational`.
- Emits `outcome`, `reason`, and `assessment_kind` on success.

Register beside `guideline-assessment` in `_NAMED_RUN_SCAN_HANDLERS`.

Add counters in `compute-counters`:
- `GUIDELINE_OUTCOME_RUNS`, `GUIDELINE_OUTCOME_PINNED`, `GUIDELINE_OUTCOME_CLEAN`
- `GUIDELINE_OUTCOME_DROPPED`, `GUIDELINE_DROP_RATE_BPS`

### UPDATED: .claude/skills/audit-runs/scans-implement.tsv

Add `guideline-ship-outcome` scan entry, severity `high`, named-handler type.

### UPDATED: skills/fluff-analysis/scripts/fluff-analysis.py

Add implement guideline outcome coverage. Reuse `implement_step8_reachable` (import from `audit_runs`) and `GUIDELINE_SHIP_OUTCOME_MIN_LARCH_VERSION` for classification.

Enumerate all implement run dirs with manifest. For each:
- Not step8-eligible or below cutover: `missing-legacy`.
- Step8-eligible, at/above cutover, artifact absent/malformed: `missing-current`.
- Valid artifact: classify as `valid` with outcome (pinned/clean/dropped).

Compute `drop_rate = dropped / (pinned + clean + dropped)` over `valid` runs only. Do not include `missing-*` in the denominator.

Render compact section: runs scanned, valid / missing-current / missing-legacy counts, pinned / clean / dropped counts, drop rate, reason histogram for dropped outcomes.

Keep existing design guideline assessment section unchanged.

### UPDATED: docs/run-log-batches.md

Document `architectural-guideline-outcome` batch: slug, file name, schema, schema version, replace-mode behavior, feature-era cutover logic, and step8 condition.

### UPDATED: docs/run-logs.md

Add implement Step 8 guideline outcome section. Include `architectural-guideline-outcome.json` in the implement consumer-core keep set (retention section).

### UPDATED: python/tests/implement/test_ship.py

Add unit coverage:
- Pinned note: writes `pinned` sidecar and flushes before PR creation.
- Clean (absent guidelines): writes `clean` sidecar; `guidelines_status=absent`.
- Absent/invalid guidelines: `outcome=clean` with correct `guidelines_status`; never `dropped`.
- Materialization or redaction failure: writes `dropped` sidecar with stable reason token; stalls before PR in normal mode.
- Sidecar write failure in normal mode: stalls before PR creation.
- `--no-logs-commit`: sidecar written to tmpdir; no stall on failure.
- Rebase-refresh (`_refresh_guidelines_gate_after_rebase`): writes sidecar and flushes before `ensure_pr`.
- Log-only flush advances HEAD: `note_consumable` accepts fingerprint-stable note after larch-logs-only commit.
- Volatile-only result with existing committed artifact: accepted.
- Volatile-only result with missing committed artifact: stalls before PR creation.
- Stale prior sidecar cleared before new compose attempt.
- `needs_assessment=True`: sidecar skip, no flush.

Update existing warning-flush tests to expect new all-outcome flush behavior and stall message text.

### UPDATED: python/tests/issue/test_audit_runs.py

Add audit scan tests:
- `implement_step8_reachable` matches `_scan_required` step8 gating on representative manifests.
- Missing artifact below cutover: `informational`.
- Missing artifact at/above cutover, step8-eligible: `fail`.
- Valid pinned/clean/dropped artifacts with `schema_version=1`: classify correctly.
- gc-slimmed run with missing artifact: `informational`.
- Malformed, symlinked, empty, unknown outcome, missing schema_version, unknown reason token: `fail`.
- `compute-counters` reports drop counts and rate.

### UPDATED: python/tests/report/test_gc_run_logs.py

Add coverage: implement slimming preserves `architectural-guideline-outcome.json`.

### UPDATED: python/tests/report/test_run_logs.py

Add batch registry and flush staging tests. Verify sanitizer rejects malformed JSON and accepts expected schema shape.

### UPDATED: skills/fluff-analysis/scripts/test-fluff-analysis.sh

Extend synthetic fixture with: pinned, clean, dropped, missing-current, missing-legacy (pre-Step-8 and below-cutover). Assert report includes new section, correct drop-rate, and missing bucket counts.

## Edge cases

- `needs_assessment=True`: skip sidecar write and flush; no partial outcome emitted.
- Stale prior sidecar: cleared at compose attempt start to prevent false committed outcome.
- `--no-logs-commit`: sidecar written to tmpdir only; no stall.
- Volatile-only refresh: stall unless committed artifact already exists and matches.
- Log-only flush advances HEAD: `note_consumable` accepts fingerprint-stable notes.
- Absent or invalid guidelines: `outcome=clean`, not `dropped`. Drop rate not inflated.
- Below feature-era cutover: audit and fluff-analysis return `informational`; no false failures.
- GC slimming before keep-set update ships: audit treats gc-slimmed absent artifact as `informational`.
- `guidelines_status` always from materialized compose metadata, not inferred from note content.

## Failure modes

- Sidecar write failure in normal mode: stall before PR creation.
- Pre-PR flush failure (non-volatile-only): stall before PR creation.
- Volatile-only result with missing committed artifact: stall before PR creation.
- Malformed sidecar: flush fails closed through JSON sanitizer.
- Audit cannot infer step8: returns `informational` for legacy runs.
- Fluff-analysis malformed outcome: count as `missing-current` or `missing-legacy`; do not crash.

## Testing strategy

Run focused Python tests:

- `python3 -m pytest python/tests/implement/test_ship.py`
- `python3 -m pytest python/tests/report/test_run_logs.py`
- `python3 -m pytest python/tests/report/test_gc_run_logs.py`
- `python3 -m pytest python/tests/issue/test_audit_runs.py`

Run the skill-local harness:

- `bash skills/fluff-analysis/scripts/test-fluff-analysis.sh`

Run relevant checks for touched files:

- `python3 python/cli.py checks run-relevant`

## Acceptance

Run focused Python tests:

- `python3 -m pytest python/tests/implement/test_ship.py`
- `python3 -m pytest python/tests/report/test_run_logs.py`
- `python3 -m pytest python/tests/report/test_gc_run_logs.py`
- `python3 -m pytest python/tests/issue/test_audit_runs.py`

Run the skill-local harness:

- `bash skills/fluff-analysis/scripts/test-fluff-analysis.sh`

Run relevant checks for touched files:

- `python3 python/cli.py checks run-relevant`

review_status: complete
rounds_completed: 2
difficulty: HARD
diff_lines: 750
