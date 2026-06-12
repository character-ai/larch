### OOS_1: [OUT_OF_SCOPE] SECURITY.md emergency gate count stale vs SKILL.md and runtime
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt, codex-specialist-edge-cases-output.txt, cursor-specialist-testing-output.txt
- **Severity**: latent
- **Concern**: The emergency downgrade paragraph in `SECURITY.md` still says exactly three Preflight gates are bypassable and that emergency does not suppress the admission gate, while `skills/implement/SKILL.md` documents four (including `missing-designed-prefix`) and `scripts/implement-preflight.sh` allows `--emergency` to continue after `ADMISSION_RESULT=missing-designed-prefix`. Operators reading `SECURITY.md` as authority may underestimate emergency admission bypass scope, especially alongside new `--merge` compatibility text.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Separate doc-alignment issue.
  - From cursor-specialist-edge-cases-output.txt: Reconcile gate count and list with skills/implement/SKILL.md in a follow-up doc patch.
  - From codex-specialist-edge-cases-output.txt: Update the emergency downgrade wording in a separate scoped patch to include or explicitly qualify the missing-designed-prefix admission bypass.


