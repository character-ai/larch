## Goal
Fix session-transcript.jsonl capture inconsistency across /implement runs by replacing 5 silent-skip points with a single wrapper script that always records the outcome; add operator_cwd and operator_repo_root to manifest.json (schema version 2).

## Implementation Plan
See plan.txt.

## Test plan
- Run scripts/test-capture-session-transcript.sh — all 6 skip/success paths
- Run scripts/test-larch-logs-manifest.sh — schema_version=2, operator_cwd, operator_repo_root
- Run /relevant-checks
