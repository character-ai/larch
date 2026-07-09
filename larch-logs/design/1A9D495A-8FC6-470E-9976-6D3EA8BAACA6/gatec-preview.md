## Final Design Plan

The plan is very large. Showing the full plan body below.

## Plan

## Approach

Implement the approved outline with minimum scope, incorporating accepted plan-review findings on guard placement, RefreshSkip wiring, parser targeting, direct-commit bypass paths (Step 7a, `run-log commit`, `capture-transcript`), recovery-test updates, and the standalone flush entry point.

1. Move the two entries:
   - Remove `G-Orch-4` and `G-Obs-4` from `ARCHITECTURAL_GUIDELINES.md`.
   - Do not renumber later `G-Orch-*` or `G-Obs-*` entries.
   - Add `I-Slot-1` under a new `## Panel integrity` section in `ARCHITECTURAL_INVARIANTS.md`.
   - Add `I-Outcome-1` under `## Run-log integrity`.

2. Keep invariant entry shape consistent:
   - Heading matches `INVARIANT_HEADING_RE`.
   - Body includes the prose contract.
   - Include `Evidence of violation:`.
   - Include `Mechanical backing:`.
   - For `I-Slot-1`, cite existing slot-drop backing, including `reviewer-prune-ledger.tsv`, `*-slots.ndjson`, dropped-slot sidecars, and tests in `python/tests/review/test_plan_review_round.py`, `python/tests/review/test_plan_review_panel.py`, and agent waterfall drop coverage.
   - For `I-Outcome-1`, cite the new flush-time guard, the shared pre-terminal check on all direct commit entry points, and `python/tests/report/test_run_log_flush.py` plus the updated recovery expectations in `python/tests/report/test_run_logs.py`.

3. Add shared pre-terminal label helpers (in `python/larch/report/run_log_flush.py`, imported by commit/capture callers):
   - Add `PRETERMINAL_FORBIDDEN_OUTCOME_LABELS: Final[frozenset[str]]` to `python/larch/core/config.py` with members `stalled`, `bailed`, and `bailed-needs-user-input` (per G-Cfg-1; protocol literals belong in config).
   - Add:
     - `_parse_preterminal_outcome_label(text: str) -> str | None` — scan **all lines** for the canonical run-summary heading (`line.strip().startswith("## /")`), same contract family as `final_report._summary_stalled_heading_index` but generalized for any forbidden label; extract the trailing outcome label after `: ` or ` — ` (em-dash); return `None` when no `## /` heading is found. **Do not** read the first arbitrary `##` section (FINDING_2).
     - `_parse_preterminal_outcome_label_from_run_dir(run_dir: Path) -> str | None` — when `final-summary.md` exists under `run_dir`, parse its text; return `None` when the file is missing.
     - `_check_preterminal_outcome_label(outcome: str) -> None` — accept the already-parsed label (per G-Py-5; injectable for tests) and raise `ShipError` when `outcome` is in `config.PRETERMINAL_FORBIDDEN_OUTCOME_LABELS`.
     - `_preterminal_outcome_refresh_skip(ctx: RunContext) -> RefreshSkip | None` — read the settled on-disk `final-summary.md` from `_run_log_dir(ctx)`; when a forbidden label is present, return `RefreshSkip(skipped=True, reason=config.REFRESH_SKIP_COMMIT_FAILED, error=...)` naming the rejected label and pre-terminal context; otherwise return `None`.
     - `_preterminal_outcome_commit_blocked(run_dir: Path) -> str | None` — shared boolean gate for direct-commit CLIs: return a bounded error string when the staged run_dir summary parses to a forbidden label, else `None`.

4. Wire the guard on every pre-terminal commit path:
   - **Placement in `flush_logs_pre()` (FINDING_1 placement):** never call the guard immediately after the first `_write_final_report()` inside `_stage_pre_commit()`. `_stage_pre_commit()` performs two final-report writes plus `_reconcile_stalled_summary_backstop()` between them; the guard must observe the post-reconciliation summary. In `flush_logs_pre()`, call `_preterminal_outcome_refresh_skip(ctx)` **once** after `_stage_pre_commit()` returns and after the manifest `update_manifest` block, **immediately before** `_commit_run()`; when it fires, return the `RefreshSkip` directly — do not call `_commit_run()`.
   - **RefreshSkip envelope (FINDING_4):** do not let a forbidden pre-terminal label propagate as an uncaught `ShipError` from `flush_logs_pre()`. The refresh CLI (`refresh_run_logs_main`, Step 7a, ship refresh helpers) must continue to receive structured `RefreshSkip` / `REFRESH_*` output.
   - **`larch_log_flush_main()`:** call `_preterminal_outcome_refresh_skip(ctx)` after `_stage_pre_commit(..., mode="flush")` returns and before `_commit_run()`; on forbidden labels, skip commit and emit a bounded warning (do not raise through the CLI).
   - **`larch_log_commit_main()` (FINDING_1):** before `_commit_run()`, resolve the staged run dir via `_run_dir(log_root, skill, run_id)` and call `_preterminal_outcome_commit_blocked(run_dir)`; when blocked, print a bounded warning to stderr, return non-zero exit, and do not commit. This closes the Step 7a bypass where `run-log commit` ran after `flush_logs_pre()` already refused.
   - **`capture_transcript_main()` (FINDING_3):** when `--defer-commit` is not `true` and `--no-logs-commit` is not `true`, call the same `_preterminal_outcome_commit_blocked` check on `log_root / skill / run_id` immediately before `_commit_run()`; on forbidden labels, skip commit and emit via `_capture_transcript_emit` with a bounded `commit-failed` (or dedicated pre-terminal) message — do not commit the tree.
   - **`step_7a.py` (FINDING_1 belt-and-suspenders):** after `flush_logs_pre()`, when `refresh.skipped` and `refresh.reason == config.REFRESH_SKIP_COMMIT_FAILED`, do **not** invoke `run-log commit`; keep `log_flush_status` degraded without attempting a commit that the guard would refuse anyway.
   - **Terminal carve-out:** leave post-merge `flush_logs_post()`, finalize teardown `commit_larch_logs`, and other true terminal reconciliation commit paths unguarded so legitimately ended runs may still commit final `stalled` or `bailed` summaries.

5. Add regression tests:
   - In `python/tests/report/test_run_log_flush.py`:
     - Unit-test `_check_preterminal_outcome_label` for `stalled`, `bailed`, `bailed-needs-user-input`, and allowed neutral labels.
     - Unit-test `_parse_preterminal_outcome_label` for canonical and legacy heading punctuation.
     - Unit-test that a file with a prefixed `## Architectural` (or other non-run) section **before** the `## /implement ...` heading still parses only the run heading label (FINDING_2).
     - Cover `flush_logs_pre()` refusing commit when the settled `final-summary.md` contains `: stalled` or `: bailed`, asserting `skip.skipped` and `skip.reason == config.REFRESH_SKIP_COMMIT_FAILED` (not a raised `ShipError`).
     - Cover an allowed neutral label such as `shipping` or `pr-created` still committing.
     - Cover `larch_log_flush_main()` skipping commit when the settled summary has a forbidden label.
   - In `python/tests/report/test_run_logs.py`:
     - Rewrite `test_flush_logs_pre_rewrites_stalled_summary_after_clean_pr_recovery` so the **first** `flush_logs_pre(..., strict_final_report=True)` returns `RefreshSkip(skipped=True, reason=config.REFRESH_SKIP_COMMIT_FAILED)` while the on-disk summary may still contain `: stalled` before recovery; keep the **second** refresh asserting recovery to `: pr-created` / neutral outcome after stall state clears.
     - Add `test_larch_log_commit_main_refuses_preterminal_stalled_summary` (or equivalent): seed a forbidden heading under the staged `log_root` implement run dir and assert `larch_log_commit_main` does not commit (non-zero rc, no commit sha).
     - Add `test_capture_transcript_main_refuses_preterminal_stalled_summary` (or equivalent): with `--defer-commit false`, assert transcript capture does not commit when `final-summary.md` has a forbidden label.
   - In `python/tests/implement/test_step_7a.py` and `skills/implement/scripts/test-step-7a.sh`: assert Step 7a does not invoke `run-log commit` when `flush_logs_pre` returns `REFRESH_SKIP_COMMIT_FAILED` for a pre-terminal stalled summary.

6. Sweep references:
   - Run `rg "G-Orch-4|G-Obs-4" docs/ skills/ python/ README.md SECURITY.md .github/workflows ARCHITECTURAL_GUIDELINES.md ARCHITECTURAL_INVARIANTS.md`.
   - Update any prose or fixtures that cite the old guideline IDs to `I-Slot-1` / `I-Outcome-1` where appropriate.
   - Expected result after edits: no old IDs in `ARCHITECTURAL_GUIDELINES.md`; no old IDs in runtime docs, skills, or Python references unless a test fixture explicitly documents history.

## Files to modify/create

### UPDATED: ARCHITECTURAL_GUIDELINES.md

Remove only the `G-Orch-4` and `G-Obs-4` entries.

Leave `G-Orch-5`, `G-Orch-6`, and `G-Obs-5` headings unchanged. Do not renumber.

### UPDATED: ARCHITECTURAL_INVARIANTS.md

Add `I-Slot-1` under a new `## Panel integrity` section.

Add `I-Outcome-1` under `## Run-log integrity`.

Keep current invariant prose style. Include real mechanical backing for each entry.

### UPDATED: python/larch/core/config.py

Add `PRETERMINAL_FORBIDDEN_OUTCOME_LABELS: Final[frozenset[str]]` constant containing `stalled`, `bailed`, and `bailed-needs-user-input`.

### UPDATED: python/larch/report/run_log_flush.py

Add shared parse/check/enforcement helpers (`_parse_preterminal_outcome_label`, `_parse_preterminal_outcome_label_from_run_dir`, `_check_preterminal_outcome_label`, `_preterminal_outcome_refresh_skip`, `_preterminal_outcome_commit_blocked`).

Wire `_preterminal_outcome_refresh_skip(ctx)` into `flush_logs_pre()` after full `_stage_pre_commit()` staging completes and immediately before `_commit_run()`.

Wire the same enforcement into `larch_log_flush_main()` immediately before `_commit_run()`.

Wire the same enforcement into `capture_transcript_main()` immediately before `_commit_run()` when commit is not deferred/suppressed.

Return `RefreshSkip` for forbidden pre-terminal labels on the refresh path; reserve direct `ShipError` from `_check_preterminal_outcome_label` for unit tests and internal callers that translate to `RefreshSkip` or bounded CLI refusal.

Do not change outcome normalization broadly unless needed for label parsing.

### UPDATED: python/larch/report/run_log_commit.py

Import and call `_preterminal_outcome_commit_blocked` in `larch_log_commit_main()` immediately before `_commit_run()` for implement staging trees.

Refuse commit with bounded stderr warning and non-zero exit when a forbidden pre-terminal label is present.

### UPDATED: python/larch/implement/step_7a.py

After `flush_logs_pre()`, skip the `run-log commit` subprocess when `refresh.skipped` and `refresh.reason == config.REFRESH_SKIP_COMMIT_FAILED`.

### UPDATED: python/tests/report/test_run_log_flush.py

Add focused unit and integration tests for parse (including prefixed non-run `##` sections), check, `flush_logs_pre()` RefreshSkip refusal, allowed neutral commit, and `larch_log_flush_main()` skip behavior.

### UPDATED: python/tests/report/test_run_logs.py

Rewrite `test_flush_logs_pre_rewrites_stalled_summary_after_clean_pr_recovery` (and any closely coupled assertions) so pre-terminal stalled summaries refuse the first commit under I-Outcome-1 while the existing two-phase recovery flow still commits `pr-created` after stall clears.

Add regression tests for `larch_log_commit_main` and `capture_transcript_main` pre-terminal refusal paths.

### UPDATED: python/tests/implement/test_step_7a.py

Add coverage that Step 7a does not fall through to `run-log commit` after a pre-terminal `REFRESH_SKIP_COMMIT_FAILED` refresh skip.

### UPDATED: skills/implement/scripts/test-step-7a.sh

Extend harness expectations so pre-terminal refresh refusal does not invoke `run-log commit`.

## Edge cases

- A summary heading may use legacy punctuation (`: stalled` or ` — stalled`). Parse only lines matching `startswith("## /")`; ignore earlier `##` sections such as architecture diagrams or other headings (FINDING_2).
- `bailed-needs-user-input` is also a forbidden pre-terminal label.
- Missing `final-summary.md` must not become a new failure in this guard. Existing completeness checks own missing artifacts; `_preterminal_outcome_refresh_skip` and `_preterminal_outcome_commit_blocked` return `None` / no block.
- `_reconcile_stalled_summary_backstop()` may rewrite manifest-only recoveries between the two final-report writes. The guard must run only after that reconciliation and the second write have settled.
- Terminal post-merge reconciliation and finalize teardown must still allow final failure labels where the run has actually ended.
- `larch_log_flush_main()` and `capture_transcript_main()` must not crash their CLIs; skip commit with a bounded warning when the guard fires.
- Step 7a must not treat a pre-terminal refresh refusal as grounds to retry commit via the direct `run-log commit` path.

## Failure modes

- The guard runs before `_reconcile_stalled_summary_backstop()` or the second final-report write, rejecting recoverable runs or missing labels reintroduced by later staging.
- The guard raises `ShipError` through `flush_logs_pre()` instead of returning `RefreshSkip`, breaking `python/cli.py run-log refresh` wire output.
- The guard runs on terminal teardown paths and blocks legitimate final reports.
- `larch_log_commit_main()` or `capture_transcript_main()` remain unguarded, allowing direct commit of forbidden pre-terminal labels after refresh refusal (FINDING_1, FINDING_3).
- Step 7a still calls `run-log commit` after `flush_logs_pre()` returns `REFRESH_SKIP_COMMIT_FAILED`, relying on downstream failure instead of skipping (FINDING_1).
- The parser reads the first `##` heading instead of the `## /...` run heading, letting forbidden labels slip through or blocking neutral runs (FINDING_2).
- Existing recovery tests still expect the first strict flush to commit `: stalled`, causing CI failure after the guard lands.
- The invariant entry names a backstop that does not exist.
- Reference sweep misses old IDs in fixtures or docs.

## Testing strategy

Run targeted checks only:

```bash
python3 python/cli.py architectural-invariants read
```

Verify it reports 6 entries including `I-Slot-1` and `I-Outcome-1`.

python3 -m pytest python/tests/report/test_run_log_flush.py python/tests/report/test_run_logs.py -k "preterminal or stalled_summary or flush_logs_pre_rewrites_stalled or larch_log_commit_main_refuses or capture_transcript_main_refuses"

python3 -m pytest python/tests/implement/test_step_7a.py -k "preterminal or commit_failed"

skills/implement/scripts/test-step-7a.sh

Run the reference sweep:

rg "G-Orch-4|G-Obs-4" docs/ skills/ python/ README.md SECURITY.md .github/workflows ARCHITECTURAL_GUIDELINES.md ARCHITECTURAL_INVARIANTS.md

If any panel-slot backing prose is changed or questioned, also run:

python3 -m pytest python/tests/review/test_plan_review_round.py python/tests/review/test_plan_review_panel.py python/tests/agents/test_agent_waterfall.py

difficulty: MODERATE
diff_lines: 265
