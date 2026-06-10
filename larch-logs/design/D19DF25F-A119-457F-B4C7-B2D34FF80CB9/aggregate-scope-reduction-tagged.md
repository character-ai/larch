### FINDING_2:
- **Reviewer(s)**: Codex-Edge
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: python/logging_util.py:62-66; scripts/lib-quiet.md:41-44
- **Concern**: [SCOPE-REDUCTION] Proposed DESIGN_TMPDIR-before-IMPLEMENT_TMPDIR order over-changes quiet log precedence. Scenario: The documented shell quiet order prefers IMPLEMENT_TMPDIR before DESIGN_TMPDIR; globally flipping Python precedence can send implement-side Python logs into a design tmpdir when both vars are present
- **Proposed resolution**: Add DESIGN_TMPDIR only as a fallback before TMPDIR while preserving existing IMPLEMENT_TMPDIR precedence

### FINDING_1:
- **Reviewer(s)**: Codex-Pragmatic
- **Severity**: latent
- **Focus area**: risk-integration
- **Location**: python/logging_util.py:62-69; scripts/lib-quiet.sh:22-31
- **Concern**: [SCOPE-REDUCTION] Planned DESIGN_TMPDIR-before-IMPLEMENT_TMPDIR priority broadens the fix and breaks the existing quiet-log priority. Scenario: An implement or ship-pr Python process that inherits both a valid IMPLEMENT_TMPDIR and a stale valid DESIGN_TMPDIR would write quiet logs under the design directory, diverging from lib-quiet and splitting implement diagnostics
- **Proposed resolution**: Keep IMPLEMENT_TMPDIR first and add DESIGN_TMPDIR only as a fallback before TMPDIR; adjust the planned logging_util test to cover DESIGN fallback when IMPLEMENT is unset rather than design-over-implement priority

### FINDING_1:
- **Reviewer(s)**: Codex-dyn-api-callers
- **Severity**: latent
- **Focus area**: risk-integration
- **Location**: python/logging_util.py:62-66; scripts/lib-quiet.sh:26-35
- **Concern**: [SCOPE-REDUCTION] DESIGN_TMPDIR-before-IMPLEMENT_TMPDIR changes global quiet-log precedence. Scenario: Current Python quiet_init uses IMPLEMENT_TMPDIR when set, and bash quiet defaults also check IMPLEMENT_TMPDIR before DESIGN_TMPDIR; the plan's proposed order sends Python child logs to DESIGN_TMPDIR whenever both env vars exist, which is broader than the design-log publish fix.
- **Proposed resolution**: Preserve IMPLEMENT_TMPDIR precedence and add DESIGN_TMPDIR only as a fallback before TMPDIR; adjust the proposed logging_util test to cover DESIGN_TMPDIR when IMPLEMENT_TMPDIR is unset, not preference over implement.
