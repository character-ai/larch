### [Plan Review] FINDING_2

### FINDING_2: design_classification bound too late for early Step 0b exits
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Concern**: Approach says tier resolves during flag parsing but Step 0b edits only replace sub-step 5 Tier resolution. Sub-step 4 already-planned ad-hoc Q&A exits before sub-steps 5–6; run-params merges can lack `design_classification` even though default SIMPLE is the product intent.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Innovation: Add to Step 0b item 1: bind design_classification to HARD when --hard is parsed else SIMPLE immediately after public flag parse; keep sub-step 5 as a no-op reaffirmation or drop redundant prose

