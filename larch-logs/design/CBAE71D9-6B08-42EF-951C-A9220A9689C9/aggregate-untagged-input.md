### FINDING_1:
- **Reviewer(s)**: Codex-Innovation
- **Severity**: minor
- **Focus area**: correctness
- **Location**: docs/configuration-and-permissions.md:161-163
- **Concern**: The planned `--coder` description conflates explicit external-tool overrides with `--coder claude`. Scenario: An operator using `--coder claude` would not retain external tools as fallbacks because the current dispatcher selects Claude directly, so the documentation would describe behavior that does not occur
- **Proposed resolution**: Describe `--coder codex` and `--coder cursor` as external-tool overrides with the other external tool and Claude as fallbacks; document separately that `--coder claude` selects Claude directly

### FINDING_2:
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: minor
- **Focus area**: correctness
- **Location**: docs/configuration-and-permissions.md:196
- **Concern**: Plan omits revising the stale LARCH_CURSOR_MODEL bullet that conflates Step 2 with fix/voter defaults. Scenario: After the MODERATE Step 2 grok-4.5 default lands, line 196 still says voters and fix/coder roles share composer-2.5 or LARCH_CURSOR_MODEL, which contradicts the new Step 2 MODERATE default and blurs the global-versus-tier distinction the plan requires
- **Proposed resolution**: Add an explicit task under the LARCH_CURSOR_MODEL update to revise or remove line 196: split Step 2 coder defaults from voter/fix/review-panel defaults, and qualify the When-not-set composer-2.5 bullet as the global fallback for roles without a difficulty-specific Step 2 map

### FINDING_3:
- **Reviewer(s)**: Codex-Pragmatic
- **Severity**: minor
- **Focus area**: correctness
- **Location**: docs/configuration-and-permissions.md:161-164
- **Concern**: 1. The planned `--coder` wording is too broad and conflicts with the existing `--coder=claude` behavior. Scenario: `--coder=claude` selects Claude directly; it does not keep the two external tools as fallbacks, so the proposed documentation could mislead operators about the override contract
- **Proposed resolution**: Limit the fallback wording to `--coder=codex` and `--coder=cursor`, and state separately that `--coder=claude` selects Claude directly

### FINDING_4:
- **Reviewer(s)**: Codex-Requirements
- **Severity**: minor
- **Focus area**: correctness
- **Location**: docs/configuration-and-permissions.md:161-163
- **Concern**: Document the `--coder` override semantics separately for external choices and `--coder claude`. Scenario: `--coder claude` selects Claude directly in the current dispatcher and does not retain Codex or Cursor as fallbacks, so the planned wording would misdocument an accepted CLI mode
- **Proposed resolution**: Clarify that `--coder codex` or `--coder cursor` reorders the external tools and keeps the remaining tools as fallbacks, while `--coder claude` selects Claude directly
