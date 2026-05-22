## Goal
Update documentation to align with the issue-anchored /design+/implement workflow after the cutover, removing stale references to retired flags and design-boundary patterns.

## Implementation Plan
## Plan

### Files to modify

1. **AGENTS.md** — 2 replacements (lines 55, 58): the `/design --subagent requires SendMessage` paragraph becomes a one-sentence `--hard`/non-inline pointer; the `NEVER write $IMPLEMENT_TMPDIR/session-env.sh` paragraph becomes a one-line pointer to implement NEVER #14.
2. **README.md** — Remove the `--inline` internal-flag parenthetical from the `/design` catalog description (line 73).
3. **docs/workflow-lifecycle.md** — 5 changes: (a) remove `IMPLEMENT→DESIGN` mermaid edge + add /design as peer orchestrator; (b) update /implement description to say "materializes from issue-anchored larch:plan"; (c) reframe End-to-End Flow to show /design as predecessor; (d) update /design Standalone Usage entry to current tier flags; (e) remove `--quick` and `--full` rows from Flags table, remove `/design` from `--auto` "Available on" column.
4. **docs/run-logs.md** — 9 changes: (a) remove both `--design-only` clauses from intro exceptions paragraph; (b) update plan-goals-test section to describe issue-body materialization; (c) update plan-review-tally.json section to describe stub referencing /design plan review; (d) remove "design-only" from final-summary notes list; (e) drop `--design-only` prefix from session-transcript section; (f) update larch:plan tracking comment description; (g) remove `--design-only` sentence from larch:diagrams; (h) remove `--design-only` sentence from larch:final-summary; (i) check code-review-tally section for stale "quick-mode" reference.
5. **docs/agents.md** — Update line 41: replace "/implement invokes /design first" with description of /design as prerequisite peer that writes the issue-body plan.
6. **docs/topology.md** — Regenerate via `bash scripts/generate-topology-docs.sh` (expected: no content change).

No changes needed in: docs/configuration-and-permissions.md, docs/external-reviewers.md, SECURITY.md, skills/compress-skill/SKILL.md.

### Approach

**AGENTS.md**:
- Line 55: Replace the full `/design --subagent requires SendMessage` paragraph with: `- **On the \`--hard\` tier with non-inline host dispatch, \`/design\` uses an Agent-tool subagent for the heavy phase; \`SendMessage\` is required for suspend recovery in that mode** — see \`skills/design/references/flags.md\`.`
- Line 58: Replace the full NEVER #14 mirror paragraph with: `- **Do not write \`$IMPLEMENT_TMPDIR/session-env.sh\` from prompt-side orchestrator code** — see \`skills/implement/SKILL.md\` NEVER #14 for sanctioned writers.`
- Leave `/review --subagent requires SendMessage` paragraph intact.

**README.md**: Remove the trailing parenthetical "Internal `--inline` is documented only in `skills/design/references/flags.md` (not a public `/implement` argv)." from the /design catalog row.

**docs/workflow-lifecycle.md**: (a) Remove `IMPLEMENT -->|invokes| DESIGN` edge from mermaid; add `/design` as standalone peer orchestrator node. (b) Update /implement description sentence. (c) Reframe End-to-End Flow: DESIGN_PHASE subgraph → single predecessor node. (d) Update /design Standalone Usage to tier flags. (e) Remove `--quick`/`--full` rows from Flags table; remove `/design` from `--auto` Available-on column.

**docs/run-logs.md**: 9 targeted section edits per the plan. Key: both `--design-only` clauses in intro paragraph; plan-goals-test section; plan-review-tally.json section; final-summary notes; session-transcript; larch:plan comment; larch:diagrams; larch:final-summary.

**docs/agents.md**: Single sentence update at line 41.

**docs/topology.md**: Run `bash scripts/generate-topology-docs.sh`.

### Edge cases

- AGENTS.md line 55: New note is scoped to `--hard` / non-inline dispatch only. The `--trivial` and `--simple` tiers (quick_mode=true) have no SendMessage risk.
- AGENTS.md line 58: The one-liner points to implement NEVER #14 without duplicating the full rationale.
- docs/run-logs.md Change (a): Remove BOTH --design-only clauses from intro paragraph while keeping `--forked` and redaction warning.
- docs/agents.md: Change only the sequential composition example sentence; leave archetype descriptions intact.

### Failure modes

1. Removing both --design-only clauses from run-logs.md intro but accidentally keeping `repo_unavailable=true` text intact.
2. workflow-lifecycle.md mermaid syntax error after removing IMPLEMENT→DESIGN edge.
3. docs/agents.md: changing more than the sequential composition example sentence.

### Testing strategy

- Run `make lint` and `agent-lint`.
- Run `bash scripts/generate-topology-docs.sh` and diff against `docs/topology.md`; expect empty diff.
- Grep for `--design-only`, `--inline` (in public catalog context), `/imaq` across modified files.
- Grep for "invokes /design" in docs/ to confirm both docs/agents.md and workflow-lifecycle.md are updated.
- Grep for "exported plan.txt" and "quick mode" in plan-goals-test context in run-logs.md.
- Verify AGENTS.md replacements: grep for "requires SendMessage" (shortened /design note + /review note only).

## Acceptance

- Docs match code reality after the issue-anchored cutover (#2485).
- `make lint`, `agent-lint`, and CI markdown checks pass.
- No stale references to `--design-only`, standalone `/design` as /implement sub-invocation, or retired quick/inline modes in the modified docs.

diff_lines: 95

## Test plan
(no test plan section in plan-file)
