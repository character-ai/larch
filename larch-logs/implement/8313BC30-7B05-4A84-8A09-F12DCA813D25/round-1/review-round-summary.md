# Review Round 1

- Mode: `diff`
- 7 accepted, 2 rejected (1 neutral)

## Accepted Findings

### FINDING_1: Round-loop mocks still use the legacy voter contract
- **Reviewer(s)**: cursor-specialist-correctness, cursor-specialist-edge-cases, cursor-specialist-testing
- **Severity**: major
- **Concern**: The externals-present round-loop tests still exercise the retired Claude-first / legacy vendor contract instead of the Codex-primary semantic dispatch/tally contract, so pytest can stay green while voter labeling or handoff wiring regresses.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness: Address the concern above.
  - From cursor-specialist-edge-cases: Address the concern above.
  - From cursor-specialist-testing: Address the concern above.


### FINDING_2: HARD panel tests miss resolved_model coverage
- **Reviewer(s)**: cursor-specialist-correctness, codex-specialist-correctness, cursor-specialist-edge-cases, cursor-specialist-testing, codex-specialist-testing
- **Severity**: minor
- **Concern**: The HARD design panel tests still only verify model_role, not resolved_model, so the default-vs-review Codex model split could drift without CI catching it.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness: Address the concern above.
  - From codex-specialist-correctness: Address the concern above.
  - From cursor-specialist-edge-cases: Address the concern above.
  - From cursor-specialist-testing: Address the concern above.
  - From codex-specialist-testing: Address the concern above.


### FINDING_12: Filename inference maps semantic vote outputs to positional slots
- **Reviewer(s)**: dyn-dyn-voters
- **Severity**: major
- **Concern**: `_infer_voter_slot()` returns positional slot ids for the new semantic vote-output basenames, and `_assign_voter()` stores that value as the voter label on the deprecated `--voter-files` path, which breaks attribution and calibration parsing.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-dyn-voters: Have `_infer_voter_slot()` return semantic labels (`codex-validity`, `cursor-plan-fidelity`, …) or map matched slot ids through a fixed slot→label table before `_assign_voter()`; add a tally test that feeds the new basenames via `--voter-files` and asserts `v1_tool`/`v2_tool`/`v3_tool`.


### FINDING_13: Bare slot numbers still canonicalize to Claude/Codex/Cursor
- **Reviewer(s)**: dyn-dyn-voters
- **Severity**: major
- **Concern**: `_canonical_tool_for_slot()` still maps bare slot numbers to the legacy Claude/Codex/Cursor labels, so two-part voter specs can record the wrong tool label even when the path uses the new semantic basename.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-dyn-voters: Map `"1"`/`"2"`/`"3"` to `codex-validity` / `codex-plan-fidelity` / `codex-pragmatism` (or reject two-part specs and require `SLOT:TOOL:PATH`); keep legacy `Claude`/`Codex`/`Cursor` only as accepted explicit tool tokens, not slot defaults.


