### FINDING_1:
- **Reviewer(s)**: Cursor-Arch, Cursor-dyn-sentinel-flow
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/design/SKILL.md:1340-1341
- **Concern**: Step 3b anti-halt blockquote and prose step-3b boundary omitted from explicit retarget list. Scenario: Item 3 retargets ~1303/1334/1336/1338 and adds a completion-boundary fence but leaves `> **Continue to Step 4 IMMEDIATELY.**` and the prose-only `step-3b` write; orchestrator can skip FINALIZE and Step 4 reads missing `rejected-findings.md`
- **Proposed resolution**: Extend item 3: replace line 1340 to require the Step 3b completion boundary (not direct Step 4); delete the prose `step-3b` write at 1341 (fence owns it after FINALIZE succeeds); broaden the harness pin to match `Continue to Step 4` as well as `continue to Step 4` / `IMMEDIATELY continue to Step 4`

### FINDING_2:
- **Reviewer(s)**: Codex-Arch
- **Severity**: latent
- **Focus area**: risk-integration
- **Location**: skills/design/SKILL.md:1341-1367
- **Concern**: Step 4 removal assumes every Step 4 resume has passed the new Step 3b FINALIZE boundary. Scenario: A pre-PR paused run can already have .completed/step-3b but no .completed/finalize; after this PR pause-load resumes at Step 4, Step 4 no longer runs FINALIZE, and rejected-findings.md may be missing when voting was skipped
- **Proposed resolution**: Fold a compatibility FINALIZE check into the existing Step 4 entry fence when .completed/finalize is absent, or route step-4 resumes without finalize back through the Step 3b boundary; add a pause-resume fixture for the old step-3b-only state

### FINDING_3:
- **Reviewer(s)**: Codex-Edge
- **Severity**: important
- **Focus area**: correctness
- **Location**: scripts/design-pause-load.sh:253-259
- **Concern**: Step-4 resume compatibility is missing after FINALIZE moves to Step 3b. Scenario: A design paused before this PR after .completed/step-3b but before old Step 4 ACTION=FINALIZE resumes at Step 4; the new Step 4 assumes rejected-findings.md and sibling artifacts already exist, so legacy paused runs can fail or proceed with missing finalize artifacts
- **Proposed resolution**: Add a minimal compatibility path, e.g. when restored STEP=4 and .completed/finalize is absent, route back through Step 3b completion boundary or run an idempotent finalize fallback in the Step 4 entry fence; cover this in test-design-pause-resume.sh

### FINDING_4:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: skills/design/SKILL.md:1340
- **Concern**: Step 3b blockquote still says "Continue to Step 4 IMMEDIATELY" but is omitted from the retarget list and the proposed harness pin is case/order-sensitive. Scenario: After Step 4 item 1 is removed, an orchestrator can follow the blockquote and skip the new completion-boundary fence, so FINALIZE never runs and Step 4 reads missing rejected-findings.md on skip paths
- **Proposed resolution**: Retarget line 1340 to require the Step 3b completion boundary first; extend the harness pin to catch this variant (e.g. case-insensitive match or explicit "Continue to Step 4 IMMEDIATELY" literal)

### FINDING_5:
- **Reviewer(s)**: Codex-Innovation
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: scripts/test-implement-anti-halt.sh:64
- **Concern**: Plan retargets Step 3b continuation prose but does not account for the existing anti-halt harness literal. Scenario: Removing or rewriting the current "Continue to Step 4 IMMEDIATELY" banner makes make lint fail even if the new completion boundary is correct
- **Proposed resolution**: Preserve that literal in the new boundary-qualified Step 3b reminder, or update this harness needle in the same PR to the new completion-boundary wording

### FINDING_6:
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: skills/design/SKILL.md:1168
- **Concern**: Proposed Step 3b harness pin only guards phrases "continue to Step 4" / "IMMEDIATELY continue to Step 4" inside the Step 3b region; cap-reached Gate-B-bypass at line 1168 sits in Step 3 and says "Step 3b, then Step 4" / "Step 3b → Step 4" without "completion boundary". Scenario: After Step 4 item 1 is removed, an implementer can pass CI while leaving line 1168 unchanged; cap-reached / skipped-cap-reached runs are a primary no-voting path and may skip the new FINALIZE fence, so Step 4 reads missing rejected-findings.md artifacts
- **Proposed resolution**: Extend scripts/test-design-structure.sh to scan the Step 3 slice (e.g. <!-- step:3 — through <!-- step:3.5) for Step 3b→Step 4 routing that lacks a completion-boundary reference, or add an explicit pin for line 1168; keep the planned SKILL.md retarget of Gate-B-bypass macro prose in item 3

### FINDING_7:
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: important
- **Focus area**: correctness
- **Location**: plan.txt:90-92; scripts/test-design-structure.sh (new assertion)
- **Concern**: Proposed Step 3b bypass pin only requires a completion-boundary token somewhere in the Step 3b region, not on each bypass line. Scenario: A stale line such as skills/design/SKILL.md:1303 or :1338 can still say "continue to Step 4" while another line mentions "completion boundary"; CI passes but that branch skips the FINALIZE fence and Step 4 reads artifacts FINALIZE would have created
- **Proposed resolution**: Make the harness line-scoped: fail any Step 3b-region line matching continue-to-Step-4 (case-insensitive) unless that same line routes through the Step 3b completion boundary

### FINDING_8:
- **Reviewer(s)**: Codex-Requirements
- **Severity**: important
- **Focus area**: correctness
- **Location**: scripts/test-design-structure.sh:705-709
- **Concern**: Planned Step 3b bypass assertion is too weak if it only checks for a completion-boundary token anywhere in the region. Scenario: A stale line like "Then IMMEDIATELY continue to Step 4" could remain while another Step 3b line mentions "completion boundary", so the harness passes even though that branch can bypass FINALIZE
- **Proposed resolution**: Make the assertion line-scoped: fail any Step 3b line containing "continue to Step 4" or "IMMEDIATELY continue to Step 4" unless that same line directs the run to the Step 3b completion boundary first

### FINDING_9:
- **Reviewer(s)**: Codex-dyn-sentinel-flow
- **Severity**: important
- **Focus area**: correctness
- **Location**: <TMPDIR>/plan.txt:55-60; skills/design/SKILL.md:1334-1340; scripts/test-design-structure.sh:1303-1320
- **Concern**: Plan omits the current generic Step 3b “Continue to Step 4 IMMEDIATELY” prose path from the explicit retarget list, and the proposed harness check is region-token scoped enough to miss it.. Scenario: If skills/design/SKILL.md:1340 remains as a direct Step 4 instruction, an orchestrator can skip the new FINALIZE completion-boundary fence; Step 4 then reads artifacts that FINALIZE would have created.
- **Proposed resolution**: Add the skills/design/SKILL.md:1340 continuation line to the retarget list and make the structure test fail any Step 3b line/block that says “continue to Step 4” unless that same continuation explicitly routes through the Step 3b completion boundary.

### FINDING_10:
- **Reviewer(s)**: Cursor-dyn-cross-ref-stale
- **Severity**: important
- **Focus area**: correctness
- **Location**: <TMPDIR>/plan.txt:55-60
- **Concern**: skills/design/SKILL.md:1340. Scenario: Step 3b retarget list omits anti-halt blockquote
- **Proposed resolution**: Plan item 3 lists early-exit lines (~1303, ~1334, ~1336, ~1338) but not the `> **Continue to Step 4 IMMEDIATELY.**` blockquote at skills/design/SKILL.md:1340. New harness pin forbids bare "continue to Step 4" without "completion boundary"; scripts/test-implement-anti-halt.sh:64 requires the exact substring `Continue to Step 4 IMMEDIATELY` in SKILL.md under make lint (test-harnesses-4). Implementer updates only the enumerated lines; line 1340 stays a direct Step 4 bypass, failing the new structure pin and/or removing the anti-halt literal CI requires. Add ~1340 to item 3 retargets (e.g. completion-boundary-then-Step-4 wording that keeps `Continue to Step 4 IMMEDIATELY`); add `bash scripts/test-implement-anti-halt.sh` to Testing strategy.

