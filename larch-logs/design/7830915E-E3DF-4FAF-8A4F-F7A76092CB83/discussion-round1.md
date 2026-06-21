# Round 1 — Scope and Hard Constraints

Resolved via Step 1c clarifying questions on issue #4776.

## Decision 1: Where fate adjustment happens
- **Question**: Live tally change vs retroactive-only?
- **Resolution**: Retroactive only. A new analysis reads committed run logs plus current GitHub issue fate and reports a fate-adjusted OOS scoreboard. The live tally keeps the provisional `+1`. Do NOT change `python/voting.py::classify_result` or the live OOS award path. Mirrors `/voter-calibration` and `/fluff-analysis`.
- **Source**: user

## Decision 2: Write / mutation boundary
- **Question**: What may the tool write or mutate?
- **Resolution**: Report only. Print the fate-adjusted scoreboard and write a report artifact (and/or a new section in `/analyze-issues` output). NEVER rewrite committed `larch-logs/*` TSVs. Do NOT add a committed persistent reviewer ledger. Commit nothing automatically.
- **Source**: user

## Decision 3: Fate-to-points policy
- **Question**: How does each realized issue fate map to the OOS point?
- **Resolution**: Dock unfixed/combined to 0. Closed by a fixing/merged PR keeps `+1`. Closed-unfixed (wontfix / not-planned) maps to `0`. Combined-away maps to `0`. Still-open, including stale `[OOS]`, stays provisional (no change yet). No `-1` penalty.
- **Source**: user

## Decision 4: Code reach
- **Question**: How far does the code change extend?
- **Resolution**: Extend `python/analyze_issues.py` (it already fetches issues and computes `reviewer_effectiveness`). Teach `/combine-issues` to durably record which issues it combined away so combined-away fate is unambiguous. This matches the issue's "feed `/analyze-issues` and `/combine-issues` outcomes back" wording.
- **Source**: user

## Decision 5: OOS origin coverage (assumption to confirm at outline)
- **Question**: Does the reconciler cover only `/design` plan-review OOS, or also `/review` code-review OOS?
- **Resolution (assumption)**: Cover filed OOS issues recorded in committed run logs regardless of originating skill, keyed by proposer label plus filed issue URL. Primary evidence and examples come from `/design` (the issue's focus: "27.8% of /design OOS proposals"). Surface this in the Step 1d.7 outline for confirmation.
- **Source**: codebase
