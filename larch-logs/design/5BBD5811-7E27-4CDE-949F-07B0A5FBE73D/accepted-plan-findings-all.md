### FINDING_1: Pre-PR outcome flush choreography
- **Reviewer(s)**: Cursor-Arch, Cursor-Innovation, Cursor-Pragmatic, Codex-dyn-Run Log Integrity
- **Severity**: important
- **Concern**: The ship-time outcome sidecar/flush path can run too early, depend on warning logging, duplicate a pre-PR commit on fresh runs, or treat an already-committed volatile-only retry as a new failure.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: In ship_guidelines gate classification, skip sidecar write and pre-PR outcome flush whenever needs_assessment=True and the gate is not a terminal dropped path (read/redaction/materialization failure). Emit the sidecar only after the gate resolves to pinned, clean, or dropped
  - From Cursor-Innovation: Write and classify the outcome sidecar before optional warning append; treat warning append as best-effort detail only
  - From Cursor-Innovation: When needs_assessment is true, skip outcome commit and pre-PR flush; write the durable outcome only on the path that proceeds to PR compose
  - From Cursor-Pragmatic: Specify one post-guidelines pre-PR flush on fresh runs: defer the postbump `flush_logs_pre` until after `_guidelines_gate_before_pr`, or add a batch-only restage path that commits the outcome without a second full refresh when postbump already flushed; update `test_straight_merge_green_ci_single_pre_pr_flush` / fresh-path flush-count tests accordingly.
  - From Codex-dyn-Run Log Integrity: In the guideline-outcome flush hook, accept no-op or volatile-only only after verifying the committed `architectural-guideline-outcome.json` exists for the run and matches the tmpdir sidecar, or return a distinct unchanged success from `flush_logs_pre`.


### FINDING_2: Step-8 guideline scan must reuse shared reachability
- **Reviewer(s)**: Cursor-Arch, Cursor-dyn-Run Log Integrity
- **Severity**: important
- **Concern**: The new guideline-ship-outcome scan needs to share the same Step 8 reachability and handler-registration semantics as required-files, or it will drift on pre-Step-8 and legacy runs.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Add a named handler registered beside guideline-assessment that reuses the existing step8 reachability helper (final-summary.md, version-bump-reasoning.md, or chained step9a1, with steps_ran.step8=false respected). Document that predicate in the scan section of the plan
  - From Cursor-dyn-Run Log Integrity: Implement `guideline-ship-outcome` by calling the shared step8 predicate (extract from `_scan_required` if needed), then apply version-aware legacy handling. Register the handler beside `guideline-assessment` (`audit_runs.py:203-206`) and wire `scans-implement.tsv` to the named handler.


### FINDING_3: Fluff-analysis denominator needs missing coverage
- **Reviewer(s)**: Cursor-Arch, Cursor-dyn-Run Log Integrity, Codex-dyn-Run Log Integrity
- **Severity**: important
- **Concern**: Fluff-analysis should include step8-eligible runs that are missing the new artifact as missing coverage, not silently exclude them, and compute drop_rate only over valid outcomes.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Enumerate implement run dirs with the same cutoff or since_version filters as design assessment coverage, mark step8-eligible runs without a valid outcome JSON as missing, and compute drop_rate as dropped divided by pinned+clean+dropped among runs with valid outcomes while listing missing separately
  - From Cursor-dyn-Run Log Integrity: Collect only runs that satisfy the same step8 predicate (or parseable outcome JSON), treat legacy/missing as `missing` excluded from drop-rate numerator/denominator, and compute `drop_rate` from `dropped / (pinned+clean+dropped)`. Extend `test-fluff-analysis.sh` with legacy and pre-Step-8 fixtures.
  - From Codex-dyn-Run Log Integrity: Mirror the design coverage pattern for implement: enumerate committed `larch-logs/implement/*` run dirs, infer Step 8 reachability, classify present, malformed, missing-current, and missing-legacy or unknown, then compute the drop rate over valid outcome records while reporting missing buckets.


### FINDING_6: Log-only flush can stale out durable note metadata
- **Reviewer(s)**: Codex-Arch, Codex-Innovation, Cursor-dyn-Run Log Integrity
- **Severity**: important
- **Concern**: A logs-only pre-PR commit advances HEAD and can make a fingerprint-valid note look stale to consumability checks.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Arch: Add a firm plan step to keep the durable note consumable across the log-only commit, either by repinning the note metadata to the post-flush HEAD when only larch-logs changed or by teaching note_consumable/load_or_prepare to accept fingerprint-stable notes after larch-logs-only commits.
  - From Codex-Innovation: Add an explicit post-flush metadata refresh or fingerprint-based same-diff acceptance path, plus a resume or PR-create-failure test
  - From Cursor-dyn-Run Log Integrity: After a successful log-only flush with a pinned note, bump durable note `HEAD_SHA`/`ASSESSED_HEAD_SHA` to the post-commit HEAD when the implementation diff fingerprint is unchanged, or teach compose reload to trust fingerprint match across log-only HEAD advances. Add a `test_ship.py` case that flushes a pinned outcome, advances HEAD with a logs-only commit, then exercises `_refresh_guidelines_gate_after_rebase`.


### FINDING_7: Required-file row needs legacy cutover
- **Reviewer(s)**: Codex-Arch, Cursor-Innovation, Codex-Requirements, Codex-dyn-Run Log Integrity
- **Severity**: important
- **Concern**: Adding the outcome JSON to generic step8 required-files will false-fail older runs unless the row is version-aware or omitted in favor of the dedicated scan.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Arch: Add a version or feature-era condition for this required file, update _scan_required to treat pre-feature Step 8 absences as informational, or leave the new artifact out of required-files and rely on the dedicated guideline-ship-outcome scan for coverage.
  - From Cursor-Innovation: Gate the row on introducing larch_version (manifest.json) in both verify paths, or omit it from run-logs-required-files.tsv and enforce only via the version-aware guideline-ship-outcome scan
  - From Codex-Requirements: Keep enforcement in `guideline-ship-outcome`, or add a version-aware condition for the required-files row. In `audit_runs.py`, return `informational`/`skip` when the artifact is absent on runs below the introducing version (mirror design `guideline-assessment` at `audit_runs.py:182-189`). Add `test_audit_runs.py` coverage for a legacy run with `final-summary.md` but no outcome JSON.
  - From Codex-dyn-Run Log Integrity: Do not put the new file under the generic `step8` condition, or add a cutover-aware required-file rule that returns informational for pre-feature or unknown legacy runs and fails only current Step 8 runs.


### FINDING_8: Absent or invalid guidelines should stay clean
- **Reviewer(s)**: Cursor-Innovation, Cursor-dyn-Run Log Integrity
- **Severity**: important
- **Concern**: The ship-time classifier shouldn't turn missing or invalid guidelines into dropped outcomes, or the drop rate will be inflated.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Innovation: Map guidelines_status absent or invalid to outcome=clean (assessment_kind empty); reserve dropped for guidelines_status=present when the PR ships without a note
  - From Cursor-dyn-Run Log Integrity: Spell out classification: `absent`/`invalid` -> `outcome=clean` with matching `guidelines_status`; reserve `dropped` for `guidelines_status=present` failures (materialization, redaction, fingerprint/stale handling). Add unit tests in `test_ship.py` for absent and invalid repos.


### FINDING_9: GC slimming must retain outcome artifact
- **Reviewer(s)**: Codex-Innovation, Codex-Pragmatic, Codex-Requirements, Cursor-dyn-Run Log Integrity
- **Severity**: important
- **Concern**: Retention pruning must not delete the durable outcome JSON from aged implement logs, or later audits will lose the only committed source of truth.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Innovation: Add `architectural-guideline-outcome.json` to the implement keep set and include any matching retention test or docs update in the plan
  - From Codex-Pragmatic: Add the artifact to the implement keep set, update the retention docs and skill prose that list consumer-core files, and extend `python/tests/report/test_gc_run_logs.py` to assert slimming preserves it.
  - From Codex-Requirements: Add architectural-guideline-outcome.json to the implement keep set, update the retention docs, and include it in the existing GC keep-set coverage
  - From Cursor-dyn-Run Log Integrity: Add `architectural-guideline-outcome.json` to implement `SKILL_KEEP` and the `/implement` consumer-core list in `docs/run-logs.md` retention. Extend `test_gc_run_logs.py` to assert the file survives slimming.


### FINDING_10: Rebase refresh must share outcome flush contract
- **Reviewer(s)**: Cursor-Pragmatic, Cursor-Requirements, Cursor-dyn-Run Log Integrity
- **Severity**: important
- **Concern**: The rebase refresh path and its tests need the same outcome flush/commit contract as initial PR creation, or rebases can ship without committed outcomes.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Pragmatic: Replace `_flush_guidelines_warning_before_pr` inside `_guidelines_gate_before_pr` with the all-outcome flush hook so every caller (initial PR create and rebase refresh) stages/commits the sidecar before `ensure_pr`; add/adjust a merge-loop rebase test to assert the batch is committed.
  - From Cursor-Requirements: State explicitly that outcome sidecar write plus pre-PR flush run inside `_guidelines_gate_before_pr` (or a single helper it always calls) so both the initial PR-create path and `_refresh_guidelines_gate_after_rebase` share one contract; add a rebase-refresh unit test in `test_ship.py`.
  - From Cursor-dyn-Run Log Integrity: Add `test_ship.py` coverage that drives `_refresh_guidelines_gate_after_rebase` (or merge-loop rebase stubs) and asserts outcome sidecar write plus `flush_logs_pre` ordering before `ensure_pr` for pinned/clean and dropped cases.


### FINDING_12:
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: python/larch/report/gc_run_logs.py:20-25
- **Concern**: [SCOPE-REDUCTION] Plan omits gc-run-logs keep-set updates for the new batch. Scenario: /design already keeps `architectural-guideline-assessment.md` in `SKILL_KEEP`, but implement `SKILL_KEEP` and `docs/run-logs.md` retention lists do not mention `architectural-guideline-outcome.json`. `/gc-run-logs` will delete the new artifact from slimmed implement dirs, so audit and fluff-analysis lose the durable drop signal on aged runs.
- **Proposed resolution**: Add `architectural-guideline-outcome.json` to implement `SKILL_KEEP` in `python/larch/report/gc_run_logs.py` and to the implement consumer-core keep set in `docs/run-logs.md` (retention section), mirroring the design assessment file.


### FINDING_1: Missing-outcome scans need a shared feature-era floor
- **Reviewer(s)**: Cursor-Arch, Cursor-Innovation, Cursor-Pragmatic, Cursor-Requirements
- **Severity**: important
- **Concern**: The audit and fluff paths need one explicit release/version cutover to distinguish legacy Step 8 runs from current-era runs with missing `architectural-guideline-outcome.json`; otherwise historical runs can false-fail and current misses can be misbucketed.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Add a single config Final (for example GUIDELINE_SHIP_OUTCOME_MIN_LARCH_VERSION) set to the shipping release, reuse it in _guideline_ship_outcome_scan_obj and fluff-analysis implement coverage, and document the rule in docs/run-log-batches.md: compare manifest larch_version before failing on absence.
  - From Cursor-Innovation: Add a `GUIDELINE_SHIP_OUTCOME_INTRODUCED_VERSION` Final (ship version) and use it in the audit handler and fluff legacy classification; cover the boundary in `test_audit_runs.py` and `test-fluff-analysis.sh`.
  - From Cursor-Pragmatic: Add a `GUIDELINE_SHIP_OUTCOME_MIN_LARCH_VERSION` Final (or equivalent) and compare `manifest.json::larch_version` in `_guideline_ship_outcome_scan_obj` and fluff-analysis. Below cutover: informational on absence. At/above cutover plus step8 reachability: fail on missing, empty, symlinked, or malformed outcome JSON.
  - From Cursor-Requirements: Add a single shared cutover constant (for example GUIDELINE_SHIP_OUTCOME_MIN_VERSION in config.py) and use it in _guideline_ship_outcome_scan_obj and fluff-analysis; fail only when step8-eligible, manifest version >= cutover, and artifact absent.


### FINDING_2: Step 8 reachability needs one shared helper
- **Reviewer(s)**: Cursor-Arch, Cursor-Innovation, Cursor-Pragmatic, Cursor-Requirements
- **Severity**: important
- **Concern**: Audit, required-files, and fluff-analysis all need the same Step 8 reachability predicate; duplicating or inlining it risks drift on bail-only, empty-manifest, and pre-Step-8 stall cases.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Extract a module-level step8_reachable(run_dir, manifest) helper from _scan_required cond logic and call it from both _scan_required and _guideline_ship_outcome_scan_obj; add audit tests that the helper matches required-file step8 gating on representative manifests.
  - From Cursor-Innovation: Extract one shared `implement_step8_reached(run_dir, manifest)` helper (prefer the existing `run_logs` predicate) and call it from the new audit handler and fluff collector.
  - From Cursor-Pragmatic: Avoid a hand-copied `cond("step8")` in the new handler and in fluff-analysis. Factor or import the existing `run_logs` step8 reachability helper so audit, fluff-analysis, and required-files stay aligned on bail-signal and empty-manifest edge cases.
  - From Cursor-Requirements: Extract implement_step8_reachable(run_dir, manifest) from _scan_required cond(step8) and call it from _guideline_ship_outcome_scan_obj and the new fluff-analysis collector before classifying missing-current.
  - From Cursor-Requirements: Mirror _collect_guideline_assessment_coverage wiring: enumerate implement runs with manifest, apply shared implement_step8_reachable, then classify missing-current only when reachable and era-eligible; keep other absent runs in missing-legacy.


### FINDING_3: Outcome flush must happen on the guidelines pass
- **Reviewer(s)**: Cursor-Arch, Cursor-Innovation, Cursor-Pragmatic, Cursor-Requirements
- **Severity**: blocking
- **Concern**: The pre-PR postbump refresh is not enough; the outcome flush has to run unconditionally on the guidelines compose attempt, after `load_or_prepare_guidelines_note` resolves, and volatile-only can only pass if a matching committed artifact already exists.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Clarify in ship.py that postbump refresh and guidelines outcome refresh are sequential compose attempts, volatile-only on the outcome pass must accept an already-committed matching artifact, and HEAD repin/fingerprint-stable note handling applies after the outcome commit even when postbump already advanced HEAD.
  - From Cursor-Innovation: Always invoke the shared outcome flush helper for every resolved gate (`pinned`/`clean`/`dropped`), not only when `warning_logged=True`; keep `needs_assessment=True` as the sole skip.
  - From Cursor-Pragmatic: Always invoke the new outcome write+flush helper from `_guidelines_gate_before_pr` after `load_or_prepare_guidelines_note` resolves, for every terminal gate result except `needs_assessment=True` sidecar skip. Remove the `warning_logged` guard; keep warning append as a separate best-effort step.
  - From Cursor-Requirements: After volatile-only, stall before PR creation unless run_dir/architectural-guideline-outcome.json exists and matches the tmpdir sidecar; treat missing or mismatched artifact as REFRESH_SKIP_COMMIT_FAILED in non-no-logs-commit mode.


### FINDING_4: Outcome sidecar writes must fail closed
- **Reviewer(s)**: Codex-Arch, Cursor-Innovation, Codex-Innovation, Codex-Pragmatic, Cursor-Requirements, Codex-Requirements
- **Severity**: blocking
- **Concern**: Best-effort outcome sidecar writes and staging allow Step 8 runs to ship without a durable committed outcome when write, flush, or verification fails; normal log-commit mode should stall before PR creation instead of proceeding with only a warning.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Arch: For non-`--no-logs-commit` runs, treat a terminal outcome sidecar write or verification failure as the same pre-PR stall class as flush failure. Only allow best-effort continuation in `--no-logs-commit` mode.
  - From Cursor-Innovation: Treat unresolved outcome persistence as fail-closed in normal log-commit mode: stall before PR when sidecar write or pre-PR flush cannot produce the committed batch (retain the `--no-logs-commit` non-stall carve-out).
  - From Codex-Innovation: Make current outcome JSON write and stage verification a required pre-PR gate except for no-logs-commit and unresolved needs_assessment. Return the write failure through GuidelinesGateResult or the flush hook and stall before PR creation.
  - From Codex-Pragmatic: Treat outcome sidecar write failure as a pre-PR stall except --no-logs-commit. Add a focused test that sidecar write failure blocks PR creation in normal mode.
  - From Cursor-Requirements: Treat sidecar write failure like flush failure in normal mode: log warning, classify outcome=dropped with reason sidecar-write-failed when classifiable, and stall before PR creation unless --no-logs-commit. Keep best-effort only for no-logs-commit.
  - From Codex-Requirements: Make the sidecar write return success or failure. In non-`--no-logs-commit` mode, stall before PR creation when the outcome sidecar cannot be written or staged. Keep best-effort only for the human-readable warning append.


### FINDING_5: Clear stale outcome sidecars on skip paths
- **Reviewer(s)**: Codex-Innovation
- **Severity**: important
- **Concern**: A prior `architectural-guideline-outcome.json` can survive in the tmpdir and later be staged on a skip path, producing a false current outcome from an ambient stale artifact.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Innovation: Clear GUIDELINE_SHIP_OUTCOME_SIDECAR at the start of each compose outcome attempt and include it in stale artifact cleanup/invalidation, or make flushing consume only the current GuidelinesGateResult outcome rather than any ambient sidecar.


### FINDING_6: guidelines_status must come from materialization, not note emptiness
- **Reviewer(s)**: Cursor-Pragmatic, Cursor-Requirements
- **Severity**: important
- **Concern**: Outcome classification must use materialized `guidelines_status` and related compose metadata, not infer from note emptiness; otherwise absent/invalid cases can be mislabeled and present-guideline drops can be counted as clean.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Pragmatic: Thread `guidelines_status` (and `assessment_kind` when known) from `prepare_compose_assessment` / `read_guidelines` into `GuidelinesShipOutcome` construction. Classify `outcome=clean` for absent/invalid before evaluating present-guideline drop reasons.
  - From Cursor-Requirements: When classifying, read MATERIALIZE_ENV GUIDELINES_STATUS if present, else architectural_guidelines.read(repo_root); map absent/invalid to clean and present materialization/read/redaction failures to dropped only when guidelines_status=present.


