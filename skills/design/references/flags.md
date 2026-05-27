# Flag Reference

**Consumer**: `/design` argument parsing (loaded before Step 0 via the MANDATORY directive adjacent to the compact flag table in `SKILL.md`).

**Contract**: normative rules for public `/design` argv (`--simple`, `--hard`, `--partition` / `-p`, `--brainstorm`, `--manual` / `-m`, `--no-dedup`, `--run-id`) plus internal orchestration tokens retained for nested hosts and CI harness pins.

**When to load**: once at the top of `/design` invocation, before Step 0 executes.

**Binding convention**: `SKILL.md`'s compact flag table is a non-normative index. This file is authoritative for validation, tier mapping, and internal dispatch notes.

---

## Public `/design` flags

- `--simple`: mutually exclusive tier. Maps to `design_classification=SIMPLE` in v2 `run-params.json`. SIMPLE skips upfront sketches and dialectic, but still runs the full external plan-review panel. Designer and reviewers bias toward minimum-change. Re-run cap: 3 total review runs.
- `--hard`: mutually exclusive tier. Maps to `design_classification=HARD` in v2 `run-params.json`. HARD runs 4 personality sketches, dialectic when contested, and the full external plan-review panel. Designer and reviewers bias toward thoroughness. Re-run cap: 5 total review runs.
- `--no-dedup`: forward to `/larch:issue` on the verbal-create path. Default `false`.
- `--run-id <ID>`: optional stable run id. Default empty.
- `--partition` / `-p`: public boolean flag, default `false`. When set, Step **2b.5** routes directly to the **Split-path** (decomposition panel) when no hard threshold fired. The flag is persisted to `$DESIGN_TMPDIR/run-params.json` as `partition_requested` (boolean) via `scripts/write-run-params.sh`.
- `--brainstorm`: public boolean flag, default `false`. When set, Step **1d.5** runs after Round 1 discussion and before Gate A (see `references/brainstorm.md`). Persisted as `brainstorm_requested` (boolean) in `run-params.json` via `scripts/write-run-params.sh`.
- `--manual` / `-m`: public boolean flag, default `false`. When set, restores the Gate B 3-option `AskUserQuestion` (Apply all / Go through each / Switch to discussion mode) on every Gate B entry. Default (`false`) makes Gate B auto-apply every accepted finding to `$DESIGN_TMPDIR/plan.txt` after printing a compact findings list. Persisted as `manual_gate_b` (boolean) in `run-params.json` via `scripts/write-run-params.sh`. Scope: Gate B only — Gate A (Step 1e) discussion sub-rounds and Gate C (Step 4b) final approval are unchanged in both modes. Whole-run sticky: parsed once at argv, read on every Gate B entry including Step 3 re-entries from Gate C(c) "Re-run review panel". Independent of tier / partition / brainstorm flags (no mutual exclusion).

`--trivial` is removed. `SKILL.md` Pre-Step-0 prints `**⚠ /design: --trivial flag removed; tier consolidation in #2956. Use --simple or --hard.**` and exits 1 before `session-setup.sh`.

**Mutual exclusion**: at most one of `--simple` / `--hard` on argv; duplicate tier flags hard-error before Step 0. `--manual` / `-m` is independent of all other public flags.

**Positional tail**: after flags, either `^[0-9]+$` (existing issue) or verbal feature text (create issue via `/larch:issue` first).

## Plan-size thresholds (Step 2b.5)

Mechanical evaluation lives in `skills/design/scripts/check-plan-size.sh` (sibling `check-plan-size.md`). Thresholds use **strict `>`** (800 lines does **not** trip the hard plan-body trigger; 801 does).

The historical **ownership-domains** sprawl heuristic from early design notes is **not** part of L1; it is intentionally omitted (Round 1 decision on issue #2670).

**Hard trigger** — any one suffices (no operator Continue override in the hard `AskUserQuestion`):

- Plan body line count **>** 800.
- `diff_lines` trailer **>** 1500.

**`--partition` / `-p` (Step 2b.5)**: when `partition_requested=true` in `run-params.json`, Step 2b.5 routes directly to the **Split-path** even if no hard threshold fired. That path runs the real decomposition panel. Full procedure, idempotent sentinels, and filing semantics live in `skills/design/references/decompose-panel.md`.

## Helper output — `TRIGGER_REASONS`

The helper emits comma-separated reason tokens in fixed priority order `plan-body-lines`, `diff-lines`.

## `check-plan-size.sh` contract (summary)

- **Input**: `$DESIGN_TMPDIR/plan.txt` (or `--plan-file`) with a final non-empty `diff_lines: <N>` trailer matching `emit-plan.sh` grammar.
- **Machine output**: `emit_kv` on FD 3 (`lib-quiet.sh`) — `PLAN_LINES`, `DIFF_LINES`, `HARD_TRIGGER_FIRED`, `TRIGGER_REASONS`. On validation failure only: `PLAN_SIZE_STATUS` is `missing-plan` or `missing-diff-lines`.
- **Exit codes**: **0** when the plan parses; **2** only when emitting `PLAN_SIZE_STATUS`; **3** on argv / usage errors.

## Plan-command validator

Plan-command validator runs unconditionally on both SIMPLE and HARD after each successful `ACTION=EMIT_PLAN` on `plan.txt` and once on `composed-plan.md` in Step 5c.

**Defect handling**: when machine output reports `VALIDATE_STATUS=defects-found`, use the shared **Fix-and-retry / Override / Cancel** AskUserQuestion body in `SKILL.md` (**### Plan command validator failure (shared)**).

## Internal — sketch dispatch (not public argv)

- `/design` sketch phase is inline-only (issue #2487): sketches, external collectors, synthesis, dialectic, and plan review run in the orchestrator session per `SKILL.md`. There is no Agent-tool offload path for the sketch phase.
- `brainstorm_requested` in `run-params.json`: boolean sibling to `partition_requested`; Step **1d.5** reads this field (default `false` when absent) instead of re-parsing argv after subshell boundaries.

## Legacy — `--branch-info` and `--step-prefix` (internal orchestration)

These are not public `/design` argv surfaces after issue #2485; they remain documented for older nested-call contracts and CI literals.

- `--branch-info <values>`: parse IS_MAIN, IS_USER_BRANCH, USER_PREFIX, CURRENT_BRANCH from space-separated KEY=VALUE pairs. Historical note: `/design` itself no longer creates a feature branch even when this legacy flag is passed; `/implement` owns the feature-branch lifecycle.
- `--step-prefix <prefix>`: encodes numeric prefix, textual breadcrumb path, and optional parent skill path using a `::` delimiter. See `${CLAUDE_PLUGIN_ROOT}/skills/shared/progress-reporting.md`.
