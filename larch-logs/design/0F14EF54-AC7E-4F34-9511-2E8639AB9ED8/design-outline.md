## Proposed Design Outline

### Goals
- Replace `run_review_shell()` façades in `review_aggregate.py`, `review_tally.py`, and `compose_review.py` with in-process Python implementations
- Port `prune-nit-findings.sh` to Python and register `review prune-nit-findings` CLI verb in `review_aggregate.py`
- Delete all 6 legacy bash scripts, `review_legacy.py`, and bash harnesses; append to `migrated-scripts.tsv`; keep lints green

### Non-goals
- Re-architecting the finding format, OOS contract, or voting protocol
- Porting plan-review bash bodies (C3a1/C2 scope; only code-review pipeline bodies here)
- Adding new CLI verbs beyond those implied by the 6 scripts

### Approach sketch
- Extract the large inline Python validation body in `aggregate-findings.sh` into standalone functions in `review_aggregate.py`; convert remaining awk/bash to Python
- Port `tally-code-votes.sh` (ballot splitting, OOS routing, classification TSV) and `emit-tally.sh` (round summary, `review-summary.json`, rejected-findings file) to `review_tally.py`; `log-phase.sh` thin-wraps the already-Python `run-log` CLI
- Port `compose-review-findings.sh` (JSONL record composition, awk-based category/severity extraction) to `compose_review.py`
- Add `prune_nit_findings` and `prune_nit_findings_main` to `review_aggregate.py`; register in `cli.py`; change `review_pipeline.py` `prune_nits` field from `_run_command_string` to `_call_maybe_override`
- Delete all legacy bash scripts and `review_legacy.py`; convert prune-nit bash harness to pytest; update `migrated-scripts.tsv`; run `make lint-retired-scripts`

### Surfaces in scope
- `python/review_aggregate.py`, `python/review_tally.py`, `python/compose_review.py`
- `python/review_legacy.py` (deleted)
- `python/legacy_review_shell/` (all 6 files deleted, directory removed)
- `python/cli.py` (new `review prune-nit-findings` entry)
- `python/review_pipeline.py` (prune_nits caller update)
- `python/test_review_aggregate.py`, `python/test_review_tally.py`, `python/test_compose_review.py`
- `python/migrated-scripts.tsv`
- `skills/review/scripts/prune-nit-findings.sh` (deleted)
- `skills/review/scripts/prune-nit-findings.md` (deleted)
- `skills/review/scripts/test-prune-nit-findings.sh` + `.md` (deleted)
- `skills/review/SKILL.md` (update references)

### Open questions
- None.
