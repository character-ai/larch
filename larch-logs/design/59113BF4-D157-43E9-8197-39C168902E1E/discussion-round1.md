## Decision 1: Root cause of misclassification
- **Question**: What causes protected-path-edit-required-out-of-scope to land at transient-infra?
- **Resolution**: The token is not in the dispatch-bail-token case arm in classify_from_evidence(). Evidence from state files (which includes step, phase, bail, and file content) may contain transient-matching words, causing the transient grep to fire instead. The token also is not in safe_bail_reason_value() so it's sanitized to "redacted" in public output.
- **Source**: codebase

## Decision 2: New class vs dispatch-failure reuse
- **Question**: Should we reuse dispatch-failure or create a new protected-path class?
- **Resolution**: New class FAILURE_CLASS=protected-path per issue. dispatch-failure has retry cap=3 which is wrong for a permanent ban; protected-path needs cap=1.
- **Source**: issue + codebase

## Decision 3: RESUME_HINT correctness
- **Question**: Does RESUME_HINT need to change?
- **Resolution**: No. resume_hint_for() already returns step2-impl for step=2 (main agent can edit protected paths). Only FAILURE_CLASS and retry cap need fixing.
- **Source**: codebase

## Decision 4: Operator warning scope
- **Question**: What does "warning to operator" mean in the issue?
- **Resolution**: Satisfied by the new FAILURE_CLASS=protected-path label in the stall classification output. The "first-detection message clarifying the path name" is OOS — the bail_reason token does not encode the path name; extracting it from the Codex manifest is a separate effort.
- **Source**: codebase + issue analysis
