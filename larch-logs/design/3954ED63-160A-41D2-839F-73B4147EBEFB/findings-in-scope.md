### FINDING_1: Step 2.4 normalize-coder-scout bash fence left unclosed
- **Reviewer(s)**: Cursor-Arch, Cursor-Innovation, Cursor-Requirements
- **Severity**: blocking
- **Concern**: The plan’s Step 2.4 excerpt copies a one-line `normalize-coder-scout` / `larch-run.sh` bash fence into `skills/implement/SKILL.md` without a closing ```. An implementer can paste an unclosed fence, swallow absent-input guidance inside the block, and fail `scripts/test-implement-fence-shape.sh` / `make lint`; the fence may never run as intended.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Close the fence immediately after the one-line command; keep the absent-input guidance as prose outside the fence (the plan Failure modes section already calls this out).
  - From Cursor-Innovation: In the SKILL.md edit close the fence on the line immediately after the one-line larch-run.sh command; keep absent-input guidance as prose outside the fence
  - From Cursor-Requirements: Close the ```bash fence immediately after the normalize command line; keep the absent-input guidance as prose outside the fence (the plan Failure modes section already states this rule but the excerpt itself is still broken)

### FINDING_2: External-coder normalize must not hardcode raw manifest input path
- **Reviewer(s)**: Cursor-Arch
- **Severity**: important
- **Concern**: Refactoring `_normalize_scout` / `normalize_coder_scout_main` must not hardcode `scout-coder-manifest.raw.json` as `--input` for all producers. `DispatchState.launch_scout_manifest` is tool-specific (Codex uses `codex-step2-out/scout-coder-manifest.json`; Cursor uses a tmpdir-local path); only the main-agent path uses `scout-coder-manifest.raw.json`. Hardcoding the raw path breaks Codex/Cursor normalization.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: In `normalize_coder_scout_main`, bind `--input` to `launch_scout_manifest` for external coders and to `scout-coder-manifest.raw.json` for `--producer main-agent`; document both in `step2-dispatch.md`.

### FINDING_3: Scout normalize must not treat filtered-empty or invalid manifests as ok with eligibility marker
- **Reviewer(s)**: Cursor-Arch, Cursor-Innovation
- **Severity**: important
- **Concern**: `filter-manifest` `SCOUT_STATUS=empty` must not map directly to `SCOUT_CODER_STATUS=ok`, and `step2-external-scout-eligible.txt` must not be written unconditionally. When raw archetype count is >0 but filtered count is 0, or when status is `missing-or-invalid`, the code can still mark scout as `ok` and write the eligibility marker. That leaves reserved-slug or stale markers that confuse operators, `final_report`, and downstream static-only / pre-scouted handling.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Keep the plan’s raw-count-before-filter rules in `normalize_coder_scout_main`: `ok` only when raw count is 0 (intentional empty) or filtered count > 0; raw>0 filtered=0 → `missing-or-invalid` and no eligibility marker.
  - From Cursor-Innovation: In normalize_coder_scout_main write step2-external-scout-eligible.txt only when status is ok; delete the unconditional marker write in the refactor

### FINDING_4: Intentional empty pre-scouted manifests misclassified as parse-failed
- **Reviewer(s)**: Cursor-Arch, Cursor-Innovation
- **Severity**: important
- **Concern**: When `review_and_fix` forwards `SCOUT_CODER_STATUS=ok` with `{"archetypes":[]}`, `review_pipeline` uses `_normalize_scout_manifest` then requires `_scout_archetypes()` to be truthy. Valid intentional empty manifests fall into `parse-failed` / `pre_scouted_manifest_validation` instead of static-only success with a dedicated empty branch.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Implement FINDING_1: if pre-scouted normalize succeeds and raw/filtered archetype count is 0 with producer `ok`, set `SCOUT_STATUS=pre-scouted-empty`, write the round manifest, skip `_synthesize_dynamic_slots`, and do not set `parse-failed`.
  - From Cursor-Innovation: Add explicit pre-scouted-empty branch when normalized count is zero and producer status is ok; skip _synthesize_dynamic_slots; do not set parse-failed

### FINDING_5: Implement Step 5 still runs separate scout when no valid pre-scouted manifest
- **Reviewer(s)**: Cursor-Arch, Cursor-Innovation
- **Severity**: important
- **Concern**: On `/implement` Step 5, when `scout_status == "na"` and there is no valid `--pre-scouted-manifest` (e.g. emergency / main-agent `claude_fallback` / explicit `--coder claude`), `review_pipeline` still enters the `scout dynamic-archetypes` branch (~262s in issue #4954). The separate-role scout was meant to be retired when the coder supplies archetypes.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Add FINDING_7: for `site == "implement Step 5"` with `scout_status == "na"` and no valid `--pre-scouted-manifest`, write an empty round manifest, set `producer-missing` or `producer-invalid`, skip lines 1043-1067, continue static-only.
  - From Cursor-Innovation: When site==implement Step 5 and scout_status==na without valid --pre-scouted-manifest set producer-missing/producer-invalid write empty round manifest and continue static-only; never call scout dynamic-archetypes

### FINDING_6: `--site` default incorrectly inherits implement gating from ambient `IMPLEMENT_TMPDIR`
- **Reviewer(s)**: Cursor-Arch
- **Severity**: important
- **Concern**: `dispatch_panel` / `review_core` default `--site` to `"implement Step 5"` when `IMPLEMENT_TMPDIR` is set. Standalone `/review` in a reused env can inherit implement-specific scout gating and suppress its own dynamic scout.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Apply FINDING_8: default `--site` to `"review Step 2"` unconditionally; keep explicit `--site "implement Step 5"` from `review_and_fix.py` and add the same explicit pass in `skills/review/SKILL.md`.

### FINDING_7: `_clear_external_scout_state` leaves stale scout status and raw manifest
- **Reviewer(s)**: Cursor-Arch
- **Severity**: important
- **Concern**: On `claude_fallback` / recovery, `_clear_external_scout_state` clears the normalized manifest and marker but not `step2-scout-coder-status.env` or `scout-coder-manifest.raw.json` (or tool outdir copies). Stale `SCOUT_CODER_STATUS=ok` can mislead `final_report` after tmpdir reuse.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Extend cleanup per plan: unlink `step2-scout-coder-status.env`, `scout-coder-manifest.raw.json`, and tool outdir copies; test `claude_fallback` cleanup in `test_implement_dispatch.py`.

### FINDING_8: Producer-failure warnings must be owned by `dispatch_panel`, not normalize or Step 5 preflight
- **Reviewer(s)**: Cursor-Arch
- **Severity**: important
- **Concern**: The plan moves persisted producer-failure warnings to `dispatch_panel` after diff classification with a `.producer-scout-warning-logged` sentinel, but `dispatch_panel` has no current producer-warning append. Warnings must not fire on `skipped-*` or `pre-scouted-empty`, and must not be appended from `normalize_coder_scout_main` or Step 5 preflight.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Wire FINDING_4/10 in `dispatch_panel`: after diff classification, if `SCOUT_STATUS` is `producer-missing` / `producer-invalid`, append one `Warnings` entry via `IMPLEMENT_TMPDIR` + sentinel; never append from `normalize_coder_scout_main` or Step 5 preflight.

### FINDING_9: Step 2 anti-halt text can skip mandatory main-agent normalize fence
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: blocking
- **Concern**: Step 2 anti-halt still says “Continue to Step 3 IMMEDIATELY” with no carve-out for the new `normalize-coder-scout` fence. On main-agent paths (`--emergency`, `claude_fallback`, `--coder claude`), the orchestrator can skip writing `scout-coder-manifest.raw.json` and the mandatory normalize fence, so Step 5 still hits `review_pipeline` scout `dynamic-archetypes` (the #4954 failure mode).
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Pragmatic: In the Step 2.4 edit, insert the raw-write + normalize fence immediately before the Step 3 breadcrumb, and replace the line-496 anti-halt text with continue to Step 3 only after the normalize fence completes on main-agent paths; keep the external STATUS=complete path unchanged

### FINDING_10:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/implement_dispatch.py:1051-1061
- **Concern**: [SCOPE-REDUCTION] External-coder normalize refactor must pin --input to launch_scout_manifest not only main-agent .raw.json. Scenario: Refactor to normalize_coder_scout_main without an explicit external --input contract may break Codex/Cursor paths that today filter st.launch_scout_manifest in _normalize_scout only on STATUS=complete
- **Proposed resolution**: In implement_dispatch.py section state external path passes --input launch_scout_manifest (codex-step2-out copy when applicable); main-agent uses scout-coder-manifest.raw.json; keep _normalize_scout callsite on complete only

### FINDING_11:
- **Reviewer(s)**: Codex-Generic
- **Severity**: important
- **Focus area**: architecture
- **Location**: python/design_lifecycle.py:2990-3439, python/agents.py:2793-3168, skills/design/SKILL.md:482-484, skills/design/references/plan-review.md:3-55, python/design_summary.py:167-245
- **Concern**: [SCOPE-REDUCTION] Design dynamic-archetype migration is outside the issue scope. Scenario: The issue and examples target /implement Step 5, especially main-agent emergency. The current design path already has the Step 2b drafter materialize scout-plan-manifest.json and Step 3 consume it, so the proposed design warnings, summaries, and docs add behavior not needed for the implement fix.
- **Proposed resolution**: Drop the firm design_lifecycle.py, design_summary.py, skills/design/*, and design scout test changes unless a separate design regression is demonstrated.
