## Plan

# Plan — Remove `/design` soft plan-size triggers and `FILES_COUNT` factor

## Goal

Eliminate `/design` Step 2b.5 soft-trigger machinery entirely (mechanical soft thresholds + semantic-soft estimate + soft `AskUserQuestion`) and remove `FILES_COUNT` as a tracked metric. Keep only hard triggers (`PLAN_LINES > 800` OR `DIFF_LINES > 1500`). The `--partition` / `-p` flag stays but now routes directly to Split-path (decomposition panel) with no threshold check.

Rationale: soft prompts have produced zero accepted-Split outcomes in practice and create friction on every plan write; `FILES_COUNT > 8` is also a false-positive driver (a plan touching 9 small files is not architecturally large).

## Files to modify/create

### UPDATED: `skills/design/scripts/check-plan-size.sh`

Rewrite mechanical evaluation to hard-only.

- Remove the `FILES_COUNT=$(grep -cE ...)` computation line.
- Remove `soft_plan`, `soft_diff`, `soft_files`, `soft_trigger` variables and the entire soft-trigger evaluation block (lines ~90-101, ~108-113 in current source).
- Keep `hard_plan` / `hard_diff` / `hard_trigger` exactly as today (no `FILES_COUNT` was ever in hard logic).
- Simplify `reasons` array: only `plan-body-lines` and `diff-lines` participate, only appended when the corresponding hard threshold tripped. Remove the `files-count` branch.
- Remove `emit_kv SOFT_TRIGGER_FIRED ...` (all three sites in the if/else).
- Remove `emit_kv FILES_COUNT ...`.
- Keep `emit_kv HARD_TRIGGER_FIRED`, `emit_kv TRIGGER_REASONS`, `emit_kv PLAN_LINES`, `emit_kv DIFF_LINES`. Exit codes (0/2/3) and `PLAN_SIZE_STATUS` semantics unchanged.

### UPDATED: `skills/design/scripts/check-plan-size.md`

- Drop the `Files count (FILES_COUNT)` bullet from **Input contract**.
- Remove `FILES_COUNT` and `SOFT_TRIGGER_FIRED` rows from the **Output contract** table.
- Update `TRIGGER_REASONS` row: fixed priority is now `plan-body-lines`, `diff-lines` only (no `files-count`); reasons list only appears when `HARD_TRIGGER_FIRED=true`.
- Update **Strict `>` boundary semantics** line: only 800/1500 hard remain. Drop the 250/600/8 soft mention.
- Remove the **Hard precedence** paragraph — no soft to be precedence-over.
- Trim **Edit in sync** sentence: still includes `test-check-plan-size.sh`, `test-check-plan-size.md`, the `Makefile` target, `skills/design/references/flags.md`, and `skills/design/SKILL.md` Step 2b.5.

### UPDATED: `skills/design/scripts/test-check-plan-size.sh`

Remove every soft-trigger-only test case; keep hard cases and parsing/error cases. Net result: ~10 cases instead of 18.

- Remove Cases 2 (plan-body soft), 3 (diff soft), 4 (files soft).
- Remove Case 5 (multiple soft).
- Case 8 (hard + soft dimensions): rewrite to assert only hard precedence (`HARD_TRIGGER_FIRED=true`) and `TRIGGER_REASONS=plan-body-lines` (the diff threshold at 700 does not cross hard `>1500`, and `files-count` is gone).
- Case 11: drop sub-cases 11a (250 boundary plan), 11b (600 boundary diff), 11b2 (diff zero), 11c (8 boundary files), keep 11d (800 boundary plan, no hard) and 11e (1500 boundary diff, no hard).
- Case 12 (zero headings): remove `assert_kv_eq FILES_COUNT 0`; keep the `run_ok` invocation to prove no `set -e` regression.
- Case 14 (whitespace-tolerant headings): remove `assert_kv_eq FILES_COUNT 2`. The case loses its only assertion; delete the whole case (the heading-counting code is gone).
- Case 16 (`###NEW:` without whitespace): remove `assert_kv_eq FILES_COUNT 5`. Delete the whole case for the same reason.
- Case 18 (`--plan-file` override): drop the heading lines; keep `PLAN_LINES` and a kept hard or no-trigger assertion.
- Case 1 (no triggers): remove `assert_kv_eq FILES_COUNT 5`; keep the SOFT/HARD/REASONS assertions but change the SOFT one — since `SOFT_TRIGGER_FIRED` is no longer emitted, replace with a negative check that `grep -q '^SOFT_TRIGGER_FIRED=' "$out"` finds nothing.
- Add one new case proving `FILES_COUNT` is **not** emitted on a plan with 10 file headings (regression guard).
- Remove all remaining `assert_kv_eq SOFT_TRIGGER_FIRED ...` lines. Add explicit "not emitted" assertions for both `SOFT_TRIGGER_FIRED` and `FILES_COUNT` in at least one happy-path case.

### UPDATED: `skills/design/scripts/test-check-plan-size.md`

Update the **Cases exercised** list to reflect the kept cases. Remove entries 2, 3, 4, 5, 11a-c, plus the FILES_COUNT mention in 12, 13, 15, 16. Add a new bullet documenting the negative-assertion regression case for `SOFT_TRIGGER_FIRED` / `FILES_COUNT` non-emission.

### UPDATED: `skills/design/references/flags.md`

Rewrite the **Plan-size thresholds (Step 2b.5)** section.

- Delete the entire **Soft trigger** subsection (the three bullets plus the "Semantic soft (orchestrator-only)" bullet).
- Keep the **Hard trigger** subsection unchanged (plan body > 800; `diff_lines` > 1500). Drop the trailing "There is **no** mechanical hard threshold on files-count alone." sentence — there is no `files-count` consideration anywhere now.
- Rewrite the `--partition` / `-p` bullet (line 20) and the `--partition` / `-p` (Step 2b.5) note (line 47):
  - Public flag, default `false`, mutually exclusive with `--trivial`.
  - **Semantics**: when set, Step 2b.5 routes directly to the **Split-path** (decomposition panel) regardless of plan size — no Continue option, no threshold inspection. Hard triggers also route to Split-path automatically; `--partition` is the user-initiated override that fires the same path on small plans.
  - Persisted as `partition_requested` (boolean) in `run-params.json` via `scripts/write-run-params.sh`.
- Delete the **Helper output — `TRIGGER_REASONS`** paragraph's `trigger=partition-flag` and `trigger=semantic-estimate` annotation sentences. Update the priority list to `plan-body-lines`, `diff-lines`.
- Rewrite the **`check-plan-size.sh` contract (summary)** section:
  - Machine output is now `PLAN_LINES`, `DIFF_LINES`, `HARD_TRIGGER_FIRED`, `TRIGGER_REASONS`. (`FILES_COUNT` and `SOFT_TRIGGER_FIRED` removed.)

### UPDATED: `skills/design/SKILL.md`

Rewrite Step 2b.5 to remove soft/semantic-soft branches.

- Item 3 (Return-code handling, `_plan_size_rc` is 0): parse list becomes `HARD_TRIGGER_FIRED=`, `TRIGGER_REASONS=`, `PLAN_LINES=`, `DIFF_LINES=`. Remove the `SEMANTIC_SOFT_ESTIMATE` binding paragraph entirely.
- Item 4 (Hard branch): remove `FILES_COUNT` from the printed counts line. Description references "PLAN_LINES, DIFF_LINES" only.
- Item 5 (Soft branch): **delete entirely**.
- Renumber Item 6 → Item 5 (No-trigger branch). Rewrite condition: fires when `HARD_TRIGGER_FIRED=false` AND `PARTITION_REQUESTED=false`. Remove `FILES_COUNT=<n>` from the breadcrumb (now `PLAN_LINES=<n> DIFF_LINES=<n>`).
- Add new Item before No-trigger: **Partition branch** (`PARTITION_REQUESTED=true AND HARD_TRIGGER_FIRED=false`). Route directly to Split-path (decomposition panel) without an intermediate `AskUserQuestion`. Step 2b.5 prints a `## Plan Size — Partition requested` section noting `trigger=partition-flag` and the current `PLAN_LINES` / `DIFF_LINES`, then enters Split-path.
- The Hard branch retains its Split/Cancel `AskUserQuestion` semantics unchanged.

(Step 2b.5 logic that lives outside SKILL.md — namely `scripts/write-run-params.sh` — does not need changes; `partition_requested` persistence stays.)

### UPDATED: `skills/design/references/decompose-panel.md`

- Update the **Consumer** line (line 3): entry paths are now "hard trigger or `--partition` / `-p`". Drop "soft trigger" and "semantic soft estimate".

### UPDATED: `CHANGELOG.md`

Add a single bullet describing the soft-trigger removal and `FILES_COUNT` retirement; reference the new issue number (#2805).

## Approach

The change is structurally a series of deletions plus three targeted updates: the `--partition` semantics in `flags.md`, the new "Partition branch" in `SKILL.md` Step 2b.5, and a regression-guard test case in `test-check-plan-size.sh`. No callers compute or depend on `FILES_COUNT` outside the `/design` Step 2b.5 surface (verified via grep — `SCOPE_FILES_COUNT` in `skills/review/` is an unrelated variable).

Order of edits:
1. `check-plan-size.sh` (the source of truth for the contract change).
2. `check-plan-size.md` (sibling contract — keep them in sync).
3. `test-check-plan-size.sh` + `test-check-plan-size.md` (drive harness to reflect new contract; running it must pass).
4. `flags.md` (normative public-flag and threshold prose).
5. `SKILL.md` Step 2b.5 (prompt-side branches consume the new helper output).
6. `decompose-panel.md` (cosmetic prose update on entry paths).
7. `CHANGELOG.md`.

After edits, run `bash scripts/relevant-checks.sh` (or `make lint`) to exercise the full pre-commit / harness suite, including `make test-check-plan-size`.

## Edge cases

- **Helper backward compatibility for older callers.** Any external automation reading `SOFT_TRIGGER_FIRED=` or `FILES_COUNT=` lines will silently stop seeing those keys. In-repo only `skills/design/SKILL.md` Step 2b.5 reads them, and Step 2b.5 is rewritten in the same change. No deprecation shim is added — the keys disappear in one cut.
- **`--partition` invocation on a plan that would also have hit hard.** `HARD_TRIGGER_FIRED=true` short-circuits to the Hard branch (Split/Cancel `AskUserQuestion`); `--partition` does not need an early route in that case. Only when `HARD_TRIGGER_FIRED=false AND PARTITION_REQUESTED=true` does the new Partition branch fire.
- **Plans with the trailer `diff_lines: 0`** (a valid trailer indicating a doc-only or estimate-zero plan): unchanged — neither hard threshold trips, so the No-trigger breadcrumb fires.
- **Plans without any `### NEW/UPDATED/REWRITTEN` headings** (e.g., pure doc plans): unchanged — `FILES_COUNT` was previously emitted as `0`; it is no longer emitted at all.
- **Run-params persistence**: `write-run-params.sh` still records `partition_requested` (boolean). The schema fields `partition_requested` and `brainstorm_requested` stay.

## Failure modes

- **Test harness drift in `test-check-plan-size.sh`**: if assertions for removed keys remain, the harness will fail on the first run. Earliest signal: `make test-check-plan-size` failure during step 3. Mitigation: every removed `assert_kv_eq SOFT_TRIGGER_FIRED ...` and `assert_kv_eq FILES_COUNT ...` line is matched 1:1 with a deletion; the harness file is small enough to inspect after edits.
- **SKILL.md Step 2b.5 parsing leftover**: if `SOFT_TRIGGER_FIRED=` is still in the parse loop, the loop variable is just empty — no breakage — but the dead reference is misleading. Earliest signal: `agent-lint` (S030) or grep for `SOFT_TRIGGER_FIRED`. Mitigation: grep after edits.
- **Stale prose in another doc**: `docs/` or `larch-logs/` may mention soft triggers as a feature. `larch-logs/**/*` is committed historical run output and is left alone (history). `docs/` may need a sweep. Earliest signal: a follow-up grep `soft.trigger|SOFT_TRIGGER` in `docs/` and `README.md` after edits. Mitigation: include the grep in the post-edit verification.

## Testing strategy

- `make test-check-plan-size` — must pass with the rewritten harness.
- `bash scripts/relevant-checks.sh` (or `make lint`) — full pre-commit and structural suite. `scripts/test-design-structure.sh` is part of this and would catch SKILL.md/Step-2b.5 anchor drift if any.
- Grep verification after edits:
  - `grep -rnE 'SOFT_TRIGGER_FIRED|FILES_COUNT|files-count|SEMANTIC_SOFT_ESTIMATE' skills/ scripts/ docs/ --include='*.sh' --include='*.md'` should return zero non-larch-logs hits.
  - `grep -rn 'Soft Trigger' skills/ scripts/ docs/` should return zero non-larch-logs hits.

No new test files; only edits to the existing harness.


## Acceptance

- `make test-check-plan-size` passes with the rewritten harness.
- `bash scripts/relevant-checks.sh` (or `make lint`) passes end-to-end.
- Post-edit grep: `grep -rnE 'SOFT_TRIGGER_FIRED|FILES_COUNT|files-count|SEMANTIC_SOFT_ESTIMATE' skills/ scripts/ docs/ --include='*.sh' --include='*.md'` returns zero non-`larch-logs/` hits.
- Post-edit grep: `grep -rn 'Soft Trigger' skills/ scripts/ docs/` returns zero non-`larch-logs/` hits.
- `/design` Step 2b.5 on a future plan with 9+ files no longer fires a soft-trigger AskUserQuestion.

diff_lines: 280
