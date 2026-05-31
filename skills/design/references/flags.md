# Flag Reference

**Consumer**: `/design` argument parsing (loaded before Step 0 via the MANDATORY directive adjacent to the compact flag table in `SKILL.md`).

**Contract**: normative rules for **public** `/design` argv (`--hard`, `--partition` / `-p`, `--brainstorm`, `--manual` / `-m`, `--no-dedup`, `--run-id`) plus **internal** orchestration tokens retained for nested hosts and CI harness pins.

**When to load**: once at the top of `/design` invocation, before Step 0 executes, via the MANDATORY directive adjacent to the compact flag table. Do NOT load mid-flow; flag parsing runs once and the decisions are sticky.

**Binding convention**: `SKILL.md`'s compact flag table is a non-normative index — this file is authoritative for validation, tier mapping, and internal dispatch notes.

---

## Public `/design` flags

**Tier**: SIMPLE is the default (no tier flag). `--hard` is the only public tier flag and maps to `design_classification=HARD`, `sketch_budget=4`, `review_budget=full`, `workflow_path=HARD`. When `--hard` is absent, the orchestrator resolves `design_classification=SIMPLE`, `sketch_budget=0`, `review_budget=full`, `workflow_path=SIMPLE` (no sketches; full plan-review panel per `SKILL.md` Step 2a).

- `--no-dedup`: forward to `/larch:issue` on the verbal-create path. Default `false`.
- `--run-id <ID>`: optional stable run id. Default empty.
- `--partition` / `-p`: public boolean flag, default `false`. Semantics: when set, Step **2b.5** routes directly to the **Split-path** (decomposition panel) when no hard threshold fired — no Continue option, no threshold inspection. Hard triggers still show the hard **Split/Override/Cancel** prompt: Split enters Split-path, Override records the strongly discouraged escape hatch and continues the surrounding review flow, and Cancel exits. `--partition` is the user-initiated override that fires Split-path on small plans; it cannot auto-downgrade a hard trigger. The flag is persisted to `$DESIGN_TMPDIR/run-params.json` as `partition_requested` (boolean) via `scripts/write-run-params.sh` so Gate B and post-plan discussion re-entries read it from a fresh Bash subshell without re-parsing argv.
- `--brainstorm`: public boolean flag, default `false`. When set, Step **1d.5** runs after Round 1 discussion and before Step **1d.7** outline-approval (Gate A re-entry only post-plan) (see `references/brainstorm.md`). Persisted as `brainstorm_requested` (boolean) in `run-params.json` via `scripts/write-run-params.sh`.
- `--manual` / `-m`: public boolean flag, default `false`. When set, restores today's Gate B 3-option `AskUserQuestion` (Apply all / Go through each / Switch to discussion mode) on every Gate B entry. Default (`false`) makes Gate B auto-apply every accepted finding to `$DESIGN_TMPDIR/plan.txt` after printing a compact findings list. Persisted as `manual_gate_b` (boolean) in `run-params.json` via `scripts/write-run-params.sh`. Scope: Gate B only — Gate A (Step 1e) discussion sub-rounds and Gate C (Step 4b) final approval are unchanged in both modes. Whole-run sticky: parsed once at argv, read on every Gate B entry including Step 3 re-entries from Gate C(c) "Re-run review panel". Independent of all tier/partition/brainstorm flags (no mutual exclusion).

`scripts/write-run-params.sh` writes schema v3 `run-params.json`. In addition to the v2 boolean fields, it persists nullable `design_classification_reason`, `design_classification_source`, `sketch_budget`, `review_budget`, and `workflow_path` fields for Step 2 and Step 3 rehydration.

**Mutual exclusion**: at most one `--hard` on argv; duplicate `--hard` → hard error before Step 0. Any unrecognized or disallowed leading public `--` flag → hard error before Step 0 (never swallowed as positional/verbal feature text). `--manual` / `-m` is independent of all other public flags.

**Positional tail**: after flags, either `^[0-9]+$` (existing issue) or verbal feature text (create issue via `/larch:issue` first).

## Plan-size thresholds (Step 2b.5)

Mechanical evaluation lives in `skills/design/scripts/check-plan-size.sh` (sibling `check-plan-size.md`). Thresholds use **strict `>`** (800 lines does **not** trip the hard plan-body trigger; 801 does).

The historical **ownership-domains** sprawl heuristic from early design notes is **not** part of L1; it is intentionally omitted (Round 1 decision on issue #2670).

**Hard trigger** — any one suffices (explicit, strongly-discouraged Override-and-proceed escape hatch in the hard `AskUserQuestion`; `--partition` still cannot auto-downgrade a hard trigger):

- Plan body line count **>** 800.
- `diff_added` trailer **>** 2000 when present in the final metadata block immediately above `diff_lines:`; otherwise legacy `diff_lines` trailer **>** 1500.
- Deletions (`diff_deleted`) never trip.
- `mechanical_churn: true` downgrades only the diff trigger to a soft advisory (`SOFT_ADVISORY`); plan-body hard triggers are unchanged.

**`--partition` / `-p` (Step 2b.5)**: when `partition_requested=true` in `run-params.json`, Step 2b.5 routes directly to the **Split-path** even if no hard threshold fired. That path runs the **real decomposition panel** (8 external slots via `scripts/dispatch-with-waterfall.sh`). Full procedure, idempotent sentinels, and filing semantics live in `skills/design/references/decompose-panel.md`.

## Multi-round loop env vars

Normative argv validation lives in `skills/design/scripts/plan-review-loop.sh` (`--round-cap`, `--convergence-threshold`). SKILL.md Step 3 passes `"${LARCH_DESIGN_ROUND_CAP:-5}"` and `"${LARCH_DESIGN_CONVERGENCE_THRESHOLD:-3}"` when the env vars are unset or empty. Invalid explicit values cause `plan-review-loop.sh` argv validation to fail before any review round launches. Step 3 normalizes that failure to the `panel-failed` branch, skips Gate B, and proceeds to Step 3b / Step 4 / Gate C with the pre-review `plan.txt` unchanged. There is no silent fallback or clamping. See `docs/configuration-and-permissions.md` § Environment Variables.

| Variable | Default (unset/empty) | Invalid explicit values | Semantics |
|---|---|---|---|
| `LARCH_DESIGN_ROUND_CAP` | `5` | Non-numeric or non-positive → `plan-review-loop.sh` argv validation exit `2`; Step 3 surfaces `panel-failed` and continues at Step 3b (Gate B skipped) | Upper bound on **inner** plan-review rounds inside one Step 3 `plan-review-loop.sh` invocation. The Step 3 **review-run counter** (tier-derived cap: SIMPLE = `3`, HARD = `5`) limits Gate C re-entries separately — `LARCH_DESIGN_ROUND_CAP` is **not** clamped against that tier cap; the two layers compose. |
| `LARCH_DESIGN_CONVERGENCE_THRESHOLD` | `3` | Non-numeric or negative → `plan-review-loop.sh` argv validation exit `2`; Step 3 surfaces `panel-failed` and continues at Step 3b (Gate B skipped) | Per-round `ACCEPTED_COUNT` bound that, combined with zero `IMPORTANT_ACCEPTED_COUNT` across two consecutive non-degraded rounds, triggers convergence. |

## Helper output — `TRIGGER_REASONS`

The helper emits comma-separated reason tokens in **fixed priority order** `plan-body-lines`, then `diff-added` (new-style) or `diff-lines` (legacy) — the order hard thresholds are evaluated, **not** lexicographic.

## Per-round velocity (deferred)

Between-review-round velocity (>20% plan growth **and** >10 accepted findings) is deferred to L3 / issue **#2672** and does **not** ship in L1. A best-effort gated tracking comment may reference this scope from `/design` issue **#2670** only; see `SKILL.md` Step **5d**.

## `check-plan-size.sh` contract (summary)

- **Input**: `$DESIGN_TMPDIR/plan.txt` (or `--plan-file`) with a **final non-empty** `diff_lines: <N>` trailer matching `emit-plan.sh` grammar. Optional trailers `diff_added:`, `diff_deleted:`, and `mechanical_churn:` MAY appear in the final contiguous metadata block immediately above `diff_lines:` (strict full-line regexes — see `check-plan-size.md`).
- **Machine output**: `emit_kv` on FD 3 (`lib-quiet.sh`) — `PLAN_LINES`, `DIFF_LINES`, `DIFF_ADDED`, `DIFF_DELETED`, `MECHANICAL_CHURN`, `SOFT_ADVISORY`, `HARD_TRIGGER_FIRED`, `TRIGGER_REASONS` (see **Helper output** above). `PLAN_LINES` excludes recognized optional metadata trailers above final `diff_lines:`. On validation failure only: `PLAN_SIZE_STATUS` is `missing-plan` or `missing-diff-lines`.
- **Exit codes**: **0** when the plan parses; **2** only when emitting `PLAN_SIZE_STATUS` (`missing-plan` / `missing-diff-lines`); **3** on argv / usage errors (missing `--design-tmpdir`, unknown flags) — no `PLAN_SIZE_STATUS` lines.

## Plan-command validator

Plan-command validator runs unconditionally on both SIMPLE and HARD after each successful `ACTION=EMIT_PLAN` on `plan.txt` and once on `composed-plan.md` in Step 5c.

**Defect handling**: when machine output reports `VALIDATE_STATUS=defects-found`, use the shared **Fix-and-retry / Override / Cancel** AskUserQuestion body in `SKILL.md` (**### Plan command validator failure (shared)**).

## Internal — sketch dispatch (not public argv)

- **`/design` sketch phase is inline-only** (issue #2487): sketches, external collectors, synthesis, dialectic, and plan review run in the orchestrator session per `SKILL.md`. There is no Agent-tool offload path for the sketch phase.

- **`brainstorm_requested` in `run-params.json`**: boolean sibling to `partition_requested`; Step **1d.5** reads this field (default `false` when absent) instead of re-parsing argv after subshell boundaries.

## Legacy — `--branch-info` and `--step-prefix` (internal orchestration)

These are **not** public `/design` argv surfaces after issue #2485; they remain documented for older nested-call contracts and CI literals.

- `--branch-info <values>`: parse IS_MAIN, IS_USER_BRANCH, USER_PREFIX, CURRENT_BRANCH from space-separated KEY=VALUE pairs. **All 4 keys are required** when this internal flag is used. Values are safe for space-splitting (USER_PREFIX is sanitized by create-branch.sh derive_user_prefix; CURRENT_BRANCH cannot contain spaces). **Historical note**: `/design` itself no longer creates a feature branch even when this legacy flag is passed (the branch step has been removed; `/implement` owns the feature-branch lifecycle). The flag remains documented for orchestration-context propagation only.
- `--step-prefix <prefix>`: encodes numeric prefix, textual breadcrumb path, and optional parent skill path using a `::` delimiter — see `${CLAUDE_PLUGIN_ROOT}/skills/shared/progress-reporting.md` for the full encoding spec.
