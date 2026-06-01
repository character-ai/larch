## Proposed Design Outline

### Goals
- Make `pre_coder_snapshot_dir()` match its documented contract: relocate in-`$PWD` round snapshots outside every Codex `--add-dir` grant.
- Harden carryover artifacts against delegated-fixer tampering with `chmod 0444`.
- Document the trust boundary and the load-bearing Step 2 grant.

### Non-goals
- Narrowing `--add-dir "$SESSION_TMPDIR"` — it stays wide (Step 2 writes `manifest.json` / `qa-pending.json` there).
- A CI sandbox-confinement check (flaky, disproportionate).
- Any change to MAV head-only carryover behavior.

### Approach sketch
- Add a second branch to `pre_coder_snapshot_dir()`: when `round_dir` resolves under `$PWD`, return `${TMPDIR:-/tmp}/larch-pre-coder-snapshots/<hash>/$(basename "$round_dir")`; else keep the existing `.pre-coder-snapshots` sibling. Every reader/writer already routes through this one helper, so the change is self-propagating.
- `chmod 0444` the snapshot files and `post-coder-head.txt` after each write; never chmod the directories, so `rm -rf` cleanup still works.
- Document the Step 2 grant rationale (comment + `.md`), and the trust boundary + IMPLEMENT_TMPDIR precondition (SECURITY.md, review-and-fix.md).
- Add an in-repo `test-review-and-fix.sh` fixture that proves the snapshot resolves outside `$PWD`, plus a `0444` perms check.

### Surfaces in scope
- `skills/review-and-fix/scripts/review-and-fix.sh` + `.md`
- `skills/review-and-fix/scripts/review-implement-step5-loop.sh` + `.md`
- `scripts/launch-codex-implement.sh` + `.md`
- `skills/review-and-fix/scripts/test-review-and-fix.sh` + `.md`
- `SECURITY.md`

### Open questions
- `<hash>` input: hash the round_dir absolute path (stable per round, disambiguates same-basename rounds across sessions). The plan will settle the exact derivation.
