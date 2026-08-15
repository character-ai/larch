# rejected-analysis.sh

Thin Bash wrapper for `/rejected-analysis`.

- Primary caller: `skills/rejected-analysis/SKILL.md`.
- Invariant: Bash owns no collection, parsing, clustering, ledger, or verdict extraction logic.
- Dispatches every `rejected-analysis` verb to `scripts/larch.sh`.
- Translates public `prepare --n DAYS` to Rust `prepare --days DAYS`.
- Harness: `skills/rejected-analysis/scripts/test-rejected-analysis.sh`.
- Edit in sync with `crates/larch-cli/src/rejected_analysis_commands.rs`, `crates/larch-core/src/rejected_analysis.rs`, and the skill contract.
