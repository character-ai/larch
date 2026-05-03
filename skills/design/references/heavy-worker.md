# Design Heavy Worker Reference

**Consumer**: `/design` heavy-phase Agent-tool subagent when `/design` is nested under `/implement` (`SESSION_ENV_PATH` non-empty).

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

## Required Reads

Before executing, read these references in this order:

1. `skills/design/references/sketch-prompts.md`
2. `skills/design/references/sketch-launch.md`
3. `skills/design/references/dialectic-execution.md` only when contested decisions are present and at least one dialectic bucket is queued
4. `skills/design/references/plan-review.md`

Also read the Step 3 external reviewer launch Bash blocks directly from `skills/design/SKILL.md` at the `### Cursor Archetype Reviewers (4 slots)` and `### Codex Archetype Reviewers (4 slots)` anchors. Those blocks intentionally stay inline in `SKILL.md` because `.github/workflows/ci.yaml` greps `skills/design/SKILL.md` for the focus-area enum (`code-quality / risk-integration / correctness / architecture / security`).

## Work

Run the same mechanics documented in `/design`:

1. Step 2a collaborative sketches.
2. Step 2a.5 dialectic resolution when contested decisions exist.
3. Step 2b implementation plan synthesis.
4. Step 3 plan review, voting, plan revision, OOS extraction, and rejected-finding tracking.

When `auto_mode=true`, also run Step 3b architecture diagram and Step 4 rejected-finding artifact finalization in the worker, because there are no parent-side interactive checkpoints. When `auto_mode=false`, stop after Step 3 so the parent can run Step 3.5, Step 3b, Step 4, and Step 5.

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

Sentinel content such as `NO_CONTESTED_DECISIONS` belongs inside the relevant artifact body, never as a manifest value.

On success, return only `DESIGN_HEAVY=complete`. On failure, return only `DESIGN_HEAVY=failed REASON=<short-token>`. Do not include plan, tally, diagram, reviewer prose, or summaries in the Agent-tool return text; those must remain in files.
