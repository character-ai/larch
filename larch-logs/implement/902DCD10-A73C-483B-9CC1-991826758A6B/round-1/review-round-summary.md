# Review Round 1

- Mode: `diff`
- 2 accepted, 0 rejected (0 neutral)

## Accepted Findings

### FINDING_1: MAV/coder terminal stall may skip to Step 18 before handoff record-only + durable bail
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, dyn-dyn-routing-contract-output.txt
- **Severity**: important
- **Concern**: Section 4 of `checks-repair-loop.md` default `NEXT_ACTION=stall` instructs `STALL_TRACKING=true` and immediate skip to Step 18 (lines 75–76) before the MAV/coder override (lines 80–81) that only defers record-only and durable bail to the SKILL.md handoff paragraph (~666). An orchestrator applying the default first reaches Step 18 without `--record-only` timing capture or `ship-pr-state.sh` seeding via **Durable Bail to Step 18 Macro**, weakening Step 18a stall recovery on MAV/coder terminal checks stalls. **Checks Failure Entry Macro** item 7 defers durable bail to handoff but does not explicitly forbid the immediate Step 18 skip at the blockquote/repair-loop layer, while item 6 tells other sites to skip directly; orchestrator may apply item-6-style skip semantics after the deferral wording and bypass the handoff execution site.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Add explicit fall-through wording in the MAV/coder bullet: do not skip to Step 18 at repair-loop site; continue to handoff paragraph for record-only + durable bail, then skip. Or qualify the default bullet to exclude MAV/coder.
  - From cursor-specialist-correctness-output.txt: Amend item 7 to state explicitly: do not skip to Step 18 at blockquote/repair-loop layer; fall through to handoff paragraph as sole execution site.
  - From dyn-dyn-routing-contract-output.txt: In §4, state explicitly that Step 5 MAV and coder-main-agent-required must not take the default skip at the repair-loop site; they must continue to the main-agent handoff terminal-stall path in `skills/implement/SKILL.md` before skipping to Step 18. Mirror the same "do not skip yet" guard in **Checks Failure Entry Macro** item 7 and the MAV/coder blockquotes (~653, ~657).


### FINDING_2: Durable Bail macro STALL_TRACKING authority conflicts with stall-branch envelope retention
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: important
- **Concern**: **Durable Bail to Step 18 Macro** item 1 cites the `step5-review-branches.md` `stall` branch as authority, which retains envelope `STALL_TRACKING` and seeds with `"$STALL_TRACKING"`, conflicting with items 3/6 that force `STALL_TRACKING=true`. On MAV/coder handoff after checks terminal stall, an orchestrator following the stall-branch seeder may write `STALL_TRACKING=false` from the parsed envelope, skipping Step 18a recovery.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: In item 1 or 6, explicitly state the macro overrides stall-branch STALL_TRACKING retention and always seeds with --stall-tracking true for this execution path.


