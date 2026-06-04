### FINDING_1:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/review/scripts/dispatch-panel.sh:183-184,393-396,445
- **Concern**: Codex dynamic twins not reflected in DYNAMIC_SLOTS/SLOT_COUNT/breadcrumb. Scenario: Plan adds a second manifest row per scouted archetype (`dyn-${name}-codex-output.txt`) but `synthesize_dynamic_slots` only increments `DYNAMIC_SLOTS` once per archetype; `SLOT_COUNT` and the launch breadcrumb use `static_* + DYNAMIC_SLOTS`, so totals undercount real launches (e.g. 4 dynamics → manifest 8 rows but `DYNAMIC_SLOTS=4`, `SLOT_COUNT` off by 4)
- **Proposed resolution**: When both vendors are up, increment dynamic counts for each emitted dynamic row (or derive `DYNAMIC_SLOTS`/`SLOT_COUNT` from manifest line count); extend `test-dispatch-panel.sh` dynamic cases to assert doubled dynamic totals and breadcrumb math

### FINDING_2:
- **Reviewer(s)**: Codex-Arch
- **Severity**: important
- **Focus area**: security
- **Location**: scripts/larch-log.sh:73-78
- **Concern**: New codex-specialist raw outputs would bypass the existing per-specialist run-log exclusion. Scenario: The plan adds codex-specialist-*-output.txt files, but write-round will match them via the broad *-output.txt include pattern and commit raw reviewer transcripts instead of relying on findings.md
- **Proposed resolution**: Add scripts/larch-log.sh and its test/docs to the plan; exclude codex-specialist-*-output.txt and sidecars alongside cursor-specialist patterns

### FINDING_3:
- **Reviewer(s)**: Codex-Arch
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: skills/implement/SKILL.md:761-763; scripts/generate-topology-docs.sh:188-195; scripts/generate-topology-docs.md:31; scripts/test-quick-mode-docs-sync.md:25-32
- **Concern**: The phrase-sync plan misses source/runtime owners still pinned to 6 Cursor specialists. Scenario: Updating docs/topology.md directly will be reverted by generate-topology-docs.sh --check, and updating POS_MARKERS without skills/implement/SKILL.md keeps the Step 5 banner stale or fails test-quick-mode-docs-sync.sh
- **Proposed resolution**: Add these files to the phrase-sync step and replace the old phrase with the same canonical wording used in README/docs/topology.tsv/test-quick-mode-docs-sync.sh

### FINDING_4:
- **Reviewer(s)**: Codex-Edge
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: skills/review/scripts/test-check-reviewer-failure-threshold.sh:75-155
- **Concern**: The plan changes check-reviewer-failure-threshold.sh to use --intended-slots and 4/8-slot denominators but omits its dedicated harness and contract doc. Scenario: `make lint` includes test-check-reviewer-failure-threshold; the current harness still asserts a hardcoded 6-slot denominator and will fail or leave the new boundary behavior untested
- **Proposed resolution**: Add skills/review/scripts/test-check-reviewer-failure-threshold.sh and skills/review/scripts/test-check-reviewer-failure-threshold.md to the plan; update cases for default 4, --intended-slots 4 and 8, both-down launched=4, and dynamic Codex-twin exclusion

### FINDING_5:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Focus area**: correctness
- **Location**: scripts/test-quick-mode-docs-sync.sh:127-258; skills/implement/SKILL.md:763
- **Concern**: Phrase migration omits the harness-checked canonical source. Scenario: Updating POS_MARKERS to the new phrase without editing `skills/implement/SKILL.md` leaves `6 Cursor specialists` in the Step 5 banner; `test-quick-mode-docs-sync.sh` positive-checks SKILL.md and will fail `make lint`
- **Proposed resolution**: Add `skills/implement/SKILL.md` to the atomic phrase-replacement file list (same canonical string as README/docs)

### FINDING_6:
- **Reviewer(s)**: Codex-Innovation
- **Severity**: important
- **Focus area**: correctness
- **Location**: scripts/render-specialist-prompt.sh:193-202
- **Concern**: Plan edits reviewer-edge-cases.md and reviewer-testing.md but says to regenerate nothing, while runtime loads agents/pre-rendered bodies before agent source. Scenario: The folded structure and plan-fidelity lenses will not reach Cursor/Codex prompts, and generator check will drift after the agent edits
- **Proposed resolution**: Regenerate agents/pre-rendered/reviewer-edge-cases-body.txt, agents/pre-rendered/reviewer-testing-body.txt, and agents/pre-rendered/.manifest via scripts/generate-pre-rendered-reviewer-prompts.sh

### FINDING_7:
- **Reviewer(s)**: Codex-Innovation
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: scripts/generate-topology-docs.sh:188-199
- **Concern**: Plan updates docs/topology.md text but omits the generator that hardcodes the stale 6 Cursor specialists phrase. Scenario: Regenerating topology will reintroduce the old phrase or make test-generate-topology-docs/check-generators fail
- **Proposed resolution**: Update scripts/generate-topology-docs.sh with the canonical phrase before regenerating docs/topology.md

### FINDING_8:
- **Reviewer(s)**: Codex-Innovation
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: skills/review/scripts/test-check-reviewer-failure-threshold.sh:75-184
- **Concern**: Plan changes threshold denominator semantics but omits the direct threshold harness that still asserts 6-slot defaults and both-down counts. Scenario: make lint runs test-check-reviewer-failure-threshold and will either fail or leave the new 4/8-slot contract untested
- **Proposed resolution**: Update this harness and its .md contract for --intended-slots 4 and 8, the new default, and dynamic Codex-output exclusion cases

### FINDING_9:
- **Reviewer(s)**: Codex-Innovation
- **Severity**: latent
- **Focus area**: correctness
- **Location**: skills/review/scripts/dispatch-panel.sh:175-183,391-445
- **Concern**: Plan adds Codex dynamic twin rows but does not state that DYNAMIC_SLOTS, SLOT_COUNT, and the launch breadcrumb must count emitted dynamic rows. Scenario: With both vendors and two scouted archetypes the manifest has four dynamic reviewers but summaries can report two, corrupting review telemetry
- **Proposed resolution**: Increment DYNAMIC_SLOTS per emitted dynamic row or derive it from manifest rows, then update dispatch-panel tests and docs

### FINDING_10:
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: important
- **Focus area**: correctness
- **Location**: scripts/test-quick-mode-docs-sync.sh:85-127
- **Concern**: Plan omits skills/implement/SKILL.md while changing the required POS_MARKERS phrase. Scenario: The harness positive-checks SKILL.md for the new anchor; leaving line 763 on 6 Cursor specialists fails make lint / test-quick-mode-docs-sync or leaves a stale Step 5 banner
- **Proposed resolution**: Add skills/implement/SKILL.md to the file list and replace the banner phrase atomically with the canonical string

### FINDING_11:
- **Reviewer(s)**: Codex-Pragmatic
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/review/scripts/review-core.sh:451-456
- **Concern**: Proposed threshold scaling leaves the existing static_dispatch_ok=false short-circuit, so the >50% denominator is bypassed for represented slot failures.. Scenario: In an 8-slot both-vendor panel, one static slot that fails through Claude sets STATIC_DISPATCH_OK=false and review-core returns panel-failed even though only 1 of 8 slots failed.
- **Proposed resolution**: Call check-reviewer-failure-threshold.sh with --intended-slots even when STATIC_DISPATCH_OK=false; reserve immediate failure only for a dispatch-level error that cannot be represented in collector-results.env.

### FINDING_12:
- **Reviewer(s)**: Codex-Pragmatic
- **Severity**: latent
- **Focus area**: risk-integration
- **Location**: scripts/larch-log.sh:73-78
- **Concern**: Plan adds codex-specialist raw outputs, but the run-log filter excludes only cursor-specialist raw outputs.. Scenario: A committed round log can include codex-specialist-security-output.txt while cursor raw outputs stay excluded, contradicting the raw per-specialist exclusion contract and duplicating reviewer transcripts.
- **Proposed resolution**: Extend the exclusion pattern and larch-log tests to cover codex-specialist-*-output.txt raw outputs alongside cursor-specialist-*-output.txt.

### FINDING_13:
- **Reviewer(s)**: Codex-Pragmatic
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: skills/review/scripts/test-check-reviewer-failure-threshold.sh:75-118
- **Concern**: The plan changes check-reviewer-failure-threshold.sh denominator behavior but omits its direct regression harness and md contract.. Scenario: After the default changes to 4 and intended slots become explicit, existing cases expecting the old 6-slot denominator can fail under make lint or preserve stale coverage.
- **Proposed resolution**: Add test-check-reviewer-failure-threshold.sh and .md to the plan; update cases to exercise --intended-slots 4 and 8 plus the fallback default.

### FINDING_14:
- **Reviewer(s)**: Codex-Pragmatic
- **Severity**: latent
- **Focus area**: code-quality
- **Location**: skills/review/scripts/dispatch-panel.sh:199-202; scripts/scout-dynamic-archetypes.sh:535-538
- **Concern**: The plan says optionally drop retired structure and plan-fidelity slugs from reserved lists, which conflicts with the stated goal of preventing their resurrection as dynamic scouts.. Scenario: A scout can return structure or plan-fidelity as a dynamic archetype, reintroducing retired lenses after the 6 to 4 collapse.
- **Proposed resolution**: Remove the optional cleanup; keep structure and plan-fidelity reserved in both lists with a short comment.

### FINDING_15:
- **Reviewer(s)**: Codex-Pragmatic
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: skills/implement/SKILL.md:761-763
- **Concern**: The plan updates public docs but omits the runtime /implement Step 5 banner that still says 6 Cursor specialists.. Scenario: After the PR, /implement prints a stale panel contract while dispatch launches 4 specialists per available vendor, confusing operators and logs.
- **Proposed resolution**: Add skills/implement/SKILL.md to the phrase-sync change and replace the banner text with the same canonical phrase.

### FINDING_16:
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/implement/SKILL.md:763
- **Concern**: Step 5 banner still says `6 Cursor specialists` but `skills/implement/SKILL.md` is absent from Files to modify. Scenario: `scripts/test-quick-mode-docs-sync.sh` requires the canonical POS marker in SKILL.md (line 127); changing the harness phrase without updating the Step 5 breadcrumb at line 763 fails `make lint`
- **Proposed resolution**: Add `### UPDATED: skills/implement/SKILL.md` — replace the Step 5 banner phrase with the same canonical string used in README/docs and `POS_MARKERS`

### FINDING_17:
- **Reviewer(s)**: Codex-Requirements
- **Severity**: important
- **Focus area**: correctness
- **Location**: plan.txt:24; skills/review/scripts/dispatch-panel.sh:175-183
- **Concern**: Dynamic slots are described as keeping the existing Cursor row and appending Codex, not gating both vendors like static slots. Scenario: In a Codex-only run, each dynamic archetype would create a Cursor-primary row that falls through to Codex plus a Codex-primary twin, so Codex reviews the same dynamic lens twice despite the gated-on-availability requirement
- **Proposed resolution**: Revise the plan to gate dynamic Cursor rows on CURSOR_AVAILABLE, Codex rows on CODEX_AVAILABLE, and emit one Cursor-primary Claude-fallback row only when neither vendor is available; add single-vendor dynamic assertions

### FINDING_18:
- **Reviewer(s)**: Codex-Requirements
- **Severity**: important
- **Focus area**: correctness
- **Location**: plan.txt:11,27,51-52,106; skills/review/scripts/dispatch-panel.sh:199-202; scripts/scout-dynamic-archetypes.sh:535-538
- **Concern**: The plan allows optional removal of retired structure and plan-fidelity reserved slugs, conflicting with its own fold requirement. Scenario: A scout could return structure or plan-fidelity as a dynamic archetype, resurrecting a retired standalone lens after the plan says those lenses are folded into edge-cases and testing
- **Proposed resolution**: Remove the optional cleanup; keep structure and plan-fidelity reserved in both lists, and only update comments or prompt text as needed

### FINDING_19:
- **Reviewer(s)**: Codex-Requirements
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: plan.txt:57-79; skills/implement/SKILL.md:763; scripts/generate-topology-docs.sh:195; scripts/generate-topology-docs.md:31; scripts/test-quick-mode-docs-sync.md:30
- **Concern**: The phrase-sync plan misses runtime, generator, and sibling contract files that still contain 6 Cursor specialists. Scenario: Editing only the listed docs leaves the /implement banner stale, topology regeneration can reintroduce the stale preamble, and the docs-sync contract documentation drifts from the harness
- **Proposed resolution**: Add these files to the update list; apply the canonical phrase to the generator source before regenerating docs/topology.md, and update the quick-mode docs-sync .md with the script

### FINDING_20:
- **Reviewer(s)**: Codex-Requirements
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: plan.txt:29-35,115-118; skills/review/scripts/check-reviewer-failure-threshold.md:11-31; skills/review/scripts/test-check-reviewer-failure-threshold.sh:68-184
- **Concern**: The new --intended-slots threshold contract lacks direct contract-doc and harness updates. Scenario: test-review-core uses a stubbed threshold checker, so parser/default behavior and 4-slot/8-slot threshold boundaries in the real script could regress unnoticed
- **Proposed resolution**: Add check-reviewer-failure-threshold.md and test-check-reviewer-failure-threshold.sh to the plan and testing list; cover --intended-slots 4 and 8, default 4, launched-slots equal intended, and dyn-*-codex-output exclusion

### FINDING_21:
- **Reviewer(s)**: Cursor-dyn-output-naming-contracts
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: skills/review/scripts/test-check-reviewer-failure-threshold.sh:68-168; skills/review/scripts/check-reviewer-failure-threshold.sh:37-40
- **Concern**: Plan changes threshold defaults and adds --intended-slots but omits the dedicated regression harness from Files to modify and Testing strategy. Scenario: The harness hardcodes INTENDED_SLOTS=6 (lines 119-128, 137-147, 155) and runs in CI via Makefile test-harnesses-19; lowering the script default to 4 without updating these cases will fail CI or leave stale 6-slot semantics untested for the new 4/8 both-vendor panel
- **Proposed resolution**: Add skills/review/scripts/test-check-reviewer-failure-threshold.sh (and sibling .md) to the plan: migrate fixtures to --intended-slots 4/8, and add one case with REVIEWER_FILE ending in dyn-example-codex-output.txt to lock the Codex dynamic-twin exclusion contract

### FINDING_22:
- **Reviewer(s)**: Cursor-dyn-reversion-completeness
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/review/scripts/test-check-reviewer-failure-threshold.sh:68-168; skills/review/scripts/check-reviewer-failure-threshold.md:13-31
- **Concern**: Threshold harness and contract doc omitted from the plan while still hardcoding the #2449-era 6-slot (and legacy 12-record HARD) world. Scenario: After `--intended-slots` defaults to 4 and both-vendor panels use 8 static slots, `make test-check-reviewer-failure-threshold` (Makefile:811-813) will fail or silently test the wrong contract; the dedicated `.md` will still document `INTENDED_SLOTS=6`
- **Proposed resolution**: Add `skills/review/scripts/test-check-reviewer-failure-threshold.sh` and `skills/review/scripts/check-reviewer-failure-threshold.md` to the UPDATED list; add 4-slot and 8-slot cases with explicit `--intended-slots` / `--launched-slots`; retire 12-record HARD fixtures unless they pass matching flags

### FINDING_23:
- **Reviewer(s)**: Codex-dyn-reversion-completeness, Codex-dyn-phrase-sync-completeness
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/review/scripts/test-check-reviewer-failure-threshold.sh:116-155; skills/review/scripts/check-reviewer-failure-threshold.md:12-31; skills/review/scripts/test-check-reviewer-failure-threshold.md:7-12
- **Concern**: Plan changes the threshold denominator but omits the dedicated threshold harness and contract docs from UPDATED targets. Scenario: The Makefile includes test-check-reviewer-failure-threshold, and its stale assertions still pin INTENDED_SLOTS=6; the docs also omit the new --intended-slots contract
- **Proposed resolution**: Add these files as explicit edit targets; update tests/docs for --intended-slots, default 4, 4-slot and 8-slot thresholds, and dynamic-slot exclusion under the new naming

### FINDING_24:
- **Reviewer(s)**: Codex-dyn-phrase-sync-completeness
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/implement/SKILL.md:759-763; scripts/test-quick-mode-docs-sync.sh:118-127; scripts/test-quick-mode-docs-sync.md:21-32
- **Concern**: Plan updates the docs-sync marker and public docs but omits the SKILL.md positive-anchor target and sibling contract doc.. Scenario: When POS_MARKERS changes to the canonical phrase, the harness still checks skills/implement/SKILL.md; leaving the Step 5 banner as "6 Cursor specialists" makes make test-quick-mode-docs-sync fail, and the sibling .md still documents the old marker.
- **Proposed resolution**: Add UPDATED entries for skills/implement/SKILL.md and scripts/test-quick-mode-docs-sync.md; change the Step 5 banner and sibling marker table to the same canonical phrase.

### FINDING_25:
- **Reviewer(s)**: Codex-dyn-phrase-sync-completeness
- **Severity**: important
- **Focus area**: correctness
- **Location**: scripts/generate-topology-docs.sh:188-195; scripts/generate-topology-docs.md:29-35; docs/topology.md:1-7
- **Concern**: docs/topology.md is generated, but the generator header still embeds the stale phrase.. Scenario: Regenerating docs/topology.md after the TSV change rewrites the header with "6 Cursor specialists", so generator checks or stale-phrase audits catch drift.
- **Proposed resolution**: Add UPDATED entries for scripts/generate-topology-docs.sh and scripts/generate-topology-docs.md; change the static header/contract text to the canonical phrase before regenerating docs/topology.md.

### FINDING_26:
- **Reviewer(s)**: Codex-dyn-phrase-sync-completeness
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: skills/review/diagram.svg:26-28
- **Concern**: The diagram update has no harness-enforced verification path; "manually confirm" is not a test.. Scenario: The SVG can keep "Reviewers (6 Cursor specialists + optional dynamic)" while all listed harnesses pass, shipping stale user-facing topology text.
- **Proposed resolution**: Add a minimal grep assertion in an existing docs-sync or review-structure harness that forbids the stale phrase or requires the canonical phrase in skills/review/diagram.svg; keep manual render confirmation only as a supplemental visual check.
