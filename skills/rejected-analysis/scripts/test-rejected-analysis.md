# test-rejected-analysis.sh

Offline structural harness for `/rejected-analysis`.

- Primary target: `skills/rejected-analysis/SKILL.md` and the Rust command/core modules.
- It pins the public `--n DAYS` interface, command KV binding contract, `/issue` sentinel discipline, durable `ingest-status.jsonl`, read-only launcher shape, and frozen `finding_hash` prose.
- It verifies that the skill translates public `--n` to Rust `--days` and calls every `rejected-analysis` verb through `scripts/larch.sh`.
- It asserts the superseded Python `rejected_analysis` module is absent.
- Makefile target: `make test-rejected-analysis`.
- Edit in sync with `skills/rejected-analysis/SKILL.md`, `crates/larch-core/src/rejected_analysis.rs`, and `crates/larch-cli/src/rejected_analysis_commands.rs`.
