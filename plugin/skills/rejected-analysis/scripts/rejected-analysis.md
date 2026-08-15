# rejected-analysis.sh

Thin Bash wrapper for `/rejected-analysis`.

- Primary caller: `skills/rejected-analysis/SKILL.md`.
- Invariant: Bash owns no collection, parsing, clustering, ledger, or verdict extraction logic.
- Dispatches `prepare` and `ingest-verdict` to `scripts/larch.sh`; `finalize` and `record` remain Python-owned until their follow-up migration.
- Translates public `prepare --n DAYS` to Rust `prepare --days DAYS`.
- Harness: `skills/rejected-analysis/scripts/test-rejected-analysis.sh`.
- Edit in sync with `crates/larch-cli/src/rejected_analysis_commands.rs`, the remaining Python finalization code, and the skill contract.
