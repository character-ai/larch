## Proposed Design Outline

### Goals
- Cut real token count of `skills/design/SKILL.md` (currently 30,131 estimated tokens / 705 lines) by tightening prose density, targeting -10% or better, measured by the new byte/token ratchet (not line count).
- Collapse the Step 3 plan-review mega-citation (line 382, repeats `plan_review.py` / `test_plan_review.py` 4+ times) and other dense citation paragraphs (e.g. the end-of-file "Plan-helper contracts" list) to one mention per fact, while keeping every agent-lint S030/S017 literal path pin intact.
- Regenerate `python/skill-closure-baseline.json` so the byte/token ratchet's committed baseline matches the shrunk file (required by `test_committed_baseline_matches_fresh_scan`).

### Non-goals
- No control-flow, step-sequencing, gate, or KV-routing changes.
- No removal of load-bearing compaction-resilience duplication (repeated NEVER / anti-halt / continuation blocks stay verbatim).
- No cross-file dedup or pointerization of shared boilerplate (that is in-flight issue #5883's scope); this pass is in-place density only within `SKILL.md` itself.

### Approach sketch
- Apply `readability-style.md` axes (Strunk & White, dyslexia-friendly, brevity, no em dashes) paragraph-by-paragraph across the whole file.
- Tighten the line-382 mega-citation and the "Plan-helper contracts" bullet list: state each fact and each S030-pinned literal path once; drop restatement.
- Leave the exact Step 0a "presence keys only for the immediate degraded-tools gate; binary-found keys for later vendor launch guards" sentence untouched: in-flight issue #5883 already has a reviewed plan replacing it with a citation, so editing it here would conflict.
- Preserve every `<!-- step:N -->` anchor, step banner, fenced bash block, KV contract name, flag name, and NEVER-block byte-for-byte.
- Regenerate `python/skill-closure-baseline.json` via `python3 python/cli.py lint skill-closure-growth --write` after the prose edit.

### Surfaces in scope
- `skills/design/SKILL.md` (whole file, prose density only).
- `python/skill-closure-baseline.json` (mandatory metadata refresh, no manual edits).

### Open questions
- None.
