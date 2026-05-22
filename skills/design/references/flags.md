# Flag Reference

**Consumer**: `/design` argument parsing (loaded before Step 0 via the MANDATORY directive adjacent to the compact flag table in `SKILL.md`).

**Contract**: normative rules for **public** `/design` argv (`--trivial`, `--simple`, `--hard`, `--no-dedup`, `--run-id`) plus **internal** orchestration tokens retained for nested hosts and CI harness pins.

**When to load**: once at the top of `/design` invocation, before Step 0 executes, via the MANDATORY directive adjacent to the compact flag table. Do NOT load mid-flow; flag parsing runs once and the decisions are sticky.

**Binding convention**: `SKILL.md`'s compact flag table is a non-normative index — this file is authoritative for validation, tier mapping, and internal dispatch notes.

---

## Public `/design` flags

- `--trivial`: mutually exclusive tier. Maps to `sketch_budget=0`, `quick_mode=true`, `review_budget=quick`, `workflow_path=SIMPLE` when writing `run-params.json` (trivial doc-only carve-out still follows the ACTION classifier when applicable).
- `--simple`: mutually exclusive tier. Maps to `sketch_budget=2`, `quick_mode=true`, `review_budget=full`, `workflow_path=SIMPLE` (2 sketch agents on the quick path per `sketch-launch.md`).
- `--hard`: mutually exclusive tier. Maps to `sketch_budget=4`, `quick_mode=false`, `review_budget=full`, `workflow_path=HARD`.
- `--no-dedup`: forward to `/larch:issue` on the verbal-create path. Default `false`.
- `--run-id <ID>`: optional stable run id. Default empty.

**Mutual exclusion**: at most one of `--trivial` / `--simple` / `--hard` on argv; duplicate tier flags → hard error before Step 0.

**Positional tail**: after flags, either `^[0-9]+$` (existing issue) or verbal feature text (create issue via `/larch:issue` first).

## Internal — heavy dispatch (not public argv)

- **Internal / CI pin #1036 (not public argv)**: host-controlled heavy dispatch may still align with legacy tokens `--subagent` and `subagent_mode=true` for harness grep stability; **operators never pass `--subagent`**. When `quick_mode=false` and the host elects **non-inline** dispatch, Step 2a runs the Agent-tool heavy worker per `references/heavy-worker.md`.
- **`--inline` (internal only)**: when the host forces inline heavy work (no Agent-tool subagent), the orchestrator skips the subagent path entirely. **Not** a public argv flag for `/design`. Operators lacking `SendMessage` should run `/implement --inline` so `/design` never dispatches a heavy subagent from the parent (see `AGENTS.md`).

## Legacy — `--branch-info` and `--step-prefix` (internal orchestration)

These are **not** public `/design` argv surfaces after issue #2485; they remain documented for older nested-call contracts and CI literals.

- `--branch-info <values>`: parse IS_MAIN, IS_USER_BRANCH, USER_PREFIX, CURRENT_BRANCH from space-separated KEY=VALUE pairs. **All 4 keys are required** when this internal flag is used. Values are safe for space-splitting (USER_PREFIX is sanitized by create-branch.sh derive_user_prefix; CURRENT_BRANCH cannot contain spaces). When `--branch-info` is absent, standalone `/design` runs `create-branch.sh --check` as usual.
- `--step-prefix <prefix>`: encodes numeric prefix, textual breadcrumb path, and optional parent skill path using a `::` delimiter — see `${CLAUDE_PLUGIN_ROOT}/skills/shared/progress-reporting.md` for the full encoding spec.
