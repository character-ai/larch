# Flag Reference

**Consumer**: `/design` argument parsing, loaded before Step 0 by the MANDATORY directive next to the compact flag table in `SKILL.md`.

**Contract**: normative `/design` flag allowlist: validation, dispatch, persistence.

**When to load**: once at invocation start, before Step 0. Do NOT load mid-flow; parsing is one shot, sticky.

**Binding convention**: `SKILL.md`'s compact flag table is a non-normative index. This file is authoritative for validation and dispatch.

---

## Public `/design` flags

Step 0-pre validation and positional classification use `skills/design/scripts/python/cli.py design parse-argv`; this is normative.

- `--no-dedup`: forward to `/larch:issue` on verbal-create path. Default `false`.
- `--run-id <ID>`: stable run id. Default empty.
- `--partition` / `-p`: default `false`. Step **2b.5** goes straight to **Split-path** when no hard threshold fired: no Continue option or threshold inspection. Hard plans still show **Split/Cancel** before automatic Split-path entry; `--partition` gives small plans the same override. Persist as `partition_requested` (boolean) in `$DESIGN_TMPDIR/run-params.json` for later re-entries.
- `--brainstorm`: default `false`. Step **1d.5** runs after Round 1 discussion and before Step **1d.7** outline-approval (Gate A re-entry only post-plan). Persist as `brainstorm_requested` (boolean).
- `--per-round-approval`: default `false`. Controls Gate B (Step 3.5). Default (`approve_requested=false`): Gate B **auto-applies** accepted in-scope findings with no `AskUserQuestion`. Set (`approve_requested=true`): Gate B asks `Apply all` / `Go through each` / `Switch to discussion mode` each review round. The latter two choices are reachable only here; discussion otherwise remains via Gate C `Discuss further`. Persist as `approve_requested` (boolean). Size brakes and validator auto-fix still run.
- `--skip-approve` / `-s`: default `false`. Auto-approves only Step **1d.7** outline-approval and Step **4b** Gate C final-plan approval as if the operator chose "Approve". It does **not** skip or answer Step 1c clarify, Step 1d round-1, degraded-tools gate, plan-size hard/drift brakes, validator escalation, dirty-tree recovery, decomposition panel, or Gate B finding-apply. Persist as `skip_approve_requested` (boolean) in `run-params.json`. Compatible with `--per-round-approval`. `-s` is the short alias and is parsed before generic short-flag rejection.
- `--approve`: **retired**. Rejected before Step 0. Use `--per-round-approval` for explicit per-round Gate B, or `--skip-approve`/`-s` for outline and final-plan auto-approval.
- `--manual` / `-m`: removed. Rejected before Step 0. No manual mode is persisted; Gate B auto-applies by default, and only `--per-round-approval` restores explicit per-round apply.

`python/cli.py session write-run-params` writes schema v3 `run-params.json` with `partition_requested`, `brainstorm_requested`, `approve_requested`, and `skip_approve_requested` booleans. `skip_approve_requested` defaults to `false` and gates Step 1d.7 and Step 4b Gate C.

**Positional tail**: after flags, argv is `^[0-9]+$` (existing issue) or verbal feature text (create issue via `/larch:issue` first). An all-digit first positional becomes `POSITIONAL_VALUE`; parsing continues, so valid flags on either side of the issue id are honored and unknown/forbidden trailing flags still error. Later non-flag tokens after an issue id are ignored. A non-digit first positional stops flag parsing and starts literal verbal text. `--` stops flag parsing: the next all-digit token becomes the issue id; otherwise the rest becomes literal verbal text. See `python/larch/design/design_argv.py`.

## Plan-size thresholds (Step 2b.5)

**Merged post-plan sites** (initial Step 2b, Gate B shared post-apply, discussion-round2 / Gate A after-discussion re-emit) call `python/cli.py design postplan-emit --with-plan-size`. It runs `python/cli.py plan check-size` and maps verdicts to thin-fence exit codes (`0`, `10`, `11`, `12`, `13`, `14`, `1`, `2`). **`python/cli.py plan check-size` remains standalone** for retained Step 2b.5 paths.

**Site-aware hard prompts**: initial Step 2b and discussion paths use Split/Cancel; retained Gate B paths use Split/Override/Cancel.

### `LARCH_DESIGN_DRIFT_MULTIPLE`

Default `2` (positive integer; invalid values fall back to `2`). `python/cli.py plan check-size` compares current plan and diff lines with `drift-baseline.env`; drift fires when either ratio exceeds the multiple. Merged `python/cli.py design postplan-emit --with-plan-size` logs to `execution-issues.md` and exits `0` after hard-size and partition checks; drift no longer prompts or halts.

Merged fence pause-save preludes and `_postplan_rc=11` `exec` arms thread `${REPO:+--repo "$REPO"}`; `python/cli.py design postplan-emit` is not passed `--repo`.

Mechanical evaluation lives in `python/cli.py plan check-size` (sibling `check-plan-size.md`). Thresholds use **strict `>`**: 800 lines does **not** trip; 801 does.

The historical **ownership-domains** sprawl heuristic is **not** part of L1; it is intentionally omitted (Round 1 decision on issue #2670).

**Hard trigger**: any one suffices. No operator Continue override exists in the hard `AskUserQuestion`.

- Plan body line count **>** 800.
- `diff_added` trailer **>** 2000 when present in the final metadata block immediately above `diff_lines:`; otherwise legacy `diff_lines` trailer **>** 1500.
- Deletions (`diff_deleted`) never trip.
- `mechanical_churn: true` downgrades only the diff trigger to a soft advisory (`SOFT_ADVISORY`); plan-body hard triggers are unchanged.

**`--partition` / `-p` (Step 2b.5)**: when `partition_requested=true` in `run-params.json`, Step 2b.5 routes directly to **Split-path** even if no hard threshold fired. That path runs the real decomposition panel via `python/cli.py agent dispatch-waterfall`; procedure and filing semantics live in `skills/design/references/decompose-panel.md`.

## Step 3 review env vars

Step 3 review is single-pass: each entry runs at most one plan-review panel. The Gate C review-run counter cap is **5**, and no env knob exists for the cap.

If the panel fails, Step 3 skips Gate B and proceeds to Step 3b, the Step 3b completion boundary (FINALIZE + step-3b), Step 4, and Gate C with pre-review `plan.txt` unchanged.

## Helper output — `TRIGGER_REASONS`

The helper emits comma-separated reason tokens in fixed priority order: `plan-body-lines`, then `diff-added` (new-style) or `diff-lines` (legacy). This is threshold order, **not** lexicographic.

## `python/cli.py plan check-size` contract (summary)

- **Input**: `$DESIGN_TMPDIR/plan.txt` (or `--plan-file`) with a **final non-empty** `diff_lines: <N>` trailer matching `emit-plan.sh` grammar. Optional `diff_added:`, `diff_deleted:`, and `mechanical_churn:` trailers MAY appear in the final contiguous metadata block above `diff_lines:` (strict full-line regexes; see `check-plan-size.md`). Numeric legacy `mechanical_churn:` values normalize to `true`; drafters emit only `true` or `false`.
- **Machine output**: `PLAN_LINES`, `DIFF_LINES`, `DIFF_ADDED`, `DIFF_DELETED`, `MECHANICAL_CHURN`, `SOFT_ADVISORY`, `SIZE_TRIGGER_FIRED`, `TRIGGER_REASONS` (see **Helper output** above). `PLAN_LINES` excludes recognized optional metadata trailers above final `diff_lines:`. On validation failure only: `PLAN_SIZE_STATUS=missing-plan` or `missing-diff-lines`.
- **Exit codes**: **0** when the plan parses; **2** only with `PLAN_SIZE_STATUS` (`missing-plan` / `missing-diff-lines` / `invalid-mechanical-churn`); **3** on argv / usage errors (missing `--design-tmpdir`, unknown flags). Exit **3** emits no `PLAN_SIZE_STATUS`.

## Plan-command validator

Post-plan validation for `plan.txt` is owned by `python/cli.py design postplan-emit` after each successful plan emit: initial Step 2b, Gate A re-entry, Gate B, and discussion-round2. Validation is unconditional; no quick-skip path or force flag exists. Step 5c validates `composed-plan.md` through `python/cli.py design step5c`, which calls the publish tail in-process before redaction unless the operator accepted proceed-anyway.

**Defect handling**: when machine output reports `VALIDATE_STATUS=defects-found`, use the shared auto-repair-then-escalate body in `SKILL.md` (**### Plan command validator failure (shared)**).

## Internal — planning dispatch (not public argv)

- **`/design` planning is inline-only** (issue #2487): sentinel prep, direct drafting, and plan review run in the orchestrator session per `SKILL.md`. Step 2a sentinel prep has no Agent-tool offload path.
- **`brainstorm_requested` in `run-params.json`**: boolean sibling to `partition_requested`; Step **1d.5** reads this field (default `false` when absent), avoiding argv re-parse after subshell boundaries.

## Legacy — `--branch-info` and `--step-prefix` (internal orchestration)

These are **not** public `/design` argv surfaces after issue #2485; they remain documented for older nested-call contracts and CI literals. `--hard` is also rejected as an unknown public flag before Step 0.

- `--branch-info <values>`: parse IS_MAIN, IS_USER_BRANCH, USER_PREFIX, CURRENT_BRANCH from space-separated KEY=VALUE pairs. All listed keys are required. Values are safe for splitting: USER_PREFIX is sanitized by pr create-branch `derive_user_prefix`, and CURRENT_BRANCH cannot contain spaces. **Historical note**: `/design` no longer creates a feature branch for this legacy flag; `/implement` owns that lifecycle. The flag remains for orchestration-context propagation only.
- `--step-prefix <prefix>`: encodes numeric prefix, textual breadcrumb path, and optional parent skill path using a `::` delimiter. See `${CLAUDE_PLUGIN_ROOT}/skills/shared/step-prefix-encoding.md` for the full encoding spec.
