## Goal
Implement issue #6998: [IMPLEMENTING] contract-unification [FEATURE] Kind-parameterize guidelines/invariants twins.

## Implementation Plan
## Plan

## Approach

Use one frozen descriptor and generic lifecycle functions across the core and ship layers, while preserving existing public names and internal wire formats.

1. Add `AssessmentKind` in a small leaf module under `larch.core`.
   - Define `GUIDELINES` and `INVARIANTS` instances.
   - Store each kind’s filenames, artifact names, environment-key prefix, status and path field names, presentation text, identifier and heading rules, authored and ship outcome vocabularies, reason tokens, and policy callables or flags.
   - Include an explicit entry-body parsing policy: guideline entries continue filtering mechanized/detail bullets, while invariant entries preserve bodies verbatim.
   - Include separate design-persistence policy from ship present-empty policy: whether design persistence requires nonempty content, whether empty content removes stale durable artifacts, and how `requires_assessment` is derived.
   - Keep existing constants as compatibility aliases where external modules import them.
   - Use existing `config.ASSESSMENT_KIND_*` and `config.ASSESSMENT_OUTCOME_*` constants rather than introducing duplicate wire literals.
   - Keep this module free of implement-layer imports to preserve core layering.

2. Parameterize `architectural_guidelines.py`.
   - Replace mechanical guideline and invariant twins with private generic functions that accept `AssessmentKind`.
   - Cover entry parsing, file reads, artifact paths, metadata paths, materialized diffs, staged and durable notes, fingerprints, invalidation, design persistence, compose preparation, compose writes, and ship-outcome validation.
   - Route parsing through the descriptor’s body-policy callable rather than applying one regex-only normalization path to both kinds.
   - Encode design-time empty-content behavior explicitly:
     - Guidelines continue to persist a present design assessment even when content is empty.
     - Invariants continue to remove stale durable artifacts for absent, invalid, or empty content, and only set `requires_assessment` when `content.strip()` is nonempty.
   - Preserve genuine guideline-only operations, including staged refresh and coverage advancement, without adding invariant behavior.
   - Preserve the existing `ComposeMaterializationResult` internal carrier names: `guidelines_status` and `guidelines_path` remain the materialization knowledge-status and path fields for **both** kinds. Do not rename or split them into kind-specific fields during genericization.
   - Keep all externally consumed guideline and invariant function names callable as thin wrappers or partials.
   - Keep each existing CLI entry function and its exact `KEY=value` output grammar. Reduce paired entry bodies to kind-bound calls into shared parser and emitter helpers.
   - Preserve validator error text and the kind-specific JSON fields `guidelines_status` and `invariants_status`.

3. Parameterize `ship_guidelines.py`.
   - Introduce generic internal gate-result and ship-outcome representations driven by `AssessmentKind`.
   - Keep `GuidelinesGateResult`, `InvariantsGateResult`, `GuidelinesShipOutcome`, and `InvariantsShipOutcome` as compatibility adapters with their current constructor keywords, attributes, and serialized schemas.
   - Merge classifiers, sidecar clear and write paths, current-note reads, prepared-result conversion, and load-or-prepare flows.
   - Preserve the existing cross-kind compose wire: `_prepared_invariant_result` must continue reading `prepared.guidelines_status` and mapping it to `InvariantsGateResult.invariants_status`.
   - Encode all current divergences in the descriptor. These include invariant `present-empty` handling, invariant `violation` outcomes, guideline `pinned` outcomes, allowed assessment vocabularies, distinct absent, invalid, empty, and note reasons, entry-body parsing, and design-persistence behavior.
   - Re-export the existing outcome and reason-token constants used by runtime and analysis consumers.

4. Parameterize the pre-PR assessment gate in `ship.py`.
   - Replace paired committed-outcome match and pre-PR gate mechanics with kind-driven helpers.
   - Preserve the invariant file precheck and its empty-file clean result.
   - Preserve guideline-only run-log flushing. Do not flush invariant outcomes.
   - Remove `_flush_invariant_outcome_before_pr`, which is unused.
   - Keep the combined snapshot and result ordering unchanged so invariant violations still short-circuit as they do now.
   - Keep current stall steps, warning text, sidecar behavior, and `no_logs_commit` behavior.

5. Preserve the public CLI registry contract.
   - Leave all 22 `python/larch/cli.py` registry keys and `_MACHINE_STDOUT_KEYS` entries byte-identical.
   - Keep their existing module and callable names unless the registry smoke test requires an equivalent kind-bound target update.
   - Do not add a new public verb.

6. Keep both shell-facing names as thin wrappers.
   - Retain `step-architectural-guidelines-write-compose.sh` and `step-architectural-invariants-write-compose.sh`.
   - Move duplicated argument and assessment-path handling into the shared Python entry path where practical.
   - Keep positional arguments, relative-path resolution, absolute-path handling, environment requirements, exit codes, and selected CLI namespaces unchanged.

## Files to modify/create

### NEW: python/larch/core/assessment_kind.py

Define the frozen `AssessmentKind` descriptor and the `GUIDELINES` and `INVARIANTS` instances. Include required artifact, wire, outcome, parsing, ship-empty, and design-persistence policies. Keep this module free of implement-layer imports.

### UPDATED: python/larch/core/architectural_guidelines.py

Replace twin implementations with kind-parameterized helpers. Retain compatibility constants, public functions, CLI entry names, stdout fields, exception behavior, schema-specific validator wrappers, and the existing `ComposeMaterializationResult.guidelines_status` and `.guidelines_path` fields as shared cross-kind materialization carriers.

### UPDATED: python/larch/implement/ship_guidelines.py

Collapse paired gate results, ship outcomes, classifiers, readers, writers, and prepare flows behind the descriptor. Preserve public twin symbols and serialized record shapes, including invariant preparation’s mapping from `prepared.guidelines_status` to invariant status.

### UPDATED: python/larch/implement/ship.py

Collapse paired pre-PR gate mechanics. Preserve kind-specific policies and remove the dead `_flush_invariant_outcome_before_pr` function.

### UPDATED: skills/implement/scripts/step-architectural-guidelines-write-compose.sh

Reduce the script to the guideline-named thin wrapper while preserving its current invocation contract.

### UPDATED: skills/implement/scripts/step-architectural-invariants-write-compose.sh

Reduce the script to the invariant-named thin wrapper while preserving its current invocation contract.

### UPDATED: python/tests/core/test_architectural_guidelines.py

Add descriptor completeness and parity tests. Exercise both compatibility APIs through shared parametrized cases and retain explicit tests for divergent parsing, design persistence, empty handling, outcome validation, metadata fields, fingerprints, materialization carriers, and CLI stdout.

Required explicit regressions:
- Guideline parsing continues to filter mechanized/detail bullets.
- Invariant parsing continues to preserve verbatim bodies.
- Present-but-empty guidelines persist design assessment state as before.
- Present-but-empty invariants remove or avoid stale durable assessment artifacts and do not set `requires_assessment`.
- Invariant `prepare_compose` continues populating `ComposeMaterializationResult.guidelines_status` and `.guidelines_path`.
- `_prepared_invariant_result` continues translating `prepared.guidelines_status` to `InvariantsGateResult.invariants_status`, including `present-empty` and `REASON_INVARIANTS_EMPTY`.

### UPDATED: python/tests/implement/test_ship.py

Convert duplicated ship-gate tests to kind-parametrized coverage where useful. Retain explicit regression cases for invariant empty files, invariant violations, guideline pinned outcomes, dropped outcomes, run-log flushing, short-circuit order, public compatibility constructors, and the invariant cross-kind materialization-status mapping.

### UPDATED: skills/implement/scripts/test-architectural-guidelines-step.sh

Verify both retained shell names delegate successfully through the generic backend. Preserve coverage for relative and absolute assessment paths, explicit outcomes, missing arguments, and kind-specific durable artifacts.

### MAY_UPDATE: python/tests/design/test_design_cli_ports.py

Change only if internal callable targets must change. Keep all registry keys and `_MACHINE_STDOUT_KEYS` assertions unchanged and add a parity assertion if it can prove both verb families reach the shared implementation without pinning private structure.

## Preserved contracts

- The 22 architectural guideline and invariant CLI keys remain unchanged.
- `_MACHINE_STDOUT_KEYS` remains unchanged.
- Existing CLI stdout key names and exit codes remain unchanged.
- Existing shell script names and arguments remain unchanged.
- `validate_guideline_ship_outcome_record` and `validate_invariant_ship_outcome_record` remain callable and accept the same JSON schemas.
- Committed outcome records retain their kind-specific status field names.
- Public twin symbols used by external modules remain callable.
- `ComposeMaterializationResult.guidelines_status` and `ComposeMaterializationResult.guidelines_path` remain unchanged shared materialization fields for both guideline and invariant compose paths.
- `_prepared_invariant_result` continues to map `prepared.guidelines_status` into `InvariantsGateResult.invariants_status`.
- Guideline-only staged refresh, pin, and invalidation asymmetries remain guideline-only.
- Guideline entry parsing continues to filter mechanized/detail bullets; invariant parsing continues to preserve verbatim bodies.
- Guidelines continue to persist present design assessments with empty content; invariants continue to remove stale design artifacts for empty content and require nonempty stripped content before setting `requires_assessment`.
- Empty invariants remain a clean outcome with `REASON_INVARIANTS_EMPTY`.
- A non-clean invariant note remains a `violation`; a non-clean guideline note remains `pinned`.
- The generic guideline outcome flush remains wired only for guidelines.

## Edge cases

- Reject a descriptor mismatch between the requested kind and an artifact’s environment keys or paths.
- Preserve absent, invalid, present-empty, current, assessment-required, and materialization-failed as distinct states.
- Preserve clean-lead classification when prose also references a guideline or invariant identifier.
- Preserve invariant headings at levels one through six and guideline `###` heading parsing.
- Preserve each kind’s existing body normalization policy after heading detection.
- Keep prior-format durable metadata readable.
- Reject stale fingerprints, symlinked artifacts, missing identity fields, and invalid authored outcomes as before.
- Keep empty `head_sha` sidecar writes fail-closed.
- Ensure compatibility adapters cannot serialize both `guidelines_status` and `invariants_status`.
- Preserve the single compose snapshot for both kinds and do not rematerialize a second diff.
- Preserve `guidelines_status` as the snapshot’s shared status carrier even when preparing invariant results.
- Preserve invariant short-circuit behavior before guideline PR-body composition.
- Preserve guideline run-log refresh handling for no-log, incomplete, volatile-only, and failed refresh results.

## Failure modes

- An incomplete descriptor could silently omit an artifact or wire field. Add completeness assertions that enumerate every required descriptor field and policy for both instances.
- Generic helpers could erase a deliberate divergence. Keep explicit descriptor-policy tests for parsing, design persistence, empty invariants, outcome vocabularies, reason tokens, heading rules, and flush policy.
- A generic parser could apply guideline filtering to invariants or remove invariant body text. Compare both public parse outputs against existing expected bodies.
- A generic design-persistence path could treat empty content identically for both kinds. Assert guideline present-empty persistence and invariant stale-artifact removal separately.
- Renaming or kind-splitting `ComposeMaterializationResult.guidelines_status` or `.guidelines_path` could break invariant classification without a compile-time error. Assert invariant compose preparation and `_prepared_invariant_result` behavior directly.
- Compatibility wrappers could break keyword construction or attribute access in external modules. Test the old constructors and public attributes directly.
- A generic serializer could change committed JSON. Compare exact dictionaries for both outcome schemas.
- CLI consolidation could rename stdout keys or alter return codes. Capture exact stdout and status for both verb families.
- Gate consolidation could flush invariant outcomes or stop flushing guidelines. Assert both negative and positive paths.
- Moving constants could introduce a core-to-implement import cycle. Keep the descriptor in `larch.core` and move shared literals upward rather than importing `ship_guidelines`.
- Shell simplification could change path resolution. Retain harness cases for relative paths under `IMPLEMENT_TMPDIR` and existing absolute paths.

## Testing strategy

1. Run targeted core tests:
   - `python3 -m pytest python/tests/core/test_architectural_guidelines.py -q`

2. Run targeted ship tests:
   - `python3 -m pytest python/tests/implement/test_ship.py -q -k 'guideline or invariant or assessment'`
   - Run the full changed test file if shared ship helpers affect unrelated cases.

3. Run CLI registry smoke coverage:
   - `python3 -m pytest python/tests/design/test_design_cli_ports.py -q`

4. Run the shell contract harness:
   - `bash skills/implement/scripts/test-architectural-guidelines-step.sh`

5. Run the documented Python linters scoped to the changed Python files.

6. Measure the final reduction.
   - Confirm the net deletion is between 900 and 1,200 lines.
   - Search for remaining exact guideline/invariant twin bodies.
   - Search runtime consumers for every retained public symbol and verify each resolves to a compatibility wrapper or generic implementation.
   - Confirm `python/larch/cli.py` registry keys and `_MACHINE_STDOUT_KEYS` entries did not change.
   - Confirm the preserved `ComposeMaterializationResult` field names are still used by both compose paths and that invariant present-empty reaches `REASON_INVARIANTS_EMPTY`.
   - Confirm design-persistence behavior remains asymmetric for empty guideline and invariant content.

## Acceptance

1. Run targeted core tests:
   - `python3 -m pytest python/tests/core/test_architectural_guidelines.py -q`

2. Run targeted ship tests:
   - `python3 -m pytest python/tests/implement/test_ship.py -q -k 'guideline or invariant or assessment'`
   - Run the full changed test file if shared ship helpers affect unrelated cases.

3. Run CLI registry smoke coverage:
   - `python3 -m pytest python/tests/design/test_design_cli_ports.py -q`

4. Run the shell contract harness:
   - `bash skills/implement/scripts/test-architectural-guidelines-step.sh`

5. Run the documented Python linters scoped to the changed Python files.

6. Measure the final reduction.
   - Confirm the net deletion is between 900 and 1,200 lines.
   - Search for remaining exact guideline/invariant twin bodies.
   - Search runtime consumers for every retained public symbol and verify each resolves to a compatibility wrapper or generic implementation.
   - Confirm `python/larch/cli.py` registry keys and `_MACHINE_STDOUT_KEYS` entries did not change.
   - Confirm the preserved `ComposeMaterializationResult` field names are still used by both compose paths and that invariant present-empty reaches `REASON_INVARIANTS_EMPTY`.
   - Confirm design-persistence behavior remains asymmetric for empty guideline and invariant content.

diff_added: 650
diff_deleted: 1700
mechanical_churn: true
oversize_override: operator
diff_lines: 2350

## Test plan
(no test plan section in plan-file)
