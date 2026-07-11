### FINDING_1:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: major
- **Focus area**: risk-integration
- **Location**: skills/implement/scripts/step-8-assessment.sh:686-696
- **Concern**: The prior Step 8 fix is incomplete: adding re-author-required only to result parsing cannot route reassessment while run_child still stamps ASSESSMENT_STATUS=complete. Scenario: Coordinator can return ARCHITECTURAL_ASSESSMENT_STATUS=ok with per-kind re-author-required results; run_child still writes ASSESSMENT_STATUS=complete after validate_results_coverage, and skills/implement/SKILL.md plus ship-pr-exit-matrix.md still require complete status before ship relaunch, so reassessment is treated as success or tool-failure instead of bounded operator re-authoring
- **Proposed resolution**: Teach run_child and terminal handlers to detect re-author-required tokens, emit a non-complete terminal status (for example ASSESSMENT_STATUS=re-author-required), and keep them out of success coverage; update skills/implement/SKILL.md, skills/implement/references/ship-pr-exit-matrix.md, and the architectural present references so that status routes to operator reassessment without ship relaunch or automatic retry



### FINDING_2:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: major
- **Focus area**: correctness
- **Location**: python/larch/implement/architectural_assessment.py:559-568
- **Concern**: Legacy repair still hard-fails when ASSESSMENT_KIND is missing instead of returning re-author-required. Scenario: A present legacy note without vocabulary-valid ASSESSMENT_KIND hits _repair_current_outcome, which raises ValueError; run() surfaces ARCHITECTURAL_ASSESSMENT_STATUS=failed and Step 8 fail-closes to tool-failure rather than requesting explicit re-authoring
- **Proposed resolution**: In repair and current-note paths, treat missing, invalid, or cross-vocabulary ASSESSMENT_KIND as per-kind re-author-required with bounded reason; do not let ValueError escape as coordinator failed status



### FINDING_3:
- **Reviewer(s)**: Codex-Arch
- **Severity**: major
- **Focus area**: correctness
- **Location**: skills/implement/scripts/step-architectural-guidelines-write-compose.sh:9-22; skills/implement/scripts/step-architectural-invariants-write-compose.sh:9-22; skills/implement/scripts/step-architectural-guidelines-write-staged.sh:9-18
- **Concern**: [1] The wrapper contract conflicts with the required omitted-outcome behavior. The plan makes the second positional outcome required, while the core CLI contract requires an omitted outcome to reach shared validation and return the distinct re-author-required result.. Scenario: When a caller invokes a retained wrapper without the outcome, `${2:?}` terminates in the shell before the Python writer runs. The caller receives a generic shell usage exit instead of the required re-author-required outcome, so the coordinator or Step 8 cannot distinguish an authoring defect from wrapper misuse.
- **Proposed resolution**: Make the outcome positional argument optional with an empty default, forward it as `--outcome`, and let the shared writer validation emit the distinct re-author-required exit. Apply the same contract to every retained wrapper.



### FINDING_4:
- **Reviewer(s)**: Codex-Arch
- **Severity**: major
- **Focus area**: risk-integration
- **Location**: python/larch/implement/architectural_assessment.py:48-53
- **Concern**: If post-write outcome validation fails, the planned cleanup does not define how to preserve pre-existing valid artifacts that the failed attempt overwrote.. Scenario: A failed current authoring attempt can write a new note, then fail while writing or validating its sidecar. Removing the note and sidecar can delete a previously valid current assessment, causing data loss and changing a recoverable reassessment failure into artifact loss.
- **Proposed resolution**: Make the write a transaction: validate before writing, stage all artifacts under attempt-specific paths, and atomically commit them together; or snapshot and restore the prior note, metadata, sidecar, and receipt when post-write validation fails. Limit cleanup to artifacts owned by the current attempt.



### FINDING_5:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: major
- **Focus area**: risk-integration
- **Location**: skills/implement/SKILL.md:699-701
- **Concern**: The Step 8 adapter/orchestrator contract for `re-author-required` is incomplete beyond `step-8-assessment.sh`. `SKILL.md` and `ship-pr-exit-matrix.md` still require `ASSESSMENT_STATUS=complete` and route any other status to tool-failure; the adapter only classifies terminals as `emit-success` vs `emit-fail-closed` via `terminal_is_success`. After the adapter changes, a valid per-kind `re-author-required` result would still fail orchestrator validation or be published as fail-closed instead of bounded reassessment.. Scenario: Add `### UPDATED:` entries for `skills/implement/SKILL.md`, `skills/implement/references/ship-pr-exit-matrix.md`, and `skills/implement/scripts/step-8-assessment.md`. Define a non-complete terminal `ASSESSMENT_STATUS` (for example `re-author-required`), extend `validate_results_coverage` and `handle_terminal_outcome`/`terminal_is_success`, and branch the assessments path to operator-visible reassessment without treating it as ship-complete or generic tool-failure. Keep the existing no-auto-retry rule by requiring failed-attempt cleanup or non-consumable legacy notes before a fresh adapter run.
- **Proposed resolution**: 



### FINDING_6:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: major
- **Focus area**: correctness
- **Location**: python/larch/core/architectural_guidelines.py:1778-1793
- **Concern**: Compose precheck still treats legacy prose-only durable notes as `status="current"` when `note_consumable` passes, without checking vocabulary-valid persisted `ASSESSMENT_KIND`. That bypasses reassessment and drives `_repair_current_outcome`, which raises on missing/invalid metadata and can collapse the whole coordinator to `ARCHITECTURAL_ASSESSMENT_STATUS=failed` instead of per-kind `re-author-required`.. Scenario: In `_compose_precheck_result` and `_invariant_compose_precheck_result`, require authored durable metadata to carry a kind-valid `ASSESSMENT_KIND` before returning `current`; otherwise continue to `assessment-required`. Update `_repair_current_outcome` to return bounded `re-author-required` (or force reassessment) rather than raising, and add coordinator/compose-precheck tests for legacy prose-only notes.
- **Proposed resolution**: 



### FINDING_7:
- **Reviewer(s)**: Codex-Innovation
- **Severity**: major
- **Focus area**: correctness
- **Location**: skills/implement/scripts/step-8-assessment.sh:331-363,512-520
- **Concern**: The Step 8 changes do not define how `re-author-required` becomes incomplete coverage rather than successful terminal coverage. Scenario: If the token is merely added to `validate_results_coverage`, the child still writes `ASSESSMENT_STATUS=complete`, `terminal_is_success` accepts the result, and the outer flow can emit success instead of routing to reassessment. Define the terminal status and handoff fields for this result, and make success validation reject it while preserving its per-kind result and reason
- **Proposed resolution**: Add an explicit re-author terminal predicate and result-env contract. Route that predicate to the existing `NEXT_ACTION=assessments` handoff without retrying the malformed assessment



### FINDING_8:
- **Reviewer(s)**: Codex-Innovation
- **Severity**: major
- **Focus area**: correctness
- **Location**: python/larch/core/architectural_guidelines.py:856-882,2982-3026
- **Concern**: The explicit outcome contract is not carried through the invariant staged-writer entry point. Scenario: The plan requires explicit outcomes for every staged writer and separate invariant/guideline vocabularies, but it only names the guideline staged wrapper. `invariants_write_staged_assessment_main` still derives `ASSESSMENT_KIND` from prose unless its function, CLI, and all callers receive and validate `--outcome`; an invariant staged refresh or pin can therefore reintroduce prose-based routing
- **Proposed resolution**: Add the invariant staged wrapper or document the direct CLI contract, thread a required-by-validation `--outcome` through `write_invariant_staged_assessment`, and update invariant staged refresh, pin, and report callers to preserve and validate it



### FINDING_9:
- **Reviewer(s)**: Codex-Innovation
- **Severity**: major
- **Focus area**: security
- **Location**: python/larch/implement/architectural_assessment.py:515-535,657-700
- **Concern**: The planned cleanup does not preserve pre-existing artifacts when a post-write consistency check fails. Scenario: The coordinator can re-author a current legacy or malformed note, overwrite its durable note, then fail while writing or validating the outcome sidecar. A cleanup path that deletes the note and sidecar created by the current attempt can also delete the prior authored note, causing data loss and leaving no recoverable assessment
- **Proposed resolution**: Add transactional preservation: validate before writes, record which target paths were absent or back up existing artifacts, and on re-author cleanup remove only newly created files or restore the prior note, metadata, and sidecar atomically



### FINDING_10:
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: major
- **Focus area**: risk-integration
- **Location**: skills/implement/SKILL.md:699-701
- **Concern**: Parent Step 8 orchestrator still accepts only ASSESSMENT_STATUS=complete. Scenario: Adapter changes can emit re-author-required, but SKILL.md and ship-pr-exit-matrix.md still hard-fail any non-complete adapter status as tool-failure with no ship relaunch; reassessment never runs
- **Proposed resolution**: Add ### UPDATED entries for skills/implement/SKILL.md, skills/implement/references/ship-pr-exit-matrix.md, skills/implement/references/architectural-guidelines-present.md, skills/implement/references/architectural-invariants-present.md, and skills/implement/scripts/step-8-assessment.md defining a terminal re-author status, required KVs, no automatic attempt-2 retry for that status, and explicit loop-back to assessments/user input without treating it as unavailable coverage



### FINDING_11:
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: major
- **Focus area**: correctness
- **Location**: python/larch/implement/architectural_assessment.py:559-568
- **Concern**: Legacy consumable notes without valid ASSESSMENT_KIND still hit the repair path and crash. Scenario: When prepare returns current for a legacy prose-only note, _repair_current_outcome raises ValueError on missing ASSESSMENT_KIND; run() surfaces ARCHITECTURAL_ASSESSMENT_STATUS=failed and Step 8 retries then fail-closes instead of bounded re-author-required
- **Proposed resolution**: Extend the architectural_assessment.py plan to treat invalid or missing ASSESSMENT_KIND in prepare/current/repair paths as per-kind re-author-required: update _compose_precheck_result or note_consumable, convert _repair_current_outcome failures into the dedicated result token, and add coordinator tests for legacy metadata without ASSESSMENT_KIND



### FINDING_12:
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: major
- **Focus area**: correctness
- **Location**: skills/implement/scripts/step-8-assessment.sh:331-363
- **Concern**: Adapter terminal state machine has no re-author branch. Scenario: validate_results_coverage and terminal_is_success allow only complete terminal success; a child returning kind:re-author-required fails coverage or triggers attempt-2 retry, contradicting the plan’s no-retry reassessment contract
- **Proposed resolution**: Spell out in step-8-assessment.sh changes a new ASSESSMENT_STATUS value, a dedicated HANDLE_ACTION, child merge rules that forbid ASSESSMENT_STATUS=complete when any kind is re-author-required, and harness assertions that attempt 2 is not used for that terminal class ### 1. Parent orchestrator still requires `complete` only (risk-integration) The plan updates `step-8-assessment.sh` to recognize `re-author-required`, but the parent contract still rejects every non-`complete` adapter outcome as tool failure. Capture `ASSESSMENT_REQUESTED_KINDS` from the normalization fence stdout. After a normal return, require adapter exit success, `BGJOB_RC=0`, `STEP=implement-step8-assessment`, a non-empty `ASSESSMENT_COVERED_FINGERPRINT`, adapter `ASSESSMENT_REQUESTED_KINDS` equal to that captured canonical binding, `ASSESSMENT_STATUS=complete`, complete `ASSESSMENT_RESULTS` coverage for exactly those requested kinds, and request identity plus covered fingerprint matching the current materializations. Compare requested kinds as an order-independent canonical set when both kinds are requested, never against raw `DETAIL` order. A validated `unavailable` state counts only when it appears as durable coverage in the adapter's complete result envelope. Never reinterpret stale, partial, unavailable outside that contract, or fail-closed output as success. Any non-timeout adapter error, nonzero `BGJOB_RC`, malformed or missing KV, stale or mismatched identity, kind mismatch, incomplete result coverage, failed fingerprint validation, or status other than `complete` routes to existing Step 8 `tool-failure` handling. Append the existing Tool Failures record and stop hard. Do not relaunch `step-8-ship.sh`, retry or replace the job prompt-side, inspect raw assessor diagnostics, or ask for an override. Preserve invariant-violation blocking and its no-override policy. `ship-pr-exit-matrix.md` and `step-8-assessment.md` mirror the same rule. Without coordinated updates, a correct adapter emitting `re-author-required` still halts the run. Prior round FINDING_2 is only partially addressed. **Suggested revision:** Add explicit `### UPDATED:` files for the SKILL, exit matrix, present-reference docs, and `step-8-assessment.md`. Define the new terminal status, required KVs, the no-retry rule, and the loop back to `assessments` / operator reassessment. ### 2. Legacy metadata repair still crashes the coordinator (correctness) The plan updates `_already_handled` and ship note reads, but legacy notes can still enter the repair path and raise: state = metadata.get("ASSESSMENT_KIND", "") allowed = {"clean", "violation"} if kind == config.ASSESSMENT_KIND_INVARIANTS else {"clean", "deviation"} if state not in allowed: raise ValueError(f"current {kind} note has no repairable assessment kind") `prepare_compose_assessment` returns `status="current"` whenever `note_consumable` passes, and `_note_consumable` does not validate `ASSESSMENT_KIND`. A legacy prose-only note therefore reaches `_repair_current_outcome`, raises, and `run()` returns `ARCHITECTURAL_ASSESSMENT_STATUS=failed`. Step 8 then retries and fail-closes instead of requesting re-authoring. This extends neutral ledger FINDING_4 with a concrete trigger path. **Suggested revision:** Treat missing, empty, invalid, or cross-vocabulary `ASSESSMENT_KIND` in prepare/current/repair as per-kind `re-author-required`. Update `_compose_precheck_result` or `note_consumable`, stop raising from `_repair_current_outcome` for that case, and add coordinator tests for legacy metadata. ### 3. Adapter state machine lacks a re-author terminal class (correctness) Today the adapter only succeeds when every kind maps to an allowed terminal state and `ASSESSMENT_STATUS=complete`: if state not in { "deterministic-clean", "handled", "clean", "deviation", "violation", "log-pending", "unavailable", }: raise SystemExit(1) `re-author-required` is absent. `terminal_is_success` also requires `TERM_STATUS=complete`. A coordinator emitting `kind:re-author-required` would fail child validation or get folded into the attempt-2 retry path, which conflicts with the plan’s “do not retry the same malformed assessment automatically” requirement. **Suggested revision:** In the `step-8-assessment.sh` plan section, name the new `ASSESSMENT_STATUS`, add a `HANDLE_ACTION` branch, forbid `complete` when any result token is `re-author-required`, and extend `test-step-8-assessment.sh` to assert no attempt-2 retry for that terminal class. --- Accepted ledger items 1, 3, 6, and 7 look addressed in the proposed file set. FINDING_2 and FINDING_4 need the gaps above to be complete end-to-end. FINDING_5 remains out of scope because the plan already removes `_classify_*` prose fallback. I did not raise optional staged-wrapper or doc-sync items; they are lower legitimacy than these three correctness paths.



### FINDING_13:
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: major
- **Focus area**: risk-integration
- **Location**: skills/implement/SKILL.md:699-701
- **Concern**: The plan updates `step-8-assessment.sh` but omits the implement orchestrator surfaces that currently hard-require `ASSESSMENT_STATUS=complete` before ship relaunch.. Scenario: After the adapter emits per-kind `re-author-required`, `skills/implement/SKILL.md` and `skills/implement/references/ship-pr-exit-matrix.md` still treat any non-`complete` adapter envelope as tool failure. The run would stall or fail closed instead of surfacing bounded reassessment, which leaves prior-round Step 8 routing incomplete.
- **Proposed resolution**: Add `### UPDATED:` entries for `skills/implement/SKILL.md`, `skills/implement/references/ship-pr-exit-matrix.md`, and the architectural present-reference docs. Define a terminal adapter status such as `ASSESSMENT_STATUS=re-author-required`, require `BGJOB_RC=0`, preserve per-kind `ASSESSMENT_RESULTS`, forbid automatic bgjob retry of the same malformed assessment, and route the main agent to reassessment/user input rather than `step-8-ship.sh`.



### FINDING_14:
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: major
- **Focus area**: correctness
- **Location**: python/larch/core/architectural_guidelines.py:1008-1028
- **Concern**: The plan removes prose routing in ship reads but does not update `write_unavailable_note`, which still preserves an authored invariant violation via `_invariant_assessment_kind(existing_note)`.. Scenario: When assessment tooling is unavailable, coordinator `_persist_unavailable` can still keep or infer violation authority from note prose. A legacy prose-only violation without valid `ASSESSMENT_KIND` can survive unavailable refresh, or a metadata-valid violation can be missed if prose is clean-shaped. That breaks the acceptance criterion that prose no longer decides ship routing.
- **Proposed resolution**: Add an explicit `architectural_guidelines.py` change for `write_unavailable_note`: preserve an existing authored invariant violation only when current durable metadata has `ASSESSMENT_KIND=violation` (and the existing sidecar/pin contract matches). Remove the prose classifier fallback and extend `test_architectural_guidelines.py` unavailable-preservation coverage accordingly.



### FINDING_15:
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: major
- **Focus area**: correctness
- **Location**: python/larch/implement/architectural_assessment.py:559-568
- **Concern**: Legacy repair handling is not wired to the new `re-author-required` result. `_repair_current_outcome` raises when `ASSESSMENT_KIND` is missing or invalid, and that exception is not converted to per-kind reassessment output.. Scenario: A present legacy authored note with empty or invalid `ASSESSMENT_KIND` makes `architectural-assessment run` return `ARCHITECTURAL_ASSESSMENT_STATUS=failed`. Step 8 then retries and fail-closes instead of requesting explicit re-authoring, so malformed legacy notes never reach the bounded reassessment path the feature requires.
- **Proposed resolution**: In `architectural_assessment.py`, name `_repair_current_outcome` explicitly: return per-kind `re-author-required` (or route through the dedicated exception path) when repair metadata is missing, invalid, or cross-vocabulary; do not let `ValueError` bubble to coordinator failure. Add coordinator coverage in `test_architectural_assessment.py` for legacy metadata on the evidence-none repair path.



### FINDING_16:
- **Reviewer(s)**: Codex-Requirements
- **Severity**: major
- **Focus area**: risk-integration
- **Location**: skills/implement/SKILL.md:697-703
- **Concern**: The prior accepted Step 8 routing fix remains incomplete because the plan changes the adapter result contract but omits the invoking skill contract. Scenario: The adapter can return `ASSESSMENT_STATUS=complete` with `re-author-required`, but the current skill requires complete coverage and then relaunches Step 8 ship. It has no branch that requests reassessment or user input, so the new result can loop back into ship or conflict with the adapter validation contract
- **Proposed resolution**: Add `skills/implement/SKILL.md` as an updated file and define the caller branch for validated `re-author-required`: preserve its kind and reason, do not treat it as completed coverage, and route to the specified reassessment or user-input action without relaunching ship. Update `skills/implement/scripts/step-8-assessment.md` if its normative result grammar changes.



