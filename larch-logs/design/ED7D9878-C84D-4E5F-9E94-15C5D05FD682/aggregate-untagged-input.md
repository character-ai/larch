### FINDING_1:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: major
- **Focus area**: correctness
- **Location**: python/larch/issue/audit_runs.py
- **Concern**: Implement audit-runs still lacks an invariant ship-outcome scan sibling. Scenario: The plan adds `RUN_LOG_BATCH_INVARIANT_SHIP_OUTCOME`, flush/validate paths, and `INVARIANT_SHIP_OUTCOME_MIN_LARCH_VERSION`, but `audit_runs.py` only mirrors the design assessment scan. `_guideline_ship_outcome_scan_obj` and `scans-implement.tsv` row `guideline-ship-outcome` still have no invariant twin, so post-cutover implement runs can commit malformed or missing `architectural-invariant-outcome.json` without audit failure.
- **Proposed resolution**: Add `_invariant_ship_outcome_scan_obj` (reuse cutover gating + `validate_invariant_ship_outcome_record`), register `invariant-ship-outcome` in `_NAMED_RUN_SCAN_HANDLERS`, add a `scans-implement.tsv` row, and extend `python/tests/issue/test_audit_runs.py` with missing/cutover/valid/malformed cases mirroring the guideline ship-outcome tests.

### FINDING_2:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: major
- **Focus area**: correctness
- **Location**: .claude/skills/audit-runs/scans-design.tsv
- **Concern**: Design audit registry never invokes the new invariant assessment scan. Scenario: `audit_runs.py` scans are driven only from `scans-design.tsv` / `scans-implement.tsv` name lists. The plan adds a Python handler for `architectural-invariant-assessment.md` but no design-registry row, so `/audit-runs --skill=design` will never run invariant assessment validation even after the handler lands.
- **Proposed resolution**: Add an `invariant-assessment` row to `scans-design.tsv` (mirror `guideline-assessment`), register the handler name in `_NAMED_RUN_SCAN_HANDLERS`, classify `clean` vs `violation` using `CLEAN_INVARIANT_PRESENTATION_NOTE` (not guideline deviation logic), and pin the row in `python/tests/issue/test_audit_runs.py`.

### FINDING_3:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: minor
- **Focus area**: correctness
- **Location**: python/larch/issue/audit_runs.py
- **Concern**: Invariant design assessment scan must distinguish violation from clean. Scenario: The guideline scan treats any non-clean body as `deviation`. Invariant Gate C persistence uses violation semantics; a copied handler would mislabel blocking violations as benign deviations in audit output.
- **Proposed resolution**: When implementing the invariant assessment scan, branch on invariant clean note equality and emit `assessment_kind` of `clean` or `violation`; add a violation-fixture test in `test_audit_runs.py`. ## Findings ### 1. Implement audit-runs missing invariant ship-outcome scan (major, correctness) The binding scope requires mirroring every guideline consumer. Implement audit already validates `architectural-guideline-outcome.json` via `_guideline_ship_outcome_scan_obj` and `.claude/skills/audit-runs/scans-implement.tsv`. The plan wires invariant outcomes through `config.py`, `run_log_flush.py`, `run_log_batch.py`, and `gc_run_logs.py`, but stops at a design-only `audit_runs.py` addition. Without an implement scan sibling, the new batch can ship without audit detection of absent, empty, symlinked, or malformed invariant outcome JSON on post-cutover Step 8 runs. **Suggested revision:** Mirror `_guideline_ship_outcome_scan_obj` for `architectural-invariant-outcome.json`, wire the `scans-implement.tsv` row, use the planned min-version constant, and add harness tests parallel to `test_guideline_ship_outcome_scan_*`. ### 2. Design audit registry row missing (major, correctness) _NAMED_RUN_SCAN_HANDLERS = { "codex-round1-adherence": _codex_round_adherence_scan_obj, "guideline-assessment": _guideline_assessment_scan_obj, "guideline-ship-outcome": _guideline_ship_outcome_scan_obj, } Scan names come from the TSV registries (`scans-design.tsv` line 3 for guidelines). A handler alone is inert without a registry row. The plan updates `audit_runs.py` and `test_audit_runs.py` but not `scans-design.tsv`, so design audits will skip invariant assessment coverage. **Suggested revision:** Add `invariant-assessment` to `scans-design.tsv` and register the handler alongside the guideline entry. ### 3. Invariant assessment scan semantics (minor, correctness) The guideline assessment scan classifies non-clean bodies as `deviation`. Invariants use blocking `violation` semantics in Gate C and Step 8. Copy-pasting the guideline classifier would misreport violations in audit chain-of-history output. **Suggested revision:** Use `CLEAN_INVARIANT_PRESENTATION_NOTE` and emit `violation` for non-clean invariant assessments; cover with a violation fixture test. --- **[OUT_OF_SCOPE]** `python/larch/issue/audit_runs.py` `compute-counters` — Mirror `GUIDELINE_OUTCOME_*` / `GUIDELINE_DROP_RATE_BPS` with `INVARIANT_OUTCOME_*` counters. Real parity gap for audit deltas, but implement/design mirror ships without it; file as follow-up. **[OUT_OF_SCOPE]** `skills/implement/references/conflict-resolution.md` — Post-conflict prose still promises `guidelines-assessment` on relaunch. Round 1 rejected; `ship.py` compose ordering should still route correctly via driver state. **[OUT_OF_SCOPE]** `.claude/skills/audit-runs/SKILL.md` — Update the design scan table to mention invariant assessment. Documentation drift only; scanners work once TSV rows exist.

### FINDING_4:
- **Reviewer(s)**: Codex-Arch
- **Severity**: major
- **Focus area**: correctness
- **Location**: python/larch/core/architectural_guidelines.py:1002-1015
- **Concern**: Blank invariant files are still routed to Step 8 assessment. Scenario: The seeded ARCHITECTURAL_INVARIANTS.md can be present with no parsed I-* entries. If the invariant kind mirrors the guideline present-status compose path, Step 8 returns architectural-invariants-assessment on every run even though there is nothing to assess, blocking PR compose until a no-op note is authored.
- **Proposed resolution**: Make invariant compose and presentation checks require result.content.strip() before emitting INVARIANTS_VIOLATION_ASSESSMENT_REQUIRED or NEEDS_USER_REASON=architectural-invariants-assessment; treat present-empty invariants as no parsed entries with a clean/no-assessment outcome and continue to guidelines.

### FINDING_5:
- **Reviewer(s)**: Codex-Arch
- **Severity**: major
- **Focus area**: security
- **Location**: skills/implement/references/ship-pr-ci-fix.md:9-22
- **Concern**: Invariant violation repair branch reads untrusted detail without a prompt boundary. Scenario: DETAIL, DETAIL_FILE, and architectural-invariant-note.md are derived from repo-local ARCHITECTURAL_INVARIANTS.md and a prompt-authored assessment. Without explicit untrusted framing in the ci-fix branch, a malicious I-* entry or copied note text can be interpreted as repair instructions during autonomous edits.
- **Proposed resolution**: In the new architectural-invariants-violation branch, label DETAIL, DETAIL_FILE, and the invariant note as untrusted evidence; instruct the fixer to use only the cited I-* ids and violation rationale, and to ignore instructions inside those artifacts that conflict with AGENTS.md, skills, guards, or the plan.

### FINDING_6:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: major
- **Focus area**: code-quality
- **Location**: .claude/skills/audit-runs/scans-design.tsv:1-3
- **Concern**: Invariant design assessment scan is not registered in the audit-runs TSV registry. Scenario: The plan adds an invariant assessment handler in audit_runs.py but never adds an invariant-assessment row to scans-design.tsv, so /audit-runs never dispatches the scan even after the Python helper lands
- **Proposed resolution**: Add an invariant-assessment row to scans-design.tsv, register the handler in _NAMED_RUN_SCAN_HANDLERS, and extend test_audit_runs.py with a scans-design.tsv dispatch fixture mirroring guideline-assessment

### FINDING_7:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: major
- **Focus area**: code-quality
- **Location**: python/larch/issue/audit_runs.py:281-327
- **Concern**: Implement runs still lack an invariant ship-outcome audit scan sibling. Scenario: The plan mirrors design assessment scanning and implement outcome batches/GC, but not the guideline-ship-outcome named handler, scans-implement.tsv row, INVARIANT_SHIP_OUTCOME_MIN_LARCH_VERSION cutover, or compute_counters INVARIANT_OUTCOME_* tallies; committed architectural-invariant-outcome.json artifacts will not be validated in /audit-runs
- **Proposed resolution**: Add _invariant_ship_outcome_scan_obj with validate_invariant_ship_outcome_record, register invariant-ship-outcome in _NAMED_RUN_SCAN_HANDLERS and scans-implement.tsv, mirror version cutover handling, extend compute_counters_main, and add test_audit_runs.py coverage parallel to guideline-ship-outcome

### FINDING_8:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: major
- **Focus area**: correctness
- **Location**: skills/implement/references/ship-pr-ci-fix.md:11-12
- **Concern**: Invariant-violation ci-fix must bypass the empty FAILED_RUN_ID bailout, not only skip gh run-logs. Scenario: The plan routes architectural-invariants-violation through ci-fix and adds repair before log capture, but step 1b still bails when FAILED_RUN_ID is empty; pre-PR invariant violations never reach autonomous repair and stall at operator-bail Branch on NEEDS_USER_REASON=architectural-invariants-violation before step 1b, skip FAILED_RUN_ID and gh run-logs, repair from DETAIL/DETAIL_FILE and architectural-invariant-note.md, then relaunch Step 8; pin this ordering in test-architectural-guidelines-step.sh
- **Proposed resolution**:

### FINDING_9:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: major
- **Focus area**: risk-integration
- **Location**: skills/design/references/design-outline.md:65-85
- **Concern**: Step 1d.7 invariant remediation lacks a durable attempt counter. Scenario: The plan bounds Gate C remediation with architectural-invariant-gatec-remediation.count but only says bounded retry for Step 1d.7 outline violations; pause/resume or repeated entry can reset the outline loop while Gate C stays bounded Persist an outline remediation counter under $DESIGN_TMPDIR (for example architectural-invariant-outline-remediation.count), read/increment it on each outline rewrite, and hard-stop after the same bound used at Gate C ### 1. [completeness] Audit-runs design registry omits invariant assessment scan (`.claude/skills/audit-runs/scans-design.tsv`) The plan adds Python scan logic for `architectural-invariant-assessment.md` but does not update `scans-design.tsv`. Audit dispatch is driven entirely by that registry (`audit_runs.py` iterates scan names from the TSV). Without a row, the handler is dead code and design runs will not get the invariant assessment mirror that guidelines already receive via `guideline-assessment`. **Suggested revision:** Add `invariant-assessment` to `scans-design.tsv`, wire the handler in `_NAMED_RUN_SCAN_HANDLERS`, and add a registry-dispatch test like `test_scan_run_dispatches_guideline_assessment_from_design_registry`. ### 2. [completeness] Audit-runs implement mirror stops at design assessment (`python/larch/issue/audit_runs.py`) Guidelines have both a design assessment scan and a `guideline-ship-outcome` named handler backed by `scans-implement.tsv`, version cutover, and `GUIDELINE_OUTCOME_*` counters in `compute_counters_main`. The plan mirrors batches, GC, and fluff-analysis for invariant outcomes but omits the implement audit surface entirely. That leaves a hole in the issue’s “mirror every consumer” contract: post-cutover implement runs can commit `architectural-invariant-outcome.json` without audit validation or summary counts. **Suggested revision:** Mirror `_guideline_ship_outcome_scan_obj` for invariants (clean/violation/dropped semantics), add `INVARIANT_SHIP_OUTCOME_MIN_LARCH_VERSION`, register `invariant-ship-outcome` in `scans-implement.tsv`, extend `compute_counters_main`, and add parallel tests in `test_audit_runs.py`. ### 3. [correctness] `ship-pr-ci-fix.md` invariant branch must precede step 1b (`skills/implement/references/ship-pr-ci-fix.md`) Round 1 accepted that routing `architectural-invariants-violation` through `ci-fix` requires a repair contract without `FAILED_RUN_ID`. The plan adds an invariant-violation branch “before the CI run-log capture path,” but the current procedure bails at step 1b when `FAILED_RUN_ID` is empty. Pre-PR invariant handoffs have no failed CI run, so the repair branch never runs unless it short-circuits before step 1b. **Suggested revision:** Make `NEEDS_USER_REASON=architectural-invariants-violation` the first branch in the procedure, before step 1b, and pin that ordering in the Step 8 harness. ### 4. [risk-integration] Step 1d.7 outline remediation needs a persisted counter (`skills/design/references/design-outline.md`) The plan correctly persists Gate C remediation in `architectural-invariant-gatec-remediation.count` (addressing the accepted round-1 finding). Step 1d.7 gets the same blocking invariant semantics but only a vague “bounded retry count” with no durable storage. On pause/resume or re-entry, outline remediation can reset while Gate C stays bounded. **Suggested revision:** Persist an outline remediation counter under `$DESIGN_TMPDIR`, increment it on each invariant-driven outline rewrite, and hard-stop after the same bound used at Gate C.
- **Proposed resolution**:

### FINDING_10:
- **Reviewer(s)**: Codex-Innovation
- **Severity**: major
- **Focus area**: code-quality
- **Location**: skills/implement/SKILL.md:1-5
- **Concern**: New invariant wrapper sibling doc lacks a parent-skill reachability pin. Scenario: The plan adds skills/implement/scripts/step-architectural-invariants-write-compose.md but only says to link it from the invariant reference and harness. Existing sibling docs under skills/implement/scripts need a parent SKILL reference or an agent-lint exclusion, or S030/orphaned-skill-files can fail and block verification.
- **Proposed resolution**: Add the new md path to the Referenced implement script files header in skills/implement/SKILL.md, or add a justified agent-lint.toml exclusion if it must stay off the runtime prompt surface.

### FINDING_11:
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: minor
- **Focus area**: correctness
- **Location**: skills/design/references/design-outline.md
- **Concern**: Step 1d.7 invariant remediation lacks durable attempt storage. Scenario: Gate C will persist architectural-invariant-gatec-remediation.count, but the outline gate only says use a bounded retry count with no $DESIGN_TMPDIR counter, so pause/resume or re-entry can reset remediation and repeat the same violation rewrite loop
- **Proposed resolution**: Mirror Gate C: persist $DESIGN_TMPDIR/architectural-invariant-outline-remediation.count, read on Step 1d.7 invariant entry, increment per remediation attempt, hard-stop after the bound, and pin the contract in scripts/test-design-structure.sh

### FINDING_12:
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: minor
- **Focus area**: risk-integration
- **Location**: python/larch/issue/audit_runs.py
- **Concern**: audit-runs mirror stops at design assessment and omits implement ship-outcome validation. Scenario: The plan adds architectural-invariant-assessment.md scanning but not an invariant-ship-outcome sibling to guideline-ship-outcome, so committed architectural-invariant-outcome.json sidecars are never schema-checked, cutover-gated, or counted even though run-log batch staging and GC keep-set work is planned
- **Proposed resolution**: Add _invariant_ship_outcome_scan_obj using validate_invariant_ship_outcome_record, register invariant-ship-outcome in the scan map, mirror _at_or_above_guideline_outcome_cutover with INVARIANT_SHIP_OUTCOME_MIN_LARCH_VERSION from config.py, extend summary delta keys, and add python/tests/issue/test_audit_runs.py parity tests ## Findings ### 1. correctness — Step 1d.7 invariant remediation lacks durable attempt storage **Location:** `skills/design/references/design-outline.md` The plan fixes Gate C unbounded remediation with a persisted `$DESIGN_TMPDIR/architectural-invariant-gatec-remediation.count`, but the Step 1d.7 outline path only calls for a bounded retry count without durable storage. On pause/resume, the outline gate can re-enter with a reset counter and repeat violation rewrites. **Suggested revision:** Persist `$DESIGN_TMPDIR/architectural-invariant-outline-remediation.count` with the same read/increment/hard-stop pattern as Gate C, and pin it in `scripts/test-design-structure.sh`. ### 2. risk-integration — audit-runs mirror stops at design assessment **Location:** `python/larch/issue/audit_runs.py` The plan’s consumer-parity rule covers audit surfaces, and it stages `architectural-invariant-outcome.json` into run logs, but `audit_runs.py` updates only add `architectural-invariant-assessment.md` scanning. Today `guideline-ship-outcome` validates implement sidecars with cutover gating and summary counts; without an invariant sibling, malformed or missing invariant outcome artifacts on post-cutover runs will not be caught. **Suggested revision:** Add `_invariant_ship_outcome_scan_obj`, a required `INVARIANT_SHIP_OUTCOME_MIN_LARCH_VERSION` in `config.py`, registry/summary wiring, and `test_audit_runs.py` coverage mirroring the guideline ship-outcome tests. --- **Prior ledger note:** Accepted round-1 items for ci-fix branching, PR refresh, rebase refresh, phase wiring, Gate C counter persistence, and design-outline inputs appear addressed in the current plan. FINDING_4 (neutral) remains partially open because only the assessment scan is planned, not ship-outcome audit parity.

### FINDING_13:
- **Reviewer(s)**: Codex-Pragmatic
- **Severity**: major
- **Focus area**: risk-integration
- **Location**: python/skill-closure-baseline.json
- **Concern**: The plan edits ratcheted skill prompts but omits the closure baseline update. Scenario: `skills/design/SKILL.md` and `skills/implement/SKILL.md` are firm updates, and `lint-skill-closure-growth` is always-run in pre-commit and CI. The new prompt text can exceed the checked baseline, leaving the implementer unable to pass CI without editing an out-of-plan file.
- **Proposed resolution**: Add `### UPDATED: python/skill-closure-baseline.json` and regenerate it with `python3 python/cli.py lint skill-closure-growth --write` when the changed skill closure grows.

### FINDING_14:
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: major
- **Focus area**: code-quality
- **Location**: python/larch/issue/audit_runs.py
- **Concern**: Audit-runs mirror is incomplete: only a design-assessment helper is planned, not the implement invariant ship-outcome scan, scan-registry rows, or compute counter wiring. Scenario: The guideline mirror registers `guideline-ship-outcome` in `_NAMED_RUN_SCAN_HANDLERS`, `.claude/skills/audit-runs/scans-implement.tsv`, and `compute_counters` (`GUIDELINE_OUTCOME_*` KVs). The plan adds only an invariant assessment scan helper and `test_audit_runs.py` assessment cases. Committed `architectural-invariant-outcome.json` artifacts would never be audited, and even the new design assessment handler will not dispatch without a `scans-design.tsv` row (see `_scan_design_guideline` in `python/tests/issue/test_audit_runs.py`).
- **Proposed resolution**: Add `_invariant_ship_outcome_scan_obj` mirroring `_guideline_ship_outcome_scan_obj` (Step 8 reachability, version cutover via `INVARIANT_SHIP_OUTCOME_MIN_LARCH_VERSION`, `validate_invariant_ship_outcome_record`); register `invariant-ship-outcome` in `scans-implement.tsv` and `invariant-assessment` in `scans-design.tsv`; extend `compute_counters` with invariant outcome KVs; add `test_audit_runs.py` registry-dispatch and ship-outcome parity tests. List the two scans TSV files as firm plan updates.

### FINDING_15:
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: major
- **Focus area**: correctness
- **Location**: skills/design/references/design-outline.md
- **Concern**: Step 1d.7 invariant remediation has no durable attempt counter. Scenario: Gate C remediation is fixed with `architectural-invariant-gatec-remediation.count`, but the outline path only says "bounded retry count" with no persisted counter. Pause/resume or re-entry can reset the count and allow unbounded rewrite loops.
- **Proposed resolution**: Persist outline remediation under `$DESIGN_TMPDIR` (for example `architectural-invariant-outline-remediation.count`), read and increment on each remediation attempt, hard-stop after the bound, and pin the contract in `scripts/test-design-structure.sh`.

### FINDING_16:
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: major
- **Focus area**: correctness
- **Location**: skills/design/references/design-outline.md
- **Concern**: `--skip-approve` lacks an explicit invariant-violation blocking carve-out. Scenario: Gate C is planned to block auto-approve on violations. Step 1d.7 still auto-approves after presentation when `skip_approve_requested=true`. With invariant violations present, that path can write `.outline-approved` and reach Step 2b before remediation finishes.
- **Proposed resolution**: Mirror Gate C: run invariant `present-note` and assessment before guidelines; under `--skip-approve`, do not write `.outline-approved` until invariant clean or absent/invalid handling succeeds; on residual violations, enter the remediation loop instead of auto-approve.
