## Decision 1: Placement of new SECURITY.md note
- **Question**: New dedicated paragraph vs. augmenting existing line 40 or line 44 paragraph?
- **Resolution**: New dedicated paragraph in SECURITY.md (placed near the existing "Claude review subprocesses" line 44 block) focused on `launch-claude-review.sh`. Cover subprocess data paths, secret-handling expectations, and the trust/logging-boundary delta vs the prior in-process Agent voter.
- **Source**: user
