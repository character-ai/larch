# Flag Reference

**Consumer**: `/design` argument parsing (loaded before Step 0 via the MANDATORY directive adjacent to the compact flag table in `SKILL.md`).

**Contract**: normative rules for **public** `/design` argv (`--hard`, `--partition` / `-p`, `--brainstorm`, `--approve`, `--no-dedup`, `--run-id`) plus **internal** orchestration tokens retained for nested hosts and CI harness pins.

**When to load**: once at the top of `/design` invocation, before Step 0 executes, via the MANDATORY directive adjacent to the compact flag table. Do NOT load mid-flow; flag parsing runs once and the decisions are sticky.

**Binding convention**: `SKILL.md`'s compact flag table is a non-normative index — this file is authoritative for validation, tier mapping, and internal dispatch notes.

---

## Public `/design` flags

Step 0-pre validation and positional classification are implemented by `skills/design/scripts/parse-design-argv.sh`; this file remains the normative allowlist and tier-mapping source.

**Tier**: SIMPLE is the default (no tier flag). `--hard` is the only public tier flag and maps to `design_classification=HARD`, `sketch_budget=4`, `workflow_path=HARD`. When `--hard` is absent, the orchestrator resolves `design_classification=SIMPLE`, `sketch_budget=0`, `workflow_path=SIMPLE` (no sketches; full plan-review panel per `SKILL.md` Step 2a).

- `--no-dedup`: forward to `/larch:issue` on the verbal-create path. Default `false`.
- `--run-id <ID>`: optional stable run id. Default empty.
- `--partition` / `-p`: public boolean flag, default `false`. Semantics: when set, Step **2b.5** routes directly to the **Split-path** (decomposition panel) when no hard threshold fired — no Continue option, no threshold inspection. Hard plans still show the hard **Split/Cancel** prompt before entering Split-path automatically; `--partition` is the user-initiated override that fires the same path on small plans. The flag is persisted to `$DESIGN_TMPDIR/run-params.json` as `partition_requested` (boolean) via `scripts/write-run-params.sh` so Gate B and post-plan discussion re-entries read it from a fresh Bash subshell without re-parsing argv.
- `--brainstorm`: public boolean flag, default `false`. When set, Step **1d.5** runs after Round 1 discussion and before Step **1d.7** outline-approval (Gate A re-entry only post-plan) (see `references/brainstorm.md`). Persisted as `brainstorm_requested` (boolean) in `run-params.json` via `scripts/write-run-params.sh`.
- `--approve`: public boolean flag, default `false`. Controls Gate B (Step 3.5) finding-acceptance UX. Default (`approve_requested=false`): Gate B **auto-applies** every accepted in-scope finding with no `AskUserQuestion` (the old #2930 behavior; see `references/approval-gates.md` §Gate B). When set (`approve_requested=true`): Gate B restores the explicit per-round prompt (`Apply all` / `Go through each` / `Switch to discussion mode`) at every review round, so `Go through each` and `Switch to discussion mode` are reachable only under `--approve` (discussion otherwise remains reachable via Gate C `Discuss further`). Persisted as `approve_requested` (boolean) in `run-params.json` via `scripts/write-run-params.sh`. Independent of the size brakes and the validator auto-fix — those quality halts fire regardless of `--approve`.
- `--manual` / `-m`: removed. These flags are rejected as unknown public flags before Step 0. There is no persisted manual mode; Gate B auto-applies by default and `--approve` is the only way to restore the explicit per-round apply prompt.

`scripts/write-run-params.sh` writes schema v3 `run-params.json`. In addition to the v2 boolean fields, it persists nullable `design_classification_reason`, `design_classification_source`, `sketch_budget`, and `workflow_path` fields for Step 2 and Step 3 rehydration.

**Mutual exclusion**: at most one `--hard` and at most one `--approve` on argv; duplicate `--hard` or duplicate `--approve` → hard error before Step 0. Any unrecognized or disallowed leading public `--` flag → hard error before Step 0 (never swallowed as positional/verbal feature text). `--manual` / `-m` are no longer public flags.

**Positional tail**: after flags, either `^[0-9]+$` (existing issue) or verbal feature text (create issue via `/larch:issue` first). When the first positional token is all digits, only that token becomes `POSITIONAL_VALUE`; any later tokens are ignored (see `parse-design-argv.md`).

## Plan-size thresholds (Step 2b.5)

**Merged post-plan sites** (initial Step 2b, Gate B shared post-apply, discussion-round2 / Gate A after-discussion re-emit) call `design-postplan-emit.sh --with-plan-size`, which runs `check-plan-size.sh` internally and maps verdicts to thin-fence exit codes (`0`, `10`, `11`, `12`, `13`, `14`, `1`, `2`). **`check-plan-size.sh` remains standalone** for retained Step 2b.5 callers such as Override-after-defects and recovery paths.

**Site-aware hard prompts**: initial Step 2b and discussion paths use Split/Cancel only; retained Gate B paths use Split/Override/Cancel.

### `LARCH_DESIGN_DRIFT_MULTIPLE`

Default `2` (positive integer; invalid values fall back to `2`). `check-plan-size.sh` compares current plan lines and diff lines against `drift-baseline.env`; drift fires when the plan ratio **or** diff ratio exceeds the multiple. Merged `design-postplan-emit.sh --with-plan-size` maps drift to exit code `14` after hard-size and partition checks.

Merged fence pause-save preludes and `_postplan_rc=11` `exec` arms thread `${REPO:+--repo "$REPO"}`; `design-postplan-emit.sh` itself is not passed `--repo`.

Mechanical evaluation lives in `skills/design/scripts/check-plan-size.sh` (sibling `check-plan-size.md`). Thresholds use **strict `>`** (800 lines does **not** trip the hard plan-body trigger; 801 does).

The historical **ownership-domains** sprawl heuristic from early design notes is **not** part of L1; it is intentionally omitted (Round 1 decision on issue #2670).

**Hard trigger** — any one suffices (no operator Continue override in the hard `AskUserQuestion`):

- Plan body line count **>** 800.
- `diff_added` trailer **>** 2000 when present in the final metadata block immediately above `diff_lines:`; otherwise legacy `diff_lines` trailer **>** 1500.
- Deletions (`diff_deleted`) never trip.
- `mechanical_churn: true` downgrades only the diff trigger to a soft advisory (`SOFT_ADVISORY`); plan-body hard triggers are unchanged.

**`--partition` / `-p` (Step 2b.5)**: when `partition_requested=true` in `run-params.json`, Step 2b.5 routes directly to the **Split-path** even if no hard threshold fired. That path runs the **real decomposition panel** (8 external slots via `scripts/dispatch-with-waterfall.sh`). Full procedure, idempotent sentinels, and filing semantics live in `skills/design/references/decompose-panel.md`.

## Step 3 review env vars

Normative argv validation lives in `skills/design/scripts/plan-review-loop.sh` (`--round-cap` only). SKILL.md Step 3 (via `run-step3-review.sh`) passes `"${LARCH_DESIGN_ROUND_CAP:-5}"` when the env var is unset or empty. Invalid explicit values cause `plan-review-loop.sh` argv validation to fail before any review round launches. Step 3 normalizes that failure to the `panel-failed` branch, skips Gate B, and proceeds to Step 3b, then the Step 3b completion boundary (FINALIZE + step-3b), then Step 4, then Gate C with the pre-review `plan.txt` unchanged. There is no silent fallback or clamping. See `docs/configuration-and-permissions.md` § Environment Variables.

| Variable | Default (unset/empty) | Invalid explicit values | Semantics |
|---|---|---|---|
| `LARCH_DESIGN_ROUND_CAP` | `5` | Non-numeric or non-positive → `plan-review-loop.sh` argv validation exit `2`; Step 3 surfaces `panel-failed` and continues at Step 3b, then the Step 3b completion boundary (FINALIZE + step-3b), then Step 4, then Gate C (Gate B skipped) | Deprecated inner-loop cap; accepted and validated for compatibility, but Step 3 review is single-pass. The Step 3 **review-run counter** (tier-derived cap: SIMPLE = `3`, HARD = `5`) limits Gate C re-entries separately. |

## Helper output — `TRIGGER_REASONS`

The helper emits comma-separated reason tokens in **fixed priority order** `plan-body-lines`, then `diff-added` (new-style) or `diff-lines` (legacy) — the order hard thresholds are evaluated, **not** lexicographic.

## `check-plan-size.sh` contract (summary)

- **Input**: `$DESIGN_TMPDIR/plan.txt` (or `--plan-file`) with a **final non-empty** `diff_lines: <N>` trailer matching `emit-plan.sh` grammar. Optional trailers `diff_added:`, `diff_deleted:`, and `mechanical_churn:` MAY appear in the final contiguous metadata block immediately above `diff_lines:` (strict full-line regexes — see `check-plan-size.md`).
- **Machine output**: `emit_kv` on FD 3 (`lib-quiet.sh`) — `PLAN_LINES`, `DIFF_LINES`, `DIFF_ADDED`, `DIFF_DELETED`, `MECHANICAL_CHURN`, `SOFT_ADVISORY`, `HARD_TRIGGER_FIRED`, `TRIGGER_REASONS` (see **Helper output** above). `PLAN_LINES` excludes recognized optional metadata trailers above final `diff_lines:`. On validation failure only: `PLAN_SIZE_STATUS` is `missing-plan` or `missing-diff-lines`.
- **Exit codes**: **0** when the plan parses; **2** only when emitting `PLAN_SIZE_STATUS` (`missing-plan` / `missing-diff-lines`); **3** on argv / usage errors (missing `--design-tmpdir`, unknown flags) — no `PLAN_SIZE_STATUS` lines.

## Plan-command validator

Post-plan validation for `plan.txt` is owned by `design-postplan-emit.sh` after each successful plan emit (initial Step 2b, Gate A re-entry, Gate B, and discussion-round2). Validation is unconditional: there is no quick-skip path and no force flag. Step 5c validates `composed-plan.md` inside `design-publish.sh` before redaction unless the operator has accepted the proceed-anyway path.

**Defect handling**: when machine output reports `VALIDATE_STATUS=defects-found`, use the shared auto-repair-then-escalate body in `SKILL.md` (**### Plan command validator failure (shared)**).

## Internal — sketch dispatch (not public argv)

- **`/design` sketch phase is inline-only** (issue #2487): sketches, external collectors, synthesis, dialectic, and plan review run in the orchestrator session per `SKILL.md`. There is no Agent-tool offload path for the sketch phase.

- **`brainstorm_requested` in `run-params.json`**: boolean sibling to `partition_requested`; Step **1d.5** reads this field (default `false` when absent) instead of re-parsing argv after subshell boundaries.

## Legacy — `--branch-info` and `--step-prefix` (internal orchestration)

These are **not** public `/design` argv surfaces after issue #2485; they remain documented for older nested-call contracts and CI literals.

- `--branch-info <values>`: parse IS_MAIN, IS_USER_BRANCH, USER_PREFIX, CURRENT_BRANCH from space-separated KEY=VALUE pairs. **All 4 keys are required** when this internal flag is used. Values are safe for space-splitting (USER_PREFIX is sanitized by create-branch.sh derive_user_prefix; CURRENT_BRANCH cannot contain spaces). **Historical note**: `/design` itself no longer creates a feature branch even when this legacy flag is passed (the branch step has been removed; `/implement` owns the feature-branch lifecycle). The flag remains documented for orchestration-context propagation only.
- `--step-prefix <prefix>`: encodes numeric prefix, textual breadcrumb path, and optional parent skill path using a `::` delimiter — see `${CLAUDE_PLUGIN_ROOT}/skills/shared/progress-reporting.md` for the full encoding spec.
