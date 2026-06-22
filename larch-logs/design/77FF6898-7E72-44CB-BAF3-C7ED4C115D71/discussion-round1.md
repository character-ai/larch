## Decision 1: Item detail level
- **Question**: What content to show per execution issue/warning entry?
- **Resolution**: Bold label text only (no raw diagnostic body). Collapses identical labels with ×N count.
- **Source**: user

## Decision 2: Deduplication
- **Question**: Should repeated identical entries be collapsed?
- **Resolution**: Yes — group identical bold labels, show "×N" count suffix.
- **Source**: user

## Decision 3: Assessment origin
- **Question**: Is the materiality assessment LLM-generated or copied from diagnostic text?
- **Resolution**: LLM-generated — one batched Claude call (Haiku model) per category at final-summary time.
- **Source**: user

## Decision 4: Scope
- **Question**: Which skill summaries get the enhancement?
- **Resolution**: Both /design (python/design_summary.py) and /implement (python/final_report.py) final summaries.
- **Source**: codebase

## Decision 5: Graceful degradation
- **Question**: What if the LLM assessment call fails or times out?
- **Resolution**: Show labels without assessments — the section still renders, assessments become empty or "unavailable".
- **Source**: codebase convention (existing graceful-degrade patterns)
