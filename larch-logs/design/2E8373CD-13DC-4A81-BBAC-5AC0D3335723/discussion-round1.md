## Decision 1: Conflict-resolution Phase 3 retry-loop shape
- **Question**: After dropping the Codex/Cursor panel from `/implement` conflict-resolution Phase 3, should main-agent self-review keep the existing up-to-2-round retry loop, or collapse to a single one-shot pass?
- **Resolution**: Keep the up-to-2-round retry loop. Main agent self-reviews each resolution; on a flagged problem it re-resolves and self-reviews again, aborting the rebase (`rebase-abort` + `STALL_TRACKING=true` + Step 18) after 2 unresolved rounds — same cap as today, with panel and voting removed.
- **Source**: default (AskUserQuestion timed out after 60s with no response; recommended option auto-applied)

## Decision 2: /implement Step 5 runtime-both-down fallback mechanism
- **Question**: When /implement Step 5's shared review panel (Codex/Cursor, both healthy at Step 0) collapses to zero successful reviewers at runtime, should the fallback reuse the existing `--self-review` inline procedure, or a separate new mechanism?
- **Resolution**: Reuse the existing `--self-review` procedure (`self-review.md`) as-is: same inline main-agent review, same artifacts (`self-review-accepted.md`, tally), same commit route. A runtime both-down collapse automatically enters that same code path instead of stalling as `panel-failed`.
- **Source**: default (AskUserQuestion timed out after 60s with no response; recommended option auto-applied)

## Decision 3: /review self-review scope depth
- **Question**: Standalone /review has no existing self-review scaffold. Should this issue build a full main-agent self-review authoring pass for /review, or a lighter warn-and-proceed response?
- **Resolution**: Build a full self-review pass for /review, modeled on /implement's `self-review.md`: main agent reads the diff/description directly and writes `findings.md` itself when the panel collapses to zero reviewers.
- **Source**: default (AskUserQuestion timed out after 60s with no response; recommended option auto-applied)

## Decision 4: /design plan self-review revision authority
- **Question**: For /design Step 3, when a plan-review round collapses to zero surviving reviewers, should main-agent self-review directly revise `plan.txt` in place, then continue through today's existing bypass destination (Step 3b -> Step 4 -> Gate C, skipping Gate B)?
- **Resolution**: Yes. Main agent re-examines `plan.txt` against the codebase, revises it directly (same authority as Gate-A-reentry Round 2 direct plan revision), prints a loud warning, then proceeds via the existing bypass path with no separate findings-to-apply list.
- **Source**: default (AskUserQuestion timed out after 60s with no response; recommended option auto-applied)

## Decision 5: Trigger condition scope
- **Question**: Should the new self-review fallback trigger only when Step 0 reported both tools healthy (`DEGRADED=false`), or whenever zero reviewers survive at the review stage regardless of Step 0 history (e.g., also covering one-down-continue-then-sole-survivor-also-fails)?
- **Resolution**: Trigger on the mechanical "zero reviewers survived" signal alone (today's `degraded-empty-collector` for /design; the zero-successful-launched-output coverage-gate branch of `panel-failed` for /review and /implement Step 5), regardless of Step 0 history. Avoids threading Step-0 health state through to the round-result layer for no behavioral difference in the common case.
- **Source**: codebase (stated assumption, not asked; low-stakes simplification consistent with minimal-change bias)

## Decision 6: Run-log/audit-tooling depth
- **Question**: Should this issue also extend `audit_runs.py` / `final_report.py` / `fluff-analysis.py` classification to recognize the new /design and /review self-review-substitute paths, mirroring the existing `/implement --self-review` tally machinery?
- **Resolution**: Out of scope for this issue. The loud warning already lands in each skill's committed `execution-issues.md` (`Warnings`), giving basic traceability. Deeper analytics/audit classification for the new paths is deferred as a follow-up; file via Step 5b OOS if reviewers flag it as necessary.
- **Source**: codebase (stated assumption, not asked; keeps this change scoped to the two behaviors named in the issue's acceptance criteria)
