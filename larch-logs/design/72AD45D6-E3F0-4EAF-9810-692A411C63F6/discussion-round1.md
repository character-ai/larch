## Decision 1: Scope of changes
- **Question**: Which sections of Step 4 change?
- **Resolution**: Sections 4 (lint rules), 5 (architectural invariants), and 6 (guideline entries); section 7 and the rest of the report are unchanged.
- **Source**: codebase (issue body explicit; section 7 not mentioned)

## Decision 2: Readability preamble
- **Question**: Should the skill-wide readability preamble be modified?
- **Resolution**: No; the carve-out is added inline within Step 4 proposal sections only.
- **Source**: codebase (issue body explicit: "Keep the rest of the report … under the existing brevity style")

## Decision 3: Rule-file text requirement
- **Question**: For invariants classified as `rule`, what is required?
- **Resolution**: Full draft `.claude/rules/*.md` file text — frontmatter `paths:` globs plus the body.
- **Source**: user (issue body explicit)
