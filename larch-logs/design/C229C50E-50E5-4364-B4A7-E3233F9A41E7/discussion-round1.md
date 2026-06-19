# Design Discussion — Round 1 (issue #4768)

Scope/constraint decisions. The three design decisions were resolved in a prior
`/design 4768` Q&A and are recorded in the issue body ("Decisions confirmed");
they are carried forward here as binding scope. The run-mode decision is from
this run.

## Decision 1: Change locus
- **Question**: Where should the skip-bad-slot-and-continue behavior live?
- **Resolution**: Add an opt-in `--skip-invalid-slots` flag to the shared loader `_load_slots` / `agent dispatch-waterfall` (`python/agent_waterfall.py`). Only the plan-review panel (`dispatch_panel` in `python/plan_review_panel.py`) passes it. All other consumers (voters, `/review`, aggregator, decompose panel) keep the fail-closed default.
- **Source**: user (prior Q&A, recorded in issue #4768)

## Decision 2: Dispatch scope
- **Question**: Which `/design` paths get graceful degradation?
- **Resolution**: Reviewer panel only (`dispatch_panel`). `dispatch_voters`, `/review`, the aggregator, and the decompose panel keep fail-closed behavior.
- **Source**: user (prior Q&A, recorded in issue #4768)

## Decision 3: Drop criteria
- **Question**: What counts as droppable at load time?
- **Resolution**: Drop structurally-invalid rows only (today's `_load_slots` checks: bad JSON, non-dict row, bad/empty slot, bad tool, bad/empty output, newline in output, non-string `agent`/`prompt_file`, both set, neither set). Do NOT drop structurally-valid-but-unrenderable rows (a row whose `prompt_file` points at a missing/empty file is still loaded).
- **Source**: user (prior Q&A, recorded in issue #4768)

## Decision 4: Hard constraint — fail closed when no valid slots remain
- **Question**: What happens if every slot row is invalid?
- **Resolution**: Even with `--skip-invalid-slots`, `_load_slots` must still raise (fail closed) when zero valid slots remain after dropping bad rows, preserving the existing "slots file contains no slot rows" guarantee. Degrade only while at least one valid slot survives.
- **Source**: codebase (issue text: "proceed when at least one valid slot remains")

## Decision 5: Hard constraint — contract test stays green
- **Question**: Must the existing fail-closed contract be preserved for default callers?
- **Resolution**: Yes. `test_load_slots_validation_rejects_bad_rows` (`python/test_agent_waterfall.py:449`) must stay green — the default (no flag) behavior is unchanged; only `--skip-invalid-slots` callers degrade.
- **Source**: codebase / user (prior Q&A)

## Decision 6: Run mode
- **Question**: Lean plan-only path vs. full `/design` flow with the plan-review panel?
- **Resolution**: Full `/design` flow, including the full plan-review panel, voting, and revisions.
- **Source**: user (this run)
