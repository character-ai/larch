## Goal
Remove diagrams from git run logs in /implement; continue posting diagrams to the tracking issue only.

## Goal
Remove the larch-log.sh write --batch diagrams calls from /implement so diagrams are no longer saved to git run logs, while keeping tracking-issue-summary.sh upsert-summary calls so diagrams still get posted to the tracking issue.

## Implementation Plan

### Files to modify

1. skills/implement/SKILL.md:
   - In the "single source of truth" description (~line 384): remove "diagrams" from the list
   - In the batch mapping table (~line 639): remove the "Step 7a | diagrams" row
   - In the design-only path (~line 852): remove the `larch-log.sh write --batch diagrams` call; keep the tracking-issue upsert comment
   - In Step 7a "Larch-log batch — `diagrams`" section (~line 1345): rename section to "Diagrams summary comment — `larch:diagrams`", remove the `larch-log.sh write` call, keep only the tracking-issue-summary.sh upsert-summary instruction
   - In the post-/design legal next-actions matrix row "design-only" (~line 823): remove "write `diagrams` batch →" from the permitted next-actions column

2. scripts/larch-log-batches.sh: remove the line `diagrams .md replace mermaid`

3. scripts/larch-log-batches.md: remove `diagrams` from the slug table list

4. scripts/test-larch-logs-batches.sh: remove the three lines testing diagrams (the slug in the list, the extension assertion, the sanitizer assertion)

5. scripts/test-larch-log.sh: remove/update the test that writes to the diagrams batch

6. skills/implement/scripts/post-design-boundary.md: update the design-only `➡️` directive to remove "write diagrams log batch"

7. skills/implement/references/pr-body-template.md: remove "diagrams" from the "rich report content" note

### Testing strategy
Run /relevant-checks which runs pre-commit and agent-lint. The test-larch-logs-batches.sh and test-larch-log.sh are run via make lint / pre-commit.

## Test plan
Run /relevant-checks (pre-commit + agent-lint) after changes. The test-larch-logs-batches.sh tests should pass with diagrams removed; test-larch-log.sh should not test diagrams batch write.
