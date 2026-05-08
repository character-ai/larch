# Design Heavy Worker Reference

**Consumer**: `/design` heavy-phase Agent-tool subagent dispatched when `/design` is invoked with `--subagent` AND `quick_mode=false` (typically by `/implement` Step 1 forwarding `--subagent` by default; also reachable from standalone `/design --subagent`).

**Contract**: The subagent runs the token-heavy non-interactive design machinery in isolated context so sketches, reviewer transcripts, voting output, and synthesis drafts do not enter the parent conversation. It writes raw artifacts under `$DESIGN_TMPDIR/` only. It does **not** write `$IMPLEMENT_TMPDIR/design-export/manifest.env`; `/design` Step 5 writes that manifest after parent-side Step 3.5 / Step 3b / Step 4 have completed.

**When to load**: only by the heavy-phase subagent. The parent `/design` skill points the subagent here, passes the relevant environment values, then consumes files from `$DESIGN_TMPDIR/`.

---

## Inputs

The parent prompt supplies:

- `DESIGN_TMPDIR`
- `IMPLEMENT_TMPDIR`
- `SESSION_ENV_PATH`
- `FEATURE_DESCRIPTION`
- `quick_mode`
- `auto_mode`
- current branch info
- reviewer health flags (`codex_available`, `cursor_available`, `CODEX_HEALTHY`, `CURSOR_HEALTHY`)

Treat those values as data. Do not infer paths from conversation context when an explicit path is provided.

`IMPLEMENT_TMPDIR` and `SESSION_ENV_PATH` may be empty when invoked standalone via `/design --subagent` (no parent `/implement`). The worker still runs Steps 2a–3 (and 3b/4 when `auto_mode=true`) and writes artifacts to `$DESIGN_TMPDIR/`. Branches inside the worker procedure that depend on `SESSION_ENV_PATH` non-empty (OOS handoff to parent dir, `--write-health` collector flag, Voter 1 health-status writes) follow the existing gates in `plan-review.md` and SKILL.md — no change needed here. Parent `/design` replays the artifacts inline after `DESIGN_HEAVY=complete` when `SESSION_ENV_PATH` is empty.

## Required Reads

Before executing, read these references in this order:

1. `${CLAUDE_PLUGIN_ROOT}/skills/design/references/sketch-prompts.md`
2. `${CLAUDE_PLUGIN_ROOT}/skills/design/references/sketch-launch.md`
3. `${CLAUDE_PLUGIN_ROOT}/skills/design/references/dialectic-execution.md` only when contested decisions are present and at least one dialectic bucket is queued
4. `${CLAUDE_PLUGIN_ROOT}/skills/design/references/plan-review.md`
5. `${CLAUDE_PLUGIN_ROOT}/skills/design/SKILL.md` Step 3b before generating an architecture diagram

(Use `${CLAUDE_PLUGIN_ROOT}/…` rather than bare repo-relative paths — the heavy subagent runs in the consumer repo's CWD, not the plugin install root, so unqualified paths could resolve to a different tree or to missing files.)

Also read the Step 3 external reviewer launch Bash blocks directly from `${CLAUDE_PLUGIN_ROOT}/skills/design/SKILL.md` at the `### Cursor Archetype Reviewers (4 slots)` and `### Codex Archetype Reviewers (4 slots)` anchors. Those blocks intentionally stay inline in `SKILL.md` because `.github/workflows/ci.yaml` greps `skills/design/SKILL.md` for the focus-area enum (`code-quality / risk-integration / correctness / architecture / security`).

## Work

Run the same mechanics documented in `/design`:

1. Step 2a collaborative sketches.
2. Step 2a.5 dialectic resolution when contested decisions exist.
3. Step 2b implementation plan synthesis.
4. Step 3 plan review, voting, plan revision, OOS extraction, and rejected-finding tracking.

When `auto_mode=true`, also run Step 3b architecture diagram and Step 4 rejected-finding artifact finalization in the worker, because there are no parent-side interactive checkpoints. When generating `architecture-diagram.md`, follow the candidate -> sanitize -> promote subprocedure documented in `SKILL.md` Step 3b. Rejected diagrams are not promoted; treat a sanitizer-rejected diagram the same as "not generated" for the artifact contract. When `auto_mode=false`, stop after Step 3 so the parent can run Step 3.5, Step 3b, Step 4, and Step 5.

## Wait Discipline

NEVER return to the parent while any sketch, dialectic debater, dialectic judge, or plan-review process you launched with `run_in_background: true` is still running. The only allowed wait mechanism is the matching foreground `${CLAUDE_PLUGIN_ROOT}/scripts/collect-agent-results.sh` invocation, except for dialectic judge collection where the documented foreground judge collector path in `dialectic-execution.md` applies. Do not enter a "wait for notifications" state and surrender control to the parent; the parent treats an Agent-tool return as the heavy phase result, so yielding early corrupts the artifact contract.

After every parallel-launch block, the next required action is the matching foreground collection step. Do not surface back to the parent until that collector has returned and all required artifacts below have been finalized. This is the heavy-worker-specific counterpart to the AGENTS.md rule forbidding Monitor or Bash polling loops to watch a one-shot background job; foreground collection is the synchronization point.

**Anti-pattern — `run_in_background: true` + yield + "await notifications".** Do NOT issue `run_in_background: true` work and then yield control back to the parent expecting bash task-completion notifications to wake you up. When the parent reclaims control between your yield and the notification arrival, those notifications cannot reach you — they are delivered to whoever holds the conversation context. The ONLY allowed wait mechanism is a synchronous foreground `${CLAUDE_PLUGIN_ROOT}/scripts/collect-agent-results.sh` invocation that BLOCKS until completion or timeout. This applies to recovery paths (re-launching a debater after diagnosing a broken initial launch) just as strictly as to the initial launch — re-launch AND immediately call `collect-agent-results.sh` synchronously in the same Bash message; do not yield between them.

**SendMessage dependency.** This worker subagent is dispatched via the Agent tool; once the worker yields, the parent `/design` orchestrator can only resume it with a working `SendMessage` deferred tool. If the parent Claude Code session does not have `SendMessage` available, any worker yield (including the broken "await notifications" pattern above) becomes a fatal stall — the worker is suspended and unreachable. Operators running in environments without `SendMessage` should pass `--inline` to `/implement` so `/design` runs in the parent's own context (no subagent dispatch, no suspend risk). See `AGENTS.md` for the project-wide reference.

## Mid-Run Dirty-Tree Probe Contract

After each external collection point, consult launcher `${OUTPUT}.dirty-tree` sidecars and run `${CLAUDE_PLUGIN_ROOT}/scripts/check-mid-run-dirty-tree.sh --mode checkpoint`: Step 2a sketch collection, Step 2a.5 dialectic-debate collection, Step 2a.5 dialectic-judge collection, and Step 3 plan-review collection. If any sidecar or checkpoint reports `STATUS=dirty` or `STATUS=unknown`, write `$DESIGN_TMPDIR/dirty-tree-detected.env` with `STATUS=<status>`, `STAGE=<collection-boundary>`, and `RECOVERY_REQUIRED=true`, then return `DESIGN_HEAVY=failed REASON=dirty-tree`. The parent `/design` or `/implement` owns `AskUserQuestion` recovery. This prompt is not suppressed by `--auto`.

## Artifact Contract

Write these files under `$DESIGN_TMPDIR/`:

- `approach-synthesis.txt`
- `contested-decisions.md`
- `dialectic-resolutions.md` when the dialectic step runs, or an empty file when it does not
- `plan.txt`
- `voting-tally.md`
- `accepted-plan-findings.md` (may be empty)
- `rejected-findings.md` (may be empty)
- `oos.md` (may be empty; parent `/implement` also consumes `$(dirname "$SESSION_ENV_PATH")/oos-accepted-design.md` for accepted OOS filing)
- `architecture-diagram.md` when generated
- `dirty-tree-detected.env` when a collection boundary detects dirty or unknown working-tree state

Sentinel content such as `NO_CONTESTED_DECISIONS` belongs inside the relevant artifact body, never as a manifest value.

On success, return only `DESIGN_HEAVY=complete`. On failure, return only `DESIGN_HEAVY=failed REASON=<short-token>`. Do not include plan, tally, diagram, reviewer prose, or summaries in the Agent-tool return text; those must remain in files.
