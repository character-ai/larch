## Proposed Design Outline

### Goals
- Consolidate the post-rewrite chain (dedup + postplan + marker writes) into one script called from three prompt-side sites.
- Reduce `approval-gates.md`, `SKILL.md` Step 1e, and `discussion-rounds.md` Round 2 to a single wrapper call + exit-code branch.

### Non-goals
- No changes to the in-loop apply path (`review-design-step3-loop.sh`). It already internalizes this chain.
- No new plan-size or validation behavior. Exit codes relay unchanged.
- No HARD-flow snapshot sub-steps (removed in #4019).

### Approach sketch
- Add `skills/design/scripts/design-step35-settle.sh --site (gate-b|gate-a|discussion-round2) [--round-num N]`.
- Internally: call `gate-b-dedup-plan.sh --dedup`, then write `.gate-b-postapply-ready-N` (gate-b site only), then call `design-step2b-postplan.sh --site <mapped-site>`.
- Exit 0: settle `.completed/step-2b.5`; relay 10/12/13 for operator brakes; `exec` pause-save on 11; abort on 1/2/*.
- `gate-a` maps to `discussion-round2` for the postplan call.
- Replace the three prose-directed `set +e` + `printf` + `case` blocks with one wrapper call + a 4-arm `case` on `_settle_rc` (0/10/12/13).
- Add sibling `design-step35-settle.md` per the script-md-siblings rule.
- Extend `test-gate-b-dedup-plan.sh` and `test-gate-b-apply-mode.sh`.

### Surfaces in scope
- `skills/design/scripts/design-step35-settle.sh` (new)
- `skills/design/scripts/design-step35-settle.md` (new sibling)
- `skills/design/references/approval-gates.md` (§Shared post-apply pipeline)
- `skills/design/SKILL.md` (Step 1e Gate A optional-trailer guard)
- `skills/design/references/discussion-rounds.md` (Round 2 plan revision authority)
- `skills/design/scripts/test-gate-b-dedup-plan.sh`
- `skills/design/scripts/test-gate-b-apply-mode.sh`

### Open questions
- None.
