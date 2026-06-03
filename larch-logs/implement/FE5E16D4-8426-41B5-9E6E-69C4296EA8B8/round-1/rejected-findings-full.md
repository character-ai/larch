### [rejected] FINDING_10

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_10: risk-integration: scripts/implement-bootstrap.sh:681-710
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [latent] No offline test exercises _phase_coder_implicit PATH availability probing. Swapped codex/cursor branches could regress with only static string pins staying green. Add PATH-stubbed implement-bootstrap --up-to-phase coder cases asserting coder= and coder_fallback= KV output.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_14

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_14: security: docs/installation-and-setup.md:139-140
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: [latent] Documented apiKeyHelper uses echo $ANTHROPIC_API_KEY without quoting. A malicious or malformed ANTHROPIC_API_KEY value (e.g. containing $(cmd) or unescaped quotes) executed when Claude runs apiKeyHelper from *_api aliases could run arbitrary shell commands on the operator machine. Use printf '%s\n' "$ANTHROPIC_API_KEY" in a tiny wrapper script referenced by apiKeyHelper, or document that keys must be shell-safe single-line tokens.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_15

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_15: risk-integration: scripts/ship-pr.sh:2039-2125
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [important] CI fix vendor order ignores Step 0 codex_available; always tries Codex first even when implementer already fell back to Cursor. Probe-failed Codex + healthy Cursor: /implement uses Cursor implementer then CI fix wastes first attempt on Codex before Cursor. Thread session availability into run_ci_fix_vendor tier selection or align base tuple with resolved coder.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=1 EXON=2 JUDGE_ERROR=0

