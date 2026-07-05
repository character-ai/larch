### FINDING_1: Missing update for the dedicated ci-fix harness
- **Reviewer(s)**: Cursor-Arch, Codex-Arch, Cursor-Innovation, Codex-Innovation, Cursor-Pragmatic, Codex-Pragmatic, Cursor-Requirements, Codex-Requirements, Cursor-dyn-Ci Fix Contract, Codex-dyn-Ci Fix Contract
- **Severity**: major
- **Concern**: The plan rewrites Step 6 but leaves out the dedicated `scripts/test-implement-step8-exit3-first-fixer.sh` harness that still asserts the old `Make the minimal repo edit` phrase, so CI will fail after the doc change unless that harness is updated and added to testing.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Add `### MAY_UPDATE: scripts/test-implement-step8-exit3-first-fixer.sh` (or `### UPDATED:` if you want it firm): replace the `Make the minimal repo edit` require needle with the same stable substring chosen for the new all-failures Step 6 rule. Add `bash scripts/test-implement-step8-exit3-first-fixer.sh` (or `make test-implement-step8-exit3-first-fixer`) to Testing strategy alongside `scripts/test-implement-structure.sh`.
  - From Codex-Arch: Add `scripts/test-implement-step8-exit3-first-fixer.sh` to the plan's UPDATED list and replace the stale needle with a stable phrase from the new all-failures rule.
  - From Cursor-Innovation: Add `### UPDATED: scripts/test-implement-step8-exit3-first-fixer.sh` to replace the Step 6 needle with a stable phrase from the new all-failures rule; add `make test-implement-step8-exit3-first-fixer` to Testing strategy
  - From Codex-Innovation: Add `scripts/test-implement-step8-exit3-first-fixer.sh` to the update set and replace the stale needle with the new all-failures wording, or document why the harness is intentionally left unchanged.
  - From Cursor-Pragmatic: Add `### UPDATED: scripts/test-implement-step8-exit3-first-fixer.sh` (or fold into the structure-harness bullet as a required sibling update): replace the `Make the minimal repo edit` needle with the same stable phrase chosen for the new all-failures Step 6, and add `bash scripts/test-implement-step8-exit3-first-fixer.sh` to Testing strategy.
  - From Codex-Pragmatic: Add `### UPDATED: scripts/test-implement-step8-exit3-first-fixer.sh` and replace the stale needle with the new all-revealed-failures wording; keep `scripts/test-implement-structure.sh` synchronized if it still asserts the old phrase.
  - From Cursor-Requirements: Add `### MAY_UPDATE: scripts/test-implement-step8-exit3-first-fixer.sh` with the same needle-retarget rule as test-implement-structure.sh; pick one stable phrase from the new all-failures Step 6 for both harnesses; list `bash scripts/test-implement-step8-exit3-first-fixer.sh` in Testing strategy when Step 6 wording changes
  - From Codex-Requirements: Add this harness to the UPDATED or MAY_UPDATE list and swap the needle for the new all-failures wording
  - From Cursor-dyn-Ci Fix Contract: Add ### UPDATED: scripts/test-implement-step8-exit3-first-fixer.sh: replace the Step 6 needle with the same stable all-failures phrase used in ship-pr-ci-fix.md; add bash scripts/test-implement-step8-exit3-first-fixer.sh to Testing strategy.
  - From Codex-dyn-Ci Fix Contract: Add `### UPDATED: scripts/test-implement-step8-exit3-first-fixer.sh` and replace the stale needle with a stable phrase from the new all-failures Step 6 rule.


### FINDING_2: Structure harness is mandatory, not optional
- **Reviewer(s)**: Cursor-Innovation, Cursor-dyn-Ci Fix Contract
- **Severity**: minor
- **Concern**: The plan treats `scripts/test-implement-structure.sh` as a discretionary `MAY_UPDATE`, but the same stale Step 6 phrase is pinned there too, so any rewrite breaks the harness and it needs a required update.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Innovation: Promote `scripts/test-implement-structure.sh` to `### UPDATED:` (not MAY_UPDATE) and require the new Step 6 substring at lines 709 (and any duplicate pins)
  - From Cursor-dyn-Ci Fix Contract: Promote scripts/test-implement-structure.sh to ### UPDATED: and require replacing both Step 6 needles with one shared stable phrase from the new rule.


