# snapshot-untracked.sh

**Purpose**: Capture a sorted list of untracked files for pre-review baseline comparison. Replaces the inline compound command in `/implement` Step 5 that triggered "Unhandled node type: ;" permission prompts.

**Invariants**:
- Always exits 0 — callers must never abort on snapshot failure
- On any failure, removes both temp file and output file so `check-review-changes.sh` sees `UNTRACKED_BASELINE=missing` (issue #651 guard)
- Default output is sorted and newline-delimited for `check-review-changes.sh`; `--nul` switches to sorted NUL-delimited output for `check-mid-run-dirty-tree.sh`
- Uses `set -o pipefail` so `git ls-files` failures propagate through the pipe
- Atomic write via temp file + `mv -f`

**Stdout contract**: None (silent operation).

**Call sites**:
- `skills/implement/SKILL.md` Step 5 pre-review snapshot
- `scripts/launch-cursor-review.sh` and `scripts/launch-codex-review.sh` pre-launch dirty-tree baselines

**Edit-in-sync**: `skills/implement/scripts/check-review-changes.sh` (newline-delimited consumer), `scripts/check-mid-run-dirty-tree.sh` (NUL-delimited consumer), and the review launchers.
