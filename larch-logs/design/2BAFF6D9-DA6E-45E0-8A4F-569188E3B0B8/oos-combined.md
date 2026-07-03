### OOS_1: Tally-error doc still claims restore-without-restore
- **Description**: `plan-review.md` says a Step 3 tally-error "restores cumulative accepted artifacts," but no restore helper exists anywhere in the codebase — the `.prev.md` sidecars are delete-only (used during manual Gate A/C re-entry cleanup), never written or read as a snapshot-then-restore mechanism. The actual tally-error behavior only fail-closes by not clearing cumulative files; it does not implement restore. Affected: `skills/design/references/plan-review.md:65` ("Tally failures" bullet under "Single-pass review").
- **Reviewer**: Cursor-Arch
- **Severity**: latent
- **Focus area**: architecture
- **Location**: skills/design/references/plan-review.md:65
- **Phase**: design
