# Design Heavy Worker Reference

**Consumer**: `/design` heavy-phase Agent-tool subagent dispatched when `/design` is invoked with `--subagent` AND `quick_mode=false` (typically by `/implement` Step 1 forwarding `--subagent` by default; also reachable from standalone `/design --subagent`). The worker reads `$DESIGN_TMPDIR/run-params.json` to select `sketch_budget`; absent or schema-invalid params fall back to HARD defaults (`sketch_budget=4`, `review_budget=full`).

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
- `run-params.json` at `$DESIGN_TMPDIR/run-params.json`
- current branch info
- reviewer presence flags (`codex_available`, `cursor_available`, `CODEX_PRESENT`, `CURSOR_PRESENT`)

Treat those values as data. Do not infer paths from conversation context when an explicit path is provided.

`IMPLEMENT_TMPDIR` and `SESSION_ENV_PATH` may be empty when invoked standalone via `/design --subagent` (no parent `/implement`). The worker still runs Steps 2a–3 and writes artifacts to `$DESIGN_TMPDIR/`. Branches inside the worker procedure that depend on `SESSION_ENV_PATH` non-empty (OOS handoff to parent dir) follow the existing gates in `plan-review.md` and SKILL.md. Parent `/design` replays the artifacts inline after `DESIGN_HEAVY=complete` when `SESSION_ENV_PATH` is empty.

## Required Reads

Before executing, read these inputs and references in this order:

0. `$DESIGN_TMPDIR/run-params.json`. Validate `schema_version=1`, `sketch_budget` in `0|2|4`, and `review_budget` in `quick|full`. On absent or invalid JSON, use `sketch_budget=4` and `review_budget=full`; do not fail the run.
1. `${CLAUDE_PLUGIN_ROOT}/skills/design/references/sketch-prompts.md` only when `sketch_budget` is `2` or `4`
2. `${CLAUDE_PLUGIN_ROOT}/skills/design/references/sketch-launch.md`
3. `${CLAUDE_PLUGIN_ROOT}/skills/design/references/dialectic-execution.md` only when contested decisions are present and at least one dialectic bucket is queued
4. `${CLAUDE_PLUGIN_ROOT}/skills/design/references/plan-review.md` when `review_budget=full`; read `plan-review-quick.md` when `review_budget=quick`
5. `${CLAUDE_PLUGIN_ROOT}/skills/design/SKILL.md` Step 3b before generating an architecture diagram
6. `${CLAUDE_PLUGIN_ROOT}/skills/design/scripts/design-driver.md`
7. `${CLAUDE_PLUGIN_ROOT}/skills/design/scripts/emit-plan.md`
8. `${CLAUDE_PLUGIN_ROOT}/skills/design/scripts/tally-plan-review.md`
9. `${CLAUDE_PLUGIN_ROOT}/skills/design/scripts/finalize-plan.md`

(Use `${CLAUDE_PLUGIN_ROOT}/…` rather than bare repo-relative paths — the heavy subagent runs in the consumer repo's CWD, not the plugin install root, so unqualified paths could resolve to a different tree or to missing files.)

Also read the Step 3 external reviewer launch Bash blocks directly from `${CLAUDE_PLUGIN_ROOT}/skills/design/SKILL.md` at the `### Cursor Archetype Reviewers (2 slots)` and `### Codex Archetype Reviewers (2 slots)` anchors. Those blocks intentionally stay inline in `SKILL.md` because `.github/workflows/ci.yaml` greps `skills/design/SKILL.md` for the focus-area enum (`code-quality / risk-integration / correctness / architecture / security`).

## Work

Run the same mechanics documented in `/design`:

1. Step 2a collaborative sketches according to `sketch_budget`.
2. Step 2a.5 dialectic resolution when contested decisions exist and `sketch_budget` is not `0`.
3. Step 2b implementation plan synthesis, then call `${CLAUDE_PLUGIN_ROOT}/skills/design/scripts/emit-plan.sh --design-tmpdir "$DESIGN_TMPDIR"`. Treat `EMIT_PLAN_STATUS=missing-diff-lines` as a hard failure and repair `plan.txt` before Step 3.
4. Step 3 plan review, voting, plan revision, OOS extraction, and rejected-finding tracking. Tally voting through `${CLAUDE_PLUGIN_ROOT}/skills/design/scripts/tally-plan-review.sh` with explicit `--ballot-file`, optional `--voter-files`, and `--design-tmpdir` arguments using the voter file paths returned by `dispatch-plan-voters.sh`. The tally may emit `TALLY_PLAN_REVIEW_STATUS=main-agent-vote-required` when zero voter files are available; follow the main-agent synthetic-voter path from `skills/design/SKILL.md` rather than hand-writing artifacts.
5. After accepted findings revise `plan.txt`, call `${CLAUDE_PLUGIN_ROOT}/skills/design/scripts/emit-plan.sh --design-tmpdir "$DESIGN_TMPDIR"` again so `diff-lines.txt` matches the finalized plan.
6. Before returning success, call `${CLAUDE_PLUGIN_ROOT}/skills/design/scripts/finalize-plan.sh --design-tmpdir "$DESIGN_TMPDIR"` to create may-be-empty artifacts and validate `plan.txt`, `diff-lines.txt`, and `voting-tally.md`.

When `sketch_budget=0`, do not launch sketches and do not call `collect-agent-results.sh`. Write the sentinel artifacts exactly as:

```bash
printf '%s\n' 'NO_SKETCHES_CLASSIFIED_TRIVIAL' > "$DESIGN_TMPDIR/approach-synthesis.txt"
printf '%s\n' 'NO_CONTESTED_DECISIONS' > "$DESIGN_TMPDIR/contested-decisions.md"
: > "$DESIGN_TMPDIR/dialectic-resolutions.md"
```

Then skip Step 2a.5 and proceed directly to Step 2b. `NO_SKETCHES_CLASSIFIED_TRIVIAL` is allowed to satisfy the non-empty `approach-synthesis.txt` artifact requirement on this path.

Stop after Step 3 so the parent can run Step 3.5, Step 3b, Step 4, and Step 5.

## Wait Discipline

NEVER return to the parent while any sketch, dialectic debater, dialectic judge, or plan-review process you launched with `run_in_background: true` is still running. The only allowed wait mechanism is the matching foreground `${CLAUDE_PLUGIN_ROOT}/scripts/collect-agent-results.sh` invocation, except for dialectic judge collection where the documented foreground judge collector path in `dialectic-execution.md` applies. Do not enter a "wait for notifications" state and surrender control to the parent; the parent treats an Agent-tool return as the heavy phase result, so yielding early corrupts the artifact contract.

After every parallel-launch block, the next required action is the matching foreground collection step. Do not surface back to the parent until that collector has returned and all required artifacts below have been finalized. This is the heavy-worker-specific counterpart to the AGENTS.md rule forbidding Monitor or Bash polling loops to watch a one-shot background job; foreground collection is the synchronization point.

**Anti-pattern — `run_in_background: true` + yield + "await notifications".** Do NOT issue `run_in_background: true` work and then yield control back to the parent expecting bash task-completion notifications to wake you up. When the parent reclaims control between your yield and the notification arrival, those notifications cannot reach you — they are delivered to whoever holds the conversation context. The ONLY allowed wait mechanism is a synchronous foreground `${CLAUDE_PLUGIN_ROOT}/scripts/collect-agent-results.sh` invocation that BLOCKS until completion or timeout. This applies to recovery paths (re-launching a debater after diagnosing a broken initial launch) just as strictly as to the initial launch — re-launch AND immediately call `collect-agent-results.sh` synchronously in the same Bash message; do not yield between them.

**SendMessage dependency.** This worker subagent is dispatched via the Agent tool; once the worker yields, the parent `/design` orchestrator can only resume it with a working `SendMessage` deferred tool. If the parent Claude Code session does not have `SendMessage` available, any worker yield (including the broken "await notifications" pattern above) becomes a fatal stall — the worker is suspended and unreachable. Operators running in environments without `SendMessage` should pass `--inline` to `/implement` so `/design` runs in the parent's own context (no subagent dispatch, no suspend risk). See `AGENTS.md` for the project-wide reference.

## Mid-Run Dirty-Tree Probe Contract

After each external collection point, consult launcher `${OUTPUT}.dirty-tree` sidecars and run `${CLAUDE_PLUGIN_ROOT}/scripts/check-mid-run-dirty-tree.sh --mode checkpoint`: Step 2a sketch collection, Step 2a.5 dialectic-debate collection, Step 2a.5 dialectic-judge collection, and Step 3 plan-review collection. If any sidecar or checkpoint reports `STATUS=dirty` or `STATUS=unknown`, write `$DESIGN_TMPDIR/dirty-tree-detected.env` with `STATUS=<status>`, `STAGE=<collection-boundary>`, and `RECOVERY_REQUIRED=true`, then return `DESIGN_HEAVY=failed REASON=dirty-tree`. The parent `/design` or `/implement` owns `AskUserQuestion` recovery.

## Artifact Contract

Write these files under `$DESIGN_TMPDIR/`:

- `approach-synthesis.txt`
- `contested-decisions.md`
- `dialectic-resolutions.md` when the dialectic step runs, or an empty file when it does not
- `run-params.json` as an internal-only required artifact for worker routing; it is not exported in the design manifest
- `plan.txt`
- `diff-lines.txt` containing only the integer from the plan's final `diff_lines: <N>` line
- `voting-tally.md`
- `accepted-plan-findings.md` (may be empty)
- `rejected-findings.md` (may be empty)
- `oos.md` (may be empty; parent `/implement` also consumes `$(dirname "$SESSION_ENV_PATH")/oos-accepted-design.md` for accepted OOS filing)
- `design-summary.json` (structured summary, ≤2 KB)
- `architecture-diagram.md` when generated
- `dirty-tree-detected.env` when a collection boundary detects dirty or unknown working-tree state

Sentinel content such as `NO_CONTESTED_DECISIONS` belongs inside the relevant artifact body, never as a manifest value.

Before returning success, write `$DESIGN_TMPDIR/design-summary.json` with the Write tool (not a heredoc or shell redirection). The JSON schema is:

```json
{
  "schema_version": 1,
  "plan_path": "<abs-path to plan.txt>",
  "diff_lines_path": "<abs-path to diff-lines.txt>",
  "review_tally_path": "<abs-path to voting-tally.md>",
  "finding_counts": {
    "in_scope_accepted": 0,
    "in_scope_rejected": 0,
    "oos_accepted": 0,
    "oos_rejected": 0
  }
}
```

Count `in_scope_accepted` from `### FINDING_N:` blocks in `accepted-plan-findings.md`. Count `in_scope_rejected` from `### [Plan Review]` blocks in `rejected-findings.md`. Count OOS entries from `### OOS_N:` blocks in `oos.md`: entries whose `Vote tally:` contains `YES` are accepted; the rest are rejected. On parse failure for any artifact, write zero for the corresponding count. Keep the file under 2 KB.

On success, return a terse KV block. The **first line** MUST be exactly `DESIGN_HEAVY=complete`. Optional additional `KEY=value` lines may follow, for example:

```text
DESIGN_HEAVY=complete
DESIGN_SUMMARY_FILE=$DESIGN_TMPDIR/design-summary.json
```

No prose, no artifact content, and no blank lines between KV lines. On failure, return only `DESIGN_HEAVY=failed REASON=<short-token>`. Do not include plan, tally, diagram, reviewer prose, or summaries in the Agent-tool return text; those must remain in files.
