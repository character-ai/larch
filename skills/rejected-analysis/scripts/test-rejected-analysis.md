# test-rejected-analysis.sh

Offline structural harness for `/rejected-analysis`.

- Primary target: `skills/rejected-analysis/SKILL.md` plus the thin wrapper and `python/cli.py` registry.
- It pins the public `--n DAYS` interface, wrapper KV binding contract, `/issue` sentinel discipline, durable `ingest-status.jsonl`, read-only launcher shape, and frozen `finding_hash` prose.
- It verifies `rejected-analysis.sh prepare --n` translates to Python `--days`, and that public `--days` is rejected at the wrapper layer.
- Makefile target: `make test-rejected-analysis`.
- Edit in sync with `skills/rejected-analysis/SKILL.md`, `skills/rejected-analysis/scripts/rejected-analysis.sh`, `python/rejected_analysis.py`, and `python/cli.py`.
