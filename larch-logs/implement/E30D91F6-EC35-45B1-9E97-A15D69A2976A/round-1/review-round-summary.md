# Review Round 1

- Mode: `diff`
- Accepted findings: 6
- Rejected findings: 1
- Exonerated findings: 5
- Neutral findings: 2

## Accepted Findings

### FINDING_1: Progress Reporting still documents nested /design breadcrumb behavior
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-security-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-edge-cases-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Concern**: After nested-mode / `SESSION_ENV_PATH` removal, `skills/design/SKILL.md` (Progress Reporting, ~34–36) still tells orchestrators to prepend parent context “when nested,” which contradicts standalone-only /design and can be read as supported nested transport or optional nested mode distinct from `STEP_NUM_PREFIX` / `PARENT_SKILL_PATH` env prefixes.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-security-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-edge-cases-output.txt, cursor-specialist-plan-fidelity-output.txt: Address the concern above.

---


### FINDING_11: CLAUDE_PLUGIN_ROOT export depends on loader expansion; weak static detection
- **Reviewer(s)**: cursor-specialist-testing-output.txt, cursor-specialist-security-output.txt
- **Concern**: `skills/design/SKILL.md` export of `CLAUDE_PLUGIN_ROOT` relies on the skill loader expanding `${CLAUDE_PLUGIN_ROOT}` inside quotes before Bash; A5 cannot catch missing expansion, so failures surface late as broken paths; security angle: empty or wrong value could resolve `scripts/...` under an unintended root.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Document manual /design smoke in PR; consider future render-time self-check if tooling allows.
  - From cursor-specialist-security-output.txt: Keep A5 pin; add post-export non-empty guard with explicit error exit or document fatal misconfiguration in SECURITY.md writer contract.

---


### FINDING_14: Implement / ship-pr still read IMPLEMENT_TMPDIR oos-accepted-design.md while tally no longer mirrors parent tmpdir
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Concern**: `skills/implement/SKILL.md` and `scripts/ship-pr.sh` still treat `IMPLEMENT_TMPDIR/oos-accepted-design.md` as an input; if tally no longer materializes that path from standalone design, Step 9a.1 / OOS combine can be silently empty vs older nested-era expectations.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.

---


### FINDING_2: CHANGELOG 41.0.0 understates co-shipped /design and tally/test surface
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Concern**: The 41.0.0 section emphasizes round-trip removal but omits or underplays /design nested-mode cleanup, tally/OOS contract changes, and related harness/assertion updates shipped in the same bump, weakening traceability for operators and automation that read only the CHANGELOG.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-plan-fidelity-output.txt: Address the concern above.

---


### FINDING_6: voting-protocol still maps design OOS to IMPLEMENT_TMPDIR after design-local layout change
- **Reviewer(s)**: cursor-specialist-correctness-output.txt
- **Concern**: `skills/shared/voting-protocol.md` (around 277) still implies design/review-accepted OOS for voting lives under `$IMPLEMENT_TMPDIR`; post parent-tmpdir handoff / #2588-style split, design OOS is written under `$DESIGN_TMPDIR`, so readers may expect `IMPLEMENT_TMPDIR/oos-accepted-design.md` from plan review incorrectly.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Address the concern above.

---


### FINDING_9: Check 13 comment still describes parent /implement OOS handoff removed from tally-plan-review
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Concern**: `scripts/test-design-structure.sh` (around 4269–4272) comment still references parent `/implement` OOS handoff via `plan-review.md` / parent tmpdir wiring that `tally-plan-review.sh` no longer implements; misleads maintainers searching for obsolete paths.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.

---


