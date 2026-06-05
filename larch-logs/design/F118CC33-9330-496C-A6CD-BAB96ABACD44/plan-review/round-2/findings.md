### FINDING_1:
- **Reviewer(s)**: Cursor-Arch, Cursor-Edge, Cursor-Pragmatic, Cursor-Requirements
- **Severity**: important
- **Focus area**: correctness
- **Location**: scripts/test-timing-report.sh:128-158
- **Concern**: Design run-params fallback harness omits LARCH_TIMING_SKILL=design after planned gate. Scenario: Plan gates resolve_workflow_fallback on LARCH_TIMING_SKILL=design but keeps V2/V1_PATH cases unchanged without that env; default skill is implement so run-params.json beside the ledger is ignored and workflow_path stays unknown while tests still expect SIMPLE
- **Proposed resolution**: Prefix V2 and V1_PATH timing-report.sh invocations with LARCH_TIMING_SKILL=design (and DESIGN_TMPDIR when needed); document this in the scripts/test-timing-report.sh plan subsection

### FINDING_2:
- **Reviewer(s)**: Codex-Arch
- **Severity**: latent
- **Focus area**: architecture
- **Location**: skills/report-tokens/scripts/run-analysis.md:35-48
- **Concern**: Plan omits the wrapper contract after changing implement report-token workflow handling. Scenario: After the PR, this contract would still say implement scans timing-report/run-params workflow artifacts and reports aggregate workflow costs, contradicting the proposed scanner/render behavior
- **Proposed resolution**: Add this file to the plan; make run-params workflow fallback and SIMPLE/HARD split design-only, and state implement has no workflow dimension

### FINDING_3:
- **Reviewer(s)**: Codex-Arch
- **Severity**: latent
- **Focus area**: architecture
- **Location**: scripts/test-timing-report.md:3; docs/linting.md:194
- **Concern**: Harness docs still promise workflow row/path coverage after proposed test changes. Scenario: The plan removes workflow rows and changes timing-report coverage to implement omission plus design-only fallback gating, but the harness docs would keep stale workflow-path coverage claims
- **Proposed resolution**: Add these existing docs to the plan and replace workflow latest/path phrasing with the new implement-omission and design-only fallback coverage

### FINDING_4:
- **Reviewer(s)**: Codex-Edge, Codex-Pragmatic
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: scripts/test-timing-report.sh:138-158
- **Concern**: Plan gates run-params workflow fallback on LARCH_TIMING_SKILL=design but says to keep these design fallback cases unchanged. Scenario: The harness unsets LARCH_TIMING_SKILL, so these calls default to implement; after the proposed gate they will not resolve run-params.json and the SIMPLE markdown/JQ assertions fail
- **Proposed resolution**: Set LARCH_TIMING_SKILL=design on the V2 and V1 design fallback timing-report invocations and update test-timing-report.md to document the explicit design gate

### FINDING_5:
- **Reviewer(s)**: Codex-Innovation
- **Severity**: important
- **Focus area**: correctness
- **Location**: plan.txt Acceptance grep vs skills/implement/scripts/test-step2-dispatch.sh:917-950
- **Concern**: Acceptance grep forbids --workflow under skills/implement while the proposed negative tests must keep --workflow literals. Scenario: The implementer cannot both add --workflow rejection coverage and pass the stated acceptance grep
- **Proposed resolution**: Narrow the grep to production call sites or explicitly exclude test files that assert legacy flag rejection

### FINDING_6:
- **Reviewer(s)**: Codex-Innovation
- **Severity**: important
- **Focus area**: correctness
- **Location**: scripts/test-timing-report.sh:138-157
- **Concern**: Design fallback tests are said to stay unchanged, but the proposed code gates fallback on LARCH_TIMING_SKILL=design. Scenario: Those calls currently unset LARCH_TIMING_SKILL, so they default to implement and fail to resolve run-params workflow
- **Proposed resolution**: Prefix the existing design fallback markdown and JSON invocations with LARCH_TIMING_SKILL=design

### FINDING_7:
- **Reviewer(s)**: Codex-Pragmatic
- **Severity**: latent
- **Focus area**: risk-integration
- **Location**: python/report_tokens_render.py:193-211
- **Concern**: Plan removes workflow from implement Cache JSON NDJSON, which is a durable report-tokens output. Scenario: Visible implement tables can drop workflow without changing the machine-readable cache schema; removing the key can break consumers that read Cache JSON records
- **Proposed resolution**: Keep the workflow key for all skills, using an empty or unknown value for implement, and remove only the markdown workflow grouping/columns

### FINDING_8:
- **Reviewer(s)**: Codex-Requirements
- **Severity**: important
- **Focus area**: security
- **Location**: SECURITY.md:74-76
- **Concern**: FINDING_1: Plan changes the /report-tokens implement scan-input boundary but omits the required SECURITY.md update. Scenario: After python/report_tokens_scan.py stops reading implement timing-report.json/run-params.json for workflow, SECURITY.md would still say those implement auxiliary JSON files are scan inputs and warning sources, contradicting the new security boundary and AGENTS.md's SECURITY.md-update constraint
- **Proposed resolution**: Add a minimal SECURITY.md edit stating implement workflow auxiliary artifacts are no longer read for workflow classification while design auxiliary workflow fallback remains

### FINDING_9:
- **Reviewer(s)**: Codex-Requirements
- **Severity**: latent
- **Focus area**: risk-integration
- **Location**: python/report_tokens_issue.py:20-29
- **Concern**: FINDING_2: Global aggregate label neutralization can change design issue trim notices despite the design-unchanged acceptance criterion. Scenario: When a /report-tokens --skill=design posted issue is oversized and the aggregate section is omitted, the trim notice would change from Aggregate cost by workflow to Aggregate cost because the registry is global, so report-tokens design behavior is not fully unchanged
- **Proposed resolution**: Keep the design omitted-section label unchanged; use a skill-aware or body-heading-derived label so implement can say Aggregate cost without changing design trimming text

### FINDING_10:
- **Reviewer(s)**: Cursor-dyn-design-implement-boundary
- **Severity**: important
- **Focus area**: correctness
- **Location**: scripts/timing-report.sh:42-55,102-106; scripts/test-timing-report.sh:128-158
- **Concern**: Plan gates resolve_workflow_fallback on LARCH_TIMING_SKILL=design but leaves design harness invocations on default implement. Scenario: Existing V2_DIR and V1_PATH_DIR cases (lines 128-158) call timing-report.sh without LARCH_TIMING_SKILL; default is implement (timing-report.sh:98). After the gate, run-params.json beside the ledger is never read, workflow stays unknown, and grep for **Workflow path**: SIMPLE fails despite production design callers always exporting LARCH_TIMING_SKILL=design (render-final-summary.sh:102-104, design-publish.sh:256)
- **Proposed resolution**: Add LARCH_TIMING_SKILL=design to every design fallback harness invocation (V2 and V1_PATH blocks); optionally set DESIGN_TMPDIR to the fixture dir to mirror production env -u IMPLEMENT_TMPDIR hygiene

### FINDING_11:
- **Reviewer(s)**: Codex-dyn-design-implement-boundary
- **Severity**: important
- **Focus area**: correctness
- **Location**: scripts/timing-report.sh:93-111; scripts/test-timing-report.sh:128-158
- **Concern**: F1: The plan gates workflow fallback on LARCH_TIMING_SKILL=design but leaves existing design fallback test invocations unchanged.. Scenario: With the proposed gate, current design fallback fixtures run without LARCH_TIMING_SKILL and would either fail or force the implementation to keep an implicit fallback.
- **Proposed resolution**: Set LARCH_TIMING_SKILL=design on the design fallback harness invocations and keep implement leakage tests explicitly at LARCH_TIMING_SKILL=implement.

### FINDING_12:
- **Reviewer(s)**: Codex-dyn-design-implement-boundary
- **Severity**: latent
- **Focus area**: architecture
- **Location**: python/report_tokens_issue.py:20-29
- **Concern**: F2: The proposed global aggregate label change would affect design issue truncation text.. Scenario: Changing aggregate from Aggregate cost by workflow to Aggregate cost in the shared registry changes design report issue output when sections are omitted, despite the plan claiming design output is byte-identical.
- **Proposed resolution**: Do not change the shared label globally; derive the omitted-section label from the skill-specific section heading/body or otherwise gate the new Aggregate cost label to implement only.

### FINDING_13:
- **Reviewer(s)**: Cursor-dyn-json-schema-contract
- **Severity**: important
- **Focus area**: correctness
- **Location**: scripts/test-timing-report.sh:128-158
- **Concern**: Design run-params fallback cases invoke timing-report.sh without LARCH_TIMING_SKILL=design. Scenario: After gating resolve_workflow_fallback to design-only (plan timing-report.sh ~100-106), V2/V1_PATH invocations keep the default implement skill; run-params fallback never runs and workflow_path becomes unknown while greps/jq still expect SIMPLE
- **Proposed resolution**: Export LARCH_TIMING_SKILL=design (and DESIGN_TMPDIR when using a design tmpdir) on every design fallback timing-report.sh invocation in those cases; keep SIMPLE expectations unchanged

### FINDING_14:
- **Reviewer(s)**: Codex-dyn-json-schema-contract
- **Severity**: important
- **Focus area**: correctness
- **Location**: scripts/test-timing-report.sh:138-158
- **Concern**: Proposed design-only workflow fallback gate conflicts with unchanged design fallback harness calls that run without LARCH_TIMING_SKILL=design. Scenario: make test-timing-report will default timing-report.sh to implement, skip resolve_workflow_fallback, and fail the SIMPLE markdown and JSON expectations
- **Proposed resolution**: Prefix the V2 and V1 design fallback invocations with LARCH_TIMING_SKILL=design, while keeping the new implement plus DESIGN_TMPDIR leak test on implement/default skill

### FINDING_15:
- **Reviewer(s)**: Codex-dyn-json-schema-contract
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/test_report_tokens_render.py:148-169
- **Concern**: Implement renderer drops workflow surfaces but this existing escaping test still expects the workflow string in implement output. Scenario: After the plan removes workflow columns/grouping for implement, SIMPLE\\|spoof no longer appears and py-test fails despite correct implement output
- **Proposed resolution**: Move the workflow-escape assertion to a design render case, or remove it from the implement case and keep the phase-cell escaping assertion

### FINDING_16:
- **Reviewer(s)**: Codex-dyn-json-schema-contract
- **Severity**: important
- **Focus area**: correctness
- **Location**: scripts/test-timing-report.sh:23-60
- **Concern**: Proposed timing-report fixture removal does not verify that legacy v1 workflow rows are ignored for implement. Scenario: If the awk workflow matcher is accidentally left in place, tests with no workflow row still pass while legacy implement ledgers can emit workflow_path HARD
- **Proposed resolution**: Add or retain a small implement fixture with v1 workflow HARD and assert no markdown Workflow path line plus JSON workflow_path == unknown

### FINDING_17:
- **Reviewer(s)**: Cursor-dyn-md-script-pairing
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/implement/scripts/test-run-step2-dispatch.md:11
- **Concern**: Plan updates test-run-step2-dispatch.sh to drop --workflow HARD from expected argv fixtures but omits the sibling harness contract .md. Scenario: The Coverage bullet still states WORKFLOW_PATH is HARD for Step 2 dispatcher argv; harness authors and make test-run-step2-dispatch maintainers will follow stale contract after the .sh rewrite
- **Proposed resolution**: Add ### UPDATED: skills/implement/scripts/test-run-step2-dispatch.md — remove WORKFLOW_PATH=HARD from Coverage; document argv without --workflow (aligned with run-step2-dispatch.md and the rewritten .sh fixtures)

### FINDING_18:
- **Reviewer(s)**: Codex-dyn-md-script-pairing
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/implement/scripts/test-run-step2-dispatch.md:7-15
- **Concern**: Plan rewrites test-run-step2-dispatch.sh argv fixtures but omits the companion md update. Scenario: After the proposed launcher rewrite removes --workflow, the harness contract still says WORKFLOW_PATH is HARD for the Step 2 dispatcher argv
- **Proposed resolution**: Update test-run-step2-dispatch.md in the plan; state that no workflow flag is forwarded and keep only plan, feature file, cursor presence, stdout, and answers coverage

### FINDING_19:
- **Reviewer(s)**: Codex-dyn-md-script-pairing
- **Severity**: important
- **Focus area**: correctness
- **Location**: scripts/test-timing-report.md:1-3
- **Concern**: Plan rewrites test-timing-report.sh workflow assertions but omits the companion md update. Scenario: The proposed harness removes implement workflow rows and adds a DESIGN_TMPDIR fallback-gate case, but the spec still claims workflow latest row rendering as coverage
- **Proposed resolution**: Update test-timing-report.md in the plan; describe implement no-workflow markdown plus JSON unknown, design-only fallback, vendor/path/terse/summary/outlier coverage

### FINDING_20:
- **Reviewer(s)**: Codex-dyn-md-script-pairing
- **Severity**: latent
- **Focus area**: architecture
- **Location**: scripts/timing-ledger.md:13-19; scripts/timing-ledger.sh:304-310
- **Concern**: The proposed timing-ledger.md edit only drops workflow from the enum and subcommand docs, leaving the post-change subcommand list under-specified. Scenario: The script still exposes record-vendor-task and record-round after workflow-path is removed, so a doc that simply deletes workflow would still not match the actual dispatch arms and row types
- **Proposed resolution**: When updating timing-ledger.md, make the enum mark/vendor/round and list mark, record-vendor-task, record-round, and dump; remove only workflow-path behavior
