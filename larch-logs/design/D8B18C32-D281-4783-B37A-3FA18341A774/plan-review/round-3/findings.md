### FINDING_1:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Focus area**: architecture
- **Location**: skills/implement/scripts/stall-recovery-report.sh:792-799
- **Concern**: safe_step_value full-string rewrite is bundled into a wiring-only bugfix. Scenario: #3568 is silent ITEMS_TOTAL=0 from heading-less bug-body; issue-input-file already exists and prefix glob already maps 8a<script> to unknown; ~half the planned diff is sanitizer churn unrelated to filing
- **Proposed resolution**: Drop the safe_step_value rewrite from this PR; wire issue-input-file in stall-recovery.md plus the structure/parse-input pins only

### FINDING_2:
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/implement/references/stall-recovery.md:40-42 vs scripts/test-implement-structure.sh:83-87
- **Concern**: Proposed step-4 prose wraps `/larch:issue --input-file` and `stall-recovery-issue-input.md` onto separate lines, but the wiring pin requires both on one line. Scenario: Following the plan's own stall-recovery.md bullet literally makes `grep -E '/larch:issue --input-file.*stall-recovery-issue-input\.md'` fail in CI even when step 4 is wired correctly
- **Proposed resolution**: Put the full dev-clone invocation on one physical line in stall-recovery.md (e.g. `` `/larch:issue --input-file $IMPLEMENT_TMPDIR/stall-recovery-issue-input.md` ``), or relax the harness grep to match across the wrapped command block; prefer the single-line prose fix to match the stated pin contract

### FINDING_3:
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: scripts/test-implement-structure.sh:83-87
- **Concern**: Same-line /larch:issue grep conflicts with wrapped Step 4 example in the plan. Scenario: The planned grep requires `/larch:issue --input-file` and `stall-recovery-issue-input.md` on one line, but the Step 4 rewrite example splits that command across two lines; an implementer can follow the prose and fail `make test-implement-structure`
- **Proposed resolution**: In the stall-recovery.md section, require the `/larch:issue --input-file $IMPLEMENT_TMPDIR/stall-recovery-issue-input.md` line to stay on one physical line (or relax the grep to the Step 4 paragraph without a same-line constraint)

### FINDING_4:
- **Reviewer(s)**: Cursor-dyn-prose-executable
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/implement/references/stall-recovery.md:19
- **Concern**: Step 4 rewrite bullets omit the DRY_RUN_DECISION gate before /larch:issue. Scenario: A full step-4 rewrite from the plan bullets alone can run /larch:issue and stall-recovery-issue.env normalization under LARCH_STALL_RECOVERY_DRY_RUN=1
- **Proposed resolution**: After bug-body (and local-only issue-input-file), restate: parse DRY_RUN_DECISION from bug-body stdout; when true skip /larch:issue and env normalization; only on dev-clone non-dry-run path file via stall-recovery-issue-input.md then normalize ISSUE_1_* keys
