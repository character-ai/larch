### OOS_1: [OUT_OF_SCOPE] Thin-wrapper template vs recipe step 4 (accepted plan tension)
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt, cursor-specialist-testing-output.txt
- **Severity**: latent
- **Concern**: The new surfaces prescribe `python3 "${CLAUDE_PLUGIN_ROOT}/python/cli.py"` as the canonical thin-wrapper delegation form, while recipe step 4 in `docs/python-migration.md` still requires script-dir-first `PLUGIN_ROOT` derivation for Bash callers. An author copying only the new policy text may ship wrappers that fail when run directly from a checkout without a prehydrated `CLAUDE_PLUGIN_ROOT`, unlike existing thin wrappers such as `skills/implement/scripts/write-final-report.sh`. Sources mark this out of scope because acceptance criteria and the plan explicitly prescribe the `${CLAUDE_PLUGIN_ROOT}` form, recipe step 4 remains the authoritative Bash-caller pattern, failure is loud rather than silent, and the tension was raised and rejected at design review.


