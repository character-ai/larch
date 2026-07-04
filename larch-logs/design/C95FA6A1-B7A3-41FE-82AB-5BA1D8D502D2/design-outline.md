## Proposed Design Outline

### Goals
- Compress fixed instruction prose ("scaffold") in the implement no-agent specialist builder and the shared voter prompt builder, using #6158's scaffold/payload columns to produce a measured, honest byte drop.
- Preserve every parser-facing token byte-for-byte: finding/OOS anchors, `YES`/`NO`, the severity set, `ELIGIBLE_VOTERS`/`EFFECTIVE_VOTERS`/`vN_tool` keys, and the anti-format directive.

### Non-goals
- Static `agents/*.md` specialist files (round XI's territory) and the design plan-review / aggregator builders (sibling #6159, #6161).
- New scaffold-byte ratchets, panel topology changes, dispatch/voting logic changes, or a payload-dedup redesign (explicitly deferred per the #6166 umbrella).

### Approach sketch
- Trim/fold the fixed prose strings inside the no-agent specialist prompt path in `review_dispatch_panel.py` and inside `render_voter_main` (plus its static-text helpers) in `rendering.py`, following the #5979 "delete and fold, don't rewrite" style.
- Re-render affected prompts with `--payload-bytes-output` (or read `panel-prompt-sizes.tsv`) before/after to capture the scaffold-byte delta the acceptance criterion requires.
- Run the rendering/voting/review-pipeline test suites plus `lint skill-closure-growth --skill panel-tier` as a safety net.

### Surfaces in scope
- `python/larch/review/review_dispatch_panel.py`
- `python/larch/rendering/rendering.py` (`render_voter_main` and its static-text helpers)
- Associated rendering/review-pipeline test files

### Open questions
- How to operationalize "vote parse rate unchanged on a live run" (automated dispatch vs. monitoring the next production runs) — the plan will propose a concrete approach for reviewers to weigh in on.
