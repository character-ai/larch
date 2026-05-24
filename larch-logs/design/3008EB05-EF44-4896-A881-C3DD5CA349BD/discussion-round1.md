## Decision 1: Granularity of literal-anchor assertions
- **Question**: Whole-file grep -Fq, or section-scoped via existing `<!-- step:N -->` block extraction?
- **Resolution**: Section-scoped — extract Step 3 block from SKILL.md and Gate C block from approval-gates.md before greping for the literal headers.
- **Source**: user
