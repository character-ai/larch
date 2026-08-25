# test-rejected-analysis.sh

Offline structural harness for `/rejected-analysis`.

- Primary target: `skills/rejected-analysis/SKILL.md`, the thin wrapper, and Rust command/core modules.
- It pins the public `--n DAYS` interface, wrapper KV binding contract, `/issue` sentinel discipline, durable `ingest-status.jsonl`, read-only launcher shape, and frozen `finding_hash` prose.
- It verifies `rejected-analysis.sh prepare --n` translates to Rust `--days`, and that public `--days` is rejected at the wrapper layer.
- It asserts the superseded Python `rejected_analysis` module is absent.
- Makefile target: `make test-rejected-analysis`.
- Edit in sync with `skills/rejected-analysis/SKILL.md`, `skills/rejected-analysis/scripts/rejected-analysis.sh`, `crates/larch-core/src/rejected_analysis.rs`, and `crates/larch-cli/src/rejected_analysis_commands.rs`.
