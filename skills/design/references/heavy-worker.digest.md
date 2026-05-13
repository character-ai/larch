# Design Heavy Worker Reference — Digest

**Consumer**: `/design` heavy-phase Agent-tool subagent dispatched when `--subagent` AND `quick_mode=false`.

> **If dispatching a subagent, read the full `heavy-worker.md` before proceeding.**

**Contract**: Runs token-heavy design machinery (sketches → dialectic → plan → plan review) in an isolated Agent-tool subagent context. Writes raw artifacts under `$DESIGN_TMPDIR/` only. Does NOT write `manifest.env` — parent `/design` Step 5 writes that after Steps 3.5/3b/4.

**When to load**: by the parent `/design` orchestrator when consulting the dirty-tree probe contract (Step 2a.5 collection boundaries). Load the full `heavy-worker.md` when dispatching a subagent.

## Inputs

Pass explicitly to the subagent: `DESIGN_TMPDIR`, `IMPLEMENT_TMPDIR`, `SESSION_ENV_PATH`, `FEATURE_DESCRIPTION`, `quick_mode`, `auto_mode`, current branch info, reviewer health flags (`codex_available`, `cursor_available`, `CODEX_HEALTHY`, `CURSOR_HEALTHY`).

## Artifact Contract

Subagent writes under `$DESIGN_TMPDIR/`:

- **Required non-empty**: `approach-synthesis.txt`, `plan.txt`, `diff-lines.txt`, `voting-tally.md`
- **Required, may be empty**: `contested-decisions.md`, `oos.md`, `rejected-findings.md`, `accepted-plan-findings.md`
- **Conditional**: `dialectic-resolutions.md` (empty file when dialectic skipped), `architecture-diagram.md` (`auto_mode=true` only), `dirty-tree-detected.env` (on dirty-tree at any collection boundary)

**Return sentinel** (only content in the Agent-tool return text): `DESIGN_HEAVY=complete` on success; `DESIGN_HEAVY=failed REASON=<token>` on failure. No plan/prose in return text — artifacts stay in files.

## Key Invariants

- **SendMessage dependency**: without `SendMessage`, any subagent yield becomes a fatal stall — pass `--inline` to avoid subagent dispatch.
- **Dirty-tree recovery**: on `DESIGN_HEAVY=failed REASON=dirty-tree`, read `$DESIGN_TMPDIR/dirty-tree-detected.env` (`STATUS`, `STAGE`, `RECOVERY_REQUIRED=true`) and prompt for recovery — not suppressed by `--auto`.

## Mid-Run Dirty-Tree Probe Contract

After each external collection boundary (sketch, dialectic-debate, dialectic-judge, plan-review), consult launcher `${OUTPUT}.dirty-tree` sidecars and run `${CLAUDE_PLUGIN_ROOT}/scripts/check-mid-run-dirty-tree.sh --mode checkpoint`. On `STATUS=dirty` or `STATUS=unknown`: write `$DESIGN_TMPDIR/dirty-tree-detected.env` with `STATUS=<status>`, `STAGE=<boundary>`, `RECOVERY_REQUIRED=true`, then return `DESIGN_HEAVY=failed REASON=dirty-tree`. Dedup per boundary via `$DESIGN_TMPDIR/.dirty-tree-prompted-<boundary>`.
