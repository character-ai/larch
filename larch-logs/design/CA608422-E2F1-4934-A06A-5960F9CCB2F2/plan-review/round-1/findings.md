### FINDING_1:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: important
- **Focus area**: security
- **Location**: SECURITY.md:105,127
- **Concern**: Part 2 omits SECURITY.md though AGENTS.md requires updates for security-relevant routing changes; line 105 still documents a Cursor-first Step 0 reversal and Cursor → Codex → Claude, and line 127 repeats that contract plus Phase 4 (#2738) undoing #2756. Scenario: After the flip, the canonical security doc contradicts live `phase_coder_select` / fixer behavior; operators may mis-pin `--coder` or misread sandbox delegation scope
- **Proposed resolution**: make SECURITY.md an explicit Part 2 file: rewrite the `/implement` Step 0 paragraph on line 105 (order, #3337 vs #2738 narrative, explicit-pin guidance) and replace line 127; extend the stale-prose grep in Failure modes to include SECURITY.md

### FINDING_2:
- **Reviewer(s)**: Cursor-Edge, Cursor-Pragmatic
- **Severity**: important
- **Focus area**: security
- **Location**: SECURITY.md:127
- **Concern**: Plan omits SECURITY.md while flipping omitted---coder routing back to Codex-first. Scenario: Post-merge SECURITY.md still says Cursor → Codex → Claude, describes Phase 4 as reversing to Cursor-first, and tells operators to use --coder=codex for Codex-first — inverted vs runtime
- **Proposed resolution**: Add a minimal SECURITY.md:127 sync (Codex-first omitted --coder; drop or rewrite the Phase 4 reversal paragraph) per AGENTS.md security-doc convention

### FINDING_3:
- **Reviewer(s)**: Cursor-dyn-doc-order-drift
- **Severity**: important
- **Focus area**: correctness
- **Location**: docs/external-reviewers.md:103
- **Concern**: CI / checks recovery row still documents Cursor→Codex→Claude. Scenario: Canonical routing table contradicts codex-first ship-pr.sh after Part 2
- **Proposed resolution**: Add docs/external-reviewers.md to Part 2 doc-sync (Codex→Cursor→Claude) or defer with R-style note
