### [Plan Review] FINDING_3

### FINDING_3:
- **Reviewer(s)**: Codex-Arch
- **Severity**: latent
- **Focus area**: architecture
- **Location**: scripts/render-run-summary.md:8-13, scripts/render-run-summary.sh:214-237
- **Concern**: Plan duplicates the run-summary schema in both caller fallbacks despite render-run-summary being the shared summary source. Scenario: Future schema changes can update the renderer but leave degraded implement/design bodies missing or differently ordered bullets
- **Proposed resolution**: Extract one shared degraded-summary helper or add a renderer mode that bypasses token-cost while reusing the same body-emission logic; keep the absolute last-resort fallback minimal only if the shared helper itself is unavailable


### [Plan Review] FINDING_28

### FINDING_28:
- **Reviewer(s)**: Cursor-dyn-fallback-schema-parity
- **Severity**: nit
- **Focus area**: correctness
- **Location**: skills/design/scripts/render-final-summary.sh:271-302
- **Concern**: Design degraded path is only Stage 2 self-compose (no renderer re-invoke).. Scenario: Implement gets Stage 1 re-invoke; design goes straight to compose on any render failure—acceptable but asymmetrical if failure is transient/env-only.
- **Proposed resolution**: Optional: mirror implement Stage 1 (re-invoke `--skill design` without `COST_ARGS`) before self-compose; not required if compose is complete.


### [Plan Review] FINDING_32

### FINDING_32:
- **Reviewer(s)**: Codex-dyn-fallback-schema-parity
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: scripts/test-render-run-summary.sh:59-65,231-240,242-276; scripts/test-render-run-summary-format.sh:48-53; skills/design/scripts/test-render-final-summary.sh:94-115; Makefile:67-67,254-260,599-600; <TMPDIR>/plan.txt:151-163
- **Concern**: FINDING_4 CI does not currently pin the exact renderer schema before adding hard-coded fallbacks. Scenario: Current CI runs renderer tests, but they grep sentinel/cost/selected bullets and selected design omissions rather than asserting the full ordered bullet list for implement with PR, implement without PR, design approved, and design cancelled. A future renderer schema change could leave the self-composed fallback stale without a loud failure.
- **Proposed resolution**: Add exact ordered schema golden tests or a shared schema fixture/helper consumed by renderer and fallbacks; make fallback tests compare field names and ordering against the canonical renderer contract for the same metadata.


