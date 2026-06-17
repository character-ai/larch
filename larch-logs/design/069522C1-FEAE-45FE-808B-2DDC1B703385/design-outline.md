## Proposed Design Outline

### Goals
- Port `dispatch-code-voters.sh` to an in-process Python `agent dispatch-voters` verb, preserving all runtime behavior and `VOTER_*` KVs byte-for-byte.
- Cut every live consumer over to the new verb; delete the bash script and harness; record retirements in `migrated-scripts.tsv`.
- Aggressive C1a closeout: hunt and remove stale references and dead hooks; make `lint-retired-scripts`, `py-test`, and `lint` green.

### Non-goals
- Do not port or retire the C1b legacy review shells (`review-core.sh` and siblings); retarget the call site only.
- No behavior change to the voter panel: shrink-not-backfill, parallel dispatch, parse-rate retry, and the sentinel barrier are all preserved.
- No new voter slots, vendors, or panel-tier changes.

### Approach sketch
- Add `dispatch_voters` logic to a Python module (placement decided in plan drafting; `python/voting.py` holds voting primitives, `agent_waterfall.py` / `review_dispatch.py` host dispatch peers).
- Register `("agent", "dispatch-voters")` in `python/cli.py` `_REGISTRY`; reuse `agent dispatch-waterfall`, `agent launch-claude-review`, and `agent wait-reviewers` like the sibling ports did.
- Retarget `review-core.sh` line 92 (the `REVIEW_CORE_DISPATCH_VOTERS_SH` default) to call `python3 cli.py agent dispatch-voters`.
- Port `test-dispatch-code-voters.sh` coverage to colocated pytest.
- Sweep docs, Makefile, `agent-lint.toml`, lint allowlists, `test-review-structure.sh`, and the `test_voting.py` retired-path literal.

### Surfaces in scope
- `python/`: new or updated voter-dispatch module, colocated pytest, `cli.py` registry row.
- `scripts/dispatch-code-voters.sh` + `.md` + `test-dispatch-code-voters.*` (delete).
- `python/legacy_review_shell/review-core.sh` (retarget call site).
- `docs/review-agents.md`, `docs/agents.md`; `Makefile`; `agent-lint.toml`; lint allowlists; `scripts/test-review-structure.sh`; `python/test_voting.py`; `python/migrated-scripts.tsv`; `skills/review/SKILL.md`.

### Open questions
- Module placement for the ported logic (new `python/agent_voters.py` vs. fold into `python/voting.py` or `review_dispatch.py`); resolved during plan drafting.
