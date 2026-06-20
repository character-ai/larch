### External Reviewer Issues

- **Step design Step 3 — collect-results cursor NOT_SUBSTANTIVE failed (exit 0)**:
  ```
## Structured collector record

REVIEWER_FILE=<TMPDIR>/plan-review/round-1/dyn-cursor-plan-secret-count-contract.txt|TOOL=cursor|STATUS=NOT_SUBSTANTIVE|EXIT_CODE=0|FAILURE_REASON=structured records not found after repair

## Reviewer output (<TMPDIR>/plan-review/round-1/dyn-cursor-plan-secret-count-contract.txt)

I'll locate the secret-count plan and read the four Python modules you named, then trace how `SECRET_SCRUB_VIOLATIONS` is parsed and counted.
**Verdict:** The plan correctly identifies the root bug (`_commit_run` never propagates scrub counts), but as written it will still **undercount on the design publish path** and can **break or weaken parsing** unless it addresses the `src==dest` skip, pre-redact semantics, and the `LARCH_` vs `SECRET_` key split.

**Plans inspected:** GitHub issue [#4833](https://github.com/character-ai/larch/issues/4833) **Item 14**; [#4799](https://github.com/character-ai/larch/issues/4799) Description (merged into #4833); `larch-logs/design/BEBB7037-AA88-4887-A2E9-4DD7EDFD52A2/plan.txt` (stdout envelope §, `_commit_run` aggregated scrub §, `larch_log_commit_main` / `larch_log_flush_main` §, `scrub-log-secrets` contract §); `larch-logs/implement/908739B9-29BC-4355-99DE-B5DB60AFC676/plan-goals-test.md` (#4782 design-tail wiring).

**Code inspected:** `python/run_logs.py`, `python/design_log_publish_flow.py`, `python/design_publish.py`, `python/redact.py`, `python/test_design_log_publish_flow.py`, `python/test_design_publish.py`.

---


- **Step design Step 3 — collect-results codex NOT_SUBSTANTIVE failed (exit 0)**:
  ```
## Structured collector record

REVIEWER_FILE=<TMPDIR>/plan-review/round-1/dyn-codex-plan-secret-count-contract.txt|TOOL=codex|STATUS=NOT_SUBSTANTIVE|EXIT_CODE=0|FAILURE_REASON=structured records not found after repair

## Reviewer output (<TMPDIR>/plan-review/round-1/dyn-codex-plan-secret-count-contract.txt)

Found **2 issues**. Both are **undercounting**. I found no standalone double-counting or parser-shape issue in `_scrub_violations`.


- **Step design Step 3 — collect-results cursor NOT_SUBSTANTIVE failed (exit 0)**:
  ```
## Structured collector record

REVIEWER_FILE=<TMPDIR>/plan-review/round-1/dyn-cursor-plan-step3-warning-propagation.txt|TOOL=cursor|STATUS=NOT_SUBSTANTIVE|EXIT_CODE=0|FAILURE_REASON=structured records not found after repair

## Reviewer output (<TMPDIR>/plan-review/round-1/dyn-cursor-plan-step3-warning-propagation.txt)

Reviewing the Step 3 warning propagation plan against `python/plan_review.py` and tests; searching the repo for the plan and warning constants.
**Verdict:** `_STEP3_ROUND_CARRY_KEYS` limits within-round carry to the two warning keys, but **neither survives auto-continuation into the next review round**. Final envelopes are shape-compatible when warnings are present; multi-round runs can still drop round-1 warnings before terminal emit.

**Plan inspected:** `larch-logs/implement/28C17E9B-46FE-4C51-9DAD-1D41D64F9EDB/plan-goals-test.md` — **Warning propagation (finding 5)** (lines 27–33, 120–127, 204–211, 223, 257); `python/plan_review.py`; `python/test_plan_review.py`; `python/design_lifecycle.py` (`PHASE_RESULT_ENV_ALLOW_KEYS`); `python/plan_review_round.py`; `skills/design/scripts/design-step3-review.sh`.

---


- **Step design Step 3 — collect-results codex NOT_SUBSTANTIVE failed (exit 0)**:
  ```
## Structured collector record

REVIEWER_FILE=<TMPDIR>/plan-review/round-1/dyn-codex-plan-step3-warning-propagation.txt|TOOL=codex|STATUS=NOT_SUBSTANTIVE|EXIT_CODE=0|FAILURE_REASON=structured records not found after repair

## Reviewer output (<TMPDIR>/plan-review/round-1/dyn-codex-plan-step3-warning-propagation.txt)


- **Step design Step 3 — collect-results cursor NOT_SUBSTANTIVE failed (exit 0)**:
  ```
## Structured collector record

REVIEWER_FILE=<TMPDIR>/plan-review/round-1/dyn-cursor-plan-reviewer-prune-tokenizer.txt|TOOL=cursor|STATUS=NOT_SUBSTANTIVE|EXIT_CODE=0|FAILURE_REASON=structured records not found after repair

## Reviewer output (<TMPDIR>/plan-review/round-1/dyn-cursor-plan-reviewer-prune-tokenizer.txt)

Searching for the reviewer-prune tokenization plan and inspecting the cited files.
Checking the outer wrapper output format and whether a formal tokenization fix plan exists in the repo.
**Verdict:** The tokenization fix direction (label-map-aware plan-mode parsing, keep pipe split and ledger schema) is sound, but the plan is **ambiguous on algorithm choice**, **under-specifies precedence**, and **does not yet pin the multi-reviewer regression** the tally harness already defines.

Inspected: `larch-logs/implement/6A891157-868F-41AC-8B78-D3FAD828A6DC/plan-goals-test.md` (§`python/review_pipeline.py`, lines 35–39, 102–125), `larch-logs/implement/6A891157-868F-41AC-8B78-D3FAD828A6DC/round-1/oos-accepted-review.md` (OOS_6), `larch-logs/design/56D18AE2-A61B-4277-8239-A6388F8C2455/plan.txt` (Approach, line 29), `larch-logs/design/0439581E-3853-4DDA-A390-D5AEF99D5D27/findings-in-scope.md` (FINDING_3), `python/review_pipeline.py`, `python/test_review_pipeline.py`, `skills/design/scripts/test-findings-classification.sh`, `python/plan_review_tally.py`.


- **Step design Step 3 — collect-results codex NOT_SUBSTANTIVE failed (exit 0)**:
  ```
## Structured collector record

REVIEWER_FILE=<TMPDIR>/plan-review/round-1/dyn-codex-plan-reviewer-prune-tokenizer.txt|TOOL=codex|STATUS=NOT_SUBSTANTIVE|EXIT_CODE=0|FAILURE_REASON=structured records not found after repair

## Reviewer output (<TMPDIR>/plan-review/round-1/dyn-codex-plan-reviewer-prune-tokenizer.txt)

I found **one issue**.


- **findings aggregator**: merged output failed validation; leaving <TMPDIR>/findings-in-scope.md unchanged. See <TMPDIR>/aggregator-validate.stderr.
### FINDING_1: Plan-mode whitespace tokenization is not implemented or covered

- **Plan section:** `larch-logs/implement/EAEF11AA-1D1D-40BD-A472-00C7C004E8D9/plan-goals-test.md:35-38`, `:65-67`
- **Inspected files:** `python/review_pipeline.py:350-367`, `python/test_review_pipeline.py:684-715`, `skills/design/scripts/test-findings-classification.sh:24-28`, `:137-138`

**Issue:** The plan requires plan-review `finding_reviewers` cells to split on **commas and whitespace runs**. Current `python/review_pipeline.py` plan mode only does `cell.split(",")`, so a whitespace-derived multi-reviewer cell like `Cursor-Pragmatic Codex-Arch` is treated as one token and matches neither reviewer.

**Why it matters:** `skills/design/scripts/test-findings-classification.sh` creates a tab-separated reviewer cell and asserts it becomes `Cursor-Pragmatic Codex-Arch`. That is exactly the whitespace case the reviewer-prune tokenization path must count.

**Coverage gap:** `python/test_review_pipeline.py` only covers a **single** space-containing dynamic label. It does not cover:
- plan-mode comma-separated reviewers,
- plan-mode whitespace-separated reviewers,
- preserving code-review `|` splitting.

**Constraints check:** Code-review pipe splitting is still separate at `python/review_pipeline.py:366-367`. Ledger schema is not implicated by this fix. Add a label-tokenization helper and tests without changing `_prune_ledger_header()`.
## Reviewer stderr (<TMPDIR>/plan-review/round-1/dyn-codex-plan-reviewer-prune-tokenizer.txt.diag)

(file missing: <TMPDIR>/plan-review/round-1/dyn-codex-plan-reviewer-prune-tokenizer.txt.diag)

## Failed-agent stderr tail (<TMPDIR>/plan-review/round-1/dyn-codex-plan-reviewer-prune-tokenizer.txt.stderr-tail)

(file missing: <TMPDIR>/plan-review/round-1/dyn-codex-plan-reviewer-prune-tokenizer.txt.stderr-tail)

## Launcher stderr (<TMPDIR>/plan-review/round-1/dyn-codex-plan-reviewer-prune-tokenizer.txt.launch-stderr)

⏳ codex agent: still running (1m elapsed)
⏳ codex agent: still running (2m elapsed)
✓ codex agent: completed (exit code 0, output 1458 bytes)
  ```
### In-Scope Findings

- **correctness** `python/review_pipeline.py:364-366` — **Plan section:** OOS_6 / `#4772` plan-goals-test.md line 39 (“Preserve plan-mode token parsing”). **Inspected:** `python/review_pipeline.py:364-366`, `skills/design/scripts/test-findings-classification.sh:28,137`, `python/plan_review_tally.py:49-57,240`. Shipped code uses comma-only `cell.split(",")` in plan mode. Tally writes `finding_reviewers` as `Cursor-Pragmatic Codex-Arch` (tab in ballot → space via `_sanitize_tsv_cell`). That whole string is one unmatched token, so neither reviewer gets ledger credit. This violates the `#3619` grammar (`[,[:space:]]+`, `plan.txt` line 29) and the tally harness contract. **Suggested fix:** Plan must explicitly supersede design FINDING_3’s “comma-only” resolution and mandate label-map-aware tokenization in the `plan_mode` branch only.

- **architecture** `python/review_pipeline.py:350-365` — **Plan section:** OOS_6 (“Tokenize using label-map longest-match, or split on commas and whitespace only when segments resolve to known labels”). **Inspected:** `python/review_pipeline.py:350-365`, `432-437`. The plan offers two algorithms without choosing one or defining precedence. `_read_classification_counts` already receives `label_list` from `reviewer_prune_record`; the plan should pin a single ordered rule set, e.g. (1) stripped cell equals a known label → `{cell}`; (2) if `,` present → comma-split + trim; (3) else greedy longest-match scan against `label_list` sorted by length. **Suggested fix:** Replace the “or” with one canonical algorithm and document precedence in the `python/review_pipeline.py` plan subsection.

- **testing** `python/test_review_pipeline.py:684-714` — **Plan section:** OOS_6 (“add a multi-reviewer space-separated plan-mode prune regression test”; keep `test_reviewer_prune_record_plan_mode_preserves_spaced_dynamic_label`). **Inspected:** `python/test_review_pipeline.py:684-714`, `skills/design/scripts/test-findings-classification.sh:137`. Only the spaced single-label case exists (`Cursor-dyn-Api Contract`). There is no test for `Cursor-Pragmatic Codex-Arch` with two manifest slots and a label map. The plan calls for coverage but does not pin fixture shape (two-slot manifest, two-row label map, classification row with space-separated cell, assert both slots get `accepted_count=1`). **Suggested fix:** Add an explicit `### UPDATED: python/test_review_pipeline.py` bullet with exact fixture values mirroring `test-findings-classification.sh:137`.

- **correctness** `python/review_pipeline.py:364-367` — **Plan section:** User constraint / `#4772` plan-goals-test.md lines 35-40 (“Preserve code-review label normalization”). **Inspected:** `python/review_pipeline.py:364-367`, `python/test_review_pipeline.py:785-826`. Code-review path correctly uses `cell.split("|")` + `_normalize_code_label`. Plan is sound **if** tokenization changes stay inside `if plan_mode:` and do not touch line 367 or `_prune_ledger_header()` (`python/review_pipeline.py:387-388`). **Suggested fix:** Add an explicit plan guard: “no edits outside the `plan_mode` branch of `_read_classification_counts`; ledger header/writers unchanged.”

- **risk-integration** `python/review_pipeline.py:435` — **Plan section:** `#4772` plan-goals-test.md lines 87-93 (plan-review label map). **Inspected:** `python/review_pipeline.py:432-437`. `plan_mode = bool(label_mp)` gates plan tokenization on `--label-map` presence. Code review without a label map still uses pipe splitting even when the column is `finding_reviewers`. Plan should state that label-map-aware parsing applies only when `label_map` is supplied (native `/design` path), so implementers do not change the no-label-map code-review record path. **Suggested fix:** Document the `bool(label_mp)` gate in the plan’s edge-cases section.

### Out-of-Scope Observations

- `python/progress_report.py:692-696` also comma-splits `finding_reviewers` only; scoreboard attribution will stay inconsistent with prune ledger until separately fixed. Not in the three-file scope.
- `skills/design/scripts/test-findings-classification.sh` should remain unchanged; it is the upstream contract (`:137`). The fix belongs in `python/review_pipeline.py`, not the harness.
- Comma-separated multi-reviewer cells (`Cursor-Pragmatic, Codex-Arch`) are not pinned in either the tally harness or the proposed pytest fixture; worth a second test case once the algorithm is fixed.
## Reviewer stderr (<TMPDIR>/plan-review/round-1/dyn-cursor-plan-reviewer-prune-tokenizer.txt.diag)

(empty: <TMPDIR>/plan-review/round-1/dyn-cursor-plan-reviewer-prune-tokenizer.txt.diag)

## Failed-agent stderr tail (<TMPDIR>/plan-review/round-1/dyn-cursor-plan-reviewer-prune-tokenizer.txt.stderr-tail)

(file missing: <TMPDIR>/plan-review/round-1/dyn-cursor-plan-reviewer-prune-tokenizer.txt.stderr-tail)

## Launcher stderr (<TMPDIR>/plan-review/round-1/dyn-cursor-plan-reviewer-prune-tokenizer.txt.launch-stderr)

⏳ cursor agent: still running (1m elapsed)
⏳ cursor agent: still running (2m elapsed)
⏳ cursor agent: still running (3m elapsed)
⏳ cursor agent: still running (4m elapsed)
✓ cursor agent: completed (exit code 0, output 5905 bytes)
  ```
### In-Scope Findings

No in-scope issues found. I inspected **plan** `larch-logs/design/C229C50E-50E5-4364-B4A7-E3233F9A41E7/plan.txt:27-33,120-127,200-207`, **code** `python/plan_review.py:39-52,109-113,370-470,1300-1494`, and **tests** `python/test_plan_review.py:17-65,1064-1190`.

The code limits round carry to `DEGRADED_PANEL_WARNING` and `INVALID_SLOT_PANEL_WARNING` via `_STEP3_ROUND_CARRY_KEYS`, clears carry state before true continuation rounds, and emits the new fields as optional envelope KVs. The final envelope shape remains backward-compatible because existing keys are preserved and the new warning keys are additive.
## Reviewer stderr (<TMPDIR>/plan-review/round-1/dyn-codex-plan-step3-warning-propagation.txt.diag)

(file missing: <TMPDIR>/plan-review/round-1/dyn-codex-plan-step3-warning-propagation.txt.diag)

## Failed-agent stderr tail (<TMPDIR>/plan-review/round-1/dyn-codex-plan-step3-warning-propagation.txt.stderr-tail)

(file missing: <TMPDIR>/plan-review/round-1/dyn-codex-plan-step3-warning-propagation.txt.stderr-tail)

## Launcher stderr (<TMPDIR>/plan-review/round-1/dyn-codex-plan-step3-warning-propagation.txt.launch-stderr)

⏳ codex agent: still running (1m elapsed)
✓ codex agent: completed (exit code 0, output 636 bytes)
  ```
### In-Scope Findings

- **risk-integration** `python/plan_review.py:51,109-112,1367-1369,1449-1470` — `_STEP3_ROUND_CARRY_KEYS` names only `DEGRADED_PANEL_WARNING` and `INVALID_SLOT_PANEL_WARNING`, and `_step3_round_carry_values()` filters post-apply envelopes to those keys when `degraded_exit` is false (plan section: within-round propagation via `step3_loop_persist_envelope` / `step3_loop_emit_envelope`, plan-goals-test.md:120–127). That works **within one round** (panel → apply → post-apply → continuation check). On `PLAN_REVIEW_CONTINUE=true`, the loop unlinks `.step3-review-result.env` and sets `degraded_values = {}` (lines 1453–1454, 1469–1470), so **no warning key survives into round N+1**. Round 1 `INVALID_SLOT_PANEL_WARNING` is lost if round 2 converges without re-emitting it. **Suggested fix:** Before reset, merge `_STEP3_ROUND_CARRY_KEYS` from `degraded_values` (or the result env) into a durable carry buffer reloaded at the next round entry; or preserve only those keys across `round_num += 1` instead of clearing to `{}`.

- **correctness** `python/plan_review.py:1486-1493` + `python/plan_review.py:1208-1223` — Final `complete` envelope is built from `degraded_values` (last round only) plus a filtered merge from `_run_continuation`. `plan_review_continuation` emits counts and `DEGRADED_PANEL` but **never** re-emits warning keys (lines 1208–1223). So `complete_values.update(...)` at line 1487 cannot recover prior-round warnings after the continuation reset. Terminal stdout/`.step3-review-result.env` may omit degradation the operator already saw in round 1. **Suggested fix:** Carry warnings across continuation as above, or archive them to a sidecar merged at final emit.

- **risk-integration** `python/plan_review.py:39-50,428-435` — Plan finding 5 (plan-goals-test.md:124) adds both warnings to `MERGE_KEYS` so mid-loop persist merges do not drop them. `MERGE_KEYS` only applies when `.step3-review-result.env` still exists during `step3_loop_persist_envelope` (lines 426–435). Continuation **deletes** that file first (lines 1453–1454), so merge cannot restore cross-round warnings. **Suggested fix:** Do not rely on `MERGE_KEYS` for cross-round survival; explicit carry or sidecar is required.

- **risk-integration** `python/test_plan_review.py:36-65` vs plan-goals-test.md:204-211 — Plan asks for a loop/harness test: round `values` with a warning → persisted `.step3-review-result.env` + terminal emit. Tests only call `step3_loop_persist_envelope` / `step3_loop_emit_envelope` directly. No test covers `_STEP3_ROUND_CARRY_KEYS` staging in `run_step3_review` (lines 1367–1369) or multi-round continuation loss (lines 1469–1470). A regression in carry staging or continuation reset would not fail CI. **Suggested fix:** Add a stubbed `run_step3_review` test: round 1 emits `INVALID_SLOT_PANEL_WARNING`, continuation returns `PLAN_REVIEW_CONTINUE=true`, round 2 completes → assert both warnings appear in final persist/emit (or document intentional single-round-only carry and test that contract).

- **architecture** plan-goals-test.md:27-33,87-98 vs `python/plan_review_panel.py:411-413`, `python/plan_review_round.py:414-417` — Plan threads invalid-slot degradation as `DEGRADED_PANEL_WARNING` end-to-end. Implementation splits keys: `INVALID_SLOT_PANEL_WARNING` (invalid-slot drops) and `DEGRADED_PANEL_WARNING` (voter quota degradation, `plan_review_round.py:525-526`). Both are in allowlists and envelope writers, so **envelope shape stays compatible**, but the plan’s single-key model is not what ships. **Suggested fix:** Update the plan acceptance text, or normalize invalid-slot warnings to `DEGRADED_PANEL_WARNING` as the plan states.

---

### Within-round behavior (plan-aligned)

| Phase | What survives | Source |
|--------|----------------|--------|
| Round complete (`LOOP_STATUS=complete`) | Only `_STEP3_ROUND_CARRY_KEYS` stashed into `degraded_values` | `python/plan_review.py:1367-1369` |
| Post-apply / postplan-operator emit | Filtered to carry keys (unless `degraded_exit`) | `python/plan_review.py:109-112,1429-1438` |
| `zero-findings-degraded-panel` | Full `values` dict in `degraded_values` | `python/plan_review.py:1370-1385` |
| Final `complete` (single round, no continue) | Warnings from `degraded_values` + optional merge from `cont` | `python/plan_review.py:1486-1493` |

---

### Final envelope compatibility (when warnings are present)

These surfaces agree on both keys:

- `PHASE_RESULT_ENV_ALLOW_KEYS` — `python/design_lifecycle.py:265-266`
- `step3_loop_persist_envelope` / `step3_loop_emit_envelope` — `python/plan_review.py:417-420,455-458`
- `--read-result-env` — `python/plan_review.py:1314-1315`
- Bash allowlist + replay — `skills/design/scripts/design-step3-review.sh:569-570,612,718-719`

Envelope **schema** is compatible. **Content** can be wrong on multi-round paths because carry state is cleared before the next round.

---

### Out-of-Scope Observations

- Cross-round `degraded_values` reset at `python/plan_review.py:1469-1470` predates this branch and clears **both** warning keys equally (`larch-logs/implement/28C17E9B-46FE-4C51-9DAD-1D41D64F9EDB/round-2/oos-accepted-review.md`, OOS_7).
- `awaiting-apply` / `awaiting-revise` pass full `degraded_values` (`python/plan_review.py:1402-1414`); post-apply paths use filtered `_step3_round_carry_values()`. Equivalent on the normal `complete` path; diverges only on `zero-findings-degraded-panel` (`degraded_exit=true`).
- Bash wrapper wiring for `INVALID_SLOT_PANEL_WARNING` appears present in current `design-step3-review.sh`; the Python cross-round gap remains the main propagation risk for multi-round designs.
## Reviewer stderr (<TMPDIR>/plan-review/round-1/dyn-cursor-plan-step3-warning-propagation.txt.diag)

(empty: <TMPDIR>/plan-review/round-1/dyn-cursor-plan-step3-warning-propagation.txt.diag)

## Failed-agent stderr tail (<TMPDIR>/plan-review/round-1/dyn-cursor-plan-step3-warning-propagation.txt.stderr-tail)

(file missing: <TMPDIR>/plan-review/round-1/dyn-cursor-plan-step3-warning-propagation.txt.stderr-tail)

## Launcher stderr (<TMPDIR>/plan-review/round-1/dyn-cursor-plan-step3-warning-propagation.txt.launch-stderr)

✓ cursor agent: completed (exit code 0, output 304 bytes)
⏳ cursor agent: still running (1m elapsed)
⏳ cursor agent: still running (2m elapsed)
✓ cursor agent: completed (exit code 0, output 6899 bytes)
  ```
### FINDING_1: Scrub counts are discarded before `SECRET_SCRUB_VIOLATIONS` is emitted

- **Severity:** High
- **Plan section:** `larch-logs/design/BEBB7037-AA88-4887-A2E9-4DD7EDFD52A2/plan.txt:38-58`, `:110-124`, `:588-596`
- **Inspected:** `python/run_logs.py`, `python/design_log_publish_flow.py`, `python/design_publish.py`, `python/redact.py`
- **Location:** `python/run_logs.py:1626-1653`, `:1739-1781`, `:1799-1867`; downstream: `python/design_log_publish_flow.py:230-243`, `:295-305`, `:420-425`; `python/design_publish.py:420-431`
- **Issue:** `_copy_tree_to_repo()` calls `_scrub_run_tree()` for the run tree and `larch-logs/shared`, but ignores the returned `(violations, files_scrubbed)`. `_commit_run()` then resets `violations = 0` and emits that zero on every success path.
- **Impact:** Any scrubbed secret in the committed run tree or shared tree is reported as `SECRET_SCRUB_VIOLATIONS=0`. The design-log publisher trusts that stdout value, so `/design publish` misses the rotation warning.
- **Fix:** Return aggregate scrub counts from `_copy_tree_to_repo()` and use them in `_commit_run()` for all no-change, volatile-only, diff-quiet, and commit-success stdout paths.

### FINDING_2: Breadcrumb quiet logs are added after the scrub gate

- **Severity:** High
- **Plan section:** `larch-logs/design/BEBB7037-AA88-4887-A2E9-4DD7EDFD52A2/plan.txt:53-58`, `:118-120`, `:225-245`, `:597-600`
- **Inspected:** `python/run_logs.py`, `python/design_log_publish_flow.py`, `python/design_publish.py`, `python/redact.py`
- **Location:** `python/run_logs.py:1826-1838`, `:2075-2131`; `python/redact.py:33-49`, `:273-278`, `:319-324`, `:357-376`, `:379-384`
- **Issue:** `_commit_run()` scrubs the copied run tree, then calls `publish_breadcrumbs_main()`, which writes `breadcrumbs/quiet.log` after that scrub. Breadcrumb staging uses `redact_breadcrumb_file()`, but that path does not apply the full `scrub_log_secrets()` extra-family gate for Slack, Google API, Stripe live, and GitLab PAT patterns.
- **Impact:** Extra-family secrets in quiet logs can be committed without being scrubbed or counted. The emitted `SECRET_SCRUB_VIOLATIONS` can still be `0`.
- **Fix:** Publish breadcrumbs before the final scrub, or run `_scrub_run_tree()` again on the committed destination after breadcrumb publishing and aggregate that count.
## Reviewer stderr (<TMPDIR>/plan-review/round-1/dyn-codex-plan-secret-count-contract.txt.diag)

(file missing: <TMPDIR>/plan-review/round-1/dyn-codex-plan-secret-count-contract.txt.diag)

## Failed-agent stderr tail (<TMPDIR>/plan-review/round-1/dyn-codex-plan-secret-count-contract.txt.stderr-tail)

(file missing: <TMPDIR>/plan-review/round-1/dyn-codex-plan-secret-count-contract.txt.stderr-tail)

## Launcher stderr (<TMPDIR>/plan-review/round-1/dyn-codex-plan-secret-count-contract.txt.launch-stderr)

⏳ codex agent: still running (1m elapsed)
⏳ codex agent: still running (2m elapsed)
⏳ codex agent: still running (3m elapsed)
⏳ codex agent: still running (4m elapsed)
✓ codex agent: completed (exit code 0, output 2469 bytes)
  ```
### FINDING_1: **correctness** `python/run_logs.py:1837-1865` — Plan premise is right; count is discarded after scrub runs

**Plan:** #4833 Item 14; BEBB7037 `plan.txt` “Scrub secrets before git add/commit and emit `SECRET_SCRUB_VIOLATIONS=N` on stdout.”

`_copy_tree_to_repo` already calls `_scrub_run_tree` (lines 1755, 1777) but drops the return value. `_commit_run` then hardcodes `violations = 0` and emits that on every stdout exit path (1842, 1853, 1859, 1865). Implement flush (`2166-2171`) and the #4782 design tail both consume this stdout contract, so both rotation warnings are inert today despite scrubbing.

**Plan gap:** Wiring must capture and sum scrub totals inside `_copy_tree_to_repo` (run tree + `larch-logs/shared`) and assign them before the early returns, not add a second blind scrub pass.

---

### FINDING_2: **correctness** `python/run_logs.py:1748-1761` — Design publish undercounts because commit skips scrub when `src == dest`

**Plan:** #4833 Item 14 mentions design pre-redact but not this path.

Design publish (`design_log_publish_flow.py:278-299`) stages directly into `worktree/larch-logs/design/<run_id>`, then calls `run-log commit` with `--log-root` set to that same worktree. In `_copy_tree_to_repo`, when `src.resolve() == dest.resolve()`, the copy+scrub block is skipped entirely; only `rels.append(...)` runs.

So for design logs, **`_scrub_run_tree` never runs at commit time**. Threading counts only from `_copy_tree_to_repo` scrub will still yield **0** on the design path even when secrets exist. Item 14’s “even if `_commit_run` counted, post-redaction tree would report 0” is true for a different reason than stated: commit scrub is bypassed, not merely redundant.

**Suggested plan fix:** Require in-place scrub (and count aggregation) when `src == dest`, or scrub during `_copy_tree_redacted` and accumulate counts there.

---

### FINDING_3: **correctness** `python/design_log_publish_flow.py:164-173` + `python/redact.py:319-324` vs `357-376` — Pre-redact undercounts base secret families

**Plan:** #4833 Item 14 Description (design path pre-redacts via `redact secrets`).

`_copy_tree_redacted` pipes each file through `redact secrets` → `redact_secrets_only` → `_redact_secrets_pem` (base families only). `scrub_log_secrets` / `_scrub_run_tree` also count and scrub **extra** families (`crsr_`, Slack, Stripe, etc., `redact.py:44-50`).

Any base-family secret removed during design copy is **never counted**. Extra-family secrets are only counted if commit-time scrub runs (FINDING_2: it does not on the worktree path).

A plan that only wires `_commit_run` ← `_scrub_run_tree` leaves the design operator warning inert for the common leak classes.

---

### FINDING_4: **risk-integration** `python/run_logs.py:1754-1777` — Double-scrub / double-count if plan adds a dedicated `scrub-log-secrets` pass

**Plan:** #4833 Item 14 “thread … from `_copy_tree_to_repo` / `_scrub_run_tree` **(or a dedicated `redact scrub-log-secrets` pass)**”; BEBB7037 `plan.txt` line 333 (separate `scrub-log-secrets` gate for design publish).

`_scrub_run_tree` and `redact.scrub_log_directory` are the same algorithm (`run_logs.py:1643-1651`, `redact.py:467-475`). Adding a **second** `main_scrub_log_secrets` invocation without removing the in-tree scrub would:

- Re-walk the tree twice (harmless but wasteful).
- Risk **double-counting** if both passes contribute to one `SECRET_SCRUB_VIOLATIONS` total.

Plan should pick **one** authoritative counter per tree copy, not “or” both.

---

### FINDING_5: **correctness** `python/redact.py:508-509` vs `python/design_log_publish_flow.py:240-243` — `LARCH_` vs `SECRET_` prefix mismatch can break parsing

**Plan:** BEBB7037 `plan.txt` line 333 (“preserving `LARCH_SECRET_SCRUB_VIOLATIONS` parsing”); #4833 Item 14 cites `main_scrub_log_secrets`.

`main_scrub_log_secrets` emits `LARCH_SECRET_SCRUB_VIOLATIONS` / `LARCH_SECRET_SCRUB_FILES`. All downstream consumers parse **`SECRET_SCRUB_VIOLATIONS`**:

| Consumer | Location | Parser |
|---|---|---|
| `larch_log_commit_main` | `run_logs.py:2026-2027` | `startswith("SECRET_SCRUB_VIOLATIONS=")` |
| Implement flush | `run_logs.py:2167` | same |
| Design log-publish | `design_log_publish_flow.py:240-243` | same; `isdigit()` guard |
| Design publish tail | `design_publish.py:425-426` | `publish_kv["SECRET_SCRUB_VIOLATIONS"]` |

If the plan wires a subprocess call to `redact scrub-log-secrets` and parses `LARCH_*` keys without normalizing to `SECRET_SCRUB_VIOLATIONS=` on `run-log commit` stdout / `log_publish_main` KV output, **`_scrub_violations` silently returns `"0"`** (non-matching prefix → default). That is a parsing breakage, not just undercount.

---

### FINDING_6: **correctness** `python/run_logs.py:2026-2027` vs `design_log_publish_flow.py:240-242` — Envelope parser is looser than design parser

**Plan:** BEBB7037 `plan.txt` commit stdout envelope contract.

`larch_log_commit_main` stores `line.split("=", 1)[1]` with **no** `isdigit()` check. `_scrub_violations` rejects non-numeric values (defaults to `"0"`). `design_publish.py` uses `isdigit()` before warning.

If a wired count ever carries whitespace or a non-numeric sentinel, the **envelope can advertise a value the design tail ignores**, breaking end-to-end parity. Plan should require bare decimal integers on the `SECRET_SCRUB_VIOLATIONS=` line (matching `_scrub_violations` and tests at `test_design_log_publish_flow.py:323-335`).

---

### FINDING_7: **correctness** `python/run_logs.py:2167` — Flush warning uses a brittle zero test (minor once counts are live)

**Plan:** BEBB7037 `plan.txt` lines 140-141 (“parse commit stdout … stderr warning text when count > 0”).

Flush checks `line.startswith("SECRET_SCRUB_VIOLATIONS=") and not line.endswith("=0")` instead of parsing the integer. Today harmless because the value is always `0`. After wiring real counts:

- Values like `…=10` are fine.
- The check still ignores the numeric magnitude (no count in the warning text).
- Trailing whitespace on `=0` could false-trigger.

Prefer `int` parsing aligned with `_scrub_violations` when the plan activates this path.

---

### FINDING_8: **risk-integration** `python/run_logs.py:1844-1853` — Volatile-only path must preserve scrub counts for warnings

**Plan:** BEBB7037 `plan.txt` volatile-only envelope; #4833 Item 14 (implement flush warning).

Volatile-only early return still emits `SECRET_SCRUB_VIOLATIONS={violations}` (1853). If violations are wired from pre-status scrub, a scrubbed-then-restored volatile sidecar can still warrant a rotation warning (`test_run_logs.py:1085-1118` exercises this on the legacy `_larch_log_commit` path with `_warn_secret_scrub`; `_commit_run` has no equivalent stderr banner).

Plan should specify: **emit the accumulated pre-volatile scrub count on stdout even when `argv == ("larch-log-volatile-only",)`**, and decide whether `_commit_run` should also call `_warn_secret_scrub` for parity with `_larch_log_commit` (`1709-1715`).

---

### FINDING_9: **testing** — Plan lacks an end-to-end non-zero integration test on the real scrub path

**Plan:** #4782 `plan-goals-test.md` “Add tests”; BEBB7037 pytest coverage expectations.

Existing coverage:

- `test_design_publish.py:421-457`: rotate warning via **fake** `FAKE_CLI_SCRUB_VIOLATIONS`, not real scrub.
- `test_design_log_publish_flow.py:123`: asserts `SECRET_SCRUB_VIOLATIONS=0` on clean runs.
- `test_run_logs.py:825-837`: `_scrub_run_tree` unit test only; **no** `_commit_run` → non-zero stdout → flush/design-tail test.

Plan should require at least one integration test that places a known `scrub_log_secrets`-detectable token in a staged tree and asserts non-zero `SECRET_SCRUB_VIOLATIONS` on `run-log commit` stdout **and** the design `log_publish_main` KV, separately covering the `src != dest` (implement) and `src == dest` (design worktree) branches.

---

## Summary table

| Risk | Severity | Design path | Implement path |
|---|---|---|---|
| Hardcoded `violations = 0` | Confirmed bug | Inert warning | Inert warning |
| `src == dest` skips scrub | Plan silent | **Always undercounts** | N/A (tmpdir ≠ repo) |
| Pre-`redact secrets` | Item 14 noted | Undercounts base families | N/A |
| Second scrub pass | “or” wording | Double-count risk | Double-count risk |
| `LARCH_*` vs `SECRET_*` | BEBB7037 vs code | Parsing → silent 0 | Parsing → silent 0 |

**Bottom line:** Implementing Item 14 as “assign `_scrub_run_tree` return value in `_commit_run`” fixes the implement path only when `src != dest`. The plan needs explicit design-path counting (in-place scrub or per-file accumulation in `_copy_tree_redacted`), a single scrub authority, and a normalized `SECRET_SCRUB_VIOLATIONS=` decimal contract on all stdout/KV surfaces consumers already parse.
## Reviewer stderr (<TMPDIR>/plan-review/round-1/dyn-cursor-plan-secret-count-contract.txt.diag)

(empty: <TMPDIR>/plan-review/round-1/dyn-cursor-plan-secret-count-contract.txt.diag)

## Failed-agent stderr tail (<TMPDIR>/plan-review/round-1/dyn-cursor-plan-secret-count-contract.txt.stderr-tail)

(file missing: <TMPDIR>/plan-review/round-1/dyn-cursor-plan-secret-count-contract.txt.stderr-tail)

## Launcher stderr (<TMPDIR>/plan-review/round-1/dyn-cursor-plan-secret-count-contract.txt.launch-stderr)

⏳ cursor agent: still running (1m elapsed)
⏳ cursor agent: still running (2m elapsed)
⏳ cursor agent: still running (3m elapsed)
⏳ cursor agent: still running (4m elapsed)
⏳ cursor agent: still running (5m elapsed)
✓ cursor agent: completed (exit code 0, output 10510 bytes)
  ```
