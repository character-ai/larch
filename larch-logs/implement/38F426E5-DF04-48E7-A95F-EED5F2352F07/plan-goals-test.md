## Goal
Create docs/run-logs.md documenting larch-log batches committed with every PR, and link from README.

## Implementation Plan
1. Create docs/run-logs.md documenting: directory structure, manifest.json, all 11 batch files, tracking-issue marker-keyed comments.
2. Edit README.md to link "Tracked runs" to docs/run-logs.md.

## Test plan
Run /relevant-checks (pre-commit + agent-lint).
