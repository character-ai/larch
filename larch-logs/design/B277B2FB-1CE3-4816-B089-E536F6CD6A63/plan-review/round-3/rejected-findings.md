### [Plan Review] FINDING_5

### FINDING_5: Structure tests still pin retired fat-fence artifacts
- **Reviewer(s)**: Cursor-Innovation, Cursor-Requirements
- **Severity**: important
- **Concern**: The migration retires inline parse/fat-fence behavior, but existing `scripts/test-design-structure.sh` checks still look for `.design-postplan-emit-result.env`, `_postplan_out` heredoc parsing, and literal `check-plan-size.sh` placement that may no longer exist in the collapsed Step 2b region.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Innovation: List explicit retirements: lines 515-517, 689-694, and any pin requiring stdout KV merge or literal check-plan-size.sh in the Step 2b region; replace with --with-plan-size and assert_thin_fence pins per plan lines 155-167
  - From Cursor-Requirements: Add an explicit test-design-structure.sh task: drop or repoint lines 515-516 for merged sites; keep only pins still valid on thin fences (for example rc=2 abort prose at 517 if retained in the case arm)


