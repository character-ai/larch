## Decision 1: Valid routing destinations
- **Question**: Is AGENTS.md a valid destination, or strictly (hook / lint / ARCHITECTURAL_GUIDELINES.md / ARCHITECTURAL_INVARIANTS.md)?
- **Resolution**: Strictly the four listed categories, with BASH_AUTHORING.md also accepted. AGENTS.md is NOT a valid destination for new content.
- **Source**: user

## Decision 2: Already-mechanically-enforced rules
- **Question**: For rules covered by existing lint or hook (agent-lint S017, markdownlint MD038, block-submodule-edit.sh), should we delete and add prose elsewhere, or just delete?
- **Resolution**: Delete the rule file only. No prose duplication needed.
- **Source**: user

## Decision 3: gh-body-file.md destination and treatment
- **Question**: Where does the large gh-body-file.md rule go?
- **Resolution**: BASH_AUTHORING.md, slimmed down to the minimum useful content.
- **Source**: user

## Decision 4: AGENTS.md-covered rules
- **Question**: python-first-scripts.md is already covered in AGENTS.md. Delete or route?
- **Resolution**: Delete. Content is already documented in AGENTS.md; no new routing destination needed.
- **Source**: codebase
