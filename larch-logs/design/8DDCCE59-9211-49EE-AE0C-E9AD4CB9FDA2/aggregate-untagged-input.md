### FINDING_1:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: python/larch/cli.py:51-56
- **Concern**: [PRIOR INCOMPLETE] Add `difficulty resolve-panel` to the CLI dispatch table. Scenario: The plan adds `difficulty resolve-panel` and `/review` calls it before the loop, but `python/larch/cli.py` still registers only validate/write/render verbs. Shell wrappers cannot invoke the resolver and tier wiring fails at runtime.
- **Proposed resolution**: Add `### UPDATED: python/larch/cli.py` registering `("difficulty", "resolve-panel")` to `resolve_panel_main` (or the planned entrypoint) in both dispatch maps, matching G-CLI-1.

### FINDING_2:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/larch/state/session_env.py:73-1272
- **Concern**: [PRIOR INCOMPLETE] Wire `/implement --difficulty` through `persist-run-flags`. Scenario: The plan seeds `override_source=operator` in bootstrap and has `step-5-review.sh` read bootstrap run flags, but `RUN_FLAG_KEYS` and `persist_run_flags_main` only cover force/self-review flags. The override never reaches `run-flags.sh` or Step 5 resume fences.
- **Proposed resolution**: Extend `persist_run_flags_main` with optional `--difficulty`, add `DIFFICULTY_OVERRIDE` to `RUN_FLAG_KEYS`, thread the flag through `bootstrap._persist_run_flags` / `invoke_main`, and read it in `step-5-review.sh` / `step-5-resume.sh`.

### FINDING_3:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/larch/state/session_env.py:1280-1321
- **Concern**: [PRIOR INCOMPLETE] Preserve `difficulty_override` across `write-run-params` refresh. Scenario: `write_run_params_main` rebuilds `run-params.json` from only four booleans. `init_runparams_main` always calls it on proceed/resume paths, so a stored `difficulty_override` is erased whenever init reruns without a fresh `--difficulty`.
- **Proposed resolution**: When `--difficulty` is omitted, read the existing output file and carry forward `difficulty_override`; only replace it when a new valid tier is passed. Mirror resume semantics in `design_router._merge_router_flags` or stop full-replacing on resume.

### FINDING_4:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/larch/design/design_router.py:168-270
- **Concern**: `init-runparams` must accept and forward `--difficulty`. Scenario: `design_step0._step0_init_driver_cmd` has no difficulty arg today, and `init_runparams_main` rejects unknown flags. Step 0 cannot reach `run-params.json` even after argv parsing is added.
- **Proposed resolution**: Add `--difficulty` to `init_runparams_main`, forward it into `session write-run-params`, and extend `_step0_init_driver_cmd` to pass the parsed Step 0-pre value.

### FINDING_5:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/larch/review/review_dispatch_panel.py:360-374
- **Concern**: Dynamic Codex rows ignore tier model-role policy. Scenario: Static rows get tier-aware roles in the plan, but `_append_dynamic_rows` still hardcodes `model_role: default` for every dynamic Codex slot. MODERATE/Trivial runs would still launch gpt-5.5 on dynamic archetypes.
- **Proposed resolution**: Thread `codex_review_model_role(tier)` (or the dispatch `--tier`) into dynamic row construction the same as static rows; lock with the planned panel-manifest tests.

### FINDING_6:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/larch/review/plan_review_panel.py:335-338
- **Concern**: Design dynamic Codex rows also hardcode `default` model role. Scenario: Plan-review dynamic slot assembly sets `row["model_role"] = "default"` unconditionally. HARD design escalation would still run mini Codex on dynamic plan-review slots.
- **Proposed resolution**: Apply the same tier→`review`/`default` mapping used for static design slots when `--tier` is HARD vs TRIVIAL/MODERATE.

### FINDING_7:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Focus area**: architecture
- **Location**: python/larch/state/bootstrap.py:577-600
- **Concern**: Implement override has two competing carriers without precedence. Scenario: The plan writes the operator override into bootstrap run flags and into initial `difficulty-rating.json`, while Step 5 also resolves from the record sidecar. Divergent values are possible after refresh/merge paths.
- **Proposed resolution**: Pick one authoritative store (`difficulty-rating.json` after bootstrap) and drop the redundant run-flags path, or document and test strict precedence when both differ.

### FINDING_8:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: python/larch/report/run_log_flush.py:490-508
- **Concern**: Record refresh must preserve `override_source`, not only audit/escalations. Scenario: `_refresh_difficulty_record` forwards `audit_upgrade` and `escalations` but omits `override_source` before `build_record`, so floor logic can replace `operator` during log flush despite FINDING_13.
- **Proposed resolution**: Pass through `override_source` (and post-escalation `applied_tier`) from the existing record, or route refresh through the shared merge helper planned for `write-record`.

### FINDING_13:
- **Reviewer(s)**: Codex-Innovation
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: python/larch/state/session_env.py:73,1240-1280
- **Concern**: Implement difficulty override cannot be persisted in run-flags with the planned file set. Scenario: Step 0 bootstrap is planned to write the /implement override into run-flags, but session persist-run-flags currently allows only FORCE_REQUESTED, SELF_REVIEW_REQUESTED, SELF_IMPLEMENT_REQUESTED, QUICK_MODE, and NO_ISSUES; adding DIFFICULTY_OVERRIDE only in bootstrap either fails validation or drops the value before Step 5 reads it
- **Proposed resolution**: Extend session persist-run-flags and RUN_FLAG_KEYS for DIFFICULTY_OVERRIDE, pass it from bootstrap, and have Step 5 read that exact key

### FINDING_15:
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/larch/state/session_env.py:73-74,1240-1277
- **Concern**: Wire `/implement --difficulty` through `persist-run-flags`, not only design `write-run-params`. Scenario: The plan says bootstrap writes `difficulty_override` into existing run flags and `step-5-review.sh` reads it from `$IMPLEMENT_TMPDIR/run-flags.sh`, but `RUN_FLAG_KEYS` and `persist_run_flags_main` accept only the five legacy flags and always rewrite `run-flags.sh` without a difficulty key. Step 5 never receives the operator override.
- **Proposed resolution**: Extend `RUN_FLAG_KEYS` and `persist_run_flags_main` with optional `--difficulty-override` (empty or `TRIVIAL|MODERATE|HARD`); thread it from `bootstrap.invoke` / `_persist_run_flags`; document the same contract in `bootstrap.py` and `skills/implement/scripts/step-0-bootstrap.sh`. Alternatively drop the run-flags read path and have Step 5 read override state only from `difficulty-rating.json`, but pick one source and wire it end-to-end.

### FINDING_16:
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/larch/cli.py:51-56
- **Concern**: Register `difficulty resolve-panel` in the CLI map. Scenario: The plan adds `difficulty resolve-panel` and `/review` plus `heavy-worker.md` call it before the loop, but `python/larch/cli.py` registers no `resolve-panel` verb today, so shell wrappers will fail at runtime.
- **Proposed resolution**: Add `### UPDATED: python/larch/cli.py` and register `("difficulty", "resolve-panel")` to `resolve_panel_main` per G-CLI-1, with a focused registry test if the repo pattern requires it.

### FINDING_17:
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/larch/state/session_env.py:1314-1321
- **Concern**: Preserve `difficulty_override` when `write-run-params` omits `--difficulty`. Scenario: `write_run_params_main` rebuilds `run-params.json` from four booleans only. `design_router.init_runparams_main` always calls it on proceed/init, and resume merge (`_merge_router_flags`) ORs only the legacy booleans. A rerun without a fresh `--difficulty` drops a stored override even though the plan requires resume to keep it.
- **Proposed resolution**: When `--difficulty` is absent, read existing `run-params.json` and carry forward `difficulty_override`; when present, replace it. Extend `_merge_router_flags` (or equivalent) so resume paths preserve the key unless a new valid `--difficulty` is supplied.

### FINDING_18:
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: python/larch/calibration/difficulty.py:68-84,303-305
- **Concern**: TierResolution sidecar fields need an explicit JSON persistence contract. Scenario: The plan persists `PANEL_TIER`, `ROUND_CAP`, `CODEX_MODEL_ROLE`, `AUDIT_EVALUATED`, and resume `escalated_round` in `difficulty-rating.json`, but `DifficultyRecord` and `write_record()` serialize only the dataclass via `asdict` and replace the whole file. Any `write-record` refresh (bootstrap, Step 2 dispatch, publish, log flush) can drop those fields and force audit re-roll or wrong caps on resume.
- **Proposed resolution**: Extend `DifficultyRecord` (or a documented wrapper schema) with the TierResolution/resume fields, and make `write-record` merge-on-existing-output preserve them unless explicitly replaced; cover with `test_difficulty.py`.

### FINDING_22:
- **Reviewer(s)**: Codex-Pragmatic
- **Severity**: important
- **Focus area**: architecture
- **Location**: plan.txt:22
- **Concern**: Planned config constants can create a calibration/core circular import. Scenario: Importing larch.calibration.difficulty loads larch.core.proc, proc imports config, and the planned config import of calibration.difficulty would read TRIVIAL before difficulty.py defines it
- **Proposed resolution**: Keep config.py leaf-only; do not import calibration from config. Either move tier literals into config and import them from difficulty, or leave tier tokens in difficulty and keep only non-tier tunables in config

### FINDING_23:
- **Reviewer(s)**: Codex-Pragmatic
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/larch/review/plan_review.py:362-374
- **Concern**: Design Step 3 launch guards still use the raw tier cap instead of the authorized cap. Scenario: An initial HARD design run can complete two non-substantial rounds, choose Discuss further at Gate C, then Gate A Ready for review re-enters Step 3 and launches round 3 because review_count is below the raw HARD cap
- **Proposed resolution**: Use the effective authorized cap helper for every design Step 3 entry and continuation guard, not only Gate C rendering; raw HARD cap should permit round 3 only after recorded substantiality/escalation authorization

### FINDING_24:
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/larch/state/session_env.py:1280-1321
- **Concern**: [ALREADY_ADDRESSED] `write-run-params` still replaces `run-params.json` without preserving `difficulty_override` when `--difficulty` is omitted.. Scenario: The plan adds `--difficulty` to `session write-run-params`, but `init_runparams_main` still writes only the four boolean keys. Any init refresh without a new flag drops a prior `/design --difficulty` override from `run-params.json`.
- **Proposed resolution**: When `--difficulty` is absent, read the existing file and carry `difficulty_override` forward; only overwrite it when a new valid tier is passed. Mirror the resume rule already stated for `route_main`.

### FINDING_25:
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/larch/design/design_router.py:168-284
- **Concern**: `init_runparams_main` is not tasked to parse or forward `--difficulty` into `write-run-params`.. Scenario: The plan wires `--difficulty` through `design_argv.py`, `PARSED_ENV_KEYS`, `step0_route_main`, and `route_main`, but `init_runparams_main` has no `--difficulty` token and `_step0_init_driver_cmd` cannot reach `run-params.json` on the init path.
- **Proposed resolution**: Extend `init_runparams_main` and `_step0_init_driver_cmd` with the same `--difficulty` contract as `route_main`, and pass it through to `session write-run-params`.

### FINDING_26:
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/larch/state/session_env.py:73,1240-1273
- **Concern**: Implement `--difficulty` persistence is incomplete without `persist-run-flags` / `RUN_FLAG_KEYS` updates.. Scenario: The plan says bootstrap should write `difficulty_override` into run flags, but `_persist_run_flags` only forwards the five existing keys and `RUN_FLAG_KEYS` rejects anything else. Step 5 resume cannot read a stable override from `run-flags.sh`.
- **Proposed resolution**: Add `DIFFICULTY_OVERRIDE` to `RUN_FLAG_KEYS`, extend `persist_run_flags_main` and `bootstrap invoke`/`BootstrapOptions`, and thread the value through `step-0-bootstrap.sh` like other run flags.

### FINDING_27:
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/larch/calibration/difficulty.py:68-85
- **Concern**: Resume panel state fields are not part of the `difficulty-rating.json` write contract.. Scenario: The plan requires resume to load `applied_tier`, `audit_upgrade`, `escalations`, and `escalated_round`, and to persist `PANEL_TIER`, `ROUND_CAP`, and `CODEX_MODEL_ROLE`, but `DifficultyRecord` has none of those keys and merge-on-write only names `applied_tier`.
- **Proposed resolution**: Extend `DifficultyRecord` (or documented top-level JSON keys) with `panel_tier`, `round_cap`, `codex_model_role`, `audit_evaluated`, and `escalated_round`; teach `write-record` merge and `append_escalation` to read/write them.

### FINDING_31:
- **Reviewer(s)**: Codex-Requirements
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: plan.txt:47,157,173
- **Concern**: The sidecar merge only names applied_tier, not the full persisted TierResolution fields. Scenario: resolve_panel_tier persists PANEL_TIER, ROUND_CAP, CODEX_MODEL_ROLE, and AUDIT_EVALUATED, then a later difficulty write-record or run-log refresh can rewrite difficulty-rating.json while preserving only applied_tier, override_source, audit_upgrade, and escalations; resume paths then lose the resolved cap/model state they must not reroll
- **Proposed resolution**: Extend the record schema or merge path to preserve every TierResolution field, using one consistent JSON key style, and cover refresh-after-resolution before resume

### FINDING_32:
- **Reviewer(s)**: Codex-Requirements
- **Severity**: important
- **Focus area**: correctness
- **Location**: plan.txt:105,111,120
- **Concern**: Design continuation still appears to use the raw tier cap instead of the authorized cap. Scenario: A run starting at HARD can finish round 2 with only one high accepted finding; because the raw cap is 3, plan_review_continuation can schedule round 3 even though no >=2-high substantiality reason was recorded
- **Proposed resolution**: Use the effective authorized cap in plan_review_continuation and the Step 3 pre-launch cap guard, not only Gate C rendering; add a focused HARD one-high no-round-3 case

### FINDING_33:
- **Reviewer(s)**: Codex-Requirements
- **Severity**: important
- **Focus area**: correctness
- **Location**: plan.txt:89-90,173
- **Concern**: Escalated-round state is not round-specific. Scenario: After round 1 escalates, resume into round 2 must skip pruning, but resume into round 3 must not inherit a stale escalated_round=true flag; a single persisted boolean cannot distinguish those cases
- **Proposed resolution**: Store escalation target_round values or derive escalated_round from the current round and escalation entries, then test resume into the escalated round and the following non-escalated round
