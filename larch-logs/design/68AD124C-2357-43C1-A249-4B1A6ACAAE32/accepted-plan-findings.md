### FINDING_1: cancelled-assessor-worse is rejected by render-final-summary
- **Reviewer(s)**: Cursor-Arch, Cursor-Innovation, Cursor-Requirements, Codex-Arch, Cursor-Edge, Codex-Edge, Codex-Innovation, Cursor-Pragmatic, Codex-Pragmatic, Codex-Requirements, Cursor-dyn-seam-integrity, Codex-dyn-seam-integrity
- **Severity**: important
- **Concern**: The Stop-after-WORSE path introduces `SUMMARY_OUTCOME=cancelled-assessor-worse`, but `render-final-summary.sh` enforces a closed outcome enum and will exit 2 instead of rendering a clean cancellation summary.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch, Cursor-Innovation, Cursor-Requirements: Add cancelled-assessor-worse to the case allowlist; extend test-render-final-summary.sh ten-outcome matrix; update render-final-summary.md
  - From Codex-Arch: Add cancelled-assessor-worse to render-final-summary.sh and its tests; do not rely only on SKILL.md prose enumeration
  - From Cursor-Edge: Add cancelled-assessor-worse to render-final-summary.sh case allowlist and test-render-final-summary.sh; remove no-script-change claim
  - From Codex-Edge: Add cancelled-assessor-worse to render-final-summary.sh's outcome enumeration, update render-final-summary.md, and extend test-render-final-summary.sh's outcome matrix.
  - From Codex-Innovation: Add cancelled-assessor-worse to render-final-summary.sh outcome enum and add a harness assertion for that outcome
  - From Cursor-Pragmatic: Add cancelled-assessor-worse to the case allow-list; update render-final-summary.md and test-render-final-summary.sh matrix
  - From Cursor-Pragmatic: Add cancelled-assessor-worse to the for-loop and a dedicated title/outcome assertion
  - From Codex-Pragmatic: Update render-final-summary.sh to include cancelled-assessor-worse, and add a focused test for that outcome
  - From Codex-Requirements: Update render-final-summary.sh, render-final-summary.md, and test-render-final-summary.sh outcome matrix to accept and verify cancelled-assessor-worse; keep the SKILL.md enumeration change
  - From Cursor-dyn-seam-integrity: Add `cancelled-assessor-worse` to the `case "$OUTCOME" in` allow-list in `render-final-summary.sh`, update `skills/design/scripts/render-final-summary.md` callers list, extend `skills/design/scripts/test-render-final-summary.sh` matrix (lines 381-410), and remove the erroneous “any token / no script change” note at plan lines 154-158
  - From Codex-dyn-seam-integrity: Update render-final-summary.sh outcome enumeration and rendered title/copy handling for cancelled-assessor-worse, and keep the SKILL.md prose enumeration in sync


### FINDING_2: Round cursor misses Gate B/Gate C discussion re-entry
- **Reviewer(s)**: Codex-Arch, Codex-Edge, Codex-Innovation, Codex-Pragmatic, Codex-Requirements
- **Severity**: important
- **Concern**: The plan advances the round cursor only for Gate C(c), but Gate B(c) and Gate C(b) can also return through Gate A to Step 3. Those re-review paths can reuse stale round artifacts, skip round >= 2 assessment, or collide with write-once snapshots.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Arch: Centralize round advancement for every post-plan re-entry to Step 3, or explicitly increment the cursor on Gate B(c) and Gate C(b) Gate A exits as well as Gate C(c)
  - From Codex-Edge: Increment or derive the round cursor for every post-plan Step 3 re-entry after a completed review, including Gate A Ready from Gate B/C re-entry; add tests for Gate B(c) and Gate C(b) discussion re-review paths.
  - From Codex-Innovation: Centralize round advancement for every post-plan Step 3 re-entry, or have Step 3 detect prior review artifacts and advance the cursor before launching review
  - From Codex-Pragmatic: Increment the HARD round cursor on every post-plan Ready-for-review path that re-enters Step 3, not just Gate C(c), or explicitly centralize round advancement in the Step 3 re-entry prelude
  - From Codex-Requirements: Define cursor behavior for every post-plan Gate A -> Step 3 re-entry, or explicitly exclude those paths and adjust the requirement; add structural/manual tests for Gate B(c) and Gate C(b) re-review paths


### FINDING_3: Tally semantics contradict TIE edge cases
- **Reviewer(s)**: Codex-Arch, Codex-Edge, Codex-Innovation, Cursor-dyn-tally-math, Codex-dyn-tally-math
- **Severity**: important
- **Concern**: The proposed WORSE-majority rule is internally inconsistent when TIE votes are present. A literal `worse_count > better_count` rule can classify one WORSE plus two TIE votes as WORSE, while multiple edge cases require that outcome to be NOT_WORSE; degraded two-assessor behavior is also underdocumented.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Arch: Define WORSE as a strict majority of successful assessors: 3 successful requires worse_count >= 2, 2 successful requires worse_count == 2, 1 successful requires worse_count == 1; update assessor.md and tests to match
  - From Codex-Edge: Define the 3-success case as worse_count >= 2, or explicitly require worse_count > better_count and worse_count > tie_count; pin 1W/0B/2T in test-tally-plan-assessor.sh.
  - From Codex-Innovation: Choose one rule explicitly; if ties are neutral, require worse_count >= 2 for three successful assessors and pin 1W-0B-2T in test-tally-plan-assessor.sh
  - From Cursor-dyn-tally-math: Replace the successful==3 clause with strict majority among successful assessors, e.g. worse_count*2 > successful (TIE counts toward successful but not toward worse_count/better_count); pin 0-2-1 expecting NOT_WORSE in test-tally-plan-assessor.sh
  - From Cursor-dyn-tally-math: Unify normative spec: either document that 3-successful requires worse_count>=2 (true majority) or drop/revise the 0-2-1 NOT_WORSE expectation; reflect the chosen rule identically in tally-plan-assessor.sh, tally-plan-assessor.md, and assessor.md worked examples
  - From Cursor-dyn-tally-math: Resolve rule first, then align test-tally-plan-assessor.sh cases: if 0-2-1 stays NOT_WORSE, tests must assert worse_count*2>successful (or equivalent), not bare worse_count>better_count
  - From Cursor-dyn-tally-math: Document in assessor.md that TIE is included in EFFECTIVE_ASSESSORS/successful but excluded from worse/better numerators, and that WORSE-majority requires a strict majority of successful assessors (not merely WORSE>BETTER among non-TIE votes)
  - From Codex-dyn-tally-math: Update the proposed skills/design/scripts/tally-plan-assessor.sh contract and tests to choose one rule: either keep WORSE > BETTER and change 0-2-1 to WORSE, or change the rule to require at least two WORSE votes in a 3-assessor panel when TIEs are present.
  - From Codex-dyn-tally-math: Either document the degraded-panel rule as overriding strict WORSE > BETTER for successful==2, including explicit WORSE+TIE => NOT_WORSE examples, or revise the rule to apply WORSE > BETTER consistently across degraded panels.


### FINDING_4: Assessor timing kinds are not wired through waterfall
- **Reviewer(s)**: Codex-Arch, Cursor-Pragmatic
- **Severity**: important
- **Concern**: The plan adds base assessor timing kinds, but `dispatch-with-waterfall.sh` synthesizes phase-qualified task kinds and has no timing-kind override. Assessor dispatch can either fail on an unknown option or emit unallowlisted timing kinds.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Arch: Extend dispatch-with-waterfall to accept per-slot timing_task_kind or add the actual synthesized assessor task kinds to the allowlist and structural tests
  - From Cursor-Pragmatic: Append claude/codex/cursor-plan-assessor entries to lib-timing-kinds.md in the same PR


### FINDING_5: Step 3.6 is not wired into HARD Gate B routing
- **Reviewer(s)**: Cursor-Edge, Cursor-Pragmatic, Cursor-Requirements
- **Severity**: important
- **Concern**: Multiple Gate B, Gate C, anti-halt, and structure-test anchors still route directly from Step 3.5 or settled Gate B paths to Step 3b. HARD workflows can therefore skip the new assessor step entirely, including zero-findings and Apply-all paths.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Edge: Replace proceed-to-3b with proceed-to-3.6 (HARD-only) then 3b on all Gate B terminal branches and SKILL.md line 786
  - From Cursor-Edge, Cursor-Pragmatic: Update sub-step chain to 3→3.5→3.6→3b and document Gate C(c) re-entry through 3.6
  - From Cursor-Pragmatic: Amend invariant with HARD exception; replace Step 3b arrows with Step 3.6 (HARD) then 3b; document Gate C(c) cursor increment
  - From Cursor-Pragmatic: Change settle prose to proceed to Step 3.6 when workflow_path=HARD else Step 3b
  - From Cursor-Pragmatic: Extend Check 6 awk for 3.5 < 3.6 < 3b; grep Step 3.6 between Gate B and 3b in SKILL.md
  - From Cursor-Requirements: Update every Gate-B-settled successor in SKILL.md and approval-gates.md (incl. zero-findings at approval-gates.md:104 and Gate C flow at :114) to Step 3.6 on HARD; extend anti-halt list to 3→3.5→3.6→3b; pin 3.5→3.6→3b ordering in test-design-structure.sh Check 6
  - From Cursor-Requirements: Extend Check 6 awk pin to require <!-- step:3.5 before <!-- step:3.6 before <!-- step:3b; grep for assess-plan-round.sh and snapshot-plan-round.sh write-after in Step 3.6 window


### FINDING_6: Dispatch failure can still tally stale partial assessor outputs
- **Reviewer(s)**: Cursor-Edge
- **Severity**: important
- **Concern**: The planned `assess-plan-round.sh` flow can run `tally-plan-assessor.sh` after assessor dispatch fails, allowing stale or partial files to produce a false WORSE majority.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Edge: On dispatch non-zero skip tally; emit degraded-default-open KV only; do not write verdict from partial outputs


### FINDING_7: Prompt-side SUMMARY_OUTCOME enum omits cancelled-assessor-worse
- **Reviewer(s)**: Cursor-Edge, Cursor-Pragmatic
- **Severity**: important
- **Concern**: The Final summary orchestrator contract in `SKILL.md` omits `cancelled-assessor-worse`, so prompt-side logic may treat the Stop outcome as invalid even if the renderer is updated.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Edge: Add cancelled-assessor-worse to line-266 SUMMARY_OUTCOME enumeration
  - From Cursor-Pragmatic: Add cancelled-assessor-worse to the orchestrator enumeration beside cancelled-plan-size-hard and cancelled-decompose


### FINDING_8: Tuple notation and edge-case labels are inconsistent
- **Reviewer(s)**: Cursor-Edge, Cursor-dyn-tally-math
- **Severity**: important
- **Concern**: The plan and issue text use conflicting BETTER/TIE/WORSE tuple positions, making all-TIE and all-WORSE edge cases ambiguous and risking wrong tests or documentation.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Edge: Fix edge-case bullet to three-TIE → NOT_WORSE; pin in test-tally-plan-assessor.sh
  - From Cursor-dyn-tally-math: Standardize on one canonical BETTER-TIE-WORSE label everywhere (assessor.md, edge cases, tests); add explicit 0-3-0 all-TIE to plan Edge cases alongside all-tie harness case


### FINDING_9: Assessor feature-file path is underspecified
- **Reviewer(s)**: Cursor-Edge, Codex-Pragmatic, Codex-Requirements
- **Severity**: important
- **Concern**: `assess-plan-round.sh` has no clear `--feature-file` argument or default, while `dispatch-plan-assessors.sh` requires one and the assessor prompt needs the refined problem statement. This can cause validation failure, missing feature context, or inconsistent fallback behavior.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Edge: Pass --feature-file "${IMPLEMENT_TMPDIR:-$DESIGN_TMPDIR}/feature-description.txt" through assess-plan-round and dispatch-plan-assessors
  - From Codex-Pragmatic: Add --feature-file to assess-plan-round.sh and the SKILL.md call, or mirror plan-review-loop.sh by defaulting to ${IMPLEMENT_TMPDIR:-$DESIGN_TMPDIR}/feature-description.txt and failing open with a Warning when missing
  - From Codex-Requirements: Add --feature-file to assess-plan-round.sh and the SKILL.md Step 3.6 call, or define and test the same default used by plan-review-loop.sh: ${IMPLEMENT_TMPDIR:-$DESIGN_TMPDIR}/feature-description.txt


### FINDING_10: Step 3.6 lacks a mechanical Bash/KV contract
- **Reviewer(s)**: Cursor-Edge, Cursor-Requirements
- **Severity**: important
- **Concern**: Step 3.6 is specified mostly in prose and lacks the fenced Bash invocation, environment sourcing, timing mark, KV parsing, write-after, verdict-file read, and Continue/Stop branch wiring used by neighboring steps.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Edge: Add Step 3.6 fenced bash with read-cursor write-after round N assess-plan-round KV loop and Continue/Stop branch
  - From Cursor-Requirements: Implementers improvise invocation; ASSESSOR_VERDICT / EFFECTIVE_ASSESSORS parsing drifts; WORSE Continue/Stop branch unreliable Add Step 3.6 fenced Bash block (source env, optional timing mark, write-after, assess-plan-round.sh call, KV parse, verdict-file cat, 0/3 banner from edge-case :204) matching other step contracts


### FINDING_11: Snapshot write-after and cursor ordering can desync
- **Reviewer(s)**: Codex-Innovation, Cursor-dyn-schema-drift
- **Severity**: important
- **Concern**: The plan relies on a write-last snapshot invariant that the proposed flow does not enforce. If `plan-after-round-N` is missing or stale after write-after, later assessment can skip, compare the wrong current text, or silently fail open.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Innovation: Either verify/write the current round snapshot before Gate C increments, or persist an explicit incomplete-round marker and block/repair the next cursor advance rather than silently fail-opening
  - From Cursor-dyn-schema-drift: Add explicit check after write-after that plan-after-round-<N>.txt exists (or compare plan.txt to it) before dispatch; exit missing-snapshot with Warnings when mismatch/absent


### FINDING_12: Snapshot temp file naming is unsafe
- **Reviewer(s)**: Codex-Pragmatic
- **Severity**: latent
- **Concern**: Predictable `.tmp.<pid>` copy targets in `snapshot-plan-round.sh` can collide with preserved temp paths or symlinks inside `DESIGN_TMPDIR`, weakening file-containment guarantees.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Pragmatic: Use mktemp in DESIGN_TMPDIR for temp files, refuse symlink temp/final paths, and clean up temp files with a trap before mv


### FINDING_13: Step 3 cursor read lacks a mechanical parse contract
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: important
- **Concern**: Step 3 says to replace `--round-num 1` with `read-cursor`, but does not show a Bash KV parse loop or assignment into the argument passed to `plan-review-loop.sh`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Requirements: Step 3 passes empty/wrong --round-num; round 2+ review mislabels artifacts and assessor compares wrong N Add fenced Bash in Step 3 (and Step 3.6) showing snapshot-plan-round.sh read-cursor/write-cursor calls plus KV parse into _round_num for --round-num; mirror plan-review-loop.sh stdout parsing style


### FINDING_14: 0/3 effective-assessor warning is omitted
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: important
- **Concern**: The edge cases require an operator-visible warning when all assessors fail to produce effective verdicts, but the updated Step 3.6 section omits that banner.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Requirements: Add explicit Step 3.6 prose: when ASSESSOR_VERDICT=not-worse and EFFECTIVE_ASSESSORS=0 print **⚠ 3.6: 0/3 effective assessors; proceeding without quality gate**; cover in test-assess-plan-round.sh


### FINDING_15: WORSE warning omits assessor qualifications
- **Reviewer(s)**: Cursor-Requirements, Codex-Requirements
- **Severity**: important
- **Concern**: The feature requires the WORSE warning to include assessor qualifications, but the proposed verdict/warning path surfaces only synthesized reasoning and drops the parsed `QUALIFICATIONS` content.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Requirements: Include QUALIFICATIONS excerpts in tally WORSE synthesis or print per-assessor QUALIFICATIONS under the WORSE header before AskUserQuestion
  - From Codex-Requirements: Keep the compact verdict file if required, but make Step 3.6 print the WORSE assessors' QUALIFICATIONS alongside the verdict, and add a test that a WORSE path surfaces qualifications


### FINDING_16: Plan references a nonexistent waterfall helper and misstates cursor ownership
- **Reviewer(s)**: Cursor-Requirements, Cursor-dyn-schema-drift
- **Severity**: nit
- **Concern**: The failure-mode text cites `lib-waterfall-slot.sh`, which does not exist, and says Step 3.6 increments the cursor even though the planned increment occurs in Gate C(c) before Step 3.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Requirements: Say manifest follows dispatch-plan-voters.sh inline ndjson pattern; fix failure-mode text to Gate C(c) increment-before-Step-3 vs Step 3.6 write-after ordering
  - From Cursor-dyn-schema-drift: Replace failure-mode bullet with Gate C(c) pre-Step-3 increment vs Step 3.6 write-after ordering; drop Step 3.6 cursor-increment language


### FINDING_17: Assessor artifact schema conflicts between flat and plan-review paths
- **Reviewer(s)**: Cursor-dyn-schema-drift, Codex-dyn-schema-drift
- **Severity**: important
- **Concern**: The plan, issue/feature description, reviewer description, and design-log publisher disagree on whether round snapshots, cursor, prompts, outputs, verdicts, and env files live as flat `$DESIGN_TMPDIR` files or under `plan-review/round-<N>/`. Producers, consumers, and log publishing can miss or reject each other’s artifacts.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-dyn-schema-drift: Revise the plan Acceptance to require refreshing the issue larch:plan block (and feature-description excerpt) on emit so nested paths are removed; add a structural pin or assessor.md note that names the flat paths as the only contract
  - From Cursor-dyn-schema-drift: Keep DECISION_1 flat top-level writers; document in assessor.md and design-log-publish.md that assessor/snapshot files must not be placed under plan-review/round-<N>/ except the existing TSV
  - From Codex-dyn-schema-drift: Choose one schema and update all contract surfaces. Prefer keeping round state under plan-review/round-<N>/ plus plan-review/round-cursor.txt, then extend design-log-publish.sh and design-log-publish.md allowlists beyond findings-classification.tsv so those artifacts publish instead of failing closed.
  - From Codex-dyn-schema-drift: Add explicit publish support for the new per-round assessor basenames under plan-review/round-<N>/, or revise the issue/reviewer_description-derived contract and all references to state that assessor artifacts are intentionally top-level flattened.


### FINDING_18: append-tool-failure contract is underspecified for missing snapshots
- **Reviewer(s)**: Codex-dyn-seam-integrity
- **Severity**: latent
- **Concern**: The plan says `assess-plan-round.sh` should append missing-snapshot warnings through `append-tool-failure.sh`, but does not specify the required output file and argument contract. A fail-open path can become a hard failure.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-dyn-seam-integrity: Add an explicit assess-plan-round.sh step to write the missing-snapshot diagnostic to a concrete log file, then call append-tool-failure.sh with --log, --site, --tool, --exit-code, --category Warnings, and --output-file, or switch the plan to append-execution-issue.sh with an entry file### OOS_1:
- **Description**: Gate C(c) re-run prose omits HARD-only cursor increment called out only for SKILL.md. Scenario: SIMPLE Gate C re-entry docs may imply cursor bump without HARD gate
- **Reviewer**: Cursor-Edge
- **Severity**: nit
- **Focus area**: architecture
- **Location**: skills/design/references/approval-gates.md:128
- **Phase**: design


