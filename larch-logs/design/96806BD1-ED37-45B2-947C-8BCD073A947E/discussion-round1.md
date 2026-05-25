## Decision 1: 0-judge fallback (TALLY_PLAN_REVIEW_STATUS=main-agent-vote-required)
- **Question**: When all external voters fail and the main agent casts ballots, what should findings-classification.tsv contain?
- **Resolution**: Write TSV with voting_result populated but all judge rating columns (v1_*/v2_*/v3_*) empty. Uniform file presence; no rating data when no judges produced ratings.
- **Source**: user

## Decision 2: 0-findings round (voting skipped)
- **Question**: When all reviewers report no findings and voting is skipped, what does findings-classification.tsv look like?
- **Resolution**: Write header-only TSV (no data rows) so downstream analytics see one file per round regardless of finding count.
- **Source**: user

## Decision 3: vN slot identity (cross-run per-judge analytics)
- **Question**: How do v1/v2/v3 columns map to specific judges across runs?
- **Resolution**: Sort vN slots alphabetically per row — v1=Claude, v2=Codex, v3=Cursor. Stable across runs even if dispatch order changes. Convention documented in the parser/TSV writer's sibling .md.
- **Source**: user

## Decision 4: Gate C "Re-run review panel" round numbering and TSV file
- **Question**: On Gate C re-runs of Step 3, should the round counter bump or stay at 1; should the TSV be overwritten or versioned?
- **Resolution**: Overwrite $DESIGN_TMPDIR/plan-review/round-1/findings-classification.tsv (current loop driver passes --round-num=1; matches voting-tally.md overwrite behavior). Defer real multi-round semantics to #2677.
- **Source**: user
