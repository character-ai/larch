### FINDING_1:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/larch/issue/audit_runs.py:557-629
- **Concern**: Feature-era cutoff for missing-outcome failures is unspecified. Scenario: The plan requires informational results for pre-feature-era Step 8 runs and failures for current-era Step 8 runs missing architectural-guideline-outcome.json, but it never pins how current era is derived. step8 reachability alone is true for thousands of historical implement runs that legitimately lack the artifact; without a shared minimum larch_version (or equivalent), audit-runs will false-fail legacy runs and fluff-analysis will bucket them as missing-current instead of missing-legacy.
- **Proposed resolution**: Add a single config Final (for example GUIDELINE_SHIP_OUTCOME_MIN_LARCH_VERSION) set to the shipping release, reuse it in _guideline_ship_outcome_scan_obj and fluff-analysis implement coverage, and document the rule in docs/run-log-batches.md: compare manifest larch_version before failing on absence.

### FINDING_2:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: important
- **Focus area**: architecture
- **Location**: python/larch/implement/ship.py:560-663
- **Concern**: Outcome flush must account for the existing postbump pre-PR refresh. Scenario: The plan says only one pre-PR flush occurs per compose attempt and flushes the outcome after _guidelines_gate_before_pr, but fresh ship already calls flush_logs_pre during postbump/pr-prep before the guidelines gate. The outcome sidecar cannot exist at that earlier flush, so a second pre-PR flush is required; treating postbump refresh as sufficient or collapsing the two calls would skip committing the outcome. Clarify in ship.py that postbump refresh and guidelines outcome refresh are sequential compose attempts, volatile-only on the outcome pass must accept an already-committed matching artifact, and HEAD repin/fingerprint-stable note handling applies after the outcome commit even when postbump already advanced HEAD.
- **Proposed resolution**:

### FINDING_3:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: important
- **Focus area**: architecture
- **Location**: python/larch/issue/audit_runs.py:557-629
- **Concern**: Step 8 reachability should be one shared helper, not reimplemented. Scenario: The plan says the new scan reuses the step8 predicate from _scan_required, but that predicate is nested inside _scan_required today. Copying cond(step8) into _guideline_ship_outcome_scan_obj risks drift from required-file-presence and other step8-conditioned scans (the accepted Round 1 reachability finding).
- **Proposed resolution**: Extract a module-level step8_reachable(run_dir, manifest) helper from _scan_required cond logic and call it from both _scan_required and _guideline_ship_outcome_scan_obj; add audit tests that the helper matches required-file step8 gating on representative manifests.

### FINDING_4:
- **Reviewer(s)**: Codex-Arch
- **Severity**: important
- **Focus area**: correctness
- **Location**: plan.txt:26
- **Concern**: Sidecar write failure is allowed to ship without a durable outcome. Scenario: If terminal Step 8 classification succeeds but the JSON sidecar write fails, the plan logs a warning and continues. `_stage_pre_commit` then sees no sidecar and noops, so PR creation can proceed with committed logs still missing `architectural-guideline-outcome.json`.
- **Proposed resolution**: For non-`--no-logs-commit` runs, treat a terminal outcome sidecar write or verification failure as the same pre-PR stall class as flush failure. Only allow best-effort continuation in `--no-logs-commit` mode.

### FINDING_5:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/larch/implement/ship.py:283-289
- **Concern**: Remove the warning_logged-only pre-PR flush guard. Scenario: The plan replaces the warning flush hook but never explicitly requires dropping `if result.warning_logged:` around the pre-PR flush. Today pinned/clean gates with `warning_logged=False` never flush (see `test_fresh_ship_passes_compose_guidelines_note_to_pr_body`), which is the 62% invisible-drop bug the issue targets.
- **Proposed resolution**: Always invoke the shared outcome flush helper for every resolved gate (`pinned`/`clean`/`dropped`), not only when `warning_logged=True`; keep `needs_assessment=True` as the sole skip.

### FINDING_6:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/design plan Approach / ship_guidelines.py
- **Concern**: Best-effort sidecar write conflicts with committed-log acceptance. Scenario: The plan says sidecar write is best-effort and does not stall ship, while acceptance requires a committed pinned/clean/dropped outcome on every Step-8-completed run. A tmpdir write failure would still create a PR with no durable outcome, recreating the monitoring blind spot.
- **Proposed resolution**: Treat unresolved outcome persistence as fail-closed in normal log-commit mode: stall before PR when sidecar write or pre-PR flush cannot produce the committed batch (retain the `--no-logs-commit` non-stall carve-out).

### FINDING_7:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/larch/core/config.py
- **Concern**: Feature-era floor is unspecified for audit/fluff legacy gating. Scenario: The plan requires informational results for pre-feature-era runs and failures for current-era Step-8 runs, but adds no introducing-version Final alongside other run-log wire literals. Without a single floor, audit can false-fail older Step-8 runs or fluff can mis-bucket `missing-legacy` vs `missing-current`.
- **Proposed resolution**: Add a `GUIDELINE_SHIP_OUTCOME_INTRODUCED_VERSION` Final (ship version) and use it in the audit handler and fluff legacy classification; cover the boundary in `test_audit_runs.py` and `test-fluff-analysis.sh`.

### FINDING_8:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Focus area**: architecture
- **Location**: python/larch/issue/audit_runs.py:557-614 / skills/fluff-analysis/scripts/fluff-analysis.py
- **Concern**: Step-8 reachability is not shared for fluff missing-current bucketing. Scenario: Prior round accepted shared Step-8 reachability for the audit scan, but fluff must also label `missing-current` using the same predicate already duplicated across `audit_runs._scan_required` and `run_logs._verify_condition_reached`. A third inline copy will drift on bail/legacy runs and skew drop-rate coverage.
- **Proposed resolution**: Extract one shared `implement_step8_reached(run_dir, manifest)` helper (prefer the existing `run_logs` predicate) and call it from the new audit handler and fluff collector.

### FINDING_9:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: latent
- **Focus area**: architecture
- **Location**: python/larch/implement/ship.py / python/larch/core/architectural_guidelines.py:710-717
- **Concern**: Log-only flush HEAD repair leaves two competing implementations. Scenario: The plan offers both re-pinning durable-note metadata after larch-logs-only commits and teaching `note_consumable` to accept fingerprint-stable notes. Implementing both adds complexity and risks inconsistent PR-body vs outcome metadata.
- **Proposed resolution**: Pick one minimum-change strategy in the plan (prefer fingerprint-stable `note_consumable` when diff fingerprint matches) and test only that path for the log-only flush case.

### FINDING_10:
- **Reviewer(s)**: Codex-Innovation
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/larch/implement/ship_guidelines.py:16-21
- **Concern**: Outcome sidecar write cannot stay best-effort. Scenario: The plan lets a sidecar write failure log a warning and continue. Then Step 8 can create or refresh a PR with only execution-issues detail, while audit and fluff-analysis still lack the durable pinned clean dropped record required for every Step 8 run.
- **Proposed resolution**: Make current outcome JSON write and stage verification a required pre-PR gate except for no-logs-commit and unresolved needs_assessment. Return the write failure through GuidelinesGateResult or the flush hook and stall before PR creation.

### FINDING_11:
- **Reviewer(s)**: Codex-Innovation
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/larch/core/architectural_guidelines.py:399-407
- **Concern**: Stale outcome sidecar is not retired on skip paths. Scenario: A prior architectural-guideline-outcome.json can survive in the tmpdir. If a later compose attempt reaches needs_assessment and correctly skips writing a new outcome, a later log refresh can stage the stale JSON and report a false pinned clean or dropped result.
- **Proposed resolution**: Clear GUIDELINE_SHIP_OUTCOME_SIDECAR at the start of each compose outcome attempt and include it in stale artifact cleanup/invalidation, or make flushing consume only the current GuidelinesGateResult outcome rather than any ambient sidecar.

### FINDING_12:
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: blocking
- **Focus area**: correctness
- **Location**: python/larch/implement/ship.py:283-289
- **Concern**: Outcome flush is still gated on warning_logged. Scenario: The plan replaces the warning-only flush helper but does not require removing the `if result.warning_logged` guard. Pinned and clean Step 8 paths still skip pre-PR flush, so committed logs keep lacking `architectural-guideline-outcome.json` on the majority of successful ships.
- **Proposed resolution**: Always invoke the new outcome write+flush helper from `_guidelines_gate_before_pr` after `load_or_prepare_guidelines_note` resolves, for every terminal gate result except `needs_assessment=True` sidecar skip. Remove the `warning_logged` guard; keep warning append as a separate best-effort step.

### FINDING_13:
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/larch/core/config.py:726-728
- **Concern**: No pinned feature-era cutover for the new scan. Scenario: The plan says current-era runs must fail when the artifact is missing and legacy runs are informational, but it never defines how to tell them apart. Without a release-version constant, audit will false-fail older step8 runs or never fail real omissions after ship.
- **Proposed resolution**: Add a `GUIDELINE_SHIP_OUTCOME_MIN_LARCH_VERSION` Final (or equivalent) and compare `manifest.json::larch_version` in `_guideline_ship_outcome_scan_obj` and fluff-analysis. Below cutover: informational on absence. At/above cutover plus step8 reachability: fail on missing, empty, symlinked, or malformed outcome JSON.

### FINDING_14:
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: python/larch/issue/audit_runs.py:557-629
- **Concern**: Step 8 reachability should call the shared run_logs predicate, not a third copy. Scenario: The plan says to reuse the step8 predicate but points at `_scan_required` internals. `python/larch/report/run_logs.py` already owns `_verify_condition_reached(condition="step8", ...)`, and audit duplicates that logic today.
- **Proposed resolution**: Avoid a hand-copied `cond("step8")` in the new handler and in fluff-analysis. Factor or import the existing `run_logs` step8 reachability helper so audit, fluff-analysis, and required-files stay aligned on bail-signal and empty-manifest edge cases.

### FINDING_15:
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/larch/implement/ship_guidelines.py:108-151
- **Concern**: guidelines_status must come from compose materialization, not note text. Scenario: For absent or invalid guidelines, `load_or_prepare_guidelines_note` returns an empty `note` with no `guidelines_status` on `GuidelinesGateResult`. A classifier that infers from note emptiness can mark `dropped` or skip `outcome=clean`, re-breaking the accepted drop-rate contract.
- **Proposed resolution**: Thread `guidelines_status` (and `assessment_kind` when known) from `prepare_compose_assessment` / `read_guidelines` into `GuidelinesShipOutcome` construction. Classify `outcome=clean` for absent/invalid before evaluating present-guideline drop reasons.

### FINDING_16:
- **Reviewer(s)**: Codex-Pragmatic
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/larch/implement/ship_guidelines.py:planned
- **Concern**: Outcome sidecar write cannot be best-effort. Scenario: If atomic JSON write under IMPLEMENT_TMPDIR fails, the plan logs a warning and still creates or updates the PR. That Step 8 run can ship without committed architectural-guideline-outcome.json, so committed logs do not distinguish note-shipped from note-dropped with reason.
- **Proposed resolution**: Treat outcome sidecar write failure as a pre-PR stall except --no-logs-commit. Add a focused test that sidecar write failure blocks PR creation in normal mode.

### FINDING_17:
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/larch/implement/ship.py:205-247
- **Concern**: Volatile-only pre-PR flush lacks a fail path when no committed outcome exists. Scenario: The plan accepts volatile-only when a committed architectural-guideline-outcome.json already matches the tmpdir sidecar, but does not require stall when flush_logs_pre returns REFRESH_SKIP_VOLATILE_ONLY and the run log still lacks the artifact. A first Step 8 compose with nothing new to commit besides the outcome would proceed to ensure_pr without the acceptance-criteria committed outcome.
- **Proposed resolution**: After volatile-only, stall before PR creation unless run_dir/architectural-guideline-outcome.json exists and matches the tmpdir sidecar; treat missing or mismatched artifact as REFRESH_SKIP_COMMIT_FAILED in non-no-logs-commit mode.

### FINDING_18:
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: blocking
- **Focus area**: correctness
- **Location**: python/larch/implement/ship_guidelines.py:16-22
- **Concern**: Best-effort sidecar write conflicts with committed-outcome acceptance. Scenario: The plan marks tmpdir sidecar write best-effort and non-stalling, yet acceptance requires every Step 8 run to leave a committed pinned/clean/dropped record. If atomic JSON write fails, staging stays empty, flush cannot commit, and ship still creates the PR with zero durable signal.
- **Proposed resolution**: Treat sidecar write failure like flush failure in normal mode: log warning, classify outcome=dropped with reason sidecar-write-failed when classifiable, and stall before PR creation unless --no-logs-commit. Keep best-effort only for no-logs-commit.

### FINDING_19:
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/larch/issue/audit_runs.py:557-614
- **Concern**: Feature-era cutover for legacy runs is unspecified. Scenario: The handler must return informational for pre-feature-era absences, but the plan never defines the cutover (config Final, manifest larch_version compare, or scan --current-version floor). Implementers may fail all historical Step 8 runs or never fail post-ship missing artifacts.
- **Proposed resolution**: Add a single shared cutover constant (for example GUIDELINE_SHIP_OUTCOME_MIN_VERSION in config.py) and use it in _guideline_ship_outcome_scan_obj and fluff-analysis; fail only when step8-eligible, manifest version >= cutover, and artifact absent.

### FINDING_20:
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/larch/implement/ship_guidelines.py:108-129
- **Concern**: guidelines_status sourcing is undefined on the durable-note fast path. Scenario: load_or_prepare_guidelines_note returns a cached consumable note without guidelines_status or assessment metadata, while the classifier must emit guidelines_status and distinguish outcome=clean from outcome=dropped. Rebase refresh and resume paths can mislabel present-guideline drops as clean and deflate drop_rate.
- **Proposed resolution**: When classifying, read MATERIALIZE_ENV GUIDELINES_STATUS if present, else architectural_guidelines.read(repo_root); map absent/invalid to clean and present materialization/read/redaction failures to dropped only when guidelines_status=present.

### FINDING_21:
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: important
- **Focus area**: architecture
- **Location**: python/larch/issue/audit_runs.py:557-614
- **Concern**: Step 8 reachability is described but not factored for reuse. Scenario: FINDING_2 asked to share required-files Step 8 semantics; the plan still says derive from _scan_required without extracting the nested cond(step8) logic or adding a shared helper. Audit and fluff can diverge on bail-only runs, empty steps_ran, and pre-Step-8 stalls.
- **Proposed resolution**: Extract implement_step8_reachable(run_dir, manifest) from _scan_required cond(step8) and call it from _guideline_ship_outcome_scan_obj and the new fluff-analysis collector before classifying missing-current.

### FINDING_22:
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/fluff-analysis/scripts/fluff-analysis.py:696-719
- **Concern**: missing-current bucket needs explicit Step 8 gating. Scenario: The plan adds missing-current for step8-eligible current-era runs but does not require the implement collector to apply the same Step 8 predicate before counting absences. Stalled Step 3-7 runs would inflate missing-current and distort coverage.
- **Proposed resolution**: Mirror _collect_guideline_assessment_coverage wiring: enumerate implement runs with manifest, apply shared implement_step8_reachable, then classify missing-current only when reachable and era-eligible; keep other absent runs in missing-legacy.

### FINDING_23:
- **Reviewer(s)**: Codex-Requirements
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/larch/implement/ship_guidelines.py
- **Concern**: Outcome sidecar writes are allowed to fail best-effort. Scenario: The plan says sidecar write failure only logs a warning and does not stall. A normal Step 8 run can then create or update a PR with no durable committed outcome, so audit and fluff-analysis see a missing-current artifact instead of note-shipped or note-dropped.
- **Proposed resolution**: Make the sidecar write return success or failure. In non-`--no-logs-commit` mode, stall before PR creation when the outcome sidecar cannot be written or staged. Keep best-effort only for the human-readable warning append.
