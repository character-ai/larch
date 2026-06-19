## Decision 1: Strip method — neutral token, not omission
- **Question**: Remove the `- **Reviewer**:` line entirely (omission) or keep it with a neutral token?
- **Resolution**: Keep the `- **Reviewer**:` line in voter-facing and MAV-facing ballots; set its value to a neutral, non-vendor token (`anonymous`). Block structure stays stable for parsers and fixtures. This SUPERSEDES the restored plan body's omission approach (restored plan lines 43-57).
- **Source**: user

## Decision 2: Body-text scrubbing — NO
- **Question**: Should vendor/model substrings (Codex, Cursor, Claude, Anthropic, Sonnet, Opus, Haiku) be scrubbed from finding / OOS body text?
- **Resolution**: No. Strip/neutralize only the `- **Reviewer**:` / `- **Reviewer(s)**:` attribution line. Leave body text unchanged; legitimate `Codex`, `Cursor`, and `Claude` references inside finding/OOS bodies survive. This overrides the issue's "mirror the dialectic vendor-substring scrub" suggestion in the Proposed change section.
- **Source**: user (preserved Q&A, run C7C640C6)

## Decision 3: Skills in scope — all three voting paths
- **Question**: Which voting paths are in scope?
- **Resolution**: All three — `/design` plan review, `/review` code review, and `/implement` Step 5 code review. The MAV (main-agent-vote) fallback on each path reads the same on-disk ballot, so the canonical file must be neutralized before any MAV branch reads it. OOS rows get identical neutral-token treatment.
- **Source**: user (preserved Q&A, run C7C640C6) + codebase

## Decision 4: Empirical measurement pass — out of scope
- **Question**: Is the self-vs-other YES-rate measurement part of this change?
- **Resolution**: No. The empirical measurement is a follow-up comment, not part of this change.
- **Source**: user (preserved Q&A, run C7C640C6)

## Decision 5: Scoring unaffected — proposer map out of band
- **Question**: How is proposer attribution retained for scoring when ballots are neutralized?
- **Resolution**: Proposer attribution is retained out of band in a `proposer-map.tsv` sidecar. The tally reads it so `findings-classification.tsv`, the Reviewer Competition Scoreboard, and accepted/rejected/OOS artifacts keep correct proposer labels. Tallies fall back to `voting.reviewer_for_block` when the sidecar is absent (legacy ballots and direct CLI callers still work). Scores match pre-change expectations for equivalent votes.
- **Source**: user (preserved Q&A, run C7C640C6) + codebase (`python/voting.py:185` `reviewer_for_block`)

## Decision 6: Hard constraints to preserve
- **Question**: What existing behavior must not break?
- **Resolution**: Keep `voting.reviewer_for_block` unchanged for compatibility. Keep `no self-voting exclusion` documented (the structural mitigation is neutralized ballots, not voter exclusion). Sidecar write failure is a hard error before voter dispatch — never launch voters with an un-neutralized ballot. Strip/neutralize only AFTER aggregation and prune (do not anonymize input to `aggregate-findings`, which still needs reviewer labels). Post-vote artifacts (accepted/rejected/OOS) restore the original reviewer line from the sidecar for audit and issue filing.
- **Source**: user (preserved Q&A, run C7C640C6) + codebase
