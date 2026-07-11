## Final Design Plan

The plan is very large. Showing the full plan body below.

## Plan

## Approach

1. Define separate invariant (`clean|violation`) and guideline (`clean|deviation`) outcome vocabularies, a canonical `re-author-required` result token, a non-complete Step 8 terminal status of the same name, and a distinct re-author-required exit code in shared config.
2. Consolidate tolerant assessment-note classification into one shared helper. Preserve the existing first-line canonical-clean lead behavior and identifier matching, but use classification only as a one-way consistency check—not as routing authority.
3. Thread an explicit outcome through every compose and staged writer entry point. Parse `--outcome` with an empty default rather than making it argparse-required, so omitted, invalid, cross-vocabulary, and prose-mismatched outcomes all reach the shared validation path and return the distinct re-author exit.
4. Validate explicit outcomes before any durable authored note, metadata, staged artifact, or outcome sidecar is written. A declared `clean` outcome is rejected only when the classifier finds a matching identifier without the canonical clean lead; declared `violation` and `deviation` remain authoritative even when prose is identifier-free or clean-shaped.
5. Persist the supplied outcome as `ASSESSMENT_KIND` in the existing HEAD- and diff-fingerprint-pinned metadata and in the schema-version-1 outcome sidecars. Preserve existing deterministic-clean, unavailable, absent, invalid, and invariant-empty system-derived paths.
6. Make re-author-required a first-class coordinator and Step 8 terminal state. Outcome-validation and legacy-metadata failures must not call `_persist_unavailable`, must not create consumable authored artifacts, and must route Step 8 to bounded reassessment/user input rather than completed unavailable coverage, automatic retry, or generic malformed failure.
7. Remove prose inference from ship routing, repair, and unavailable preservation. A present authored assessment requires a current, vocabulary-valid persisted `ASSESSMENT_KIND` before it can be considered handled, pinned, repaired, classified, preserved, or routed.
8. Update retained staged refresh/pin callers, wrappers, adapter contracts, parent orchestration guidance, integration harnesses, and report tests so all writer contracts supply and retain explicit outcomes and `re-author-required` cannot reach the ship relaunch path.

## Files to modify/create

### UPDATED: python/larch/core/config.py

- Add shared constants for:
  - invariant outcomes: `clean|violation`;
  - guideline outcomes: `clean|deviation`;
  - the canonical coordinator and Step 8 result token `re-author-required`;
  - the distinct re-author-required exit code and shared bounded reason/status tokens needed by writers, wrappers, coordinator callers, and Step 8.
- Keep the outcome vocabularies separate so guideline paths cannot accept `violation` and invariant paths cannot accept `deviation`.

### UPDATED: python/larch/core/architectural_guidelines.py

- Add one shared tolerant-prose classifier for guideline and invariant notes, parameterized by:
  - canonical clean lead;
  - identifier matcher;
  - kind-specific non-clean vocabulary.
- Replace the existing invariant classifier copy and expose the helper for `ship_guidelines.py`.
- Extend guideline and invariant compose and staged writer functions with an explicit outcome parameter.
- Parse `--outcome` for all four write verbs with an empty default, then validate in the shared writer path rather than relying on argparse’s required-argument failure.
- Before any durable write:
  - reject missing outcomes;
  - reject invalid or cross-vocabulary outcomes;
  - reject declared `clean` when the shared classifier finds a matching `I-*` or `G-*` identifier and the first line is not the canonical clean sentence;
  - accept canonical-clean-first-line notes with later identifier-bearing rationale;
  - accept explicit `violation` or `deviation` regardless of prose shape.
- Return the distinct re-author-required exit and existing compatible status/warning grammar for all explicit-outcome validation failures.
- Persist the explicit value in `ASSESSMENT_KIND` alongside the existing HEAD SHA and diff fingerprint, and retain it in the schema-version-1 outcome sidecars.
- Ensure staged refresh/materialization and pin paths preserve `ASSESSMENT_KIND`; when an authored staged artifact has missing, invalid, or cross-vocabulary outcome metadata, fail closed to re-author-required rather than reconstructing it from prose.
- Update `write_unavailable_note` so it preserves an existing authored invariant violation only when the current durable note and its applicable current sidecar/pin contract validate `ASSESSMENT_KIND=violation`; remove `_invariant_assessment_kind(existing_note)` or any other prose-classifier fallback from unavailable preservation.
- Preserve `/design` `persist-design-assessment`, deterministic-clean, and true unavailable writers as trusted system paths.

### UPDATED: python/larch/implement/architectural_assessment.py

- Pass each validated agent result `state` to the matching compose writer as the explicit outcome.
- Introduce a dedicated re-author-required exception/result path for missing, invalid, cross-vocabulary, clean-claim mismatch, and post-write outcome-consistency failures.
- Handle that path before the broad persistence-error handler:
  - do not call `_persist_unavailable`;
  - remove only artifacts created for the failed current authoring attempt, including authored note and outcome sidecar paths;
  - emit a per-kind `re-author-required` result with the shared reason/status grammar;
  - return a non-complete assessment result that cannot satisfy handled coverage.
- Update `_repair_current_outcome` explicitly:
  - treat missing, empty, invalid, or cross-vocabulary durable `ASSESSMENT_KIND` as a bounded per-kind `re-author-required` result;
  - do not raise `ValueError` for that legacy/malformed metadata case;
  - ensure the evidence-none repair path carries that result through the coordinator rather than reporting `ARCHITECTURAL_ASSESSMENT_STATUS=failed`.
- Update `_already_handled`, compose prechecks, and current-note reads so an authored note is not handled or returned as current until its persisted `ASSESSMENT_KIND` is present and valid for that kind.
- Preserve existing result identity checks and HEAD, diff-fingerprint, and knowledge-fingerprint validation.
- Ensure a malformed legacy authored note remains pending for reassessment rather than becoming clean, unavailable, terminally covered, or a generic coordinator failure.

### UPDATED: python/larch/implement/ship_guidelines.py

- Delete local guideline and invariant classifier copies and import the shared classifier only for independent clean-claim consistency vetoes.
- Stop deriving `assessment_kind` from note prose in every authored present-note path.
- In `_read_current_guidelines_note`, `_read_current_invariant_note`, and before any handled-coverage, pin, repair, or classification shortcut:
  - require a current authored note to carry a vocabulary-valid persisted `ASSESSMENT_KIND`;
  - return a bounded `needs_assessment`/re-author-required detail when it is missing, empty, invalid, or cross-vocabulary;
  - do not call prose classification as a fallback on that path.
- Route authored guideline outcomes only from persisted `clean|deviation` and invariant outcomes only from persisted `clean|violation`.
- Retain the independent one-way veto: a declared authored `clean` outcome with identifier-bearing, non-clean-led prose is not allowed to disarm the gate.
- Route `re-author-required` to reassessment (`needs_assessment`), not unavailable/dropped coverage or clean PR composition.
- Change unavailable handling that preserves an existing invariant violation to rely on valid current persisted metadata (`ASSESSMENT_KIND == "violation"`, with the current sidecar/pin contract where applicable), not prose classification.
- If an existing authored invariant note lacks valid outcome metadata, do not preserve it as a prose-derived violation; fail closed to re-author-required.
- Keep existing routing for deterministic-clean, true unavailable, absent, invalid, invariant-empty, and stale-note states.
- Keep `architectural-guideline-outcome.json` and `architectural-invariant-outcome.json` at schema version 1, continuing to use the existing `assessment_kind` and `outcome` fields.

### UPDATED: skills/implement/scripts/step-architectural-guidelines-write-compose.sh

- Define the wrapper input contract explicitly: accept the guideline outcome as an optional second positional argument with an empty default, then always forward it as `--outcome`.
- Preserve assessment-file containment and tmpdir behavior.
- Do not reject an omitted second positional argument in shell; allow shared Python validation to return the distinct re-author-required exit.
- Propagate the distinct re-author-required exit unchanged so callers can distinguish it from tool failure.

### UPDATED: skills/implement/scripts/step-architectural-invariants-write-compose.sh

- Define the wrapper input contract explicitly: accept the invariant outcome as an optional second positional argument with an empty default, then always forward it as `--outcome`.
- Do not make the shell positional expansion mandatory; route omitted outcomes to shared writer validation.
- Propagate the distinct re-author-required exit unchanged.

### UPDATED: skills/implement/scripts/step-architectural-guidelines-write-staged.sh

- Update the retained staged-writer wrapper to accept the explicit guideline outcome as an optional second positional argument with an empty default and forward it as `--outcome`.
- Preserve materialization metadata, outcome-sidecar metadata, and diff-fingerprint handling even though the live prompt no longer uses this staged path.
- Propagate missing, invalid, and mismatched outcomes through the distinct re-author-required exit rather than shell argument failure or generic Python usage failure.

### UPDATED: skills/implement/scripts/step-8-assessment.sh

- Recognize `re-author-required` as a valid per-kind coordinator result rather than rejecting it as malformed coverage or converting it to unavailable.
- Extend result parsing and `validate_results_coverage` so requested kinds can be covered exactly once by `re-author-required` with its preserved bounded reason, while keeping that result outside complete-success coverage.
- Add an explicit re-author terminal predicate and terminal handler branch:
  - require the child’s validated merge envelope and `BGJOB_RC=0`;
  - write `ASSESSMENT_STATUS=re-author-required`, retain `ASSESSMENT_RESULTS`, `ASSESSMENT_REQUESTED_KINDS`, identity/fingerprint KVs, and per-kind reason/detail;
  - never stamp `ASSESSMENT_STATUS=complete` when any requested kind is `re-author-required`;
  - set a dedicated `HANDLE_ACTION` for reassessment rather than `emit-success`, `retry`, or generic `emit-fail-closed`.
- Update `run_child` so a valid coordinator response containing `re-author-required` atomically writes the non-complete result envelope rather than treating the non-`ok` assessment result as a child/tool failure.
- Keep automatic retry limited to retryable transport/tool failures. A syntactically valid re-author-required result must not consume attempt 2, trigger a new bgjob attempt, or re-run the same malformed authored assessment.
- Preserve existing handling for genuine unavailable, clean, deviation, violation, absent, invalid, and failure states.
- Ensure rejoin behavior recognizes a current matching `ASSESSMENT_STATUS=re-author-required` terminal envelope, emits its persisted KVs, and routes directly to reassessment without relaunching the child or ship.

### UPDATED: skills/implement/scripts/step-8-assessment.md

- Update the normative adapter contract to list `re-author-required` as:
  - an allowed per-kind `ASSESSMENT_RESULTS` state;
  - a non-complete `ASSESSMENT_STATUS`;
  - a terminal envelope that requires `BGJOB_RC=0` and preserved per-kind result/reason data.
- Define that complete coverage and `terminal_is_success` exclude `re-author-required`, while result validation still permits it for exactly requested kinds.
- Document that it is rejoinable, not retryable, does not allow attempt 2 for the malformed assessment, and hands the parent back to `NEXT_ACTION=assessments`.
- Remove or revise any statement that treats Step 8 activation/routing as out of scope when it conflicts with the revised terminal contract.
- Keep the document synchronized with the script and harness grammar.

### UPDATED: skills/implement/scripts/test-architectural-guidelines-step.sh

- Update compose and staged wrapper invocations to pass explicit outcomes using the documented positional wrapper contract.
- Assert compose and staged metadata contains the author-supplied `ASSESSMENT_KIND` for both outcome vocabularies.
- Add wrapper-level checks that an omitted second positional outcome reaches Python and returns the distinct re-author-required exit, rather than a shell missing-argument error.
- Add checks that invalid, cross-vocabulary, and clean-claim-mismatched outcomes return the distinct re-author-required exit without producing a consumable authored note or outcome sidecar.
- Retain stale staged-artifact cleanup assertions.

### UPDATED: skills/implement/scripts/test-step-8-assessment.sh

- Add contract coverage for a coordinator result containing per-kind `re-author-required`.
- Assert Step 8 accepts and preserves the result token and reason, emits `ASSESSMENT_STATUS=re-author-required` with `BGJOB_RC=0`, and does not reinterpret it as unavailable or completed coverage.
- Assert the terminal handler routes to reassessment/user input and does not call the success/ship handoff.
- Assert the malformed assessment is not retried: no attempt-2 launch, no duplicate child execution, and no generic fail-closed conversion for this terminal class.
- Assert a matching completed rejoin of `re-author-required` preserves the reassessment route without a new bgjob start.
- Assert true unavailable behavior remains distinct from re-author-required behavior.

### UPDATED: skills/implement/SKILL.md

- Update the Step 8 and parent-orchestrator branch instructions for the new terminal adapter status.
- Require a validated Step 8 `ASSESSMENT_STATUS=re-author-required` result to preserve its per-kind result/reason and route the operator to reassessment/user input through the existing assessments handoff.
- Explicitly prohibit `step-8-ship.sh`, PR composition, automatic ship relaunch, and automatic reassessment retry for that branch.
- Keep `ASSESSMENT_STATUS=complete` plus complete successful coverage as the only Step 8 state that may proceed to ship.
- Preserve the existing bgjob wait discipline: consume the terminal envelope, validate `BGJOB_RC=0` for re-author-required, then follow the documented reassessment branch.

### UPDATED: skills/implement/references/ship-pr-exit-matrix.md

- Add the Step 8 `re-author-required` terminal case to the ship exit/routing matrix.
- Define the required adapter KVs, non-success/non-tool-failure classification, operator-visible reassessment action, and prohibition on ship relaunch.
- Distinguish it from:
  - successful completed assessment coverage;
  - genuine unavailable coverage;
  - retryable adapter/tool failure;
  - terminal fail-closed failure.
- Ensure no legacy matrix entry maps `re-author-required` to a successful exit, generic tool failure, or automatic retry.

### UPDATED: skills/implement/references/architectural-guidelines-present.md

- Update the present-state contract so authored guideline notes are authoritative only with current, vocabulary-valid persisted outcome metadata.
- Document that a Step 8 `ASSESSMENT_STATUS=re-author-required` result routes to operator reassessment/user input and must not invoke the ship relaunch.
- Keep prose classification limited to the clean-claim consistency veto; prohibit prose-only routing or legacy-note authority.

### UPDATED: skills/implement/references/architectural-invariants-present.md

- Update the present-state contract so authored invariant notes are authoritative only with current, vocabulary-valid persisted outcome metadata.
- Replace the complete-only adapter statement with the explicit distinction between:
  - `ASSESSMENT_STATUS=complete` for ship-eligible complete coverage; and
  - `ASSESSMENT_STATUS=re-author-required` for validated, non-retryable reassessment handoff.
- Document that a valid persisted invariant violation may be preserved during true unavailability only through valid durable metadata and current identity/sidecar requirements, never prose classification.
- State that re-author-required does not relaunch ship or permit an inline automatic reassessment.

### UPDATED: python/tests/core/test_architectural_guidelines.py

- Update direct compose and staged writer calls to pass explicit outcomes.
- Add table-driven coverage for both vocabularies and the shared classifier:
  - canonical clean note;
  - clean lead plus rationale naming an identifier;
  - identifier-bearing violation or deviation note;
  - identifier-free explicit violation or deviation;
  - declared clean with identifier-bearing, non-clean-led prose;
  - explicit non-clean outcome with clean-shaped prose;
  - missing, invalid, and cross-vocabulary outcomes.
- Assert writer validation runs before durable note, metadata, staged artifact, or consumable outcome-sidecar writes.
- Assert staged refresh and pin paths retain and validate explicit authored outcomes without prose fallback.
- Assert `write_unavailable_note` preserves an existing invariant violation only when current durable metadata and identity/sidecar state validate `ASSESSMENT_KIND=violation`; cover missing, invalid, cross-vocabulary, stale, and prose-only legacy notes as non-preservable.
- Assert persisted metadata carries the explicit outcome with existing HEAD and diff-fingerprint identity.
- Test CLI parsing, status output, and the distinct re-author-required exit for all four write verbs.
- Retain `/design` explicit-assessment behavior unchanged.

### UPDATED: python/tests/implement/test_architectural_assessment.py

- Verify the coordinator passes each agent result state to the matching compose writer.
- Cover identifier-free explicit violation and deviation results persisting and routing as blocking.
- Cover a clean-claim mismatch, missing outcome, invalid outcome, and cross-vocabulary outcome producing `re-author-required`, never `_persist_unavailable`.
- Add evidence-none repair-path regression coverage proving `_repair_current_outcome` returns/routs a bounded `re-author-required` result for legacy, empty, invalid, and cross-vocabulary `ASSESSMENT_KIND` metadata instead of raising `ValueError` or producing coordinator failure.
- Assert re-author failures leave no consumable authored note or outcome sidecar and are not considered handled coverage.
- Verify combined invariant and guideline results preserve separate vocabularies and identity pins.
- Verify true agent/tool unavailability still uses `_persist_unavailable` and remains behaviorally distinct from re-author-required.

### UPDATED: python/tests/implement/test_ship.py

- Replace tests of private classifier copies with shared-helper or public-routing coverage.
- Assert present authored notes with missing, empty, invalid, or cross-vocabulary `ASSESSMENT_KIND` become `needs_assessment` before handled-coverage checks, present-note short-circuits, repair, pinning, or PR composition.
- Assert prose alone cannot turn a present authored note into clean, violation, deviation, or preserved unavailable coverage.
- Add regression cases for:
  - clean-with-rationale;
  - identifier-free violation or deviation;
  - declared-clean mismatch;
  - legacy prose-only authored notes;
  - an authored invariant violation with valid persisted metadata surviving true unavailable handling;
  - a prose-shaped invariant violation without valid metadata failing closed rather than being preserved.
- Assert explicit violation and deviation remain blocking even when their prose looks clean.
- Assert outcome JSON remains schema version 1 and carries the author-supplied `assessment_kind`.
- Retain validation coverage for deterministic-clean, true unavailable, absent, invalid, invariant-empty, stale-note, and identity-drift paths.

### UPDATED: python/tests/report/test_final_report.py

- Update all staged-assessment writer calls to supply explicit outcomes.
- Add coverage that staged report refresh/pin behavior retains the explicit `ASSESSMENT_KIND` and rejects malformed authored staged metadata without prose inference.
- Preserve existing final-report assertions unrelated to assessment routing.

## Edge cases

- A canonical clean first line followed by rationale naming `I-*` or `G-*` remains clean.
- An identifier-free note explicitly declared `violation` or `deviation` remains blocking.
- A clean-shaped note explicitly declared `violation` or `deviation` remains blocking.
- A note declared `clean` with a matching identifier and no canonical clean lead is rejected before persistence.
- Guideline outcomes cannot use `violation`; invariant outcomes cannot use `deviation`.
- Omitted `--outcome`, including through retained shell wrappers, reaches shared validation and returns re-author-required rather than shell or argparse usage failure.
- Missing outcomes fail closed only on authored present-assessment paths. System-derived absent, invalid, true unavailable, deterministic-clean, and invariant-empty paths remain valid.
- A present legacy authored note without a valid `ASSESSMENT_KIND` cannot satisfy handled coverage, be repaired as current, be preserved during unavailable handling, regain authority through prose inference, or reach PR composition as clean.
- A coordinator re-author-required result is distinct from unavailable, carries `BGJOB_RC=0`, emits `ASSESSMENT_STATUS=re-author-required`, and routes to reassessment/user input without automatic reuse of the malformed assessment.
- A matching rejoined re-author-required Step 8 envelope routes to reassessment without starting a new child or ship relaunch.
- HEAD drift or diff-fingerprint drift continues to invalidate the note and sidecar regardless of explicit outcome.

## Failure modes

- If a producer or retained caller omits the new outcome contract, a mandatory shell positional or argparse-required flag would hide the re-author condition behind a generic usage error. Make wrapper outcomes optional with empty defaults, parse an empty CLI value, and validate it in the shared writer path.
- If the coordinator catches outcome validation or legacy repair metadata failure under the broad persistence handler, it can convert re-author-required into unavailable coverage or generic failure. Handle the dedicated result before `_persist_unavailable`, make `_repair_current_outcome` non-throwing for invalid authored metadata, and test artifact absence.
- If Step 8 does not stamp and route a non-complete terminal status, a valid re-author result can be mislabeled `complete`, retried automatically, or sent to ship. Add explicit `ASSESSMENT_STATUS=re-author-required`, terminal predicate, result-envelope grammar, parent handoff, and no-retry behavior.
- If `terminal_is_success` or the parent only recognizes `complete`, Step 8 may treat the new state as tool failure or success. Permit the result for exact per-kind parsing while excluding it from successful coverage and adding a dedicated reassessment branch in the script, skill, and exit matrix.
- If handled-coverage checks, compose prechecks, or repair run before authored metadata validation, a legacy or malformed note can bypass reassessment or raise `ValueError`. Validate `ASSESSMENT_KIND` during current-note reads and return bounded re-author-required/needs-assessment results.
- If unavailable preservation still reads prose, it can preserve or overwrite an authored violation based on text rather than authority. Preserve only a current, metadata-valid explicit invariant violation with the required sidecar/pin identity.
- If staged refresh/pin paths omit the explicit outcome, report or resumed flows can reintroduce prose inference. Thread and validate the outcome through every retained staged caller.
- If mismatch validation runs after writes, a failed authoring attempt can leave consumable artifacts. Validate before writes and clear only current-attempt artifacts for defensive post-write failures.

## Testing strategy

- Run focused Python tests:
  - `python3 -m pytest python/tests/core/test_architectural_guidelines.py`
  - `python3 -m pytest python/tests/implement/test_architectural_assessment.py`
  - `python3 -m pytest python/tests/implement/test_ship.py`
  - `python3 -m pytest python/tests/report/test_final_report.py`
- Run wrapper and Step 8 integration harnesses:
  - `make test-architectural-guidelines-step`
  - Run the focused `test-step-8-assessment.sh` harness through its documented Makefile target or direct repository test entry point.
- Run lint for changed Python and shell surfaces using the repository’s changed-file workflow.
- Verify CLI help and focused invocations for all four write verbs accept `--outcome`, and that omitted, invalid, cross-vocabulary, and mismatched values return the documented re-author-required exit.
- Verify all retained wrappers forward an empty omitted outcome to Python rather than terminating in shell.
- Confirm no remaining prose-routing copies or fallbacks with targeted searches for `_assessment_kind`, `_invariant_assessment_kind`, `assessment_kind or`, `_repair_current_outcome`, and unavailable-preservation classifier use.
- Confirm a `re-author-required` Step 8 result emits `ASSESSMENT_STATUS=re-author-required`, `BGJOB_RC=0`, preserved per-kind result/reason KVs, and `NEXT_ACTION=assessments`; confirm it cannot be retried, treated as unavailable/completed coverage, or passed to `step-8-ship.sh`.
- Confirm matching rejoin of the re-author-required envelope takes the same reassessment route without a fresh bgjob launch.

difficulty: HARD
diff_added: 440
diff_deleted: 125
mechanical_churn: false
diff_lines: 565
