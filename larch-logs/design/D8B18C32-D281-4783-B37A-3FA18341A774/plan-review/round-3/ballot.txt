### FINDING_1: safe_step_value rewrite bundled into wiring-only bugfix
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Concern**: `safe_step_value` full-string rewrite is bundled into a wiring-only bugfix. For #3568 (silent `ITEMS_TOTAL=0` from heading-less bug-body), `issue-input-file` already exists and the prefix glob already maps `8a<script>` to `unknown`; roughly half the planned diff is sanitizer churn unrelated to filing.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Innovation: Drop the safe_step_value rewrite from this PR; wire issue-input-file in stall-recovery.md plus the structure/parse-input pins only

### FINDING_2: Step 4 prose line-wrap conflicts with structure-test same-line grep pin
- **Reviewer(s)**: Cursor-Pragmatic, Cursor-Requirements
- **Severity**: important
- **Concern**: The planned Step 4 prose wraps `/larch:issue --input-file` and `stall-recovery-issue-input.md` onto separate lines, but `scripts/test-implement-structure.sh` pins both tokens on one physical line. An implementer who follows the plan’s `stall-recovery.md` bullets literally can wire Step 4 correctly yet still fail `make test-implement-structure` because `grep -E '/larch:issue --input-file.*stall-recovery-issue-input\.md'` requires a same-line match.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Pragmatic: Put the full dev-clone invocation on one physical line in stall-recovery.md (e.g. `` `/larch:issue --input-file $IMPLEMENT_TMPDIR/stall-recovery-issue-input.md` ``), or relax the harness grep to match across the wrapped command block; prefer the single-line prose fix to match the stated pin contract
  - From Cursor-Requirements: In the stall-recovery.md section, require the `/larch:issue --input-file $IMPLEMENT_TMPDIR/stall-recovery-issue-input.md` line to stay on one physical line (or relax the grep to the Step 4 paragraph without a same-line constraint)

### FINDING_3: Step 4 rewrite omits DRY_RUN_DECISION gate before /larch:issue
- **Reviewer(s)**: Cursor-dyn-prose-executable
- **Severity**: important
- **Concern**: The Step 4 rewrite bullets omit the `DRY_RUN_DECISION` gate before `/larch:issue`. A full Step 4 rewrite from the plan bullets alone can run `/larch:issue` and `stall-recovery-issue.env` normalization under `LARCH_STALL_RECOVERY_DRY_RUN=1`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-dyn-prose-executable: After bug-body (and local-only issue-input-file), restate: parse DRY_RUN_DECISION from bug-body stdout; when true skip /larch:issue and env normalization; only on dev-clone non-dry-run path file via stall-recovery-issue-input.md then normalize ISSUE_1_* keys
