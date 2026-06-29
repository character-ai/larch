## Decision 1: Structure-test pins in AGENTS.md
- **Question**: Are any existing tests pinning specific token strings in the files to be edited?
- **Resolution**: `test-implement-anti-polling-rule.sh` pins 7 exact strings inside AGENTS.md's Conventions section. Those strings must survive verbatim.
- **Source**: codebase

## Decision 2: BASH_AUTHORING "Residual Bash after E3" duplication
- **Question**: Can the "Residual Bash after E3" section be removed from BASH_AUTHORING.md since it duplicates AGENTS.md Conventions?
- **Resolution**: Yes — both files are Tier-1a always-loaded, so removing/cross-linking the duplicate in BASH_AUTHORING.md is a density improvement, not a rule deletion.
- **Source**: codebase

## Decision 3: KARPATHY structure tests
- **Question**: Does KARPATHY_CLAUDE.md have any structure test pins?
- **Resolution**: No — it can be freely condensed.
- **Source**: codebase

## Decision 4: CI ratchet scope
- **Question**: Is implementing a CI closure-size ratchet in scope?
- **Resolution**: Yes — include the ratchet in this PR.
- **Source**: user

## Decision 5: KARPATHY/AGENTS Honesty cross-link direction
- **Question**: Which AGENTS.md Honesty bullets overlap with KARPATHY §1?
- **Resolution**: Condense AGENTS.md Honesty bullets that philosophically restate KARPATHY §1 (e.g., "Distinguish observation from inference" restates "State your assumptions explicitly") and replace with a tighter cross-reference pointer.
- **Source**: user
