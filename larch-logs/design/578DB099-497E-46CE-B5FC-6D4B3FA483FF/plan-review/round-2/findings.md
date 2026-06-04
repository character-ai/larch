### FINDING_1:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: important
- **Focus area**: architecture
- **Location**: skills/review/scripts/dispatch-panel.sh:27-28
- **Concern**: Parallel Codex static rows plus default waterfall phase-2 Codex fallback can double-run the same archetype. Scenario: Plan mirrors /design’s paired Cursor+Codex manifest rows but only flips codex_present_for_waterfall; dispatch-plan-review-panel.sh uses --no-fallback. With both vendors up, a failed Cursor static slot (e.g. security) phase-2 relaunches Codex while codex-specialist-security-output.txt is already a phase-1 peer — extra Codex spend and findings noise, undermining the 6→4 collapse and #3463 cost story
- **Proposed resolution**: When both CURSOR_AVAILABLE and CODEX_AVAILABLE are true, pass --no-fallback to dispatch-with-waterfall.sh (match dispatch-plan-review-panel.sh) or document and test that phase-2 Codex fallback is intentionally disabled for static/dynamic rows that already have a Codex twin; drop the line-27 “Phase-2 fallback” goal if peers are the contract

### FINDING_2:
- **Reviewer(s)**: Codex-Edge
- **Severity**: latent
- **Focus area**: risk-integration
- **Location**: docs/collaborative-sketches.md:42-45
- **Concern**: Plan misses the fallback-behavior table that still says /review skips unavailable specialist slots and launches no slots when both tools are down. Scenario: After this change /review should emit available Cursor/Codex rows and use Claude fallback when both vendors are unavailable, so this adjacent failure-recovery doc would describe the opposite behavior
- **Proposed resolution**: Update the Code review row to the new availability-gated both-vendor layout and both-down Claude fallback, or point it at skills/review/scripts/dispatch-panel.md as the authority

### FINDING_3:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: skills/review/scripts/review-core.sh:446-456
- **Concern**: Plan offers a second INTENDED_SLOTS derivation in review-core (`4 * (cursor + codex)`, floored at 4) alongside dispatch `STATIC_SLOT_COUNT`. Scenario: review-core and dispatch-panel can disagree after a partial emission bug or a boolean parsing mistake; `--launched-slots` already comes from `static_slot_count`, so a separate formula reintroduces the #2449-style phantom never-launched / threshold skew
- **Proposed resolution**: Pass `--intended-slots "$static_slot_count"` (same KV as `--launched-slots`) and drop the availability formula from review-core; keep availability logic only in dispatch-panel emission

### FINDING_4:
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: important
- **Focus area**: correctness
- **Location**: scripts/scout-dynamic-archetypes.sh:341
- **Concern**: Scout prompt still lists six static reviewers including folded structure and plan-fidelity. Scenario: After the 4-archetype collapse the scout is told structure and plan-fidelity are existing static slots, so it may return fewer or mis-targeted dynamic archetypes while jq still reserves those slugs; static coverage for folded lenses is weakened
- **Proposed resolution**: Change the prompt line to name only the four surviving static slugs (security, correctness, edge-cases, testing) plus generic; keep the jq reserved list at six slugs so folded names cannot reappear as dynamics

### FINDING_5:
- **Reviewer(s)**: Codex-Pragmatic
- **Severity**: latent
- **Focus area**: risk-integration
- **Location**: skills/review/SKILL.md:39
- **Concern**: The plan omits the runtime /review skill prompt from the sync set, leaving it to describe dynamic archetypes as Cursor-primary after dispatch-panel changes them to availability-gated Cursor and Codex twin rows.. Scenario: A direct /review run still loads this prompt; stale orchestration prose can mislead operators or future prompt-side maintenance about the actual panel shape.
- **Proposed resolution**: Add skills/review/SKILL.md to the UPDATED list and change Step 2 to the 4-archetype per-available-vendor static layout plus matching dynamic twin/fallback behavior.

### FINDING_6:
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/review/scripts/review-core.sh:41-42
- **Concern**: Plan’s availability formula uses arithmetic on `cursor_available`/`codex_available`, but review-core passes `true`/`false` strings. Scenario: Implementer copies `4 * (cursor_available + codex_available)` literally; bash arithmetic errors or wrong `--intended-slots`, so the >50% panel-failure gate misfires
- **Proposed resolution**: Pass `STATIC_SLOT_COUNT` from dispatch-panel into `--intended-slots`, or convert each flag to 0/1 before multiplying; add/keep harness cases at 4 and 8 intended slots

### FINDING_7:
- **Reviewer(s)**: Codex-Requirements
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: scripts/render-specialist-prompt.sh:285-297
- **Concern**: Plan claims the folded testing lane always has the plan, but render-specialist-prompt.sh only injects implementation_plan for generic diffs. Scenario: For docs-only, test-only, or generated-only diffs, reviewer-testing will not receive the plan, so the proposed folded plan-fidelity scan cannot catch critical plan-to-implementation gaps even though the plan lists that coverage as preserved
- **Proposed resolution**: Add scripts/render-specialist-prompt.sh and its prompt-render test to the plan, with a minimal reviewer-testing-specific plan injection when PLAN_FILE is present, or narrow the stated plan-fidelity coverage claim to generic diffs only

### FINDING_8:
- **Reviewer(s)**: Cursor-dyn-vendor-flag-reentry
- **Severity**: important
- **Focus area**: correctness
- **Location**: <TMPDIR>/plan.txt:40-41
- **Concern**: review-core intended-slot guidance conflates STATIC_SLOT_COUNT with --intended-slots. Scenario: STATIC_SLOT_COUNT is the emitted static manifest row count (--launched-slots). Reusing it for --intended-slots when Codex rows fail to launch leaves INTENDED_SLOTS equal to LAUNCHED_SLOTS, so check-reviewer-failure-threshold.sh never adds never-launched failures and a >50% static panel failure can pass
- **Proposed resolution**: Remove the STATIC_SLOT_COUNT alternative for --intended-slots; compute intended only from availability (4 times vendor count, floor 4) or have dispatch-panel.sh emit a separate INTENDED_STATIC_SLOTS KV

### FINDING_9:
- **Reviewer(s)**: Codex-dyn-vendor-flag-reentry
- **Severity**: important
- **Focus area**: correctness
- **Location**: docs/collaborative-sketches.md:40-45
- **Concern**: Plan misses a canonical Codex/Cursor integration doc row that still describes /review as skipping Cursor/Codex specialist slots and launching no slots when both externals are down. Scenario: After the proposed both-vendor panel and explicit both-down Claude fallback, operators reading this shipped integration matrix get the wrong panel shape and outage behavior even though dispatch-panel.md and review-agents.md are updated
- **Proposed resolution**: Update the /review row to the new 4-archetype per-available-vendor layout and state that both-down emits Claude-fallback rows rather than no slots

### FINDING_10:
- **Reviewer(s)**: Cursor-dyn-availability-math
- **Severity**: important
- **Focus area**: correctness
- **Location**: plan.txt:40-41; skills/review/scripts/review-core.sh:451-452
- **Concern**: Plan offers two denominators: availability formula `4*(cursor+codex)` floored at 4 OR `STATIC_SLOT_COUNT` from dispatch. Scenario: Recomputing from flags can diverge from emitted manifest rows (e.g. flags both true but dispatch emits 4 rows) yielding INTENDED=8 and LAUNCHED=4, so NEVER_LAUNCHED adds 4 phantom failures and a healthy panel hard-stops
- **Proposed resolution**: In review-core.sh set `intended_slots="$static_slot_count"` (same KV as `--launched-slots`) and pass `--intended-slots "$intended_slots"`; drop the parallel availability formula from the plan

### FINDING_11:
- **Reviewer(s)**: Cursor-dyn-log-exclude-coverage
- **Severity**: important
- **Focus area**: correctness
- **Location**: scripts/test-larch-log-write-round.sh:64-69,106-108,128-129
- **Concern**: write-round harness still requires committed codex-specialist .meta. Scenario: After larch-log.sh adds codex-specialist exclusions parallel to cursor (plan lines 62-63), write-round will still assert codex-specialist-security-output.txt.meta is present and CMD_JSON-stripped; CI fails or forces a revert of the filter change
- **Proposed resolution**: Name scripts/test-larch-log-write-round.sh in the plan; flip meta to assert_not_file; add a raw codex-specialist-*-output.txt fixture with assert_not_file; drop or relocate CMD_JSON assertions that only applied to excluded meta

### FINDING_12:
- **Reviewer(s)**: Codex-dyn-log-exclude-coverage
- **Severity**: important
- **Focus area**: correctness
- **Location**: plan.txt:24,111-112; scripts/larch-log.sh:73-96; scripts/test-larch-log.sh:918-980
- **Concern**: larch-log regression plan omits the new dynamic Codex twin naming. Scenario: The plan introduces dyn-${name}-codex-output.txt but the larch-log test update only requires codex-specialist-* exclusion. Current tests only pin cursor-specialist-* exclusion, so an over-broad Codex deny such as *codex*-output.txt could silently drop dynamic Codex reviewer outputs from committed round logs.
- **Proposed resolution**: Add one minimal larch-log regression fixture for dyn-api-contract-codex-output.txt and expected sidecar behavior, while keeping the static deny precise to codex-specialist-*-output.txt and matching sidecars. Update scripts/larch-log.md to state static Codex specialist raw outputs are excluded but dyn-*-codex-output.txt follows the existing dynamic/output allow-list behavior.
