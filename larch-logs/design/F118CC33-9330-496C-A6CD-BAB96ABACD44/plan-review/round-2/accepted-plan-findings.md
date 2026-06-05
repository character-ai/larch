### FINDING_1: Design timing fallback tests must opt into design skill
- **Reviewer(s)**: Cursor-Arch, Cursor-Edge, Cursor-Pragmatic, Cursor-Requirements, Codex-Edge, Codex-Pragmatic, Codex-Innovation, Cursor-dyn-design-implement-boundary, Codex-dyn-design-implement-boundary, Cursor-dyn-json-schema-contract, Codex-dyn-json-schema-contract
- **Severity**: important
- **Concern**: Multiple reviewers report the same risk: the plan gates run-params workflow fallback on `LARCH_TIMING_SKILL=design`, but existing design fallback harness invocations still run with the default implement skill, so `run-params.json` will not be read and SIMPLE workflow assertions will fail.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch, Cursor-Edge, Cursor-Pragmatic, Cursor-Requirements: Prefix V2 and V1_PATH timing-report.sh invocations with LARCH_TIMING_SKILL=design (and DESIGN_TMPDIR when needed); document this in the scripts/test-timing-report.sh plan subsection
  - From Codex-Edge, Codex-Pragmatic: Set LARCH_TIMING_SKILL=design on the V2 and V1 design fallback timing-report invocations and update test-timing-report.md to document the explicit design gate
  - From Codex-Innovation: Prefix the existing design fallback markdown and JSON invocations with LARCH_TIMING_SKILL=design
  - From Cursor-dyn-design-implement-boundary: Add LARCH_TIMING_SKILL=design to every design fallback harness invocation (V2 and V1_PATH blocks); optionally set DESIGN_TMPDIR to the fixture dir to mirror production env -u IMPLEMENT_TMPDIR hygiene
  - From Codex-dyn-design-implement-boundary: Set LARCH_TIMING_SKILL=design on the design fallback harness invocations and keep implement leakage tests explicitly at LARCH_TIMING_SKILL=implement.
  - From Cursor-dyn-json-schema-contract: Export LARCH_TIMING_SKILL=design (and DESIGN_TMPDIR when using a design tmpdir) on every design fallback timing-report.sh invocation in those cases; keep SIMPLE expectations unchanged
  - From Codex-dyn-json-schema-contract: Prefix the V2 and V1 design fallback invocations with LARCH_TIMING_SKILL=design, while keeping the new implement plus DESIGN_TMPDIR leak test on implement/default skill


### FINDING_2: Wrapper contract needs implement/design workflow split
- **Reviewer(s)**: Codex-Arch
- **Severity**: latent
- **Concern**: The plan changes implement report-token workflow handling but omits the wrapper contract, leaving documentation that still says implement scans timing-report/run-params workflow artifacts and reports aggregate workflow costs.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Arch: Add this file to the plan; make run-params workflow fallback and SIMPLE/HARD split design-only, and state implement has no workflow dimension


### FINDING_3: Timing-report harness docs remain stale
- **Reviewer(s)**: Codex-Arch, Codex-dyn-md-script-pairing
- **Severity**: important
- **Concern**: Harness documentation still claims workflow row/path coverage even though the proposed changes remove implement workflow rows and shift coverage to implement omission plus design-only fallback behavior.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Arch: Add these existing docs to the plan and replace workflow latest/path phrasing with the new implement-omission and design-only fallback coverage
  - From Codex-dyn-md-script-pairing: Update test-timing-report.md in the plan; describe implement no-workflow markdown plus JSON unknown, design-only fallback, vendor/path/terse/summary/outlier coverage


### FINDING_4: Acceptance grep conflicts with required negative tests
- **Reviewer(s)**: Codex-Innovation
- **Severity**: important
- **Concern**: The acceptance grep forbids `--workflow` under `skills/implement`, but proposed negative tests must retain `--workflow` literals to assert legacy flag rejection.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Innovation: Narrow the grep to production call sites or explicitly exclude test files that assert legacy flag rejection


### FINDING_6: SECURITY.md must reflect changed scan-input boundary
- **Reviewer(s)**: Codex-Requirements
- **Severity**: important
- **Concern**: The plan changes `/report-tokens` implement scan inputs by no longer reading implement timing-report/run-params workflow auxiliary artifacts, but omits the required SECURITY.md update.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Requirements: Add a minimal SECURITY.md edit stating implement workflow auxiliary artifacts are no longer read for workflow classification while design auxiliary workflow fallback remains


### FINDING_7: Global aggregate label change can alter design trim notices
- **Reviewer(s)**: Codex-Requirements, Codex-dyn-design-implement-boundary
- **Severity**: latent
- **Concern**: Changing the aggregate omitted-section label globally from workflow-specific wording to neutral wording can affect design issue truncation text, violating the design-unchanged criterion.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Requirements: Keep the design omitted-section label unchanged; use a skill-aware or body-heading-derived label so implement can say Aggregate cost without changing design trimming text
  - From Codex-dyn-design-implement-boundary: Do not change the shared label globally; derive the omitted-section label from the skill-specific section heading/body or otherwise gate the new Aggregate cost label to implement only.


### FINDING_8: Existing renderer escaping test still expects workflow in implement output
- **Reviewer(s)**: Codex-dyn-json-schema-contract
- **Severity**: important
- **Concern**: The plan removes workflow surfaces from implement renderer output, but an existing escaping test still expects the workflow string in implement output, causing the Python test to fail after a correct implementation.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-dyn-json-schema-contract: Move the workflow-escape assertion to a design render case, or remove it from the implement case and keep the phase-cell escaping assertion


### FINDING_9: Tests may not catch legacy v1 workflow rows leaking into implement output
- **Reviewer(s)**: Codex-dyn-json-schema-contract
- **Severity**: important
- **Concern**: Removing timing-report fixtures without a legacy v1 workflow-row case leaves a gap where the old awk workflow matcher could remain and still emit implement workflow paths undetected.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-dyn-json-schema-contract: Add or retain a small implement fixture with v1 workflow HARD and assert no markdown Workflow path line plus JSON workflow_path == unknown


### FINDING_10: Step 2 dispatch harness contract markdown omitted
- **Reviewer(s)**: Cursor-dyn-md-script-pairing, Codex-dyn-md-script-pairing
- **Severity**: important
- **Concern**: The plan rewrites Step 2 dispatch test fixtures to remove forwarded workflow arguments but omits the sibling markdown contract, leaving stale documentation that says `WORKFLOW_PATH` is HARD for dispatcher argv.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-dyn-md-script-pairing: Add ### UPDATED: skills/implement/scripts/test-run-step2-dispatch.md — remove WORKFLOW_PATH=HARD from Coverage; document argv without --workflow (aligned with run-step2-dispatch.md and the rewritten .sh fixtures)
  - From Codex-dyn-md-script-pairing: Update test-run-step2-dispatch.md in the plan; state that no workflow flag is forwarded and keep only plan, feature file, cursor presence, stdout, and answers coverage


