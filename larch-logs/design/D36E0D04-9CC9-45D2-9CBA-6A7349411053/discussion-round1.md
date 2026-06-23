## Decision 1: Per-reviewer OOS cap value
- **Question**: What numeric cap should we enforce on per-reviewer OOS proposals?
- **Resolution**: 3 per reviewer.
- **Source**: user

## Decision 2: Cap implementation location
- **Question**: Where should the per-reviewer cap be enforced — plan_review_round.py or review_aggregate.py?
- **Resolution**: In `plan_review_round.py:_compose_findings_from_collector` (at collection time per slot, before findings are combined). Keeps per-reviewer identity unambiguous.
- **Source**: user

## Decision 3: Apply cap to both /design and /implement paths
- **Question**: Does the cap apply to /implement Step-5 code review as well as /design plan review?
- **Resolution**: Both paths. Cap in `plan_review_round.py:_compose_findings_from_collector` (design) AND in `review_pipeline.py:collect_findings` (implement). The measured waste (430 OOS, 80.2% rejected) is primarily from /implement.
- **Source**: user

## Decision 4: Rubric tightening and reviewer prompt changes
- **Question**: What kind of rubric tightening and should a numeric cap be added to reviewer prompts?
- **Resolution**: (a) Tighten `oos-acceptance-rubric.md` by adding two or three "automatic NO" heuristics under the backlog-relative question (style nits, speculative portability, polish items). (b) Add explicit "report at most 3 OOS observations" instruction to `skills/shared/reviewer-templates.md` (and regenerate generated agents; hand-edit hand-maintained agents).
- **Source**: user
