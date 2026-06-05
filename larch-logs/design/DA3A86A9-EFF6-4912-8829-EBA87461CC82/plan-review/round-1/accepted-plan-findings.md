### FINDING_1: SIMPLE co-location test is slice-wide instead of entry-fence scoped
- **Reviewer(s)**: Cursor-Arch, Codex-Arch, Codex-Requirements
- **Severity**: important
- **Concern**: The planned SIMPLE sentinel assertion can pass even if sentinel writes remain or move back into a later standalone SIMPLE bash fence, because it searches the broader Step 2a slice rather than proving the first Step 2a entry fence contains both classification and sentinel/completion writes.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Pin the first ` ```bash ` fence after `<!-- step:2a —` (extract fence body via awk, mirroring `assert_step3b_entry_guard_threads_repo`) and require both tokens inside that fence; add a negative check that no other ` ```bash ` block in the SIMPLE-branch subsection contains `NO_SKETCHES_CLASSIFIED_SIMPLE`
  - From Codex-Arch: Slice only the first Step 2a bash fence or the range before the SIMPLE branch prose, and assert it contains read-design-classification.sh, the three sentinel writes, and both .completed markers
  - From Codex-Requirements: Scope the assertion to the first Step 2a bash fence, or assert the SIMPLE branch section has no bash fence while the entry fence contains the SIMPLE guard and all three sentinel writes


### FINDING_2: Step 3b early-exit prose can skip the new completion boundary
- **Reviewer(s)**: Cursor-Edge, Cursor-Innovation, Cursor-Pragmatic
- **Severity**: important
- **Concern**: Multiple Step 3b exit paths still instruct the orchestrator to continue directly to Step 4 before the proposed completion-boundary FINALIZE fence, so removing the Step 4 FINALIZE fallback can leave required artifacts such as `rejected-findings.md` or finalize stubs unmaterialized.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Edge: In the same SKILL.md edit, retarget those lines (and the Step 3b blockquote at ~1340) to "run the Step 3b completion boundary below, then Step 4"; or move the FINALIZE+`step-3b` bash fence above the first "continue to Step 4" instruction
  - From Cursor-Innovation: Fold FINALIZE into the Step 3b entry timing fence (same turn savings, single convergence) OR reword every Step 3b exit at 1303/1334/1336/1338 to require the completion-boundary fence before entering Step 4; add a harness pin that non-architectural prose cannot say continue to Step 4 without referencing the boundary fence
  - From Cursor-Pragmatic: Retarget each early exit to run the Step 3b completion boundary bash fence first then Step 4 or replace those lines with proceed to the Step 3b completion boundary below


### FINDING_3: Step 3b FINALIZE failure can be masked and still proceed to Step 4
- **Reviewer(s)**: Codex-Edge, Codex-Innovation, Codex-Pragmatic, Codex-Requirements, Codex-dyn-doc-reference-completeness
- **Severity**: important
- **Concern**: The proposed Step 3b FINALIZE fence captures nonzero status under `set +e` but does not require the bash turn to fail or halt before Step 4, so FINALIZE validation errors can be reduced to warnings while later steps continue with missing or invalid artifacts.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Edge: In the nonzero branch, print the warning and exit nonzero before Step 4; write .completed/step-3b only after ACTION=FINALIZE returns 0
  - From Codex-Innovation: Add an explicit non-zero exit or mandatory repair-and-rerun stop in the proposed Step 3b boundary fence before entering Step 4; continue and write .completed/step-3b only when ACTION=FINALIZE exits 0
  - From Codex-Pragmatic: Add an explicit nonzero exit in the FINALIZE failure branch before Step 4, and write .completed/step-3b only after FINALIZE exits 0
  - From Codex-Requirements: Add an explicit non-zero halt in the failure branch, e.g. restore set -e then exit "$_finalize_rc" after printing the repair message; keep .completed/step-3b only in the success branch
  - From Codex-dyn-doc-reference-completeness: Add an explicit non-zero exit/return after the warning in the Step 3b FINALIZE failure branch, before Step 4, while still withholding .completed/step-3b for resume retry


### FINDING_4: Step 2a.5 completion sentinel relocation can break existing structure harness
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: important
- **Concern**: Keeping `assert_step_completion_sentinels` unchanged while moving `.completed/step-2a.5` writes before the `### 2a.5` region can make the structure harness fail, because it greps each step’s own region for its completion sentinel.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Requirements: In the `### 2a.5` SIMPLE skip prose (~`skills/design/SKILL.md:801`), add a cross-reference line containing the `.completed/step-2a.5` literal (and note entry-fence co-wrote `.completed/step-2a`), or narrow the plan to “keep assert as-is” by also updating that harness if relocating the write is intentional


### FINDING_5: Existing Step 3b prose boundary may still mark completion after failed FINALIZE
- **Reviewer(s)**: Cursor-dyn-fence-invariants
- **Severity**: important
- **Concern**: If the new FINALIZE bash fence is added without replacing the existing prose-only success-boundary instruction, the orchestrator may still write `.completed/step-3b` after a failed FINALIZE, causing resume to skip re-finalization.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-dyn-fence-invariants: In region edit 3, replace the L1341 prose boundary with the single bash fence only; state that no separate orchestrator prose may write `step-3b` after a non-zero FINALIZE exit


### FINDING_6: sketch-launch SIMPLE Mode would remain a second normative write site
- **Reviewer(s)**: Cursor-dyn-doc-reference-completeness
- **Severity**: important
- **Concern**: `skills/design/references/sketch-launch.md` still normatively describes a standalone SIMPLE bash fence writing SIMPLE sentinels, so leaving it as only conditionally updated can preserve divergent instructions and reintroduce a second write site.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-dyn-doc-reference-completeness: List sketch-launch.md as a required UPDATED file (not touch-only-if): replace the §SIMPLE Mode bash block with prose that sentinel + .completed/step-2a(.5) writes happen only in the Step 2a entry fence guarded by design_classification == SIMPLE; keep sentinel string values as reference only

