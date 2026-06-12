### FINDING_2: Drafter scout manifests bypass existing validation and caps
- **Reviewer(s)**: Cursor-Arch, Codex-Arch, Cursor-Innovation, Cursor-Pragmatic, Cursor-dyn-sentinel-parse-contract, Codex-dyn-sentinel-parse-contract
- **Severity**: important
- **Concern**: The drafter scout path validates less than the existing scout wrapper. Invalid fields, unsafe prompt content, reserved static slugs, duplicates, or over-cap archetypes can reach plan review dispatch, causing duplicate reviewer slots, budget waste, or unsafe interpolation.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Reuse the reserved-slug filter/cap from `skills/design/scripts/scout-plan-archetypes-wrapper.sh` (`filter_and_cap_manifest`) when materializing drafter scout output, or call that jq filter from the launcher after parse. Fail-open to `{"archetypes":[]}` when filtering removes everything invalid
  - From Codex-Arch: Reuse or port the existing scout-dynamic-archetypes validation and cap/filter rules before writing scout-plan-manifest.json. On invalid rows or invalid JSON, fail open to an empty manifest/static-only.
  - From Cursor-Innovation: After JSON parse, run the same filter_and_cap_manifest jq from scout-plan-archetypes-wrapper.sh:137-156 (cap 3) before atomic write; reject individual archetypes failing scout-dynamic field rules when feasible
  - From Cursor-Pragmatic: After optional scout extraction, validate with the same jq rules as scripts/scout-dynamic-archetypes.sh and apply filter_and_cap_manifest (or call a shared helper). On failure emit SCOUT_WRITTEN=false; do not write scout-plan-manifest.json.
  - From Cursor-dyn-sentinel-parse-contract: Reuse filter_and_cap_manifest (or equivalent jq) when materializing scout-plan-manifest.json, or call it from launch-codex-drafter.sh / launch-claude-drafter.sh after parse; cap at three and filter reserved slugs before rename
  - From Codex-dyn-sentinel-parse-contract: Validate or normalize the drafter scout block with the same constraints as current scout output before writing the canonical manifest. On invalid rows, fail open with SCOUT_WRITTEN=false and SCOUT_FAIL_REASON in the drafter status sidecar rather than emitting a weaker manifest.


### FINDING_3: Scout sentinel placement and parse failure rules are undefined
- **Reviewer(s)**: Cursor-Arch, Cursor-dyn-sentinel-parse-contract, Codex-dyn-sentinel-parse-contract
- **Severity**: important
- **Concern**: The plan adds `LARCH_SCOUT_BEGIN/END` without a complete contract for count, ordering, overlap, nesting, and prompt placement relative to plan and summary envelopes. Scout JSON can pollute `plan.txt`, become unparseable, or make parser failure behavior inconsistent.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Define scout sentinels as optional, exactly one balanced pair, wholly outside `LARCH_PLAN_BEGIN/END` (and outside summary sentinels). Reject overlapping/nested placement. Mirror the rule in `scripts/parse-drafter-output.md` and add harness cases in `scripts/test-launch-codex-drafter.sh`
  - From Cursor-dyn-sentinel-parse-contract: Mirror summary rules: zero or one balanced scout pair outside plan/summary envelopes; nested scout inside plan or summary is non-fatal with SCOUT_WRITTEN=false; duplicate/reversed/out-of-order scout is non-fatal; parser must exit 0 when plan is valid; document in parse-drafter-output.md
  - From Cursor-dyn-sentinel-parse-contract: Add explicit ordering after LARCH_PLAN_END (or before LARCH_SUMMARY_BEGIN): optional LARCH_SCOUT_BEGIN/END outside both envelopes; update CODEX trusted instructions in launch-codex-drafter.sh:167-175 to match
  - From Codex-dyn-sentinel-parse-contract: Specify zero or one balanced LARCH_SCOUT_BEGIN/LARCH_SCOUT_END pair; begin must precede end; scout must not overlap or nest inside plan or summary envelopes; malformed scout sentinels should set SCOUT_WRITTEN=false with a stable SCOUT_FAIL_REASON without relaxing strict plan and summary validation.


### FINDING_4: Generated implementer prompts still advertise only two output channels
- **Reviewer(s)**: Codex-Arch, Cursor-dyn-generated-file-sync, Codex-dyn-generated-file-sync
- **Severity**: important
- **Concern**: The generated Codex and Cursor implementer headers still describe only `MANIFEST_PATH` and `QA_PENDING_PATH`. Regenerated prompts can contradict the new `SCOUT_MANIFEST_PATH` sidecar contract, so external coders may omit scout output.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Arch: Update python/rendering.py with the third best-effort <SCOUT_MANIFEST_PATH> output channel, and keep the launcher invocation parameter blocks aligned with that generated prompt contract.
  - From Cursor-dyn-generated-file-sync: Add ### UPDATED: python/rendering.py extending _implementer_text() preamble for codex and cursor to list optional third SCOUT_MANIFEST_PATH channel (best-effort); regenerate both implementer agents; extend python/test_rendering.py if it pins header shape
  - From Codex-dyn-generated-file-sync: Update python/rendering.py in the plan so both implementer headers list SCOUT_MANIFEST_PATH as an optional best-effort scout manifest output, then regenerate agents/codex-implementer.md and agents/cursor-implementer.md and run generate check


### FINDING_5: Missing or invalid coder sidecars can re-enable per-round implement scout
- **Reviewer(s)**: Codex-Pragmatic, Cursor-Requirements, Codex-Requirements, Codex-dyn-sentinel-parse-contract, Cursor-dyn-flag-chain-coverage
- **Severity**: important
- **Concern**: Implement Step 5 can still invoke the legacy per-round scout when the coder sidecar is missing, empty, invalid, not forwarded, or handled by a pre-scout branch that later falls through. This violates the no-fallback-scout requirement for failed coder scout output.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Pragmatic: Use a durable external-coder marker such as $IMPLEMENT_TMPDIR/step2-spawn-coder.txt. For loop and single Step 5 external-coder runs, pass --pre-scouted-manifest $IMPLEMENT_TMPDIR/scout-coder-manifest.json even when missing or empty, and let dispatch-panel's supplied-invalid branch continue static-only. Preserve no flag only for Claude fallback and mav-apply.
  - From Cursor-Requirements: After external STATUS=complete|needs_qa, always materialize $IMPLEMENT_TMPDIR/scout-coder-manifest.json (valid JSON from the sidecar, or {"archetypes":[]} when absent/invalid). Have run-step5-review.sh pass --pre-scouted-manifest on every external-implementer Step 5 round; gate per-round scout to Claude-fallback-only via an explicit session marker, not file absence alone.
  - From Cursor-Requirements: When --pre-scouted-manifest is present, handle it in a top-level branch before the SCOUT_STATUS==na scout launch: validate once, set SCOUT_STATUS to pre-scouted or parse-failed, synthesize or clear slots, and never call scout-dynamic-archetypes.sh for any round while the flag remains set.
  - From Codex-Requirements: Revise the plan so /implement Step 5 suppresses fallback scout even when the coder sidecar is missing or invalid. For example, pass the conventional pre-scout path for implement review rounds and let dispatch-panel treat missing or invalid as static-only, or materialize a validated empty sidecar. Update the run-step5/review forwarding tests to assert missing and empty sidecars do not invoke scout.
  - From Codex-dyn-sentinel-parse-contract: For external codex/cursor Step 2 attempts, materialize a canonical empty valid scout-coder-manifest.json or another supplied pre-scout manifest on missing/invalid sidecar, then pass --pre-scouted-manifest so Step 5 stays static-only. Reserve absent flag for standalone /review and true Claude fallback paths; keep mav-apply unchanged.
  - From Cursor-dyn-flag-chain-coverage: External Codex/Cursor completes but omits the sidecar; run-step5 passes no --pre-scouted-manifest; review-and-fix defaults DYNAMIC_ARCHETYPES to 3 for implement; dispatch-panel.sh runs scout-dynamic-archetypes.sh every round — violating the issue non-goal forbidding fallback scout when the coder fails to produce a manifest When scout-coder-manifest.json is absent or empty, force static-only on the implement path (e.g. pass --dynamic-archetypes 0 from run-step5-review.sh, or in dispatch-panel.sh skip internal scout whenever IMPLEMENT_TMPDIR is set and --pre-scouted-manifest was not supplied)


### FINDING_8: Claude fallback can consume stale scout sidecars
- **Reviewer(s)**: Codex-dyn-flag-chain-coverage
- **Severity**: important
- **Concern**: Claude fallback exits can occur before external cleanup, or after manifest-invalid recovery, leaving stale or already copied scout sidecars. Step 5 can then consume pre-scout data despite the fallback contract.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-dyn-flag-chain-coverage: Define the canonical scout sidecar immediately after TMPDIR_ARG is canonicalized and remove it before every STATUS=claude_fallback emission, including coder=claude, cursor presence fallback, and manifest-invalid recovery. Keep external launch paths as the only writers, and add the stale-sidecar fallback fixture.


### FINDING_9:
- **Reviewer(s)**: Codex-Arch
- **Severity**: important
- **Focus area**: correctness
- **Location**: scripts/run-step5-review.sh:230; skills/review-and-fix/scripts/review-and-fix.sh:1354-1370; skills/review/scripts/dispatch-panel.sh:372-414
- **Concern**: [SCOPE-REDUCTION] Missing coder-scout failure path keeps per-round scout fallback for /implement. Scenario: If an external coder completes but omits or produces an invalid scout sidecar, run-step5-review passes no pre-scout flag, review-and-fix defaults implement dynamic archetypes to 3, and dispatch-panel launches scout-dynamic-archetypes on each review round. That violates the run-scout-once and no fallback-scout scope.
- **Proposed resolution**: For external coder paths, materialize or pass a valid empty pre-scout manifest when no valid coder sidecar exists, or thread an explicit static-only/pre-scouted mode. Reserve absent --pre-scouted-manifest for standalone /review and any intentionally documented Claude fallback path.


### FINDING_10:
- **Reviewer(s)**: Codex-Innovation
- **Severity**: important
- **Focus area**: correctness
- **Location**: scripts/run-step5-review.sh:188-230; skills/review-and-fix/scripts/review-and-fix.sh:1354-1370; skills/review/scripts/dispatch-panel.sh:372-391
- **Concern**: [SCOPE-REDUCTION] Missing implement scout sidecar falls back to the old per-round scout path. Scenario: The plan passes --pre-scouted-manifest only when scout-coder-manifest.json exists and is non-empty. In implement mode review-and-fix defaults dynamic archetypes to 3, so dispatch-panel.sh will spawn scripts/scout-dynamic-archetypes.sh every round when the coder omits the sidecar. That violates the feature goal and the non-goal forbidding fallback scout invocation.
- **Proposed resolution**: When Step 5 is for /implement and no coder sidecar is available, force static-only review instead of omitting the flag. For example pass --no-dynamic-archetypes or materialize/pass a valid empty pre-scout manifest. Keep absent-flag behavior unchanged for standalone /review only.




### FINDING_1: diff_lines can be stripped from extracted plan
- **Reviewer(s)**: Cursor-Arch, Codex-Arch, Codex-Innovation, Codex-Pragmatic, Codex-Requirements
- **Severity**: important
- **Concern**: The proposed sentinel ordering moves `diff_lines:` outside the `LARCH_PLAN_BEGIN` / `LARCH_PLAN_END` envelope, while existing parsing and validation expect the extracted `plan.txt` to end with that trailer. A compliant drafter output can therefore fail parsing or produce a malformed plan artifact.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: After parsing the trailing `diff_lines:` from raw output, append it (and any optional metadata trailers) to the extracted plan body before atomic write to `<plan-out>`; document the rule in `scripts/parse-drafter-output.md`.
  - From Codex-Arch: Keep diff_lines as the final line inside LARCH_PLAN_BEGIN/LARCH_PLAN_END, then place the optional scout block after LARCH_PLAN_END and before the optional summary block
  - From Codex-Innovation: Keep diff_lines as the final line inside LARCH_PLAN_BEGIN/LARCH_PLAN_END. Require order: plan block whose body ends in diff_lines, optional scout block, optional summary block.
  - From Codex-Pragmatic: Keep diff_lines as the last line inside LARCH_PLAN_BEGIN/LARCH_PLAN_END. Put the optional scout block after LARCH_PLAN_END and before the optional summary block, or keep current summary placement, but do not move the plan trailer outside the plan block.
  - From Codex-Requirements: Keep diff_lines inside LARCH_PLAN_BEGIN and LARCH_PLAN_END as the final plan body line. Align the prompt, parser, docs, and tests on one valid ordering.


### FINDING_2: step2-spawn-coder.txt repurposing breaks tmpdir reuse guard
- **Reviewer(s)**: Codex-Arch, Codex-Innovation, Cursor-Pragmatic, Codex-Requirements
- **Severity**: important
- **Concern**: The plan reuses `step2-spawn-coder.txt` as a Step 5 pre-scout marker and changes its lifecycle, but that file already records the external coder early to prevent cross-coder tmpdir reuse. Delaying, deleting, or redefining it can allow codex and cursor to reuse the same tmpdir and desynchronize resume state.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Arch: Keep step2-spawn-coder.txt semantics unchanged and add a separate successful-external-coder marker for Step 5 pre-scout detection
  - From Codex-Innovation: Preserve step2-spawn-coder.txt as the pre-launch coder guard. Use a separate completed-external marker for Step 5 pre-scout mode, or keep the existing marker semantics and clear it only on Claude fallback paths.
  - From Cursor-Pragmatic: Use a separate Step 5 eligibility marker (for example step2-external-scout-eligible.txt) or gate run-step5-review.sh on session/bootstrap state. Keep step2-spawn-coder.txt early-write semantics unchanged for the cross-coder guard.
  - From Codex-Requirements: Preserve the existing early coder-mismatch sentinel. Use a separate completed-external-coder marker for Step 5 pre-scout threading, or otherwise keep the current guard ordering and add a distinct completion signal.


### FINDING_3: pre-scouted manifests are accepted but do not synthesize dynamic slots
- **Reviewer(s)**: Cursor-Requirements, Cursor-dyn-path-contract
- **Severity**: important
- **Concern**: `--pre-scouted-manifest` can validate and set `SCOUT_STATUS=pre-scouted`, but dynamic slot synthesis only runs on the normal `ok` scout path. A valid coder-produced manifest can therefore be read and normalized while Step 5 remains static-only.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Requirements: After the pre-scout validation branch, call `synthesize_dynamic_slots` for `SCOUT_STATUS=pre-scouted` (or treat pre-scouted as `ok` for synthesis only); extend `test-dispatch-panel.sh` to assert non-zero `DYNAMIC_SLOTS` on the valid pre-scout path
  - From Cursor-dyn-path-contract: Add an early `--pre-scouted-manifest` branch before line 372 that validates/filters the file, sets `SCOUT_MANIFEST`, and on success calls `synthesize_dynamic_slots "$SCOUT_MANIFEST"` (or extract shared post-scout synthesis invoked for both `ok` and `pre-scouted`)


### FINDING_5: inline drafter fallback can reuse stale design scout sidecar
- **Reviewer(s)**: Cursor-dyn-stale-sidecar-cleanup
- **Severity**: important
- **Concern**: The design drafter failure path falls back to inline drafting without removing an existing `scout-plan-manifest.json`. Step 3 can then attach dynamic review slots from a stale manifest to an inline-only plan.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-dyn-stale-sidecar-cleanup: Add rm -f "$DESIGN_TMPDIR/scout-plan-manifest.json" (and any candidate temp globs the launchers use) to the drafter-failure / inline-fallback branch, and update the edge-case note at plan.txt:426 so static-only is enforced by deletion not absence of new output.


### FINDING_7:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Focus area**: architecture
- **Location**: scripts/parse-drafter-output.py:26-60
- **Concern**: [SCOPE-REDUCTION] Plan relocates final diff_lines after LARCH_SUMMARY_* instead of keeping it inside LARCH_PLAN_*. Scenario: Moving the trailer forces parser, launch-codex-drafter.sh:173, design-step2b-drafter.sh:224, parse-drafter-output.md:31-32, and design-postplan-emit/check-plan-size to change together; any miss leaves plan.txt without a valid diff_lines tail
- **Proposed resolution**: Keep diff_lines as the last line inside the plan envelope; add optional LARCH_SCOUT_* only between LARCH_PLAN_END and LARCH_SUMMARY_BEGIN


### FINDING_8:
- **Reviewer(s)**: Codex-dyn-path-contract
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/implement/scripts/step2-implement.sh:548-556; skills/implement/scripts/test-step2-dispatch.sh:407-460
- **Concern**: [SCOPE-REDUCTION] The plan repurposes step2-spawn-coder.txt as a completed external-coder marker and says to remove it before each Step 2 launch, but that file is the existing cross-coder tmpdir-reuse guard.. Scenario: A tmpdir that recorded codex can be relaunched with cursor if the proposed cleanup deletes or rewrites the sentinel before the guard runs. The existing coder-mismatch-tmpdir-reuse contract is pinned by tests.
- **Proposed resolution**: Preserve step2-spawn-coder.txt's current first-writer guard semantics. Do not delete it at Step 2 start. Use the existing marker for Step 5 only after preserving the guard, or add a separate completed-external marker if completion-only semantics are required.



### FINDING_2: Pre-scouted manifests can bypass low-risk dynamic skips
- **Reviewer(s)**: Codex-Innovation
- **Severity**: important
- **Concern**: The pre-scouted branch may take priority over existing docs-only, test-only, or generated-only dynamic-review skips, allowing external implement manifests to add dynamic reviewers to diffs that currently stay static-only.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Innovation: Keep the classifier skip ahead of both legacy scout launch and pre-scout synthesis. If DIFF_MODE is docs-only, test-only, or generated-only, ignore the pre-scouted file, write an empty per-round manifest, and emit the existing skipped-* status.


### FINDING_3: Optional summary contract may become mandatory
- **Reviewer(s)**: Codex-Innovation, Codex-Pragmatic, Codex-Requirements, Codex-dyn-sentinel-contract-drift
- **Severity**: important
- **Concern**: The parser, launcher, and docs plan can accidentally require `LARCH_SUMMARY_BEGIN/END`, even though current drafter output allows no summary. The new scout placement also needs to remain valid when the summary block is omitted.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Innovation: Preserve the zero-or-one summary pair contract. Require order only for blocks that are present: PLAN, optional SCOUT, optional SUMMARY. Keep no-summary outputs valid.
  - From Codex-Pragmatic: Amend the parser, launcher prompt, docs, and tests to preserve the existing optional-summary contract: plan -> optional scout -> optional summary.
  - From Codex-Requirements: Keep LARCH_SUMMARY_BEGIN/END optional; when present, require it after the optional scout block; retain no-summary launcher tests
  - From Codex-dyn-sentinel-contract-drift: Revise the plan for parse-drafter-output.py, design-step2b-drafter.sh, and the .md docs to preserve optional summary: exactly one plan block, then optional scout block, then optional summary block. If summary is omitted, scout may still appear immediately after LARCH_PLAN_END. Keep diff_lines: <N> as the final plan body line.


### FINDING_6: Drafter output templates still put summary before plan
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: important
- **Concern**: The required-output block can still print `LARCH_SUMMARY` before `LARCH_PLAN` while the parser expects plan, optional scout, then optional summary. Drafters may follow the stale template and produce output the parser rejects or mishandles.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Requirements: Reorder the printf Required output format block to LARCH_PLAN_BEGIN or LARCH_PLAN_END, optional LARCH_SCOUT sentinels, then LARCH_SUMMARY; mirror the same order in launch-codex-drafter.sh and launch-claude-drafter.sh trusted instructions


### FINDING_7: Sibling script documentation updates are incomplete
- **Reviewer(s)**: Codex-Requirements
- **Severity**: important
- **Concern**: The plan changes script behavior but does not update every required sibling `.md` file, and it labels an existing parser doc as `NEW` instead of `UPDATED`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Requirements: Add UPDATED plan sections for the missing sibling docs and change scripts/parse-drafter-output.md from NEW to UPDATED


### FINDING_8: Claude fallback Step 5 can still launch legacy per-round scout
- **Reviewer(s)**: Codex-dyn-flag-chain-completeness
- **Severity**: important
- **Concern**: If Claude fallback omits `--pre-scouted-manifest`, the implement review path can fall back to the legacy scout launch because dynamic archetypes still default to enabled. That conflicts with the goal to avoid fallback scout invocations.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-dyn-flag-chain-completeness: Make run-step5-review explicitly force static-only for Claude-fallback Step 5, such as forwarding --dynamic-archetypes 0 or an equivalent explicit static-only flag when the external eligibility marker is absent due Claude fallback. Add a focused test that asserts no scout-capable dynamic path is enabled on Claude fallback.


### FINDING_11:
- **Reviewer(s)**: Codex-Arch
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/review/scripts/dispatch-panel.sh:131-136
- **Concern**: [SCOPE-REDUCTION] Pre-scout branch drops existing diff-mode skip gate. Scenario: A /implement run with a docs-only, test-only, or generated-only diff plus a valid pre-scouted manifest would launch dynamic reviewers, while current dispatch sets SCOUT_STATUS=skipped-* and DYNAMIC_SLOTS=0
- **Proposed resolution**: Keep the classifier skip ahead of the pre-scout branch; when SCOUT_STATUS is skipped-* ignore --pre-scouted-manifest and stay static-only


### FINDING_12:
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/design/scripts/design-step2b-drafter.sh:156-162
- **Concern**: [SCOPE-REDUCTION] Scout block requires PLAN_END then optional SCOUT then SUMMARY_BEGIN but the drafter prompt still lists LARCH_SUMMARY before LARCH_PLAN. Scenario: Models can keep emitting summary-first output; scout sentinels cannot sit between PLAN_END and SUMMARY_BEGIN so scout extraction stays dead and Step 3 stays static-only despite the feature
- **Proposed resolution**: Reorder Required output format to LARCH_PLAN_BEGIN/END optional LARCH_SCOUT_* then LARCH_SUMMARY_*; mirror the same order in launch-codex-drafter.sh and launch-claude-drafter.sh trusted instructions




### FINDING_3: Missing Step 2 eligibility marker can still allow per-round scout
- **Reviewer(s)**: Cursor-Arch, Cursor-Innovation, Cursor-Pragmatic, Cursor-Requirements, Cursor-dyn-eligibility-marker-lifecycle
- **Severity**: important
- **Concern**: Step 5 lacks a durable static-only contract for runs without `step2-external-scout-eligible.txt`, so `dispatch-panel.sh` can still launch legacy per-round scout when no valid pre-scout manifest should be used.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Specify and implement one detection rule in run-step5-review.sh: when step2-external-scout-eligible.txt is absent after Step 2, forward --dynamic-archetypes 0 (or equivalent static-only control); when present, forward --pre-scouted-manifest as planned. Document the rule in run-step5-review.md and pin it in test-run-step5-review.sh.
  - From Cursor-Innovation: When step2-external-scout-eligible.txt is absent, always forward --dynamic-archetypes 0 (or --no-dynamic-archetypes) from run-step5-review.sh; do not rely on omitting --pre-scouted-manifest alone. Extend test-run-step5-review.sh to assert the forced-zero path for missing-marker runs, not only labeled Claude-fallback cases.
  - From Cursor-Pragmatic: When step2-spawn-coder.txt exists and step2-external-scout-eligible.txt is absent, force --dynamic-archetypes 0 (and do not pass --pre-scouted-manifest). Keep primary --coder claude runs (no spawn-coder file) on the existing per-round scout path
  - From Cursor-Requirements: When `step2-external-scout-eligible.txt` is absent, always append `--dynamic-archetypes 0` and omit `--pre-scouted-manifest`. When the marker exists, pass `--pre-scouted-manifest` per the existing rules. Document and pin both branches in `scripts/test-run-step5-review.sh`.
  - From Cursor-dyn-eligibility-marker-lifecycle: When the eligibility marker is absent, always append --dynamic-archetypes 0 (override session cap). Pass --pre-scouted-manifest only when the marker exists


### FINDING_6: Malformed scout sentinels can contaminate plan.txt
- **Reviewer(s)**: Cursor-dyn-parse-sentinel-contract, Codex-dyn-parse-sentinel-contract
- **Severity**: important
- **Concern**: Drafter parsing can accept malformed or misplaced scout sentinel spans while still copying scout markers or JSON into `plan.txt`, and the proposed tests do not fully pin fail-open behavior or plan decontamination.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-dyn-parse-sentinel-contract: Add an explicit parse-drafter-output.py rule: before diff_lines validation, drop any lines between plan sentinels that fall inside a misplaced scout span (or reject the whole output as fatal if stripping is too heavy); extend the test spec to assert plan.txt contains no LARCH_SCOUT_* markers and no archetypes JSON on the inside-plan-scout path
  - From Codex-dyn-parse-sentinel-contract: Add Codex and Claude drafter test cases for each malformed scout shape. Assert SCOUT_CANDIDATE_WRITTEN=false with SCOUT_FAIL_REASON, no candidate or canonical scout manifest, no LARCH_SCOUT sentinel or scout JSON in plan.txt, and strict failures still hold for duplicate or nested plan sentinels plus diff_lines outside the plan block


### FINDING_9:
- **Reviewer(s)**: Codex-Innovation
- **Severity**: important
- **Focus area**: architecture
- **Location**: scripts/parse-drafter-output.py:25-36; skills/design/scripts/design-step2b-drafter.sh:156-162
- **Concern**: [SCOPE-REDUCTION] Plan replaces the existing summary-before-plan drafter contract with plan→scout→summary. Scenario: The feature only needs one extra scout block outside the plan; reordering summary adds parser, prompt, docs, and test churn and can reject summary-first output if any prompt path remains unchanged
- **Proposed resolution**: Preserve the current summary-first contract and parser acceptance; add only optional LARCH_SCOUT_BEGIN/END extraction after LARCH_PLAN_END, without requiring global summary reordering.


### FINDING_10:
- **Reviewer(s)**: Codex-Pragmatic
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: scripts/parse-drafter-output.py:33-40
- **Concern**: [SCOPE-REDUCTION] Proposed required block order makes existing summary-before-plan drafter output invalid. Scenario: The current Step 2b prompt and launcher tests emit LARCH_SUMMARY_BEGIN before LARCH_PLAN_BEGIN. Making that shape fatal can fail delimiter extraction or force inline fallback for existing prompt overrides without being required to move scout inline.
- **Proposed resolution**: Keep legacy summary-before-plan valid when no scout block is present. Enforce only the new scout placement rules needed for the feature.




### FINDING_2: Pre-scout manifests are validated before normalization
- **Reviewer(s)**: Codex-Arch, Codex-Requirements
- **Severity**: important
- **Concern**: The planned `--pre-scouted-manifest` path validates external manifests before applying the existing cap, duplicate, reserved-slug, and filter normalization. Otherwise usable manifests can be rejected and degrade to static-only review.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Arch: Normalize with the existing scout filter rules first, then run scout_manifest_is_valid only as a post-normalization assertion before synthesize_dynamic_slots.
  - From Codex-Requirements: Normalize the supplied manifest with the existing scout reducer/filter rules before calling scout_manifest_is_valid or slot synthesis, then validate and synthesize from the normalized per-round manifest.


### FINDING_3: Stale design scout manifests can survive plan rewrites or inline fallback
- **Reviewer(s)**: Cursor-Innovation, Cursor-Pragmatic, Cursor-Requirements
- **Severity**: important
- **Concern**: After Step 2b, `plan.txt` can be rewritten or inline drafting can run without clearing the prior scout manifest. Step 3 may then launch dynamic reviewers for a rejected, superseded, or unrelated plan.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Innovation: Extend the postplan inline-retry branch (and matching test-plan-review-loop coverage) to delete scout-plan-manifest.json and scout temp files before orchestrator inline re-draft, mirroring the drafter-failure cleanup already specified for design-step2b-drafter.sh
  - From Cursor-Pragmatic: Add a shared rule: whenever plan.txt is rewritten after Step 2b and before the next Step 3 entry, remove scout-plan-manifest.json or write {"archetypes":[]}. Wire it into design-step2b-postplan inline retry, Gate B shared post-apply, and Gate A post-discussion plan rewrite paths. Document static-only fail-open for those rounds.
  - From Cursor-Requirements: Move scout sidecar and temp-file deletion to the unconditional pre-vendor block (same tier as the existing `rm -f` for `plan.txt`), and repeat removal in the drafter-failure inline-fallback branch


### FINDING_6: Drafter parser only rejects one-line residual scout JSON
- **Reviewer(s)**: Cursor-dyn-sentinel-decontam-fidelity, Codex-dyn-sentinel-decontam-fidelity
- **Severity**: important
- **Concern**: The parser’s post-sanitize fatal gate only detects single-line scout-shaped JSON. Malformed or straddling sentinel blocks can leave multi-line `archetypes` JSON in `plan.txt` while passing plan validation.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-dyn-sentinel-decontam-fidelity: After marker stripping, reject or delete any contiguous multi-line top-level object with an archetypes array inside the plan slice, not only one-line matches.
  - From Codex-dyn-sentinel-decontam-fidelity: Specify that after sentinel stripping the parser must reject any standalone JSON object in the sanitized plan body whose top-level has an archetypes array, including multi-line JSON, and add one proportional drafter harness case for unmatched or straddling in-plan scout JSON


### FINDING_9:
- **Reviewer(s)**: Codex-Arch
- **Severity**: important
- **Focus area**: architecture
- **Location**: scripts/parse-drafter-output.py:1-49
- **Concern**: [SCOPE-REDUCTION] The plan adds tolerant decontamination for duplicate, reversed, nested, pre-plan, in-summary, and in-plan scout sentinels instead of only extracting one valid post-plan scout block.. Scenario: A drafter that accidentally wraps real plan lines in misplaced scout sentinels could have those lines removed while still producing a diff_lines-valid plan. The extra parser and test matrix is not required to run scout once.
- **Proposed resolution**: Keep parse-drafter-output.py to the minimum contract: extract zero or one LARCH_SCOUT block only after LARCH_PLAN_END, ignore malformed scout after the plan, and reject any scout sentinel found inside the plan or summary instead of sanitizing spans.


### FINDING_10:
- **Reviewer(s)**: Codex-Innovation
- **Severity**: important
- **Focus area**: code-quality
- **Location**: scripts/parse-drafter-output.py:27-48
- **Concern**: [SCOPE-REDUCTION] Plan adds scout-sentinel decontamination and scout-shaped JSON scrubbing inside the plan parser. Scenario: Minimum-change feature only needs an optional scout block after LARCH_PLAN_END; accepting and rewriting malformed plan envelopes creates a new parser recovery path and can hide drafter format bugs while changing the extracted plan body
- **Proposed resolution**: Keep plan parsing strict; parse at most one optional LARCH_SCOUT block only after LARCH_PLAN_END; if scout markers or scout JSON appear before or inside the plan or summary block, ignore the scout candidate or fail the drafter output under the existing strict plan rules rather than sanitizing plan.txt


### FINDING_11:
- **Reviewer(s)**: Codex-Pragmatic
- **Severity**: important
- **Focus area**: correctness
- **Location**: scripts/parse-drafter-output.py:37-49; plan lines 68-73
- **Concern**: [SCOPE-REDUCTION] Proposed scout decontamination rewrites plan bodies and rejects legitimate scout JSON examples. Scenario: A valid plan can include a code fence showing {"archetypes":[]} or an accidental in-plan scout sentinel span; the proposed parser can reject that valid plan or delete real plan lines while still emitting plan.txt with diff_lines
- **Proposed resolution**: Accept scout only from one balanced block after LARCH_PLAN_END; remove in-plan scout span removal and scout-shaped JSON scanning; treat whole-line scout sentinels inside the plan as delimiter errors instead of repairing the plan


### FINDING_12:
- **Reviewer(s)**: Codex-Requirements
- **Severity**: important
- **Focus area**: correctness
- **Location**: scripts/parse-drafter-output.py (plan.txt:68-73)
- **Concern**: [SCOPE-REDUCTION] Parser decontamination silently rewrites malformed plan envelopes. Scenario: The feature only needs an optional scout block after LARCH_PLAN_END; accepting scout sentinels inside LARCH_PLAN_BEGIN/END by deleting spans weakens the existing strict plan extraction contract and can silently drop plan-body content from the artifact under review.
- **Proposed resolution**: Remove in-plan scout-span sanitization; require scout sentinels only after LARCH_PLAN_END, and treat any scout sentinel or scout-shaped JSON inside the plan envelope as a fatal drafter parse error while leaving out-of-plan malformed scout output fail-open.


