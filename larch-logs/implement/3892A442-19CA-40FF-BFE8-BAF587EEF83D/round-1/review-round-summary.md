# Review Round 1

- Mode: `diff`
- 4 accepted, 3 rejected (3 exonerated)

## Accepted Findings

### FINDING_1: Stale `--simple` / `--hard` tier flags in plugin description
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-security-output.txt, cursor-specialist-edge-cases-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Severity**: important
- **Concern**: Plan-required update to `.claude-plugin/plugin.json` description was not applied. The shipped marketplace/plugin metadata still advertises removed tier argv (`--simple` alongside `--hard`), while the skill contract is issue-anchored `/design` with tier flag `--hard` only and default SIMPLE. That violates live-surface completeness (zero `--simple` outside exclusions), misleads installers/operators/automation, and leaves the only prominent non–larch-logs JSON surface out of sync with `skills/design/SKILL.md` and `flags.md`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.
  - From cursor-specialist-correctness-output.txt: Address the concern above.
  - From cursor-specialist-testing-output.txt: Address the concern above.
  - From cursor-specialist-security-output.txt: Address the concern above.
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.
  - From cursor-specialist-plan-fidelity-output.txt: Address the concern above.


### FINDING_2: Structure harness does not pin tier retirement (resolution, default reason, absent gates)
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt
- **Severity**: latent
- **Concern**: `scripts/test-design-structure.sh` pins default SIMPLE and approval-gates cleanup but not **Tier resolution**, the default-tier `write-run-params` reason string (`default tier: SIMPLE (no --hard)`), or absent retired strings (**Tier gate**, `cancelled-tier-gate`, tier `AskUserQuestion`). Step 0b could regress to an interactive tier gate or argv `tier: --simple` while existing contains/absent checks still pass.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.
  - From cursor-specialist-correctness-output.txt: Address the concern above.
  - From cursor-specialist-testing-output.txt: Address the concern above.


### FINDING_4: Arg-hint structure test allows `[--simple|--hard]` regression
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: At `scripts/test-design-structure.sh:33`, the argument-hint check only requires substring `[--hard]`. Restoring `[--simple|--hard]` on that line would still pass CI.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.


### FINDING_7: Disallowed `--simple` parsed after Step 0a despite “before Step 0” prose
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: important
- **Concern**: `skills/design/SKILL.md` documents disallowed-flag abort before Step 0 with no `DESIGN_TMPDIR`, but `/design --simple <issue>` runs session-setup in Step 0a then aborts in Step 0b, leaving an ambiguous cleanup contract.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.


