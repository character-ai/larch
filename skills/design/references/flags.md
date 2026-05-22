# Flag Reference

**Consumer**: `/design` argument parsing (loaded before Step 0 via the MANDATORY directive adjacent to the compact flag table in `SKILL.md`).

**Contract**: normative rules for **public** `/design` argv (`--trivial`, `--simple`, `--hard`, `--no-dedup`, `--run-id`) plus **internal** orchestration tokens retained for nested hosts and CI harness pins.

**When to load**: once at the top of `/design` invocation, before Step 0 executes, via the MANDATORY directive adjacent to the compact flag table. Do NOT load mid-flow; flag parsing runs once and the decisions are sticky.

**Binding convention**: `SKILL.md`'s compact flag table is a non-normative index — this file is authoritative for validation, tier mapping, and internal dispatch notes.

---

## Public `/design` flags

- `--trivial`: mutually exclusive tier. Maps to `sketch_budget=0`, `quick_mode=true`, `review_budget=quick`, `workflow_path=SIMPLE` when writing `run-params.json` (the trivial doc-only carve-out follows the Step 0 router scan in `SKILL.md`).
- `--simple`: mutually exclusive tier. Maps to `sketch_budget=2`, `quick_mode=true`, `review_budget=full`, `workflow_path=SIMPLE` (2 sketch agents on the quick path per `sketch-launch.md`).
- `--hard`: mutually exclusive tier. Maps to `sketch_budget=4`, `quick_mode=false`, `review_budget=full`, `workflow_path=HARD`.
- `--no-dedup`: forward to `/larch:issue` on the verbal-create path. Default `false`.
- `--run-id <ID>`: optional stable run id. Default empty.

**Mutual exclusion**: at most one of `--trivial` / `--simple` / `--hard` on argv; duplicate tier flags → hard error before Step 0.

**Positional tail**: after flags, either `^[0-9]+$` (existing issue) or verbal feature text (create issue via `/larch:issue` first).

## Internal — sketch dispatch (not public argv)

- **`/design` sketch phase is inline-only** (issue #2487): sketches, external collectors, synthesis, dialectic, and plan review run in the orchestrator session per `SKILL.md`. There is no Agent-tool offload path for the sketch phase.

## Legacy — `--branch-info` and `--step-prefix` (internal orchestration)

These are **not** public `/design` argv surfaces after issue #2485; they remain documented for older nested-call contracts and CI literals.

- `--branch-info <values>`: parse IS_MAIN, IS_USER_BRANCH, USER_PREFIX, CURRENT_BRANCH from space-separated KEY=VALUE pairs. **All 4 keys are required** when this internal flag is used. Values are safe for space-splitting (USER_PREFIX is sanitized by create-branch.sh derive_user_prefix; CURRENT_BRANCH cannot contain spaces). **Historical note**: `/design` itself no longer creates a feature branch even when this legacy flag is passed (the branch step has been removed; `/implement` owns the feature-branch lifecycle). The flag remains documented for orchestration-context propagation only.
- `--step-prefix <prefix>`: encodes numeric prefix, textual breadcrumb path, and optional parent skill path using a `::` delimiter — see `${CLAUDE_PLUGIN_ROOT}/skills/shared/progress-reporting.md` for the full encoding spec.
