## Decision 1: JSON field backward compatibility
- **Question**: Should `neutral_count` be retained zero-filled in JSON outputs, or removed with a schema_version bump?
- **Resolution**: Remove `neutral_count` from `review-and-fix-summary.json` and run-log batch JSONL records. Bump `schema_version` from 2 to 3 in `review-and-fix-summary.json`. Bump `schema_version` from 1 to 2 in `plan-review-tally` / `code-review-tally` batch records. Update all consumers (`skills/implement/SKILL.md`, `docs/run-logs.md`, `skills/review/references/heavy-worker.md`, audit tooling, tests).
- **Source**: user

## Decision 2: Internal KV shape for scoreboard accounting
- **Question**: Should `_OUTCOME=neutral` be retained internally, or replaced with a separate `_REJECTED_SUBTYPE=neutral` flag?
- **Resolution**: Replace `_OUTCOME=neutral` with two-key shape: `FINDING_N_OUTCOME=rejected` (for all non-accepted findings) plus `FINDING_N_REJECTED_SUBTYPE=neutral|exonerated|true_rejected` (informational sub-classification for scoreboard scoring). The classifier still computes the same vote-pattern logic; only the emitted KV shape changes.
- **Source**: user
