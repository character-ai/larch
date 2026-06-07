## Goal
Implement issue #3704: [IMPLEMENTING] [BUG] /implement review dispatch: parallelize voters + default Cursor-first fix-coder\n\n## Work item 1 — Parallelize all 3 review voters (#3702).

## Implementation Plan
## Work item 1 — Parallelize all 3 review voters (#3702)

`scripts/dispatch-code-voters.sh` runs the Claude voter as a **blocking foreground call** before constructing the Codex+Cursor voter manifest. All three voters — Claude, Cursor, and Codex — should be dispatched in **parallel at the same time**, with no serial gate between them. Remove any conditional that delays external voter launch until after Claude returns.

**Affected surface:** `scripts/dispatch-code-voters.sh` — lines that call `launch-claude-review.sh` synchronously before building the external voter manifest.

## Work item 2 — Review-fix coder waterfall: default Cursor → Codex → Claude (#3703)

When review findings are applied as code fixes, the coder waterfall tries Codex first. The default for the **review-fix path** should be **Cursor → Codex → Claude** (not Codex-first). The initial implementation coder default (Codex) is unchanged — only the review-fix path changes.

**Rationale:** Cursor has stronger edit-following behavior, making it better suited for surgical fix application. Codex is the better choice for large initial implementations.

**Affected surface:** `review-and-fix.sh` (or wherever `dispatch-with-waterfall.sh` is called for the review-fix coder path) — the `--slots-file` ordering or equivalent priority.
## Work item 3 — Parallelize /design plan-review voters (#3704 addition)

`scripts/dispatch-plan-voters.sh` has the identical serialization problem as `dispatch-code-voters.sh` in work item 1: the Claude voter is launched as a **blocking foreground call** (lines 94–103), and the Codex+Cursor voter waterfall is only constructed after `voter1_rc` returns.

Apply the same fix: dispatch all three voters (Claude, Codex, Cursor) in parallel simultaneously, with no serial gate.

**Affected surface:** `scripts/dispatch-plan-voters.sh` — same structural change as work item 1 applied to the plan-review voter path.
## Work item 4 — Replace scout waterfall with Cursor → Claude (both /design and /implement)

The scout currently uses a waterfall that starts with a tool other than Cursor. Replace it with a two-entry waterfall: **Cursor first, Claude fallback** (when Cursor is unavailable). Codex should not be in the scout waterfall at all.

This applies to both the /design scout and the /implement scout.

**Affected surface:** wherever the scout is dispatched in each skill — the `--slots-file` or equivalent priority list controlling which tool runs the scout.

## Test plan
(no test plan section in plan-file)
