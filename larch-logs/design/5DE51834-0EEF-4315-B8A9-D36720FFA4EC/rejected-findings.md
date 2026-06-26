### [Plan Review] FINDING_1

### FINDING_1:
- **Reviewer(s)**: Codex-Generic
- **Severity**: important
- **Focus area**: correctness
- **Location**: docs/point-competition.md:123-125; python/plan_review_panel.py:357-359
- **Concern**: [SCOPE-REDUCTION] The planned docs change makes the rounds 2-4 pruning window sound global, but `/design` still hard-skips pruning outside rounds 3-4.. Scenario: After this plan lands, `docs/point-competition.md` would describe conditional spawning as rounds 2-4 for the same scoring surface that includes `/design`, while `python/plan_review_panel.py` returns before filtering unless the plan-review round is 3 or 4.
- **Proposed resolution**: Keep the docs minimum-change: scope the rounds 2-4 wording to `/review` or `/implement` code-review pruning, and leave `/design` documented as rounds 3-4 unless this PR deliberately changes `python/plan_review_panel.py`.

