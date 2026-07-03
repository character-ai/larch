### [Plan Review] FINDING_6

### FINDING_6: Resolve bootstrap override precedence
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Concern**: Bootstrap records the operator override in more than one place without a clear precedence rule, so refresh and merge paths can diverge on which difficulty setting is authoritative.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Innovation: Pick one authoritative store (`difficulty-rating.json` after bootstrap) and drop the redundant run-flags path, or document and test strict precedence when both differ.


### [Plan Review] FINDING_12

### FINDING_12:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Focus area**: architecture
- **Location**: plan.txt:Files to modify/create
- **Concern**: [SCOPE-REDUCTION] Drop resurrecting `skills/design/scripts/test-dispatch-plan-review-panel.sh`. Scenario: The harness was migrated in #3680; `make test-dispatch-plan-review-panel` already runs `python/tests/review/test_plan_review_panel.py -k 'panel_dispatch'`. Adding a new shell script duplicates coverage and ~1900 lines of churn.
- **Proposed resolution**: Remove the `### UPDATED: skills/design/scripts/test-dispatch-plan-review-panel.sh` entry; keep tier panel assertions in `python/tests/review/test_plan_review_panel.py` only.


### [Plan Review] FINDING_13

### FINDING_13:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: nit
- **Focus area**: code-quality
- **Location**: plan.txt:MAY_UPDATE
- **Concern**: [SCOPE-REDUCTION] Fence-shape harness path is wrong in MAY_UPDATE. Scenario: `make test-implement-fence-shape` runs `scripts/test-implement-fence-shape.sh`, not `skills/implement/scripts/...`. A prose-only Step 5 edit would skip the real harness.
- **Proposed resolution**: Point `MAY_UPDATE` at `scripts/test-implement-fence-shape.sh` (or drop the MAY_UPDATE if fence literals stay unchanged). **1. risk-integration — `python/larch/cli.py`:** Prior FINDING_1 is still open. The plan names CLI registration but never lists `python/larch/cli.py` under **Files to modify/create**. **2. correctness — `session_env.py` persist-run-flags:** Implement `--difficulty` cannot reach Step 5. Bootstrap’s `_persist_run_flags` never gets a difficulty field, and `RUN_FLAG_KEYS` has no slot for it. **3. correctness — `write-run-params` / FINDING_2:** Adding `--difficulty` to `write-run-params` is not enough. Full-file rewrite on init still drops `difficulty_override` when the flag is omitted on resume or replace flows. **4. correctness — `design_router.init_runparams`:** Step 0’s init driver and `init_runparams_main` must grow matching `--difficulty` argv support, not only `route_main`. **5–6. correctness — dynamic model roles:** Tier-aware roles are easy to miss in dynamic row builders in `review_dispatch_panel.py` and `plan_review_panel.py`; both still hardcode Codex `default`. **7. architecture — dual override carriers:** Run flags plus `difficulty-rating.json` adds surface area without a stated winner. Minimum-change path: bootstrap writes the record once; Step 5 reads the record only. **8. risk-integration — `run_log_flush.py`:** FINDING_13 needs an explicit `override_source` pass-through in `_refresh_difficulty_record`, not only CLI-side merge. **9–10. scope reduction:** Do not recreate the migrated design dispatch shell harness; fix the fence-shape `MAY_UPDATE` path to `scripts/test-implement-fence-shape.sh`. Accepted ledger items (3, 5, 8–15, 17–18, 21–24) look addressed in the current plan text; not re-raised unless implementation skips the named files.


### [Plan Review] FINDING_17

### FINDING_17:
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: important
- **Focus area**: architecture
- **Location**: skills/design/scripts/test-dispatch-plan-review-panel.sh
- **Concern**: [SCOPE-REDUCTION] Drop the retired shell harness row; tier panel checks belong in pytest only. Scenario: The plan lists `### UPDATED: skills/design/scripts/test-dispatch-plan-review-panel.sh`, but that path is absent (migrated per `python/migrated-scripts.tsv`). `make test-dispatch-plan-review-panel` already runs `python/tests/review/test_plan_review_panel.py -k 'panel_dispatch and not usage'`. Adding a new shell harness duplicates the pytest target and expands scope without new behavior.
- **Proposed resolution**: Remove the shell harness file entry; keep tier/model-role assertions solely in `python/tests/review/test_plan_review_panel.py`, which the Makefile target already exercises. [OUT_OF_SCOPE] python/tests/design/test_design_argv.py — Dedicated `--difficulty` argv tests would catch duplicate/invalid flags, but the plan already updates `design_argv.py` and broader tier behavior is covered elsewhere; optional hardening only. [OUT_OF_SCOPE] python/larch/implement/dispatch_step2.py:299-337 — Step 2 `write-record` can clobber bootstrap override before merge lands; FINDING_13’s global merge-on-existing-output mitigation is sufficient if implemented as specified. [OUT_OF_SCOPE] skills/review/SKILL.md:47 — `PANEL_SHAPE=simple|hard` prose will need a doc refresh when dispatch emits `singles|pairs`, but planned pytest and skill updates already cover the runtime contract.


### [Plan Review] FINDING_20

### FINDING_20:
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: scripts/test-implement-fence-shape.sh
- **Concern**: [SCOPE-REDUCTION] The fence-shape harness path in the plan is wrong.. Scenario: The MAY_UPDATE entry points at `skills/implement/scripts/test-implement-fence-shape.sh`, but `make test-implement-fence-shape` runs `scripts/test-implement-fence-shape.sh`. Step 5 SKILL fence edits would miss the real harness.
- **Proposed resolution**: Change the plan entry to `scripts/test-implement-fence-shape.sh` and note `EXPECTED_OLD`/`EXPECTED_NEW` updates only if Step 5 fence literals change.


