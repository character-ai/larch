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


### FINDING_16:
- **Reviewer(s)**: Codex-Innovation
- **Severity**: important
- **Focus area**: architecture
- **Location**: python/larch/core/config.py:18-23
- **Concern**: [SCOPE-REDUCTION] Reusing calibration difficulty tokens from core config violates the import layering ratchet. Scenario: Implementing DIFFICULTY_TIER_* in larch.core.config by importing larch.calibration.difficulty adds a core to domain import; the layering lint explicitly treats core importing domain packages as a violation, so py-lint can fail before the feature ships
- **Proposed resolution**: Drop the config tier aliases or make config the lower-tier source and have calibration import from config; do not import larch.calibration from larch.core.config


