# Flag Reference

**Consumer**: `/design` argument parsing (loaded before Step 0 via the MANDATORY directive adjacent to the compact flag table in `SKILL.md`).

**Contract**: the normative allowlist for all `/design` public flags — validation rules, dispatch notes, and persistence conventions.

**When to load**: once at the top of `/design` invocation, before Step 0 executes, via the MANDATORY directive adjacent to the compact flag table. Do NOT load mid-flow; flag parsing runs once and the decisions are sticky.

**Binding convention**: `SKILL.md`'s compact flag table is a non-normative index — this file is authoritative for validation and internal dispatch notes.

---

## Public `/design` flags

Step 0-pre validation and positional classification are implemented by `skills/design/scripts/python/cli.py design parse-argv`; this file remains the normative allowlist source.

- `--no-dedup`: forward to `/larch:issue` on the verbal-create path. Default `false`.
- `--run-id <ID>`: optional stable run id. Default empty.
- `--partition` / `-p`: public boolean flag, default `false`. Semantics: when set, Step **2b.5** routes directly to the **Split-path** (decomposition panel) when no hard threshold fired — no Continue option, no threshold inspection. Hard plans still show the hard **Split/Cancel** prompt before entering Split-path automatically; `--partition` is the user-initiated override that fires the same path on small plans. The flag is persisted to `$DESIGN_TMPDIR/run-params.json` as `partition_requested` (boolean) via `python/cli.py session write-run-params` so Gate B and post-plan discussion re-entries read it from a fresh Bash subshell without re-parsing argv.
- `--brainstorm`: public boolean flag, default `false`. When set, Step **1d.5** runs after Round 1 discussion and before Step **1d.7** outline-approval (Gate A re-entry only post-plan) (see `references/brainstorm.md`). Persisted as `brainstorm_requested` (boolean) in `run-params.json` via `python/cli.py session write-run-params`.
- `--per-round-approval`: public boolean flag, default `false`. Controls Gate B (Step 3.5) finding-acceptance UX. Default (`approve_requested=false`): Gate B **auto-applies** every accepted in-scope finding with no `AskUserQuestion` (the old #2930 behavior; see `references/approval-gates.md` §Gate B). When set (`approve_requested=true`): Gate B restores the explicit per-round prompt (`Apply all` / `Go through each` / `Switch to discussion mode`) at every review round, so `Go through each` and `Switch to discussion mode` are reachable only under `--per-round-approval` (discussion otherwise remains reachable via Gate C `Discuss further`). Persisted as `approve_requested` (boolean) in `run-params.json` via `python/cli.py session write-run-params`. Independent of the size brakes and the validator auto-fix — those quality halts fire regardless of `--per-round-approval`.
- `--skip-approve` / `-s`: public boolean flag, default `false`. Auto-approves exactly two operator gates — Step **1d.7** outline-approval and Step **4b** Gate C final-plan approval — as if the operator chose "Approve". Does **not** skip or auto-answer any other prompt (Step 1c clarify, Step 1d round-1, degraded-tools gate, plan-size hard/drift brakes, validator escalation, dirty-tree recovery, decomposition panel, Gate B finding-apply). Persisted as `skip_approve_requested` (boolean) in `run-params.json` via `python/cli.py session write-run-params`. Compatible with `--per-round-approval` (both may appear together). `-s` is the short alias; its arm precedes the generic short-flag reject in the parser.
- `--approve`: **retired** — rejected as an unknown public flag before Step 0. Use `--per-round-approval` to restore the explicit per-round Gate B prompt, or `--skip-approve`/`-s` to auto-approve the outline and final plan.
- `--manual` / `-m`: removed. These flags are rejected as unknown public flags before Step 0. There is no persisted manual mode; Gate B auto-applies by default and `--per-round-approval` is the only way to restore the explicit per-round apply prompt.

`python/cli.py session write-run-params` writes schema v3 `run-params.json` with `partition_requested`, `brainstorm_requested`, `approve_requested`, and `skip_approve_requested` booleans. `skip_approve_requested` defaults to `false` and is read at Step 1d.7 and Step 4b Gate C.

**Positional tail**: after flags, either `^[0-9]+$` (existing issue) or verbal feature text (create issue via `/larch:issue` first). When the first positional token is all digits, that token becomes `POSITIONAL_VALUE` and parsing continues, so flags may appear on either side of the issue id (non-contiguous argv): valid flags after the issue id are honored and unknown/forbidden flags after it still error, rather than being silently dropped. Any later non-flag tokens are ignored. A non-digit first positional instead starts verbal feature text — flag parsing stops and the remainder is taken literally (see `python/design_argv.py`).

## Plan-size thresholds (Step 2b.5)

**Merged post-plan sites** (initial Step 2b, Gate B shared post-apply, discussion-round2 / Gate A after-discussion re-emit) call `python/cli.py design postplan-emit --with-plan-size`, which runs `python/cli.py plan check-size` internally and maps verdicts to thin-fence exit codes (`0`, `10`, `11`, `12`, `13`, `14`, `1`, `2`). **`python/cli.py plan check-size` remains standalone** for retained Step 2b.5 callers such as Override-after-defects and recovery paths.

**Site-aware hard prompts**: initial Step 2b and discussion paths use Split/Cancel only; retained Gate B paths use Split/Override/Cancel.

### `LARCH_DESIGN_DRIFT_MULTIPLE`

Default `2` (positive integer; invalid values fall back to `2`). `python/cli.py plan check-size` compares current plan lines and diff lines against `drift-baseline.env`; drift fires when the plan ratio **or** diff ratio exceeds the multiple. Merged `python/cli.py design postplan-emit --with-plan-size` records a logged advisory in `execution-issues.md` and exits `0` after hard-size and partition checks — drift no longer prompts or halts execution.

Merged fence pause-save preludes and `_postplan_rc=11` `exec` arms thread `${REPO:+--repo "$REPO"}`; `python/cli.py design postplan-emit` itself is not passed `--repo`.

Mechanical evaluation lives in `python/cli.py plan check-size` (sibling `check-plan-size.md`). Thresholds use **strict `>`** (800 lines does **not** trip the hard plan-body trigger; 801 does).

The historical **ownership-domains** sprawl heuristic from early design notes is **not** part of L1; it is intentionally omitted (Round 1 decision on issue #2670).

**Hard trigger** — any one suffices (no operator Continue override in the hard `AskUserQuestion`):

- Plan body line count **>** 800.
- `diff_added` trailer **>** 2000 when present in the final metadata block immediately above `diff_lines:`; otherwise legacy `diff_lines` trailer **>** 1500.
- Deletions (`diff_deleted`) never trip.
- `mechanical_churn: true` downgrades only the diff trigger to a soft advisory (`SOFT_ADVISORY`); plan-body hard triggers are unchanged.

**`--partition` / `-p` (Step 2b.5)**: when `partition_requested=true` in `run-params.json`, Step 2b.5 routes directly to the **Split-path** even if no hard threshold fired. That path runs the **real decomposition panel** (8 external slots via `python/cli.py agent dispatch-waterfall`). Full procedure, idempotent sentinels, and filing semantics live in `skills/design/references/decompose-panel.md`.

## Step 3 review env vars

Step 3 review is single-pass: each entry runs at most one plan-review panel. The Gate C review-run counter cap is **5**, and no env knob exists for the cap.

If the panel fails, Step 3 skips Gate B and proceeds to Step 3b, then the Step 3b completion boundary (FINALIZE + step-3b), then Step 4, then Gate C with the pre-review `plan.txt` unchanged.

## Helper output — `TRIGGER_REASONS`

The helper emits comma-separated reason tokens in **fixed priority order** `plan-body-lines`, then `diff-added` (new-style) or `diff-lines` (legacy) — the order hard thresholds are evaluated, **not** lexicographic.

## `python/cli.py plan check-size` contract (summary)

- **Input**: `$DESIGN_TMPDIR/plan.txt` (or `--plan-file`) with a **final non-empty** `diff_lines: <N>` trailer matching `emit-plan.sh` grammar. Optional trailers `diff_added:`, `diff_deleted:`, and `mechanical_churn:` MAY appear in the final contiguous metadata block immediately above `diff_lines:` (strict full-line regexes — see `check-plan-size.md`). Numeric legacy `mechanical_churn:` values normalize to `true`; drafters must still emit only `true` or `false`.
- **Machine output**: Python CLI machine output — `PLAN_LINES`, `DIFF_LINES`, `DIFF_ADDED`, `DIFF_DELETED`, `MECHANICAL_CHURN`, `SOFT_ADVISORY`, `SIZE_TRIGGER_FIRED`, `TRIGGER_REASONS` (see **Helper output** above). `PLAN_LINES` excludes recognized optional metadata trailers above final `diff_lines:`. On validation failure only: `PLAN_SIZE_STATUS` is `missing-plan` or `missing-diff-lines`.
- **Exit codes**: **0** when the plan parses; **2** only when emitting `PLAN_SIZE_STATUS` (`missing-plan` / `missing-diff-lines` / `invalid-mechanical-churn`); **3** on argv / usage errors (missing `--design-tmpdir`, unknown flags) — no `PLAN_SIZE_STATUS` lines.

## Plan-command validator

Post-plan validation for `plan.txt` is owned by `python/cli.py design postplan-emit` after each successful plan emit (initial Step 2b, Gate A re-entry, Gate B, and discussion-round2). Validation is unconditional: there is no quick-skip path and no force flag. Step 5c validates `composed-plan.md` through `python/cli.py design step5c`, which calls the publish tail in-process before redaction unless the operator has accepted the proceed-anyway path.

**Defect handling**: when machine output reports `VALIDATE_STATUS=defects-found`, use the shared auto-repair-then-escalate body in `SKILL.md` (**### Plan command validator failure (shared)**).

## Internal — planning dispatch (not public argv)

- **`/design` planning is inline-only** (issue #2487): sentinel prep, direct drafting, and plan review run in the orchestrator session per `SKILL.md`. There is no Agent-tool offload path for Step 2a sentinel prep.

- **`brainstorm_requested` in `run-params.json`**: boolean sibling to `partition_requested`; Step **1d.5** reads this field (default `false` when absent) instead of re-parsing argv after subshell boundaries.

## Legacy — `--branch-info` and `--step-prefix` (internal orchestration)

These are **not** public `/design` argv surfaces after issue #2485; they remain documented for older nested-call contracts and CI literals.

- `--branch-info <values>`: parse IS_MAIN, IS_USER_BRANCH, USER_PREFIX, CURRENT_BRANCH from space-separated KEY=VALUE pairs. **All 4 keys are required** when this internal flag is used. Values are safe for space-splitting (USER_PREFIX is sanitized by the pr create-branch derive_user_prefix logic; CURRENT_BRANCH cannot contain spaces). **Historical note**: `/design` itself no longer creates a feature branch even when this legacy flag is passed (the branch step has been removed; `/implement` owns the feature-branch lifecycle). The flag remains documented for orchestration-context propagation only.
- `--step-prefix <prefix>`: encodes numeric prefix, textual breadcrumb path, and optional parent skill path using a `::` delimiter — see `${CLAUDE_PLUGIN_ROOT}/skills/shared/step-prefix-encoding.md` for the full encoding spec.
