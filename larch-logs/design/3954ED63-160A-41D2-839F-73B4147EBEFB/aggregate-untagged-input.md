### FINDING_1:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/implement/SKILL.md:92-95
- **Concern**: Step 2.4 bash fence in the plan is missing its closing ```. Scenario: The plan copies a one-line `normalize-coder-scout` fence but never closes the ```bash block before the absent-input prose. An implementer can paste an unclosed fence into SKILL.md and fail `scripts/test-implement-fence-shape.sh` / `make lint`.
- **Proposed resolution**: Close the fence immediately after the one-line command; keep the absent-input guidance as prose outside the fence (the plan Failure modes section already calls this out).

### FINDING_2:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/implement_dispatch.py:1051-1061
- **Concern**: External-coder refactor must not hardcode `scout-coder-manifest.raw.json` as `--input`. Scenario: `DispatchState.launch_scout_manifest` is tool-specific (`codex-step2-out/scout-coder-manifest.json` for Codex; tmpdir-local for Cursor). Only the main-agent path uses `scout-coder-manifest.raw.json`. Hardcoding the raw path in `_normalize_scout` / `normalize_coder_scout_main` breaks Codex normalization.
- **Proposed resolution**: In `normalize_coder_scout_main`, bind `--input` to `launch_scout_manifest` for external coders and to `scout-coder-manifest.raw.json` for `--producer main-agent`; document both in `step2-dispatch.md`.

### FINDING_3:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/implement_dispatch.py:1051-1060
- **Concern**: `filter-manifest` `SCOUT_STATUS=empty` must not map directly to `SCOUT_CODER_STATUS=ok`. Scenario: `plan_scout.filter_manifest` returns `empty` for both intentional `{"archetypes":[]}` and raw-nonempty filtered-to-zero. Today `_normalize_scout` treats `empty` as success and always writes the eligibility marker, so reserved-slug manifests can get `ok` while forwarding collapses to static-only or misparsed states.
- **Proposed resolution**: Keep the plan’s raw-count-before-filter rules in `normalize_coder_scout_main`: `ok` only when raw count is 0 (intentional empty) or filtered count > 0; raw>0 filtered=0 → `missing-or-invalid` and no eligibility marker.

### FINDING_4:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/review_pipeline.py:995-1013
- **Concern**: Valid intentional empty pre-scouted manifests are misclassified as `parse-failed`. Scenario: When `review_and_fix` forwards `SCOUT_CODER_STATUS=ok` with `{"archetypes":[]}`, dispatch uses `_normalize_scout_manifest` then requires `_scout_archetypes()` truthy. Empty lists fall into `parse-failed` / `pre_scouted_manifest_validation` instead of static-only success.
- **Proposed resolution**: Implement FINDING_1: if pre-scouted normalize succeeds and raw/filtered archetype count is 0 with producer `ok`, set `SCOUT_STATUS=pre-scouted-empty`, write the round manifest, skip `_synthesize_dynamic_slots`, and do not set `parse-failed`.

### FINDING_5:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: python/review_pipeline.py:1043-1067
- **Concern**: Implement Step 5 still launches `scout dynamic-archetypes` when no pre-scouted manifest. Scenario: Emergency / main-agent runs (`claude_fallback`, `--emergency`, explicit `--coder claude`) produce no coder manifest today, so Step 5 hits the separate scout branch (matching the `scout-round1-manifest.json.raw` timing in issue #4954).
- **Proposed resolution**: Add FINDING_7: for `site == "implement Step 5"` with `scout_status == "na"` and no valid `--pre-scouted-manifest`, write an empty round manifest, set `producer-missing` or `producer-invalid`, skip lines 1043-1067, continue static-only.

### FINDING_6:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: important
- **Focus area**: architecture
- **Location**: python/review_pipeline.py:934
- **Concern**: `--site` default keys off ambient `IMPLEMENT_TMPDIR`. Scenario: `dispatch_panel` / `review_core` default to `"implement Step 5"` when `IMPLEMENT_TMPDIR` is set. Standalone `/review` in a reused env inherits implement gating and can suppress its own dynamic scout.
- **Proposed resolution**: Apply FINDING_8: default `--site` to `"review Step 2"` unconditionally; keep explicit `--site "implement Step 5"` from `review_and_fix.py` and add the same explicit pass in `skills/review/SKILL.md`.

### FINDING_7:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/implement_dispatch.py:902-909
- **Concern**: `_clear_external_scout_state` omits status env and raw manifest. Scenario: `claude_fallback` / recovery clears normalized manifest and marker but not `step2-scout-coder-status.env` or `scout-coder-manifest.raw.json`, so stale `SCOUT_CODER_STATUS=ok` can mislead `final_report` after tmpdir reuse.
- **Proposed resolution**: Extend cleanup per plan: unlink `step2-scout-coder-status.env`, `scout-coder-manifest.raw.json`, and tool outdir copies; test `claude_fallback` cleanup in `test_implement_dispatch.py`.

### FINDING_8:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: python/review_pipeline.py:989-1087
- **Concern**: Producer-failure warning ownership is unspecified at the append site. Scenario: Plan moves persisted warnings to `dispatch_panel` after diff classification with `.producer-scout-warning-logged`, but `dispatch_panel` has no current producer-warning append and must not fire on `skipped-*` or `pre-scouted-empty`.
- **Proposed resolution**: Wire FINDING_4/10 in `dispatch_panel`: after diff classification, if `SCOUT_STATUS` is `producer-missing` / `producer-invalid`, append one `Warnings` entry via `IMPLEMENT_TMPDIR` + sentinel; never append from `normalize_coder_scout_main` or Step 5 preflight.

### FINDING_10:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: blocking
- **Focus area**: correctness
- **Location**: skills/implement/SKILL.md:Step 2.4
- **Concern**: Plan draft leaves the normalize-coder-scout bash fence unclosed. Scenario: Pasting the plan excerpt into SKILL.md omits closing backticks; make lint and test-implement-fence-shape fail and the fence never runs
- **Proposed resolution**: In the SKILL.md edit close the fence on the line immediately after the one-line larch-run.sh command; keep absent-input guidance as prose outside the fence

### FINDING_11:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/review_pipeline.py:995-1013
- **Concern**: pre-scouted intentional empty must branch before _scout_archetypes guard. Scenario: Forwarded SCOUT_CODER_STATUS=ok with {"archetypes":[]} hits else at 1009-1013 (parse-failed) today; rounds may mis-handle empty ok manifests even after producer fix
- **Proposed resolution**: Add explicit pre-scouted-empty branch when normalized count is zero and producer status is ok; skip _synthesize_dynamic_slots; do not set parse-failed

### FINDING_12:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: python/review_pipeline.py:1043-1067
- **Concern**: Implement Step 5 gate must fully replace scout dynamic-archetypes branch when pre-scouted absent/invalid. Scenario: Emergency main-agent runs show scout-round1-manifest.json.raw (~262s) because this branch still runs when review_and_fix does not forward a manifest
- **Proposed resolution**: When site==implement Step 5 and scout_status==na without valid --pre-scouted-manifest set producer-missing/producer-invalid write empty round manifest and continue static-only; never call scout dynamic-archetypes

### FINDING_13:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/implement_dispatch.py:1059-1060
- **Concern**: Eligibility marker must not be written on missing-or-invalid. Scenario: Current _normalize_scout always writes step2-external-scout-eligible.txt even when scout_status is missing-or-invalid; stale markers confuse operators and final-summary guards
- **Proposed resolution**: In normalize_coder_scout_main write step2-external-scout-eligible.txt only when status is ok; delete the unconditional marker write in the refactor

### FINDING_14:
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: blocking
- **Focus area**: correctness
- **Location**: skills/implement/SKILL.md:496
- **Concern**: Step 2 anti-halt still says Continue to Step 3 IMMEDIATELY with no carve-out for the new normalize-coder-scout fence. Scenario: On main-agent paths (--emergency, claude_fallback, --coder claude) the orchestrator can skip writing scout-coder-manifest.raw.json and the mandatory normalize fence, so Step 5 still hits review_pipeline scout dynamic-archetypes (the #4954 failure mode)
- **Proposed resolution**: In the Step 2.4 edit, insert the raw-write + normalize fence immediately before the Step 3 breadcrumb, and replace the line-496 anti-halt text with continue to Step 3 only after the normalize fence completes on main-agent paths; keep the external STATUS=complete path unchanged

### FINDING_15:
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: blocking
- **Focus area**: correctness
- **Location**: skills/implement/SKILL.md:92-95
- **Concern**: Step 2.4 normalize-coder-scout bash fence is left unclosed in the plan SKILL.md excerpt. Scenario: The plan copies a one-line `larch-run.sh` fence into `skills/implement/SKILL.md` but omits the closing ``` before the absent-input prose; `scripts/test-implement-fence-shape.sh` and `make lint` will fail, and the absent-input guidance may be swallowed into the fence block
- **Proposed resolution**: Close the ```bash fence immediately after the normalize command line; keep the absent-input guidance as prose outside the fence (the plan Failure modes section already states this rule but the excerpt itself is still broken)
