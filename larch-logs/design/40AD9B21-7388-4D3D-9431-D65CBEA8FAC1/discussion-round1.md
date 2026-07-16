## Decision 1: Baseline key scheme
- **Question**: How should clusters be identified durably across code edits?
- **Resolution**: Sorted tuple of module names + normalized content hash (SHA-256 prefix) of the common block. Not line numbers, so unrelated shifts do not force rebaselining.
- **Source**: codebase / issue #7465 (G-Det-1)

## Decision 2: Failure semantics
- **Question**: Which live-vs-baseline divergences should fail the check?
- **Resolution**: New cluster (not in baseline) → fail; grown cluster (live lines > baseline lines) → fail; stale row (baseline entry not in live) → fail (forces regen when cluster is fixed, so baseline only shrinks).
- **Source**: issue #7465

## Decision 3: Write/regen mode
- **Question**: How is the baseline generated and updated?
- **Resolution**: `--write` flag on `duplicate-code` subcommand + `--initial-reason` for new entries; Makefile `regen-duplicate-code-baseline` target follows the subprocess-via-runner pattern (bootstrap `--initial-reason` only when baseline is absent).
- **Source**: codebase (existing regen-* pattern) / issue #7465

## Decision 4: Workflow scope
- **Question**: What workflow changes are in scope?
- **Resolution**: Re-enable `push: main` trigger, raise `timeout-minutes` to 25 (cold run 14m22s + margin), add baseline-aware step. Add `issues: write` permission and a "file or update one tracking issue on failure" step per the issue's sustainability requirement.
- **Source**: issue #7465

## Decision 5: PR-time changed-files mode
- **Question**: Should a changed-files mode be included in this PR?
- **Resolution**: Out of scope per issue: "Keep it a separate step; the main-push ratchet is the priority."
- **Source**: issue #7465
