# Discussion Round 1

## Decision 1: Near-miss heading mapping
- **Question**: Should near-miss heading names (`Problem`, `Evidence`) map onto canonical sections (e.g. `Problem`->`summary`)?
- **Resolution**: Out of scope. Ship the minimal h2-h4 + fence-state fix only. Near-miss mapping stays a separate follow-up.
- **Source**: user

## Decision 2: Heading depth
- **Question**: Should `_HEADING_RE` widen to h2-h4 only, or also include h5+?
- **Resolution**: h2-h4 only. Widen to `#{2,4}`. Covers every body observed in the 2026-07-11 run.
- **Source**: user

## Decision 3: Existing h2/h3 fixtures must stay byte-identical
- **Question**: Does widening the regex and adding fence-state tracking perturb existing structured digests?
- **Resolution**: Hard constraint. Widening `{2,3}` to `{2,4}` only adds h4 matches, so h2/h3 behavior is unchanged outside fences. The fence-state fix must skip heading matches inside fenced code only; existing h2/h3 fixtures must remain byte-identical.
- **Source**: codebase

## Decision 4: Root-cause first-word dedup preserved
- **Question**: Does matching `#### Root cause` create a second `root cause` section?
- **Resolution**: No. `_pick_sections` dedups by first word (`seen_roots`), so `root cause` maps to a single section regardless of heading level. `_split_sections` uses the normalized name as a dict key, so duplicate headings collapse. Widening the regex does not change this.
- **Source**: codebase

## Non-goals
- Near-miss heading-name mapping (`Problem`->`summary`, etc.).
- h5 and deeper heading support.
