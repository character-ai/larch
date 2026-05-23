## Decision 1: main-agent-vote-required (MAV) path
- **Question**: When all 3 judges fail (rare), how does the absorbed loop interact with the main-agent vote fallback?
- **Resolution**: Wrapper exits on `main-agent-vote-required`; main agent applies synthetic ballot + dispatches `review-and-fix.sh --findings-file` + runs relevant-checks, then re-invokes the wrapper with `--starting-round N+1` so the loop resumes. Preserves full multi-round semantics under all conditions.
- **Source**: user

## Decision 2: duplicate tally-batch composition prose
- **Question**: Should the same change remove the duplicate `code-review-tally` / `review-findings-full` composition prose in `skills/implement/SKILL.md` (lines ~1245-1281)?
- **Resolution**: Yes — remove in the same change, since `flush_review_batches` in `review-and-fix.sh` already writes both batches per round (verified). Keeps the cleanup atomic.
- **Source**: user

## Decision 3: stall semantics
- **Question**: Must all existing `STALL_TRACKING=true` + skip-to-Step-16 semantics be preserved (`coder-failed`, `panel-failed`, `submodule-violation`, lint-fix-loop `failed`/`main-agent-required`, bulk-skip-ratio cap, round-cap-without-converge proceed-with-warning)?
- **Resolution**: Preserve exactly. The wrapper's final summary KV block surfaces `STALL_TRACKING=true` and stall reasons; main agent parses them and skips to Step 16 just as today. No behavior change, only dispatch cardinality changes.
- **Source**: user

## Decision 4: per-round `flush_review_batches` cadence
- **Question**: Should `flush_review_batches` continue firing per-round (current behavior) inside the absorbed loop, or be deferred to a single flush at the end?
- **Resolution**: Per-round flush — preserve current behavior. Crash-safety: if the loop dies mid-loop, the most recent round's batches still reflect a coherent snapshot.
- **Source**: user

## Decision 5: live progress visibility during multi-round wrapper call
- **Question**: Should the wrapper emit per-round breadcrumbs visible to the operator during execution, or stay silent until the final summary?
- **Resolution**: Emit per-round breadcrumbs (use the existing `emit_breadcrumb` path inherited from `review-and-fix.sh`). Preserves current Step 5 visibility for the operator; no information loss. Trivial cost.
- **Source**: user

## Decision 6: backward compatibility for single-round entry point
- **Question**: Should `review-and-fix.sh --mode diff --round-num N --round-cap M` (and `run-step5-review.sh --round-num N` calling it) remain a working dispatch path?
- **Resolution**: Preserve unchanged. The new loop wrapper internally calls the single-round path once per iteration. Existing `test-review-and-fix.sh` and `test-implement-review-token-propagation.sh` stay green without input changes; single-round mode remains available for ad-hoc debugging.
- **Source**: user

## Decision 7: change is /implement-only
- **Question**: Does this change affect `/review` standalone diff mode or `/review-and-fix` findings-mode dispatch?
- **Resolution**: No — issue text explicitly says "This change is `/implement`-only. `/review` standalone (`--diff` mode) keeps its own round loop in `skills/review/SKILL.md` Step 3." Findings-mode dispatch is also explicitly out of scope.
- **Source**: codebase (issue body)
