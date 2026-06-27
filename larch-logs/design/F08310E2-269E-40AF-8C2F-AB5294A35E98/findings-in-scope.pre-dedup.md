### FINDING_1:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: blocking
- **Focus area**: correctness
- **Location**: python/larch/design/design_pause.py:78-87
- **Concern**: pause/resume routing still keys off `.completed/step-5b.5`, which Step 5c will no longer write until publish-time sanitize. Scenario: After diagram-required Step 5b.5 writes `architecture-diagram.candidate.md` but before Step 5c, `_determine_step` returns `5b.5`; resume re-runs `design-step3b-entry.sh --mode diagram`, which deletes the candidate (`design-step3b-entry.sh:271-275`), forcing redundant regeneration or data loss. `pause_load_main` also downgrades stored `step=5c` to `5b.5` when the sentinel is absent (`design_pause.py:426-431`)
- **Proposed resolution**: Add `python/larch/design/design_pause.py` and `python/test_design_pause.py` to the plan: route to `5c` when `step-5b` is complete and `architecture-diagram.candidate.md` or `architecture-diagram.skipped` exists but `step-5b.5` does not; stop downgrading `5c`→`5b.5` in that state



### FINDING_2:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: blocking
- **Focus area**: correctness
- **Location**: python/design_publish.py:229-237
- **Concern**: Sanitizer helper contract does not require idempotency when `.completed/step-5b.5` already exists. Scenario: `finalize-step5.md` Fix-and-retry re-invokes `design-step5c.sh`. A second `publish_core` pass with an existing sentinel but no candidate will hit the ported missing-candidate branch and delete a previously promoted `architecture-diagram.md` (`design-step3b-sanitize.sh:132-138`)
- **Proposed resolution**: Specify `_sanitize_diagram_candidate` runs only when `.completed/step-5b.5` is absent; if present, no-op. Add a `test_design_publish.py` retry case: first pass promotes, validator returns rc 4, second pass keeps `architecture-diagram.md`



### FINDING_3:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: skills/design/references/finalize-step5.md:58-70
- **Concern**: Relocated sanitize prose still describes Step 5b.5 as the sanitizer owner. Scenario: Post-change operators and maintainers reading finalize-step5 will still expect a standalone 5b.5 sanitize fence and duplicate `readability-style.md` loads, undermining the slimming goal and risking reintroduction of the removed fence
- **Proposed resolution**: In `finalize-step5.md` updates, delete the Step 5b.5 sanitizer-owning sentences, state Step 5c/publish owns sanitize/promote/skip, and remove the second Step 5c `readability-style.md` mandatory-read (single read at Step 5 entry only)



### FINDING_4:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: blocking
- **Focus area**: correctness
- **Location**: python/design_publish.py:176-237
- **Concern**: _sanitize_diagram_candidate lacks idempotency when .completed/step-5b.5 already exists. Scenario: Step 5c Fix-and-retry and Override paths re-invoke design-step5c.sh per finalize-step5.md. After a first pass promotes architecture-diagram.candidate.md and touches step-5b.5, a retry hits the missing-candidate branch (shell design-step3b-sanitize.sh:132-138), deletes architecture-diagram.md, and writes architecture-diagram.skipped. That regresses a diagram that already passed sanitization.
- **Proposed resolution**: Add an early return: when step-5b.5 exists and architecture-diagram.md or architecture-diagram.skipped is present, skip sanitization. Pin with a test_design_lifecycle.py retry-after-partial-publish case and a test_design_publish.py direct-publish retry case.



### FINDING_5:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/design/SKILL.md:723-766
- **Concern**: Step 5c anti-halt gate still requires step-5b.5 before entry. Scenario: On DIAGRAM_REQUIRED=true, design-step3b-entry.sh --mode diagram does not write step-5b.5 (design-step3b-entry.sh:270-277); only the sanitizer did. After folding sanitize into Step 5c, diagram-required runs have step-5b complete and a candidate, but no step-5b.5 until the Step 5c preamble. The existing line 766 gate blocks the happy path.
- **Proposed resolution**: Replace the line 766 continuation with: continue to Step 5c after Step 5b.5 diagram entry finishes (skip path with step-5b.5, or diagram-required path with candidate written or generation bounded-failure logged). State that Step 5c owns sanitize and step-5b.5 completion before publish.



### FINDING_6:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: scripts/test-design-structure.sh:466-477
- **Concern**: Structure harness still pins the retired step-5b.5 precondition contract. Scenario: Pins at lines 466 and 766-adjacent prose require fail-closed when step-5b.5 is absent and sanitizer execution via design-step3b-sanitize.sh. After the fold, those pins either fail CI or re-lock the removed Bash fence.
- **Proposed resolution**: Update EXPECTED pins: invariant text should say Step 5c completes sanitize before publish, not that step-5b.5 must preexist Step 5c entry. Drop or replace the design-step3b-sanitize.sh primary-path pin at line 515. Add a pin that Step 5c owns sanitize-before-publish.



### FINDING_7:
- **Reviewer(s)**: Codex-Innovation
- **Severity**: important
- **Focus area**: architecture
- **Location**: skills/design/references/finalize-step5.md:60-70
- **Concern**: The plan says Step 5 should read `readability-style.md` once, but this file still has separate mandatory reads before the diagram and final-plan substeps.. Scenario: Step 5 will still load the style guide twice, so the promised once-per-Step-5 contract and line-slimming never land, and the new structure pin will fail.
- **Proposed resolution**: Collapse the two in-body reads into one Step 5 entry load, then update `scripts/test-design-structure.sh:478-479` to assert the single read.



### FINDING_8:
- **Reviewer(s)**: Codex-Innovation
- **Severity**: blocking
- **Focus area**: risk-integration
- **Location**: scripts/test-design-structure.sh:490-502
- **Concern**: The dispatch rewrite to a legacy note is not matched by the structure harness. It still asserts the old fallback table rows and `Fallback key` prose.. Scenario: The plan will fail `scripts/test-design-structure.sh` as soon as `oos-step5b-dispatch.md` stops advertising the dead status table, so the doc rewrite cannot land cleanly.
- **Proposed resolution**: Replace the table-row checks with a single legacy-note assertion and the new repair-stop contract for missing or disagreeing `NEXT_ACTION`.



### FINDING_9:
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: blocking
- **Focus area**: correctness
- **Location**: python/larch/design/design_pause.py:78-87
- **Concern**: Plan omits pause/resume routing updates after sanitize moves to Step 5c. Scenario: When step-5b is complete but step-5b.5 is absent and architecture-diagram.candidate.md already exists (diagram-required path after orchestrator authoring, before Step 5c sanitize), _determine_step still returns 5b.5 and pause_load downgrades legacy STEP=5c to 5b.5 (lines 427-431). Re-entering design-step3b-entry.sh --mode diagram with DIAGRAM_REQUIRED=true rm -f the candidate (design-step3b-entry.sh:271-275), silently discarding authored diagram work on pause/resume or crash recovery.
- **Proposed resolution**: Add ### UPDATED: python/larch/design/design_pause.py and python/test_design_pause.py to the plan. Route to 5c when step-5b is present, step-5b.5 is absent, and a readable non-empty architecture-diagram.candidate.md exists; keep 5b.5 only when diagram work is still outstanding. Apply the same candidate-aware rule in the pause_load STEP=5c downgrade block. Add pause/resume tests covering candidate-present resume to 5c.



### FINDING_10:
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/design_publish.py:229-284
- **Concern**: Plan places sanitizer in publish_core before the existing .pause-requested gate. Scenario: The plan replaces the step-5b.5 precondition with _sanitize_diagram_candidate near the top of publish_core, but publish_core pause-save remains at lines 269-284. step5c_core pause-check covers the normal /design path, yet the plan also requires direct python/cli.py design publish to sanitize when step-5b is complete. A direct publish call with .pause-requested would mutate diagram artifacts before honoring pause.
- **Proposed resolution**: In design_publish.py, run the existing .pause-requested pause-save block before _sanitize_diagram_candidate on every publish entrypoint, or extract sanitizer invocation to step5c_core after its pause gate and keep publish_core side-effect-free on pause. Add a publish_core test that asserts no sanitizer artifacts are written when .pause-requested is set.



### FINDING_11:
- **Reviewer(s)**: Codex-Pragmatic
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/test_design_publish.py:199-232
- **Concern**: Replacement publish tests still need a no-`.completed/step-5b.5` fixture. Scenario: If the new sanitizer tests keep the current shared setup that seeds `.completed/step-5b.5`, direct `design publish` is never exercised without the sentinel. The refactor can still regress on the removed hard precondition, and the suite would stay green.
- **Proposed resolution**: Add a fixture that omits `.completed/step-5b.5`, and make the replacement publish test assert direct `design publish` succeeds by sanitizing or skipping from that state.



### FINDING_12:
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/design/SKILL.md:758-766
- **Concern**: Step 5b.5 continuation still gates on `.completed/step-5b.5` after sanitize fence removal. Scenario: On `DIAGRAM_REQUIRED=true`, `design-step3b-entry.sh --mode diagram` does not write `.completed/step-5b.5` (only the skip path does). Removing the standalone `design-step3b-sanitize.sh` fence leaves no pre-Step-5c writer for that sentinel, so the orchestrator can stall on line 766 even though Step 5c is supposed to create the marker during publish.
- **Proposed resolution**: In `skills/design/SKILL.md` Step 5b.5, drop the "only after `.completed/step-5b.5` exists" gate; continue to Step 5c immediately after diagram entry plus candidate composition (or the skip breadcrumb when `DIAGRAM_REQUIRED=false`). Align the Step 5 invariant with Step 5c owning sanitize completion.



### FINDING_13:
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: python/design_publish.py:231-237
- **Concern**: Issue requires sanitizer-rejection WARN to move to Step 5c driver WARN replay, but the Python port only lists bounded `execution-issues.md` writes. Scenario: The plan updates `finalize-step5.md` prose for Step 5c WARN replay, yet `_sanitize_diagram_candidate` is specified only to append bounded warnings. Step 5c replays driver warnings via `WARN=` lines parsed from publish stdout/result-env (`_replay_warn_error` in `design_lifecycle.py`), not from execution-issues alone. Without publish-stdout `WARN=` (or equivalent driver-visible lines), sanitizer rejections lose the chat visibility the standalone 5b.5 fence currently prints.
- **Proposed resolution**: In `_sanitize_diagram_candidate`, emit bounded operator-visible sanitizer skip/reject notices as publish-stdout `WARN=` lines (matching existing Step 5c driver WARN replay), in addition to bounded execution-issues logging. Add/adjust `python/test_design_publish.py` to assert a reject path produces replayable WARN output and still omits diagram bodies.



### FINDING_14:
- **Reviewer(s)**: Codex-Requirements
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/design/scripts/design-step5b-prepare.md:22-30
- **Concern**: Plan never updates the prompt-side prepare doc that still tells Step 5b to fall back to FILE_DESIGN_OOS_STATUS when NEXT_ACTION is absent.. Scenario: That leaves a shipped runtime surface pointing at the dead dispatch table and contradicts the feature's contract to remove prompt-side fallback routing.
- **Proposed resolution**: Add this file to the plan and rewrite the fallback bullet so missing NEXT_ACTION is a repair stop, with no FILE_DESIGN_OOS_STATUS fallback reference.



### FINDING_15:
- **Reviewer(s)**: Codex-Generic
- **Severity**: blocking
- **Focus area**: correctness
- **Location**: python/design_publish.py:214-222; skills/design/scripts/design-step3b-sanitize.sh:153-156
- **Concern**: The proposed publish-time sanitizer is not specified as idempotent once `.completed/step-5b.5` already represents an accepted or skipped diagram state. Scenario: After a valid candidate is promoted, a later Step 5c retry has no candidate but does have `architecture-diagram.md`. The planned missing-candidate branch would delete the accepted diagram, write `architecture-diagram.skipped`, and clear the issue diagram on retry. The same false failure path can also warn on normal `DIAGRAM_REQUIRED=false` skips.
- **Proposed resolution**: Specify that `_sanitize_diagram_candidate` first returns success when `.completed/step-5b.5` already exists with either a non-empty `architecture-diagram.md` or `architecture-diagram.skipped`. Only treat a missing candidate as a failure/skip when there is no completed accepted or skipped state.



### FINDING_16:
- **Reviewer(s)**: Codex-Generic
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: python/larch/design/design_lifecycle.py:3990-4019; python/larch/design/design_lifecycle.py:4468-4481
- **Concern**: The plan moves sanitizer warnings into `publish_core` but does not plumb `WARN` through Step 5c output. Scenario: Sanitizer rejection would be captured inside the publish stdout temp file or only appended to `execution-issues.md`. `step5c_core` currently emits only selected result rows, so the existing Step 5c background WARN replay has no `WARN=` row to replay.
- **Proposed resolution**: Add a bounded sanitizer warning row to the publish result contract. Allow and emit `WARN` in Step 5c, deduping if needed, while preserving the no-diagram-body rule.



### FINDING_17:
- **Reviewer(s)**: Cursor-dyn-Design Finalize Flow
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: skills/design/scripts/design-step3b-sanitize.sh:136-169, python/design_publish.py, skills/design/references/finalize-step5.md:80
- **Concern**: Folding sanitize into captured publish_core drops foreground sanitizer chat breadcrumbs without a Step 5c relay contract. Scenario: Today `design-step3b-sanitize.sh` prints `**⚠ 5b.5: ...**` to orchestrator stdout before the background Step 5c fence. The plan ports sanitize into `publish_core` captured by `_capture_contract_stream_to_paths`, then deletes that stdout; `step5c_core` emits only machine KVs and finalize-step5 WARN replay expects driver WARN bodies from Step 5c output. Sanitizer skip/reject becomes execution-issues-only unless the port adds explicit bounded `WARN=` / contract-stream emission.
- **Proposed resolution**: In `_sanitize_diagram_candidate`, emit the same bounded `**⚠ 5b.5: ...**` lines (or `WARN=` rows) on the publish contract stream and document in finalize-step5 that Step 5c replays them; add a pytest asserting sanitizer skip/reject surfaces on captured publish stdout without Mermaid bodies.



### FINDING_18:
- **Reviewer(s)**: Cursor-dyn-Design Finalize Flow
- **Severity**: blocking
- **Focus area**: correctness
- **Location**: scripts/test-design-structure.sh:465-475, skills/design/SKILL.md:723-766
- **Concern**: Plan omits harness pin updates for the new Step 5 ordering contract. Scenario: `test-design-structure.sh` pins the exact invariant ending in "fail closed when `.completed/step-5b.5` is absent" and finalize-step5 sanitizer-at-5b.5 prose. The plan removes that fail-closed gate and moves sanitize to Step 5c but its `scripts/test-design-structure.sh` section never updates these pins, so `make test-design-structure` will fail or force contradictory SKILL text.
- **Proposed resolution**: Add explicit harness updates: replace the invariant pin with "Step 5c completes sanitize before publish", drop/replace the finalize-step5 sanitizer-at-5b.5 pin, and pin absence of the standalone `design-step3b-sanitize.sh` SKILL fence.



### FINDING_19:
- **Reviewer(s)**: Cursor-dyn-Design Finalize Flow
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/design/SKILL.md:756-766, plan Step 5b.5 section
- **Concern**: Diagram-required path still gated on `.completed/step-5b.5` before Step 5c in current SKILL text. Scenario: After folding sanitize into Step 5c, diagram-required runs write only `architecture-diagram.candidate.md` at Step 5b.5 and create `.completed/step-5b.5` inside publish. The plan does not explicitly remove SKILL line 766 ("Continue to Step 5c ... only after `.completed/step-5b.5` exists"), which conflicts with the deferred-sentinel design and can block legitimate continuation.
- **Proposed resolution**: In the SKILL Step 5b.5 rewrite, replace the sentinel-exists gate with "continue to Step 5c after entry/classification and any required candidate authoring; Step 5c owns sanitize completion and sentinel write."



### FINDING_20:
- **Reviewer(s)**: Cursor-dyn-Design Finalize Flow
- **Severity**: latent
- **Focus area**: correctness
- **Location**: skills/design/SKILL.md:228,794, skills/design/references/finalize-step5.md
- **Concern**: Relocating `_publish_rc` 2/3/5 abort prose leaves resume@5c without loaded abort routing. Scenario: Step 0b `resume@<STEP>` jumps directly to the named step and skips Step 5 entry, including the mandatory finalize-step5 read. Moving the `_publish_rc` abort wall out of SKILL.md into finalize-step5 with only a pointer risks resume@5c parsing publish-tail failures without the abort/stop contract.
- **Proposed resolution**: Keep a minimal inline `_publish_rc` routing table in SKILL Step 5c post-notification prose, or add an explicit resume@5c carve-out: MANDATORY read finalize-step5 before parsing `_publish_rc`. ## Findings ### 1. risk-integration — Sanitizer WARN visibility regression (`design-step3b-sanitize.sh:136-169`, `python/design_publish.py`, `finalize-step5.md:80`) **Concern:** The plan moves mechanical sanitize into `publish_core` inside a captured stdout file that Step 5c deletes. Foreground `**⚠ 5b.5: ...**` breadcrumbs from `design-step3b-sanitize.sh` will no longer reach chat, and finalize-step5’s “driver WARN replay” path does not read `execution-issues.md`. **Suggested revision:** Port must emit bounded `WARN=` or `**⚠**` lines on the publish contract stream; document Step 5c replay; test that stdout has warnings but no diagram bodies. ### 2. correctness (blocking) — Stale structure harness pins (`scripts/test-design-structure.sh:465-475`) **Concern:** Pinned invariant text still requires “fail closed when `.completed/step-5b.5` is absent” and sanitizer-at-5b.5 finalize prose. The plan’s harness section does not update these pins. **Suggested revision:** Update `test-design-structure.sh` pins to match the new ordering contract in the plan’s own `scripts/test-design-structure.sh` section. ### 3. correctness — Stale Step 5b.5→5c continuation gate (`skills/design/SKILL.md:756-766`) **Concern:** Diagram-required runs defer `.completed/step-5b.5` until Step 5c sanitize, but SKILL still tells the orchestrator to continue to Step 5c only after the sentinel exists. **Suggested revision:** Explicitly replace line 766 in the planned SKILL rewrite with candidate-authoring completion as the gate, not sentinel presence. ### 4. correctness (latent) — `_publish_rc` abort routing on resume@5c (`skills/design/SKILL.md:228,794`, `finalize-step5.md`) **Concern:** Moving rare abort prose out of always-loaded SKILL.md breaks direct resume jumps to Step 5c that skip Step 5 entry. **Suggested revision:** Keep minimal inline post-notification routing in SKILL, or mandate finalize-step5 reload on resume@5c before `_publish_rc` parsing.



