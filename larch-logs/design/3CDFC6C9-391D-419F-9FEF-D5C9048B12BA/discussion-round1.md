## Decision 1: L2 parser ownership and shipping order
- **Question**: Should L6 author the shared parser, or block on L2?
- **Resolution**: Block L6 on L2 — L6 will not ship until L2 (#2671) lands. L6 design assumes `scripts/parse-judge-vote-and-rating.sh` exists when L6 implementation starts and reuses it as-is.
- **Source**: user

## Decision 2: Backward compat for FINDING_N: vote line
- **Question**: When a judge omits or malforms rating tokens, treat as parse error or fall back to UNCERTAIN=true defaults?
- **Resolution**: Lenient — a vote line is valid if it has a recognized YES|NO|EXONERATE token. Missing or unparseable rating tokens become UNCERTAIN=true with empty values for the other axes. JUDGE_ERROR still triggers only on missing/unrecognized vote token (existing behavior).
- **Source**: user

## Decision 3: In-scope consumer flows
- **Question**: Does the per-round TSV cover both `/implement` Step 5 review rounds AND standalone `/review --diff` rounds?
- **Resolution**: Both — issue body explicitly enumerates `$IMPLEMENT_TMPDIR/round-<N>/findings-classification.tsv` (for /implement review) and `$REVIEW_TMPDIR/findings-classification.tsv` (for standalone /review). Both paths share `dispatch-code-voters.sh` + `tally-code-votes.sh`, so the prompt + TSV-writer changes apply once at the script level.
- **Source**: codebase (skills/review/SKILL.md confirms `/review --diff` is multi-round via wrapper `round_cap=5` loop calling `review-core.sh --round-num`).

## Decision 4: Reconciliation policy
- **Question**: Aggregate the 3-judge ratings or preserve raw?
- **Resolution**: Preserve all 3 raw ratings verbatim per finding (no reconciliation, no majority-vote on ratings). Matches L2's documented policy in the issue body.
- **Source**: issue body (explicit "**None**. Preserve all 3 raw ratings verbatim per finding. Same as L2.")

## Decision 5: TSV coverage scope
- **Question**: Per-finding rows for accepted/rejected/neutral/exonerated only, or also include OOS ballot items?
- **Resolution**: All ballot finding entries — `### FINDING_N:` (in-scope) AND `### OOS_N:` (out-of-scope). Issue body says "All findings on the ballot (accepted / rejected / neutral / exonerated)" and the TSV schema mentions `finding_id` which is the ballot id.
- **Source**: issue body
