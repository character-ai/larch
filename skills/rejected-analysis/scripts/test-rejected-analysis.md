# test-rejected-analysis.sh

Offline structural harness for `/rejected-analysis`.

- Primary target: `skills/rejected-analysis/SKILL.md`, the thin wrapper, Rust command/core modules, and the residual Python join helpers.
- It pins the public `--n DAYS` interface, wrapper KV binding contract, `/issue` sentinel discipline, durable `ingest-status.jsonl`, read-only launcher shape, and frozen `finding_hash` prose.
- It verifies `rejected-analysis.sh prepare --n` translates to Rust `--days`, and that public `--days` is rejected at the wrapper layer.
- Makefile target: `make test-rejected-analysis`.
- Edit in sync with `skills/rejected-analysis/SKILL.md`, `skills/rejected-analysis/scripts/rejected-analysis.sh`, `crates/larch-core/src/rejected_analysis.rs`, `crates/larch-cli/src/rejected_analysis_commands.rs`, `python/larch/issue/rejected_analysis.py`, and `python/larch/cli.py`.
