## Proposed Design Outline

### Goals
- Remove verbatim Competition notice blockquote and Voter prompts section from `plan-review.md`, replacing each with a one-line pointer to the `python/cli.py render` verbs that already emit them
- Demote `## Collecting External Reviewer Results`, `## Voting Panel launch-order and tally`, and the prose in `## Finalize Plan Review` to short loop-internal notes (no orchestrator action needed)
- Keep the semantic-dedup judgment rule, FINDING_N / OOS_N byte-preserved templates, voter line format (MAV reference), and MAV section

### Non-goals
- Do not change `python/rendering.py` or any Python implementation
- Do not reorganize sections or merge/rename headers — surgical edits only
- Do not change the `Track Rejected Plan Review Findings` section, `Single-pass review`, `Ballot file handling`, `Deferred main-agent adjudication`, or `Related: decomposition panel`

### Approach sketch
- Edit `skills/design/references/plan-review.md`: replace blockquotes/long prompts with pointers; compress three loop-internal sections to short notes; keep FINDING_N/OOS/`<READABILITY_STYLE>` line intact
- Edit `skills/design/SKILL.md` line 570: remove "the Competition notice blockquote" from the normative-source description
- Edit `skills/shared/review-acceptance-rubric.md` and `skills/shared/oos-acceptance-rubric.md`: update their pointer lines about plan-review.md

### Surfaces in scope
- `skills/design/references/plan-review.md` (primary)
- `skills/design/SKILL.md` (one-line update)
- `skills/shared/review-acceptance-rubric.md` (one-line update)
- `skills/shared/oos-acceptance-rubric.md` (one-line update)

### Open questions
- None.
