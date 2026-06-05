### FINDING_1:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: important
- **Focus area**: architecture
- **Location**: scripts/test-design-structure.sh:708-710
- **Concern**: Proposed SIMPLE sentinel pin is slice-wide, not fence-scoped. Scenario: The plan says the new assertion must fail when SIMPLE sentinels are re-split into a dedicated bash turn, but co-occurring `read-design-classification.sh` and `NO_SKETCHES_CLASSIFIED_SIMPLE` anywhere in the `<!-- step:2a —` → `### 2a.5` slice still passes if classification stays in the entry fence and sentinel writes move back to a separate fence under `### SIMPLE branch` — restoring the extra orchestrator turn without CI failure
- **Proposed resolution**: Pin the first ` ```bash ` fence after `<!-- step:2a —` (extract fence body via awk, mirroring `assert_step3b_entry_guard_threads_repo`) and require both tokens inside that fence; add a negative check that no other ` ```bash ` block in the SIMPLE-branch subsection contains `NO_SKETCHES_CLASSIFIED_SIMPLE`

### FINDING_2:
- **Reviewer(s)**: Codex-Arch
- **Severity**: important
- **Focus area**: correctness
- **Location**: scripts/test-design-structure.sh:296
- **Concern**: Proposed SIMPLE co-location assertion scopes the whole Step 2a section instead of the entry fence. Scenario: If the entry fence reads design_classification but the sentinel writes move back to a later SIMPLE bash fence, both tokens still appear between step:2a and 2a.5, so CI passes while reintroducing the dedicated turn
- **Proposed resolution**: Slice only the first Step 2a bash fence or the range before the SIMPLE branch prose, and assert it contains read-design-classification.sh, the three sentinel writes, and both .completed markers

### FINDING_3:
- **Reviewer(s)**: Cursor-Edge
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/design/SKILL.md:1303-1341
- **Concern**: Step 3b early-exit prose still jumps straight to Step 4 while FINALIZE moves to the completion-boundary fence only. Scenario: Four paths (non-architectural skip, sanitizer reject, diagram generation failed, success) say "continue to Step 4" before the boundary; today Step 4 item 1 runs FINALIZE on that jump, but the plan removes that fence—an orchestrator that follows the early-exit lines can enter Step 4 without `rejected-findings.md` / finalize stubs (especially voting-skipped runs)
- **Proposed resolution**: In the same SKILL.md edit, retarget those lines (and the Step 3b blockquote at ~1340) to "run the Step 3b completion boundary below, then Step 4"; or move the FINALIZE+`step-3b` bash fence above the first "continue to Step 4" instruction

### FINDING_4:
- **Reviewer(s)**: Codex-Edge
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/design/SKILL.md:1341-1367
- **Concern**: Step 3b FINALIZE failure path is not specified to halt before Step 4. Scenario: If finalize-plan fails, the proposed fence only warns and skips .completed/step-3b; a normal bash if-branch can still exit 0, then Step 4 no longer has its own FINALIZE fallback and may read missing artifacts or proceed with unvalidated state
- **Proposed resolution**: In the nonzero branch, print the warning and exit nonzero before Step 4; write .completed/step-3b only after ACTION=FINALIZE returns 0

### FINDING_5:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/design/SKILL.md:1303-1341
- **Concern**: FINALIZE moves to the Step 3b completion boundary but multiple exit branches still say IMMEDIATELY continue to Step 4. Scenario: Non-architectural and several architectural exit paths can jump to the step:4 marker and skip line 1341; today Step 4 item 1 still runs FINALIZE there, but after the fold Step 4 reads rejected-findings.md without materialization and fails when voting was skipped
- **Proposed resolution**: Fold FINALIZE into the Step 3b entry timing fence (same turn savings, single convergence) OR reword every Step 3b exit at 1303/1334/1336/1338 to require the completion-boundary fence before entering Step 4; add a harness pin that non-architectural prose cannot say continue to Step 4 without referencing the boundary fence

### FINDING_6:
- **Reviewer(s)**: Codex-Innovation
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/design/SKILL.md:1340-1341
- **Concern**: Planned Step 3b FINALIZE fence captures non-zero under set +e but only says to print a warning and skip step-3b sentinel; it does not say to exit or block before Step 4. Scenario: When finalize-plan rejects missing diff-lines.txt or an invalid rejected-findings.md path, the captured fence can return success after printing the warning, so Step 4 may still read missing/invalid artifacts; the missing step-3b sentinel only helps a later resume, not the current run
- **Proposed resolution**: Add an explicit non-zero exit or mandatory repair-and-rerun stop in the proposed Step 3b boundary fence before entering Step 4; continue and write .completed/step-3b only when ACTION=FINALIZE exits 0

### FINDING_7:
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/design/SKILL.md:1303-1341
- **Concern**: Step 3b early exits still say continue to Step 4 before the proposed completion boundary fence. Scenario: Removing Step 4 item 1 FINALIZE while leaving IMMEDIATELY continue to Step 4 at 1303 1334 1336 1338 can skip the new FINALIZE plus step-3b fence so rejected-findings.md is never created when voting was skipped or on non-architectural skip paths
- **Proposed resolution**: Retarget each early exit to run the Step 3b completion boundary bash fence first then Step 4 or replace those lines with proceed to the Step 3b completion boundary below

### FINDING_8:
- **Reviewer(s)**: Codex-Pragmatic
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/design/SKILL.md:1340-1364
- **Concern**: Proposed Step 3b FINALIZE fence captures nonzero but does not require the Bash turn to fail or stop before Step 4. Scenario: finalize-plan.sh can fail for missing diff-lines.txt or an invalid artifact, then the warning printf succeeds, Step 4/5 continue, and the run can publish with failed final validation despite no step-3b sentinel
- **Proposed resolution**: Add an explicit nonzero exit in the FINALIZE failure branch before Step 4, and write .completed/step-3b only after FINALIZE exits 0

### FINDING_9:
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: important
- **Focus area**: correctness
- **Location**: scripts/test-design-structure.sh:1323-1357
- **Concern**: Plan keeps assert_step_completion_sentinels unchanged but moves `.completed/step-2a.5` writes to the Step 2a entry fence (before `### 2a.5`). Scenario: Check (21) greps each step’s region for `.completed/step-$step`; step 2a.5 is `### 2a.5` → `<!-- step:2b`, so a sentinel only in the entry fence fails `make lint` / structure harness despite meeting the issue’s fold goal
- **Proposed resolution**: In the `### 2a.5` SIMPLE skip prose (~`skills/design/SKILL.md:801`), add a cross-reference line containing the `.completed/step-2a.5` literal (and note entry-fence co-wrote `.completed/step-2a`), or narrow the plan to “keep assert as-is” by also updating that harness if relocating the write is intentional

### FINDING_10:
- **Reviewer(s)**: Codex-Requirements
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/design/SKILL.md:1341-1366
- **Concern**: Step 3b FINALIZE failure may be hidden by the planned set +e wrapper. Scenario: The feature requires FINALIZE validation failure to stay surfaced and abort before Step 5, but the plan only says to print the repair warning and skip step-3b sentinel on non-zero; if the failure branch ends with a successful printf, the Bash turn can exit 0 and continue into Step 4/Step 5 after invalid artifacts
- **Proposed resolution**: Add an explicit non-zero halt in the failure branch, e.g. restore set -e then exit "$_finalize_rc" after printing the repair message; keep .completed/step-3b only in the success branch

### FINDING_11:
- **Reviewer(s)**: Codex-Requirements
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: scripts/test-design-structure.sh:296
- **Concern**: Planned SIMPLE sentinel assertion is too broad to prove the standalone fence was removed. Scenario: The proposed slice from step 2a through 2a.5 would also include the old SIMPLE branch dedicated fence, so an implementation that keeps or reintroduces that standalone turn can still pass once read-design-classification.sh appears somewhere in the slice
- **Proposed resolution**: Scope the assertion to the first Step 2a bash fence, or assert the SIMPLE branch section has no bash fence while the entry fence contains the SIMPLE guard and all three sentinel writes

### FINDING_12:
- **Reviewer(s)**: Cursor-dyn-fence-invariants
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/design/SKILL.md:1341
- **Concern**: Step 3b boundary edit adds a FINALIZE bash fence but does not explicitly delete the existing prose-only success-boundary instruction that always writes `.completed/step-3b`. Scenario: If both remain, the orchestrator can still run the L1341 `mkdir` / `: > …/step-3b` prose after a failed FINALIZE in the new fence, marking Step 3b complete and causing resume to skip re-FINALIZE before Step 4
- **Proposed resolution**: In region edit 3, replace the L1341 prose boundary with the single bash fence only; state that no separate orchestrator prose may write `step-3b` after a non-zero FINALIZE exit

### FINDING_13:
- **Reviewer(s)**: Cursor-dyn-doc-reference-completeness
- **Severity**: important
- **Focus area**: architecture
- **Location**: skills/design/references/sketch-launch.md:25-35
- **Concern**: §SIMPLE Mode still normatively prescribes a standalone bash fence that writes NO_SKETCHES_CLASSIFIED_SIMPLE / contested-decisions / dialectic-resolutions immediately, while the plan only lists this file under a conditional consistency pass. Scenario: After SKILL.md moves SIMPLE sentinel writes to the Step 2a entry fence, sketch-launch.md remains a topology-listed authority (skills/shared/topology.tsv row design.sketch.simple_slots) and is MANDATORY-read at Step 2a.2 for HARD; any orchestrator that loads it on a SIMPLE path or a future step reorder will get a second write site and divergent pause/completion semantics versus the entry fence
- **Proposed resolution**: List sketch-launch.md as a required UPDATED file (not touch-only-if): replace the §SIMPLE Mode bash block with prose that sentinel + .completed/step-2a(.5) writes happen only in the Step 2a entry fence guarded by design_classification == SIMPLE; keep sentinel string values as reference only

### FINDING_14:
- **Reviewer(s)**: Codex-dyn-doc-reference-completeness
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/design/SKILL.md:1341,1357-1364
- **Concern**: Plan moves FINALIZE to Step 3b under set +e but only says to print a warning and skip step-3b sentinel on failure, not to stop before Step 4. Scenario: Existing Step 4 runs design-driver directly, so a FINALIZE failure surfaces as a failed Bash fence before rejected-findings handling; the proposed captured fence can mask the failure and continue into Step 4 with missing artifacts
- **Proposed resolution**: Add an explicit non-zero exit/return after the warning in the Step 3b FINALIZE failure branch, before Step 4, while still withholding .completed/step-3b for resume retry
