# rejected-analysis.sh

Thin Bash wrapper for `/rejected-analysis`.

- Primary caller: `skills/rejected-analysis/SKILL.md`.
- Invariant: Bash owns no collection, parsing, clustering, ledger, or verdict extraction logic.
- Dispatches only to `python3 "${CLAUDE_PLUGIN_ROOT}/python/cli.py" rejected-analysis ...`.
- Translates public `prepare --n DAYS` to Python `prepare --days DAYS`.
- Harness: `skills/rejected-analysis/scripts/test-rejected-analysis.sh`.
- Edit in sync with `python/rejected_analysis.py`, `python/cli.py`, and the skill contract.
