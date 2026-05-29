## Proposed Design Outline

### Goals
- `scout-dynamic-archetypes.sh` tries Codex → Cursor → Claude (availability waterfall) instead of hardwired `claude --print`.
- All three tiers read the diff/context from disk via the Read tool (no prompt-embedding); remove the 256 KB input gate so the scout runs on any-size diffs.
- Trim the review diff (`gather-branch-context.sh`) to exclude `larch-logs/**`, fixing the root-cause bloat.

### Non-goals
- No change to the archetype JSON schema, validation, scout statuses, fail-open behavior, or static-panel dispatch/round count.
- No change to `/design` plan-review voting, reviewer count, or plan-scout `--prompt-override-file` semantics.
- Diff exclusion stays a fixed `larch-logs/**` pathspec — not configurable.

### Approach sketch
- Reuse the existing reviewer waterfall launchers (`launch-review.sh --tool codex|cursor`, then Claude tier), passing the diff as a `--diff-file` path; the scout's prompt tells the agent to Read it.
- Make the Claude tier tool-capable via `claude --print --allowedTools Read,Grep,Glob` + read-only permission mode, replacing embed-only for the scout.
- Delete only the 256 KB size check in `validate_context_input_file` (keep canonical/symlink/allowed-root checks).
- Add `:(exclude)larch-logs/**` to the diff and `--name-only` commands in `gather-branch-context.sh`.

### Surfaces in scope
- `scripts/scout-dynamic-archetypes.sh` (+ `.md`, `test-scout-dynamic-archetypes.sh`)
- Claude tool-capable launch path (`scripts/launch-claude-subprocess.sh` and/or scout-local) (+ siblings/harness)
- `scripts/gather-branch-context.sh` (+ `.md`, harness)
- Touch points: `skills/review/scripts/dispatch-panel.sh`, `skills/design/scripts/scout-plan-archetypes-wrapper.sh` (only if invocation changes)

### Open questions
- Whether the tool-capable Claude tier modifies shared `launch-claude-subprocess.sh` (reviewer-fallback parity) or adds a scout-scoped launch — resolved in the plan + review panel.
