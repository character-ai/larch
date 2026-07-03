### FINDING_1: Register `difficulty resolve-panel`
- **Reviewer(s)**: Cursor-Innovation, Cursor-Pragmatic
- **Severity**: important
- **Concern**: The CLI dispatch table is missing the `difficulty resolve-panel` entry, so shell wrappers and `/review` cannot invoke the resolver at runtime.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Innovation: Add `### UPDATED: python/larch/cli.py` registering `("difficulty", "resolve-panel")` to `resolve_panel_main` (or the planned entrypoint) in both dispatch maps, matching G-CLI-1.
  - From Cursor-Pragmatic: Add `### UPDATED: python/larch/cli.py` and register `("difficulty", "resolve-panel")` to `resolve_panel_main` per G-CLI-1, with a focused registry test if the repo pattern requires it.

### FINDING_2: Persist implement difficulty override through run-flags
- **Reviewer(s)**: Cursor-Innovation, Codex-Innovation, Cursor-Pragmatic, Cursor-Requirements
- **Severity**: important
- **Concern**: The operator difficulty override is planned to ride through `persist-run-flags`, but the current run-flag key set excludes it. As a result, bootstrap can write the override and Step 5 still cannot recover it from `run-flags.sh`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Innovation: Extend `persist_run_flags_main` with optional `--difficulty`, add `DIFFICULTY_OVERRIDE` to `RUN_FLAG_KEYS`, thread the flag through `bootstrap._persist_run_flags` / `invoke_main`, and read it in `step-5-review.sh` / `step-5-resume.sh`.
  - From Codex-Innovation: Extend session persist-run-flags and RUN_FLAG_KEYS for DIFFICULTY_OVERRIDE, pass it from bootstrap, and have Step 5 read that exact key
  - From Cursor-Pragmatic: Extend `RUN_FLAG_KEYS` and `persist_run_flags_main` with optional `--difficulty-override` (empty or `TRIVIAL|MODERATE|HARD`); thread it from `bootstrap.invoke` / `_persist_run_flags`; document the same contract in `bootstrap.py` and `skills/implement/scripts/step-0-bootstrap.sh`. Alternatively drop the run-flags read path and have Step 5 read override state only from `difficulty-rating.json`, but pick one source and wire it end-to-end.
  - From Cursor-Requirements: Add `DIFFICULTY_OVERRIDE` to `RUN_FLAG_KEYS`, extend `persist_run_flags_main` and `bootstrap invoke/BootstrapOptions`, and thread the value through `step-0-bootstrap.sh` like other run flags.

### FINDING_3: Preserve `difficulty_override` on run-params refresh
- **Reviewer(s)**: Cursor-Innovation, Cursor-Pragmatic, Cursor-Requirements
- **Severity**: important
- **Concern**: `write-run-params` rebuilds `run-params.json` from the current booleans only, so a stored `difficulty_override` is lost on init or resume refresh when no fresh tier flag is provided.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Innovation: When `--difficulty` is omitted, read the existing output file and carry forward `difficulty_override`; only replace it when a new valid tier is passed. Mirror resume semantics in `design_router._merge_router_flags` or stop full-replacing on resume.
  - From Cursor-Pragmatic: When `--difficulty` is absent, read existing run-params.json and carry forward difficulty_override; when present, replace it. Extend `_merge_router_flags` (or equivalent) so resume paths preserve the key unless a new valid `--difficulty` is supplied.
  - From Cursor-Requirements: When `--difficulty` is absent, read the existing file and carry `difficulty_override` forward; only overwrite it when a new valid tier is passed. Mirror the resume rule already stated for `route_main`.

### FINDING_4: Thread `--difficulty` into `init-runparams`
- **Reviewer(s)**: Cursor-Innovation, Cursor-Requirements
- **Severity**: important
- **Concern**: The Step 0 init path cannot carry a parsed difficulty override into `session write-run-params`, so `init-runparams` never reaches `run-params.json` even after argv parsing lands.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Innovation: Add `--difficulty` to `init_runparams_main`, forward it into `session write-run-params`, and extend `_step0_init_driver_cmd` to pass the parsed Step 0-pre value.
  - From Cursor-Requirements: Extend `init_runparams_main` and `_step0_init_driver_cmd` with the same `--difficulty` contract as `route_main`, and pass it through to `session write-run-params`.

### FINDING_5: Make dynamic Codex rows tier-aware
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Concern**: Dynamic Codex row assembly still hardcodes the default model role, so tier-aware reviewer-role selection is not applied consistently in either review panel.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Innovation: Thread `codex_review_model_role(tier)` (or the dispatch `--tier`) into dynamic row construction the same as static rows; lock with the planned panel-manifest tests.
  - From Cursor-Innovation: Apply the same tier→`review`/`default` mapping used for static design slots when `--tier` is HARD vs TRIVIAL/MODERATE.

### FINDING_6: Resolve bootstrap override precedence
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Concern**: Bootstrap records the operator override in more than one place without a clear precedence rule, so refresh and merge paths can diverge on which difficulty setting is authoritative.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Innovation: Pick one authoritative store (`difficulty-rating.json` after bootstrap) and drop the redundant run-flags path, or document and test strict precedence when both differ.

### FINDING_7: Preserve `override_source` during record refresh
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Concern**: Log-flush record refresh drops `override_source` from the existing difficulty record, so later writes can erase the operator origin even when the rest of the difficulty state is preserved.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Innovation: Pass through `override_source` (and post-escalation `applied_tier`) from the existing record, or route refresh through the shared merge helper planned for `write-record`.

### FINDING_8: Preserve TierResolution fields in `difficulty-rating.json`
- **Reviewer(s)**: Cursor-Pragmatic, Cursor-Requirements, Codex-Requirements
- **Severity**: important
- **Concern**: The `difficulty-rating.json` write contract does not preserve the TierResolution sidecar and resume fields, so record rewrites can lose panel tier, caps, audit state, or escalated-round state.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Pragmatic: Extend `DifficultyRecord` (or a documented wrapper schema) with the TierResolution/resume fields, and make `write-record` merge-on-existing-output preserve them unless explicitly replaced; cover with `test_difficulty.py`.
  - From Cursor-Requirements: Extend `DifficultyRecord` (or documented top-level JSON keys) with `panel_tier`, `round_cap`, `codex_model_role`, `audit_evaluated`, and `escalated_round`; teach `write-record` merge and `append_escalation` to read/write them.
  - From Codex-Requirements: Extend the record schema or merge path to preserve every TierResolution field, using one consistent JSON key style, and cover refresh-after-resolution before resume

### FINDING_9: Keep `config.py` leaf-only
- **Reviewer(s)**: Codex-Pragmatic
- **Severity**: important
- **Concern**: `config.py` is planned to import calibration/difficulty, which would create a circular dependency through `core/proc/config` and make tier literals unavailable during import.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Pragmatic: Keep config.py leaf-only; do not import calibration from config. Either move tier literals into config and import them from difficulty, or leave tier tokens in difficulty and keep only non-tier tunables in config

### FINDING_10: Use the authorized cap for design Step 3
- **Reviewer(s)**: Codex-Pragmatic, Codex-Requirements
- **Severity**: important
- **Concern**: Design Step 3 still appears to use the raw tier cap on re-entry and continuation, so a HARD run can schedule an extra round without the authorized-cap gate.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Pragmatic: Use the effective authorized cap helper for every design Step 3 entry and continuation guard, not only Gate C rendering; raw HARD cap should permit round 3 only after recorded substantiality/escalation authorization
  - From Codex-Requirements: Use the effective authorized cap in plan_review_continuation and the Step 3 pre-launch cap guard, not only Gate C rendering; add a focused HARD one-high no-round-3 case

### FINDING_11: Make escalated-round state round-specific
- **Reviewer(s)**: Codex-Requirements
- **Severity**: important
- **Concern**: The persisted escalated-round flag is not tied to the round it was earned in, so resume can treat later rounds as if the earlier escalation were still active.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Requirements: Store escalation target_round values or derive escalated_round from the current round and escalation entries, then test resume into the escalated round and the following non-escalated round

### FINDING_12:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Focus area**: architecture
- **Location**: plan.txt:Files to modify/create
- **Concern**: [SCOPE-REDUCTION] Drop resurrecting `skills/design/scripts/test-dispatch-plan-review-panel.sh`. Scenario: The harness was migrated in #3680; `make test-dispatch-plan-review-panel` already runs `python/tests/review/test_plan_review_panel.py -k 'panel_dispatch'`. Adding a new shell script duplicates coverage and ~1900 lines of churn.
- **Proposed resolution**: Remove the `### UPDATED: skills/design/scripts/test-dispatch-plan-review-panel.sh` entry; keep tier panel assertions in `python/tests/review/test_plan_review_panel.py` only.

### FINDING_13:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: nit
- **Focus area**: code-quality
- **Location**: plan.txt:MAY_UPDATE
- **Concern**: [SCOPE-REDUCTION] Fence-shape harness path is wrong in MAY_UPDATE. Scenario: `make test-implement-fence-shape` runs `scripts/test-implement-fence-shape.sh`, not `skills/implement/scripts/...`. A prose-only Step 5 edit would skip the real harness.
- **Proposed resolution**: Point `MAY_UPDATE` at `scripts/test-implement-fence-shape.sh` (or drop the MAY_UPDATE if fence literals stay unchanged). **1. risk-integration — `python/larch/cli.py`:** Prior FINDING_1 is still open. The plan names CLI registration but never lists `python/larch/cli.py` under **Files to modify/create**. **2. correctness — `session_env.py` persist-run-flags:** Implement `--difficulty` cannot reach Step 5. Bootstrap’s `_persist_run_flags` never gets a difficulty field, and `RUN_FLAG_KEYS` has no slot for it. **3. correctness — `write-run-params` / FINDING_2:** Adding `--difficulty` to `write-run-params` is not enough. Full-file rewrite on init still drops `difficulty_override` when the flag is omitted on resume or replace flows. **4. correctness — `design_router.init_runparams`:** Step 0’s init driver and `init_runparams_main` must grow matching `--difficulty` argv support, not only `route_main`. **5–6. correctness — dynamic model roles:** Tier-aware roles are easy to miss in dynamic row builders in `review_dispatch_panel.py` and `plan_review_panel.py`; both still hardcode Codex `default`. **7. architecture — dual override carriers:** Run flags plus `difficulty-rating.json` adds surface area without a stated winner. Minimum-change path: bootstrap writes the record once; Step 5 reads the record only. **8. risk-integration — `run_log_flush.py`:** FINDING_13 needs an explicit `override_source` pass-through in `_refresh_difficulty_record`, not only CLI-side merge. **9–10. scope reduction:** Do not recreate the migrated design dispatch shell harness; fix the fence-shape `MAY_UPDATE` path to `scripts/test-implement-fence-shape.sh`. Accepted ledger items (3, 5, 8–15, 17–18, 21–24) look addressed in the current plan text; not re-raised unless implementation skips the named files.

### FINDING_14:
- **Reviewer(s)**: Codex-Innovation
- **Severity**: important
- **Focus area**: correctness
- **Location**: plan.txt:10-12,37-45
- **Concern**: [SCOPE-REDUCTION] Audit still overrides an explicit operator difficulty override. Scenario: An operator runs /implement, /review, or /design with --difficulty TRIVIAL to force the cheap tier, but the planned 1:30 audit upgrades it to HARD even though the scope says --difficulty override wins and prior accepted findings required preserving that contract
- **Proposed resolution**: Do not run the audit when override_source=operator; log override_source=operator and keep the operator-selected panel tier

### FINDING_15:
- **Reviewer(s)**: Codex-Innovation
- **Severity**: important
- **Focus area**: correctness
- **Location**: plan.txt:14,111-113
- **Concern**: [SCOPE-REDUCTION] Design escalation still skips the next-tier contract. Scenario: /design at TRIVIAL with two high accepted findings jumps directly to HARD, skipping MODERATE, despite the scope saying escalated rounds run the next tier's full panel
- **Proposed resolution**: Make design escalation use the same one-tier ladder as code review; TRIVIAL escalates to MODERATE and MODERATE escalates to HARD

### FINDING_16:
- **Reviewer(s)**: Codex-Innovation
- **Severity**: important
- **Focus area**: architecture
- **Location**: python/larch/core/config.py:18-23
- **Concern**: [SCOPE-REDUCTION] Reusing calibration difficulty tokens from core config violates the import layering ratchet. Scenario: Implementing DIFFICULTY_TIER_* in larch.core.config by importing larch.calibration.difficulty adds a core to domain import; the layering lint explicitly treats core importing domain packages as a violation, so py-lint can fail before the feature ships
- **Proposed resolution**: Drop the config tier aliases or make config the lower-tier source and have calibration import from config; do not import larch.calibration from larch.core.config

### FINDING_17:
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: important
- **Focus area**: architecture
- **Location**: skills/design/scripts/test-dispatch-plan-review-panel.sh
- **Concern**: [SCOPE-REDUCTION] Drop the retired shell harness row; tier panel checks belong in pytest only. Scenario: The plan lists `### UPDATED: skills/design/scripts/test-dispatch-plan-review-panel.sh`, but that path is absent (migrated per `python/migrated-scripts.tsv`). `make test-dispatch-plan-review-panel` already runs `python/tests/review/test_plan_review_panel.py -k 'panel_dispatch and not usage'`. Adding a new shell harness duplicates the pytest target and expands scope without new behavior.
- **Proposed resolution**: Remove the shell harness file entry; keep tier/model-role assertions solely in `python/tests/review/test_plan_review_panel.py`, which the Makefile target already exercises. [OUT_OF_SCOPE] python/tests/design/test_design_argv.py — Dedicated `--difficulty` argv tests would catch duplicate/invalid flags, but the plan already updates `design_argv.py` and broader tier behavior is covered elsewhere; optional hardening only. [OUT_OF_SCOPE] python/larch/implement/dispatch_step2.py:299-337 — Step 2 `write-record` can clobber bootstrap override before merge lands; FINDING_13’s global merge-on-existing-output mitigation is sufficient if implemented as specified. [OUT_OF_SCOPE] skills/review/SKILL.md:47 — `PANEL_SHAPE=simple|hard` prose will need a doc refresh when dispatch emits `singles|pairs`, but planned pytest and skill updates already cover the runtime contract.

### FINDING_18:
- **Reviewer(s)**: Codex-Pragmatic
- **Severity**: important
- **Focus area**: correctness
- **Location**: plan.txt:12
- **Concern**: [SCOPE-REDUCTION] Operator overrides are still audit-upgraded despite the issue contract that --difficulty wins. Scenario: A user runs /implement --difficulty TRIVIAL to force the cheap tier, the 1:30 audit fires, and the plan runs HARD anyway while claiming the override won
- **Proposed resolution**: Make maybe_audit_upgrade skip when override_source=operator; log override_source=operator and do not set audit_upgrade for explicit overrides

### FINDING_19:
- **Reviewer(s)**: Codex-Pragmatic
- **Severity**: important
- **Focus area**: correctness
- **Location**: plan.txt:14
- **Concern**: [SCOPE-REDUCTION] The prior design-escalation finding is not fixed because /design still jumps not-HARD directly to HARD. Scenario: /design --difficulty TRIVIAL with two high findings in round 1 skips the MODERATE tier and immediately unlocks the HARD model and cap, over-serving the next-tier ladder
- **Proposed resolution**: Use next_tier for design too; TRIVIAL escalates to MODERATE first, and HARD is reached only from a later substantial MODERATE round

### FINDING_20:
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: scripts/test-implement-fence-shape.sh
- **Concern**: [SCOPE-REDUCTION] The fence-shape harness path in the plan is wrong.. Scenario: The MAY_UPDATE entry points at `skills/implement/scripts/test-implement-fence-shape.sh`, but `make test-implement-fence-shape` runs `scripts/test-implement-fence-shape.sh`. Step 5 SKILL fence edits would miss the real harness.
- **Proposed resolution**: Change the plan entry to `scripts/test-implement-fence-shape.sh` and note `EXPECTED_OLD`/`EXPECTED_NEW` updates only if Step 5 fence literals change.

### FINDING_21:
- **Reviewer(s)**: Codex-Requirements
- **Severity**: important
- **Focus area**: correctness
- **Location**: plan.txt:10-12
- **Concern**: [SCOPE-REDUCTION] Prior override finding remains incomplete: audit still upgrades explicit operator overrides. Scenario: An operator runs /design --difficulty TRIVIAL to force the cheap tier, the 1:30 audit fires, and the plan runs HARD anyway, violating the acceptance that --difficulty override wins and over-serving the requested minimum-change control
- **Proposed resolution**: Make operator overrides disable audit upgrades for that run, while still logging override_source=operator; update helper behavior, docs, and tests that currently require override plus audit to run HARD

### FINDING_22:
- **Reviewer(s)**: Codex-Requirements
- **Severity**: important
- **Focus area**: correctness
- **Location**: plan.txt:14,113,257
- **Concern**: [SCOPE-REDUCTION] Prior design-escalation finding remains incomplete: TRIVIAL design still jumps directly to HARD. Scenario: A TRIVIAL design round with two high accepted findings skips MODERATE and unlocks HARD model role and cap immediately, contradicting the next-tier escalation contract and adding unnecessary cost
- **Proposed resolution**: Use next_tier for design too; TRIVIAL escalates to MODERATE even if the v1 panel shape is identical, and only MODERATE escalates to HARD
