## Decision 1: Legacy Step 18 script disposition
- **Question**: Should step-18.sh remove or keep step-18a-gate.sh, step-18b-final-report.sh, step-18-finalize.sh and their .md siblings?
- **Resolution**: Remove (fold). step-18.sh owns the consolidated logic. Delete the three .sh files and their .md siblings. Update Makefile, docs/linting.md, python/migrated-scripts.tsv, and the harnesses that reference them.
- **Source**: user

## Decision 2: Test coverage for the wrapper
- **Question**: Dedicated harness or reuse existing harnesses only?
- **Resolution**: Add a dedicated test-step-18.sh harness covering no-stall (one call), stall early-exit (classification inputs intact + STALL_RECOVERY_REQUIRED=true), EMIT_BODY marker emission, and --step17-emitted ride-along. Also update test-implement-structure.sh, test-implement-timing-rehydration.sh, and test-write-final-report.sh as needed.
- **Source**: user

## Decision 3: Python-layer scope
- **Question**: Strictly shell-orchestration, or may the change touch python verbs (final-report step18b, stall-resolution)?
- **Resolution**: Python changes are permitted when they make the wrapper cleaner. Not mandatory. Prefer the minimum change; touch python only when clearly cleaner than shell sequencing.
- **Source**: user

## Decision 4: Hard constraints to preserve (behavior-identical refactor)
- **Question**: What must not change?
- **Resolution**: Preserve exactly: (a) closing token and timing marks run before teardown removes the tmpdir (issue #3425 constraint); (b) the restore-finalize-state.sh gate; (c) the [STALLED] title-rename behavior; (d) the NEVER #17 emission gates (the wrapper never emits the body and never writes .step17-emitted; the orchestrator owns emission and the sentinel write). Stall recovery must behave exactly as today. The teardown tail (rename, issue URL, stash, sentinel, finalize warnings) must be relayed verbatim.
- **Source**: codebase + feature description

## Decision 5: Orchestrator contract (must-have outcome)
- **Question**: What is the minimum viable outcome?
- **Resolution**: No-stall path is one Bash call. Stall path exits early from the gate with classification inputs intact so the orchestrator loads stall-recovery.md, runs recovery, and re-invokes the wrapper. EMIT_BODY=true (with WFR_RC=0 and non-empty summary-final.md) prints the refreshed body between stable markers before teardown; the orchestrator re-emits from captured stdout. The wrapper accepts --step17-emitted true so the sentinel write rides this call.
- **Source**: feature description

## Non-goals
- No behavioral change to stall classification/recovery or final-report semantics.
- No change to the Step 16-17 fence or the Step 17 marker-emission contract.
- The wrapper stays a skills/implement/scripts/step-18.sh shell entry (per the proposal); python edits, if any, stay behind existing verbs.
