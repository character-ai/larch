## Proposed Design Outline

### Goals
- Port `scripts/dispatch-with-waterfall.sh` to a stdlib-only `agent dispatch-waterfall` CLI verb plus importable function, preserving every observable contract.
- Full hard cutover: retarget all live callers, delete the bash + harnesses, make `lint-retired-scripts` green.
- Replace harness coverage with colocated pytest, including the no-grouped-reuse guard intent.

### Non-goals
- Do not port `dispatch-code-voters.sh` or the C1b /review and C3a1 plan-review bodies in-process; only repoint their waterfall call.
- Do not re-implement reviewer launch/collection; keep calling existing `agent launch-review|launch-claude-review|collect-results`.
- No grouped reuse-by-copy; preserve its removal.

### Approach sketch
- New `python/agent_waterfall.py` with `dispatch_waterfall(...)`; register `("agent","dispatch-waterfall")` in `cli.py`.
- Reuse `proc.py`; start launchers in a new session, kill the process group + descendant sweep on timeout/cancel (teardown parity).
- fd-3 `emit_kv` with the exact KV grammar, dropped-slots TSV, and atomic paths-file.
- Repoint bash callers to `python3 cli.py agent dispatch-waterfall`; regenerate the gzip-embedded plan-review blobs to call the verb.

### Surfaces in scope
- New: `python/agent_waterfall.py`, `python/test_agent_waterfall.py`; `cli.py` registry row.
- Updated: `decompose.py`, `legacy_review_shell/{dispatch-panel,aggregate-findings}.sh`, `dispatch-code-voters.sh`, embedded plan-review source in `plan_review.py`, `migrated-scripts.tsv`, skill/doc refs.
- Deleted: `dispatch-with-waterfall.sh`/`.md`, `test-dispatch-with-waterfall.sh`/`.md`; resolve `test-no-grouped-reuse-guard.sh` fate.

### Open questions
- Module home and in-process vs subprocess for `decompose.py`: settle during plan drafting.
- Gzip-embedded plan-review blob regeneration source and mechanism: confirm during plan drafting.
