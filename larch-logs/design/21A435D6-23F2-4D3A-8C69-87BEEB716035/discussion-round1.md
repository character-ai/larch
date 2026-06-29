## Decision 1: Always-loaded classification method
- **Question**: How should the closure walker classify references as always-loaded vs conditional?
- **Resolution**: Text inference from SKILL.md. A directive is conditional when the portion of the line before the MANDATORY marker contains "If ", "When ", "only if", "only when", or the line starts as a conditional bullet item.
- **Source**: user

## Decision 2: Justification token for growth-gate bypass
- **Question**: What does the operator do to unblock the lint when they intentionally grow SKILL.md?
- **Resolution**: Updating the baseline file IS the token. If the baseline JSON is also modified in the same commit (i.e., run `python/cli.py lint skill-closure-growth --write` and commit), the lint passes. Mirrors the complexity-baseline.json pattern.
- **Source**: user

## Decision 3: Walker depth
- **Question**: Does the closure walker recurse into referenced files for sub-references?
- **Resolution**: No. Closure = SKILL.md lines + lines of every file directly referenced by MANDATORY READ ENTIRE FILE from SKILL.md. Single level only, as stated in the issue.
- **Source**: codebase (issue statement: "each SKILL.md plus every reference it MANDATORY — READ ENTIRE FILE s")

## Decision 4: Token estimation
- **Question**: How to estimate tokens from line counts?
- **Resolution**: Characters / 4 (standard approximation for the Claude tokenizer). No external tokenizer dependency.
- **Source**: codebase (no tokenizer lib present; standard rule-of-thumb)
