## Decision 1: Include the resilience fallback (findings-jsonl derivation)
- **Question**: Beyond the always-included observability fixes, should the plan add the optional resilience fallback that derives the final-report / PR-body `Code review` line from `review-findings-full.jsonl` when `code-review-tally.json` is absent?
- **Resolution**: Yes. Include the fallback so summaries and PR bodies stop rendering `Code review: N/A` now, and the #5992/#5993 accepted-count fallback returns. The plan also always includes: capture the `voting write-tally` subprocess stderr/stdout to `code-review-tally.flush.err` in both call sites, and append an execution-issues Warnings entry on nonzero tally rc in `flush_review_batches`.
- **Source**: user

## Decision 2: The actual write-tally mechanism fix is deferred
- **Question**: Should this plan attempt to fix the root-cause mechanism that makes `voting write-tally` return nonzero in live runs?
- **Resolution**: No. The mechanism is unknown and does not reproduce offline; it needs a live-run error capture first. That is why observability comes first. The real fix lands in a follow-up once the captured `.flush.err` reveals the cause.
- **Source**: codebase / issue

## Decision 3: Back-fill and dead-branch cleanup stay out of scope
- **Question**: Should the plan back-fill `code-review-tally.json` for the v52.2.4..v52.4.2 window, or remove `final_report.py`'s "dead `CODE_REVIEW_LINE` ship-handoff branch"?
- **Resolution**: No to both. Back-fill is a separate one-off, log-only PR after the mechanism is fixed. The dead `CODE_REVIEW_LINE` branch does not exist in `final_report.py` today; only a negative-assertion test fixture references the key, so there is nothing to remove.
- **Source**: codebase / issue
