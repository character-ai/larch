## Goal
Implement issue #5659: [IMPLEMENTING] [Bug] /implement terminal: Codex implementation left two lint violations unfixable by automated repair: S030 orphaned skill files and missing readability-preamble directives. (unrecoverable at 3).

## Implementation Plan
<!-- larch-stall:signature=3b4e91085407adba2c7b242077aa72da4da8a9e76e99e1c90968d18412da26cc -->
## Report metadata
- **Report kind**: `terminal-failure`
- **Failure class**: `unrecoverable`
- **Step**: `3`
- **Bail reason**: `checks-failed`
- **Run ID**: `B76BC4CB-C067-4DA2-9370-E7AA87E6E8D1`
- **Branch**: `unknown`
- **PR URL**: `unknown`

## Root-cause finding

verdict=larch-defect
confidence=high
summary=Codex implementation left two lint violations unfixable by automated repair: S030 orphaned skill files and missing readability-preamble directives.

## Finding

The Step 3 pre-commit checks failed with two errors after Codex committed its implementation of issue #5561.

**Error 1 — S030/orphaned-skill-files** (agent-lint, exit 1):
`skills/design/scripts/design-step3b-sanitize.md` and `skills/design/scripts/design-step3b-sanitize.sh` are not referenced from `skills/design/SKILL.md`. The plan directed Codex to "remove `design-step3b-sanitize.sh` and its prompt doc as primary Step 5 surfaces" from SKILL.md, but also to "leave the wrapper in place unless tests or script inventory require retirement." The S030 lint rule (`agent-lint`) requires all files under `skills/*/scripts/` to be referenced from the corresponding `skills/*/SKILL.md`. The plan's intent — keep files but de-reference them — directly conflicts with this lint invariant. Resolution requires either deleting both files or retaining a reference (e.g., a legacy/historical note) in SKILL.md.

**Error 2 — lint-readability-preamble** (exit 1):
`skills/design/references/finalize-step5.md` expected 2 orchestrator-inline readability-style directives but found 0. The plan moved `readability-style.md` to "Step 5 entry" and directed Codex to update `finalize-step5.md`, but Codex removed the 2 required inline readability-style directives without re-inserting them in the new location within the file. The lint harness (`lint-readability-preamble`) counts occurrences in `finalize-step5.md` and found 0.

**Automated repair**: the `checks repair-loop --site step3` ran for approximately 5 minutes 30 seconds and returned `NEXT_ACTION=stall LOOP_STATUS=exhausted`, meaning automated lint-fix did not converge within the retry cap.

Evidence:
- `relevant-checks/step3-1.redacted.log` — lint output with both errors
- `stall-recovery-classification.env` — `FAILURE_CLASS=unrecoverable`, `RESUME_HINT=none`, `MATCHED_CLASSIFIER_PATTERN=no-stall`
- In-memory `STALL_TRACKING=true` set at Step 3 after repair-loop returned stall



## Attempts

| Attempt | Class | Resume hint | Outcome | UTC |
|---|---|---|---|---|
| none | n/a | n/a | n/a | n/a |

## Test plan
(no test plan section in plan-file)
