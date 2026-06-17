### OOS_1:
- **Description**: [SCOPE-REDUCTION] Port dead clarify-hard-halt wrapper despite no SKILL fence caller. Scenario: No runtime path invokes the helper after cutover; design-clarify.sh already owns failed-clarify staging
- **Reviewer**: Cursor-Innovation
- **Severity**: latent
- **Focus area**: architecture
- **Location**: skills/design/scripts/design-step0-clarify-hard-halt.md:6-13
- **Phase**: design

### OOS_2:
- **Description**: [SCOPE-REDUCTION] Register standalone design step0-parse CLI verb. Scenario: SKILL forbids a separate parse fence; only step0-session inlines parse, so a public verb and launcher allowlist slot add surface without a caller
- **Reviewer**: Cursor-Innovation
- **Severity**: latent
- **Focus area**: architecture
- **Location**: skills/design/SKILL.md:262
- **Phase**: design

