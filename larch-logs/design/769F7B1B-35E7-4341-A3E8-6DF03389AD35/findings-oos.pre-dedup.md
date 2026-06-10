### OOS_1:
- **Description**: Prose still names redact-secrets.sh inside create-one.sh. Scenario: Operator/security docs stale after port; no runtime break if sweep catches it
- **Reviewer**: Cursor-Pragmatic
- **Severity**: latent
- **Focus area**: correctness
- **Location**: skills/design/SKILL.md:1755
- **Phase**: design

### OOS_1:
- **Description**: Retiring `test-blocked-by-issue.sh` and `test-intra-batch-deps.sh` drops structural CI guards on `--blocked-by-issue` / intra-batch SKILL prose, with no pytest replacement.. Scenario: These harnesses grep `skills/issue/SKILL.md` for load-bearing `--blocked-by-issue` documentation. After deletion, SKILL prose can drift without CI signal; `lint-retired-scripts` will not catch bare `add-blocked-by.sh` mentions.
- **Reviewer**: Cursor-Requirements
- **Severity**: latent
- **Focus area**: risk-integration
- **Location**: skills/issue/SKILL.md:Step 6 / skills/issue/scripts/test-blocked-by-issue.sh
- **Phase**: design

