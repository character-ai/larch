## Decision 1: Scope of the change
- **Question**: Which Gate B branches lose the blocking prompt?
- **Resolution**: ONLY the passive-summary mode — `LOOP_STATUS=converged|cap-hit` AND `manual_gate_b=false`. All other Gate B modes are unchanged: `manual_gate_b=true` (full 3-option AskUserQuestion), `LOOP_STATUS=revision-failed|emit-plan-failed` (warning + manual handling), the zero-findings short-circuit, and the legacy/non-loop auto-apply path.
- **Source**: issue #3190

## Decision 2: Output in non-blocking passive-summary mode
- **Question**: What should print before auto-continuing?
- **Resolution**: Keep the full `## Multi-round loop result` table AND the "All accepted findings were auto-applied across N rounds; `plan.txt` reflects the final state." line, then auto-continue with no prompt.
- **Source**: user (Step 1c clarification) + issue #3190

## Decision 3: Control flow after the summary
- **Question**: Where does the run go after the non-blocking summary?
- **Resolution**: Auto-continue Step 3.6 (HARD-only assessor) → Step 3b → Step 4 → Gate C (Step 4b), with NO halt. Gate C remains the single binding final-approval decision point. The old "Switch to discussion mode" intent is covered by Gate C's "Discuss further".
- **Source**: issue #3190

## Decision 4: Hard constraints / non-goals
- **Question**: What must not change?
- **Resolution**: Do not change which findings are applied (the loop's between-round auto-apply via `revise-plan-with-waterfall.sh` is unchanged); do not weaken any approval gate; do not re-apply findings or run the shared post-apply pipeline in passive-summary mode (the loop already revised `plan.txt`). UX-only change to one Gate B branch.
- **Source**: issue #3190

## Decision 5: Harness / structural pins
- **Question**: Do any test harnesses assert the existence of the two-option passive-summary prompt?
- **Resolution**: Must verify and, if so, update them so the change does not break CI. Candidate harnesses surfaced by Step 0c grep: `scripts/test-design-structure.sh`, `scripts/test-design-multi-round-integration.sh`, `skills/design/scripts/test-step3-review-cap.sh`. (To be confirmed during plan drafting — implementation-level, not a user scope decision.)
- **Source**: codebase (Step 0c grep) + issue #3190
