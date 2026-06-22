## Decision 1: v2 scope (embedding-based auto-suppression)
- **Question**: Cover v2 (auto-suppress near-exact rejected duplicates at aggregation) or v1 only?
- **Resolution**: v1 only. Build the deterministic ledger plus reviewer/judge prompt injection. Defer v2 to a follow-up. v2's similarity threshold and "location-changed-since-rejection" computation are unresolved, v2 applies only to the code-review path, and v1 already captures most of the token savings.
- **Source**: user

## Decision 2: Consumer/surface scope
- **Question**: Which review surfaces should v1 cover?
- **Resolution**: All three. Code-review path (`/implement` Step 5 + `/review` diff; shared `render_specialist`/`render_reviewer`/`render_voter` + `review_tally.py`) and `/design` plan review (separate `render_plan_review` + `plan_review_tally.py`). A shared ledger writer keyed on `findings-classification.tsv` (both stacks emit it) is wired into both render+tally stacks.
- **Source**: user

## Decision 3: Ledger output format
- **Question**: TSV only, or TSV plus human-readable markdown?
- **Resolution**: TSV only. One ephemeral, anonymized `findings-ledger.tsv` in the review tmpdir (no proposer/authorship labels). Defer any markdown ledger.
- **Source**: user

## Decision 4: Cross-invocation persistence
- **Question**: Should the ledger persist across separate skill invocations?
- **Resolution**: Within-invocation only. The live ledger lives in the review tmpdir and resets each invocation. That matches the scope of the duplicate problem. No cross-invocation cache. (Committing the final ledger to run-logs, Decision 5, is for audit/analysis, not cross-run reuse.)
- **Source**: user

## Decision 5 (revised): Do NOT flush the ledger; it is ephemeral
- **Question**: Should `findings-ledger.tsv` be flushed to git?
- **Resolution**: No. The ledger is in-tmpdir only. It is used during the run for prompt injection, then discarded with the session tmpdir. It is never committed to `larch-logs/`. Rationale (user): the per-round `findings-classification.tsv` files are already flushed and carry suggestion authorship and full detail, so the committed audit record is already complete; flushing the ledger too would duplicate that. The plan must keep the ledger out of every committed surface: code review stages by allow-list (the ledger is excluded by default), and `/design` log-publish copies the whole tmpdir by deny-list, so the ledger basename must be added to `_PUBLISH_EXCLUDE_NAMES` in `design_log_publish_flow.py`.
- **Source**: user (revised; supersedes the earlier "flush to git" decision)

## Decision 6 (revised): No final-round append concern for the ledger
- **Question**: Must the ledger include the last round?
- **Resolution**: No. The ledger is discarded, so it does not matter whether the last round reached it. The committed record is the per-round `findings-classification.tsv` (with authorship), and the last round's file is already flushed today. Append to the ledger at end of each round for the next round's prompt injection; the final round's append is unnecessary (no later round reads it) and optional.
- **Source**: user (revised; supersedes the earlier final-round-completeness decision)

## Decision 7 (revised): Keep flushing per-round findings-classification.tsv unchanged
- **Question**: Drop per-round `findings-classification.tsv` from flushed logs?
- **Resolution**: No. Keep flushing them unchanged. They are the committed authorship/detail record. No `run_logs.py` flush-manifest change, no lossless-superset requirement on the ledger, no `/fluff-analysis` migration. `docs/run-logs.md` and the run-log batch contracts are untouched.
- **Source**: user (revised; supersedes the earlier drop-per-round decision)

## Hard constraints (from issue + codebase)
- Ledger write is a deterministic file append inside the existing tally path. No separate agent, no LLM, no extra orchestration barrier.
- Do not change vote thresholds, existing `findings-classification.tsv` content, or `voting-tally.md` output.
- Entries shown to voters carry no proposer labels, consistent with the neutralized ballot. Proposer attribution stays out of band in `proposer-map.tsv`.
- Duplicate-handling policy: rejected suppresses absent new evidence; accepted does not suppress and is annotated ("previously fixed in round N; if still present the fix may be incomplete"); neutral is treated like rejected behind a single policy knob (default suppress); OOS suppresses re-raising as new OOS.
- v1 has no embedding compare. Reviewers and judges read the ledger file and apply judgment to skip or short-circuit duplicates.
