## Goal
Add /review-and-fix to skill catalog/topology and fix stale SKILL.md line refs

## Implementation Plan

Goal: Two doc-only cleanup tasks after review-and-fix overhaul (PR #2139).

### Task 1 — Add /review-and-fix to README.md, docs/skills.md, topology.tsv, docs/topology.md

Files to modify:
- README.md: insert skill-catalog HTML block after /review block (line 117), before /set-up-forked-open-source-repo block
- docs/skills.md: insert ## /review-and-fix section between ## /review and ## /set-up-forked-open-source-repo
- skills/shared/topology.tsv: append one row: implement.review_and_fix.panel_hard<TAB>6 Cursor specialists + 6 Codex specialists<TAB>Hard panel<TAB>skills/review/scripts/dispatch-panel.sh
- docs/topology.md: regenerate via `bash scripts/generate-topology-docs.sh`

### Task 2 — Fix stale SKILL.md line references in docs/external-reviewers.md

File to modify:
- docs/external-reviewers.md line 30: replace `skills/review/SKILL.md:146-148, 177-179` with `scripts/dispatch-plan-voters.sh`
- docs/external-reviewers.md line 32: replace `skills/review/SKILL.md:160-163, 186-190` with `scripts/launch-review.sh`

Verification:
- Run `bash scripts/generate-topology-docs.sh --check` to confirm topology.md sync
- Run relevant-checks (pre-commit + agent-lint) to pass CI

Edge cases:
- topology.tsv value "6 Cursor specialists + 6 Codex specialists" must appear literally in skills/review/scripts/dispatch-panel.sh (confirmed: line 187)
- No line-number references allowed in prose per drift-prone-prose-in-docs.md rule

## Test plan
(no test plan section in plan-file)
