# Flag Reference

**Consumer**: `/design` argument parsing (loaded before Step 0 via the MANDATORY directive adjacent to the compact flag table in `SKILL.md`).

**Contract**: normative rules for **public** `/design` argv (`--trivial`, `--simple`, `--hard`, `--partition` / `-p`, `--no-dedup`, `--run-id`) plus **internal** orchestration tokens retained for nested hosts and CI harness pins.

**When to load**: once at the top of `/design` invocation, before Step 0 executes, via the MANDATORY directive adjacent to the compact flag table. Do NOT load mid-flow; flag parsing runs once and the decisions are sticky.

**Binding convention**: `SKILL.md`'s compact flag table is a non-normative index — this file is authoritative for validation, tier mapping, and internal dispatch notes.

---

## Public `/design` flags

- `--trivial`: mutually exclusive tier. Maps to `sketch_budget=0`, `quick_mode=true`, `review_budget=quick`, `workflow_path=SIMPLE` when writing `run-params.json` (the trivial doc-only carve-out follows the Step 0 router scan in `SKILL.md`).
- `--simple`: mutually exclusive tier. Maps to `sketch_budget=2`, `quick_mode=true`, `review_budget=full`, `workflow_path=SIMPLE` (2 sketch agents on the quick path per `sketch-launch.md`).
- `--hard`: mutually exclusive tier. Maps to `sketch_budget=4`, `quick_mode=false`, `review_budget=full`, `workflow_path=HARD`.
- `--no-dedup`: forward to `/larch:issue` on the verbal-create path. Default `false`.
- `--run-id <ID>`: optional stable run id. Default empty.
- `--partition` / `-p`: public boolean flag, default `false`. Mutually exclusive with `--trivial` (reject before `session-setup.sh` per `SKILL.md` Pre-Step-0 gate). Semantics: when no **hard** plan-size threshold fires at Step **2b.5**, treat a **soft** trigger as fired on every plan write so the orchestrator offers the break-up / continue flow — i.e. it **forces** the soft branch even when mechanical soft thresholds are all false. **Hard always wins**: if any hard threshold trips, Step 2b.5 uses the hard-only `AskUserQuestion` (Split / Cancel, no Continue) regardless of `--partition`. The flag is persisted to `$DESIGN_TMPDIR/run-params.json` as `partition_requested` (boolean) via `scripts/write-run-params.sh` so Gate B and post-plan discussion re-entries read it from a fresh Bash subshell without re-parsing argv.

**Mutual exclusion**: at most one of `--trivial` / `--simple` / `--hard` on argv; duplicate tier flags → hard error before Step 0. Additionally, `--trivial` and `-p`/`--partition` are mutually exclusive (same gate).

**Positional tail**: after flags, either `^[0-9]+$` (existing issue) or verbal feature text (create issue via `/larch:issue` first).

## Plan-size thresholds (Step 2b.5)

Mechanical evaluation lives in `skills/design/scripts/check-plan-size.sh` (sibling `check-plan-size.md`). Thresholds use **strict `>`** (250 lines does **not** trip the soft plan-body trigger; 251 does).

**Soft trigger** — any one suffices:

- Plan body line count **>** 250 (body = all lines except the final non-empty `diff_lines: <N>` trailer per `emit-plan.sh` grammar).
- `diff_lines` trailer **>** 600.
- Files-to-modify heading count **>** 8, counting lines matching `^###[[:space:]]+(NEW|UPDATED|REWRITTEN)[[:space:]]*:` (at least one ASCII whitespace after `###` before the keyword; aligned with the scout pattern in `scout-plan-archetypes-wrapper.sh`).
- **Semantic soft (orchestrator-only)** — after `check-plan-size.sh` returns **0** with all mechanical triggers false and without `--partition`, the main agent may still fire the same soft UI when the plan clearly packs multiple substantial independent workstreams under the numeric thresholds; procedure and precedence live in `SKILL.md` **Step 2b.5** (the helper does not evaluate this).

The historical **ownership-domains** sprawl heuristic from early design notes is **not** part of L1; it is intentionally omitted (Round 1 decision on issue #2670).

**Hard trigger** — any one suffices (no operator Continue override in the hard `AskUserQuestion`):

- Plan body line count **>** 800.
- `diff_lines` trailer **>** 1500.

There is **no** mechanical hard threshold on files-count alone.

## Helper output — `TRIGGER_REASONS`

The helper emits comma-separated reason tokens in **fixed priority order** `plan-body-lines`, `diff-lines`, `files-count` (the order thresholds are evaluated — **not** lexicographic). When the **only** cause of a soft offer is `--partition` (no mechanical soft crossings), the orchestrator may annotate user-visible copy with `trigger=partition-flag`; the helper does **not** emit that token. When the **only** cause is the Step **2b.5** semantic estimate, the orchestrator may use `trigger=semantic-estimate`; the helper does **not** emit that token either.

## Per-round velocity (deferred)

Between-review-round velocity (>20% plan growth **and** >10 accepted findings) is deferred to L3 / issue **#2672** and does **not** ship in L1. A best-effort gated tracking comment may reference this scope from `/design` issue **#2670** only; see `SKILL.md` Step **5d**.

## `check-plan-size.sh` contract (summary)

- **Input**: `$DESIGN_TMPDIR/plan.txt` (or `--plan-file`) with per-file `### NEW:` / `### UPDATED:` / `### REWRITTEN:` headings (at least one whitespace after `###` before the keyword; see regex above) and a **final non-empty** `diff_lines: <N>` trailer matching `emit-plan.sh` grammar.
- **Machine output**: `emit_kv` on FD 3 (`lib-quiet.sh`) — `PLAN_LINES`, `DIFF_LINES`, `FILES_COUNT`, `SOFT_TRIGGER_FIRED`, `HARD_TRIGGER_FIRED`, `TRIGGER_REASONS` (see **Helper output** above). On validation failure only: `PLAN_SIZE_STATUS` is `missing-plan` or `missing-diff-lines`.
- **Exit codes**: **0** when the plan parses; **2** only when emitting `PLAN_SIZE_STATUS` (`missing-plan` / `missing-diff-lines`); **3** on argv / usage errors (missing `--design-tmpdir`, unknown flags) — no `PLAN_SIZE_STATUS` lines.

## Internal — sketch dispatch (not public argv)

- **`/design` sketch phase is inline-only** (issue #2487): sketches, external collectors, synthesis, dialectic, and plan review run in the orchestrator session per `SKILL.md`. There is no Agent-tool offload path for the sketch phase.

## Legacy — `--branch-info` and `--step-prefix` (internal orchestration)

These are **not** public `/design` argv surfaces after issue #2485; they remain documented for older nested-call contracts and CI literals.

- `--branch-info <values>`: parse IS_MAIN, IS_USER_BRANCH, USER_PREFIX, CURRENT_BRANCH from space-separated KEY=VALUE pairs. **All 4 keys are required** when this internal flag is used. Values are safe for space-splitting (USER_PREFIX is sanitized by create-branch.sh derive_user_prefix; CURRENT_BRANCH cannot contain spaces). **Historical note**: `/design` itself no longer creates a feature branch even when this legacy flag is passed (the branch step has been removed; `/implement` owns the feature-branch lifecycle). The flag remains documented for orchestration-context propagation only.
- `--step-prefix <prefix>`: encodes numeric prefix, textual breadcrumb path, and optional parent skill path using a `::` delimiter — see `${CLAUDE_PLUGIN_ROOT}/skills/shared/progress-reporting.md` for the full encoding spec.
