## Proposed Design Outline

### Goals
- Wire `relevant-checks.sh` so edits to `implement-preflight.sh`, its `.md` sibling, and its test trigger `test-implement-preflight`.
- Fix stale SECURITY.md text: `--emergency` and `--merge` are compatible, not mutually exclusive.
- Add refusal-template first-line assertions to all untested admission-block branches in the harness.

### Non-goals
- No `strip_lifecycle_prefix` sync guard (Bash machinery not worth enhancing before Python migration).
- No changes to `Makefile` or `ci.yaml` (target and CI shard already exist).
- No new RESUME= tests (case 9 already covers forwarding).

### Approach sketch
- Add one `case "$f"` block in `relevant-checks.sh` covering all three files in the `implement-preflight` surface.
- Find and fix the single `mutually exclusive with --merge` sentence in `SECURITY.md`.
- Add `contains` assertions for the `**❌ /implement preflight: admission blocked` first line in `admission-blockers`, `admission-missing-designed`, `admission-report`, and `admission-error` test cases.

### Surfaces in scope
- `scripts/relevant-checks.sh`
- `SECURITY.md`
- `scripts/test-implement-preflight.sh`
- `scripts/test-implement-preflight.md` (update harness contract list if needed)

### Open questions
- None.
