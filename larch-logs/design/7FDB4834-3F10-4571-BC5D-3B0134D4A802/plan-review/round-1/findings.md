### FINDING_1:
- **Reviewer(s)**: Codex-Arch, Codex-Pragmatic
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: skills/implement/references/oos-pipeline.md proposed Step 7; skills/implement/SKILL.md:58,1042
- **Concern**: Proposed OOS pipeline writes run-statistics before the existing disposition checkpoint. Scenario: The current Step 8+ contract forbids writing run-statistics until oos-disposition-checkpoint.sh passes. If the proposed reference writes it inside Step 9a.1 first, a later checkpoint failure can leave a misleading run-statistics batch despite an unresolved OOS disposition gap.
- **Proposed resolution**: Keep run-statistics owned by the existing post-checkpoint Step 8+ block, or move the checkpoint into the new reference before any run-statistics write.

### FINDING_2:
- **Reviewer(s)**: Codex-Arch
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/implement/references/oos-pipeline.md proposed Step 4 and sentinel format; skills/issue/SKILL.md:332-345
- **Concern**: Sentinel parsing omits duplicate issue URLs from /issue. Scenario: /issue may emit ISSUE_i_DUPLICATE_OF_URL with ISSUES_DEDUPLICATED>0 and no ISSUE_i_URL. An all-dedup OOS batch could produce no URL tokens in oos-issues-created.md, causing the Step 8+ disposition gate or idempotent recovery path to treat accepted OOS as undisposed.
- **Proposed resolution**: Parse ISSUE_<i>_DUPLICATE_OF_URL alongside ISSUE_<i>_URL and include those URLs in oos-issues-created.md and recovered tallies.

### FINDING_3:
- **Reviewer(s)**: Codex-Edge
- **Severity**: important
- **Focus area**: correctness
- **Location**: plan.txt:11; skills/shared/voting-protocol.md:290-292; skills/implement/scripts/oos-disposition-checkpoint.md:12-20
- **Concern**: Proposed Step 1 only reads $IMPLEMENT_TMPDIR/oos-accepted-design.md and omits the current design-OOS resolution order. Scenario: When /design ran in-session or was exported, accepted design OOS lives in $DESIGN_TMPDIR/oos-accepted-design.md or $IMPLEMENT_TMPDIR/design-export/oos-accepted-design.md; Step 9a.1 treats it as missing, so filing/logging is skipped and the checkpoint later stalls on unresolved OOS
- **Proposed resolution**: Revise oos-pipeline.md Step 1 to resolve the design accepted-OOS path the same way as the checkpoint: explicit design tmpdir / DESIGN_TMPDIR, then $IMPLEMENT_TMPDIR/design-export/oos-accepted-design.md, then $IMPLEMENT_TMPDIR/oos-accepted-design.md

### FINDING_4:
- **Reviewer(s)**: Codex-Edge
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: plan.txt:11-12; skills/implement/scripts/oos-disposition-checkpoint.sh:175-179
- **Concern**: The Filed-URL carve-out can take the missing/empty early-exit without ensuring the checkpoint's required oos-issues.ndjson exists. Scenario: If the only accepted OOS blocks are design-phase blocks already annotated with - **Filed URL**:, the post-filter batch is empty; the pipeline exits like no OOS existed, but the checkpoint still counts non-security accepted blocks and fails validation before it can count the strict Filed URL
- **Proposed resolution**: Revise Step 2 to distinguish true no-input from all-already-filed input; ensure the oos-issues batch/ndjson exists before returning to the checkpoint, or otherwise document the required existing ndjson on that branch

### FINDING_5:
- **Reviewer(s)**: Codex-Innovation
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/issue/SKILL.md:480-485
- **Concern**: Planned Step 5 writes the Step 9a.1 sentinel without saying to suppress it when /issue reports ISSUES_FAILED>0. Scenario: Partial /issue success can create one URL, fail another item, then the parent sentinel makes reruns skip /issue; the failed OOS item may never be retried, and the loose gate can still pass from the one URL
- **Proposed resolution**: Add a Step 4/5 branch: if /issue exits non-zero or ISSUES_FAILED>0, do not write $IMPLEMENT_TMPDIR/oos-issues-created.md; log/breadcrumb the partial failure and leave the checkpoint to block until missing dispositions are resolved

### FINDING_6:
- **Reviewer(s)**: Codex-Innovation
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: skills/issue/SKILL.md:332-342
- **Concern**: Planned Step 4 parses ISSUE_<i>_URL but omits ISSUE_<i>_DUPLICATE_OF_URL from /issue's duplicate-success contract. Scenario: An all-dedup OOS batch is a valid /issue success with ISSUES_FAILED=0, but the proposed sentinel/log recovery would have no URL evidence, so OOS_PENDING can fail to clear or recover with empty URLs
- **Proposed resolution**: Update oos-pipeline.md Step 4/5 to parse ISSUE_<i>_DUPLICATE_OF_URL and ISSUE_<i>_DUPLICATE_OF_NUMBER as disposition URLs/numbers, matching the design helper precedent in skills/design/scripts/file-design-oos.sh:359-366

### FINDING_7:
- **Reviewer(s)**: Codex-Pragmatic
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: plan.txt:11-12,22; skills/implement/scripts/oos-disposition-checkpoint.sh:163-178
- **Concern**: Design-filed-only early exit lacks the checkpoint input it still requires. Scenario: When all accepted design OOS blocks already have `- **Filed URL**:` and review/main are empty, the proposed pipeline filters them out and early-exits; the checkpoint still counts the design accepted file as non-security OOS and fails exit 2 if no implement `oos-issues.ndjson` exists
- **Proposed resolution**: Document the filed-design-only path explicitly: either ensure an `oos-issues.ndjson` checkpoint input exists before returning, or update the checkpoint input contract to exclude Filed-URL design blocks / include the design sentinel; add a harness pin for that case

### FINDING_8:
- **Reviewer(s)**: Codex-Requirements
- **Severity**: important
- **Focus area**: correctness
- **Location**: scripts/test-implement-structure.sh:407-418
- **Concern**: Planned guard only checks that oos-pipeline.md appears once in SKILL.md, while the plan requires mandatory load directives at two Step 8+ OOS consumption points. Scenario: An implementation can update only the Exit 0 branch or only the OOS checkpoint block; CI still passes, leaving one runtime path able to execute Step 9a.1 without loading the restored canonical procedure
- **Proposed resolution**: Add a fixed-string assertion that the exact mandatory directive occurs twice, or add two fixed-string checks covering the Exit 0 and OOS checkpoint wording without awk section extraction

### FINDING_9:
- **Reviewer(s)**: Codex-dyn-contract-drift
- **Severity**: important
- **Focus area**: correctness
- **Location**: <TMPDIR>/plan.txt:20-22; skills/implement/SKILL.md:1024,1042; skills/implement/scripts/oos-disposition-gate.md:35-37
- **Concern**: Proposed oos-pipeline.md makes run-statistics a pre-checkpoint pipeline write, but current contracts keep run-statistics orchestrator-owned after checkpoint exit 0. Scenario: If the OOS pipeline writes run-statistics and then oos-disposition-checkpoint fails, the run gets statistics despite SKILL.md saying not to write them before a passing checkpoint
- **Proposed resolution**: Change oos-pipeline.md step 7 to defer run-statistics to the existing post-checkpoint SKILL.md block; the pipeline should only expose counts/URLs for that later write

### FINDING_10:
- **Reviewer(s)**: Codex-dyn-contract-drift
- **Severity**: important
- **Focus area**: correctness
- **Location**: <TMPDIR>/plan.txt:11; skills/shared/voting-protocol.md:290-292; skills/implement/scripts/oos-disposition-checkpoint.md:11-20
- **Concern**: Proposed source list reads only $IMPLEMENT_TMPDIR/oos-accepted-design.md, but current contracts resolve design OOS through $DESIGN_TMPDIR and design-export fallbacks. Scenario: In-session design OOS can be missed by the filing pass while the disposition checkpoint still sees it and blocks OOS_PENDING clearing
- **Proposed resolution**: Add the same design OOS resolution order to oos-pipeline.md: DESIGN_TMPDIR, then implement design-export, then implement-local fallback

### FINDING_11:
- **Reviewer(s)**: Codex-dyn-contract-drift
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: <TMPDIR>/plan.txt:22; skills/implement/SKILL.md:40,407
- **Concern**: Plan says repo_unavailable skips larch-log Accepted-OOS writes, but current SKILL.md says repo_unavailable reports Skipped — repo unavailable in the oos-issues batch. Scenario: Operators lose the only durable repo-unavailable OOS audit row even though the plan claims no behavior change
- **Proposed resolution**: Split the carve-out: forked_target skips accepted OOS log updates; repo_unavailable skips /issue but still writes the documented oos-issues Skipped — repo unavailable record

### FINDING_12:
- **Reviewer(s)**: Codex-dyn-contract-drift
- **Severity**: latent
- **Focus area**: correctness
- **Location**: <TMPDIR>/plan.txt:18,23; skills/issue/SKILL.md:332-343,442-450; skills/design/scripts/file-design-oos.md:14-15
- **Concern**: Proposed sentinel parse/format records ISSUE_i_URL but omits ISSUE_i_DUPLICATE_OF_URL from /issue’s stdout contract. Scenario: An all-deduplicated OOS batch succeeds in /issue but oos-issues-created.md may contain no URL token, so idempotency recovery and the disposition gate cannot see the disposition
- **Proposed resolution**: Have oos-pipeline.md record both ISSUE_i_URL and ISSUE_i_DUPLICATE_OF_URL as disposition URLs in oos-issues-created.md; keep the table/tally wording neutral to created-or-deduplicated URLs

### FINDING_13:
- **Reviewer(s)**: Codex-dyn-guard-robustness
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: scripts/test-implement-structure.sh:407-418; skills/implement/SKILL.md:1024,1042
- **Concern**: FINDING_1: Planned load-directive assertion only proves one SKILL.md occurrence. Scenario: The plan requires mandatory loading at both Step 8+ OOS entry points, but a single grep for the path can pass if only Exit 0 or only OOS checkpoint is updated
- **Proposed resolution**: Add a fixed-string count for the full mandatory directive phrase plus oos-pipeline.md path and require at least two occurrences

### FINDING_14:
- **Reviewer(s)**: Codex-dyn-guard-robustness
- **Severity**: important
- **Focus area**: correctness
- **Location**: scripts/test-implement-structure.sh:407-418; skills/implement/scripts/oos-disposition-gate.md:14-15,31
- **Concern**: FINDING_2: Sentinel guard pins only the heading, not the sentinel format. Scenario: A gutted oos-pipeline.md with only “oos-issues-created.md sentinel format” would pass while dropping the table header or filed tally that idempotent recovery and the loose URL counter rely on
- **Proposed resolution**: Keep the heading grep, and add fixed-string greps for `| OOS title | Issue | URL |`, `- **Filed**: <N>`, and the `issues/<n>` URL-token shape

### FINDING_15:
- **Reviewer(s)**: Codex-dyn-guard-robustness
- **Severity**: latent
- **Focus area**: correctness
- **Location**: scripts/test-implement-structure.sh:407-418; skills/implement/scripts/oos-issue-cap.md:3-6,59-65; skills/implement/scripts/oos-file-conflict-deps.md:3-5,40-45
- **Concern**: FINDING_3: Helper assertions can pass on helper-name mentions without proving pipeline wiring. Scenario: A gutted restore could mention `oos-issue-cap.sh` and `oos-file-conflict-deps.sh` in see-also prose while omitting the cap pre-pass or file-conflict invocation contract
- **Proposed resolution**: Add minimal fixed-string greps for invocation fragments such as `oos-issue-cap.sh --input-file`, `oos-file-conflict-deps.sh --input-file`, and `--output "$IMPLEMENT_TMPDIR/oos-intra-batch-deps.tsv"`
