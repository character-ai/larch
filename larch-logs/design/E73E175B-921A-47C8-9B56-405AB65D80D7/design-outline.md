## Proposed Design Outline

### Goals
- Port `oos-serialize.sh` and `normalize-oos-block-header.sh` to `python/oos.py` with full parity.
- Expose `oos serialize` and `oos normalize-header` CLI verbs via `python/cli.py`.
- Cut over all three callers and delete the old bash scripts, harnesses, and `.md` siblings.

### Non-goals
- Do not port `is_security_block` from `lib-vote-tally.sh` (stays bash).
- Do not change OOS wire format semantics or caller behavior.

### Approach sketch
- Implement `oos_serialize()` in `python/oos.py` using stdlib only; preserve security-filter, rejected-tally, and seq-numbering logic.
- Implement `normalize_oos_block_header()` in `python/oos.py`; replace the awk one-liner with Python `re.sub`.
- Register `("oos", "serialize")` and `("oos", "normalize-header")` in `_REGISTRY` of `python/cli.py`.
- Replace `$SHARED_DIR/oos-serialize.sh` in `emit-tally.sh` with `python3 .../cli.py oos serialize`.
- Replace `$NORMALIZE_OOS_HELPER` in `tally-code-votes.sh` and `review-and-fix.sh` with `python3 .../cli.py oos normalize-header`.

### Surfaces in scope
- `python/oos.py` (new), `python/test_oos.py` (new), `python/cli.py` (two registry entries)
- `skills/review/scripts/emit-tally.sh`, `skills/review/scripts/tally-code-votes.sh`, `skills/review-and-fix/scripts/review-and-fix.sh` (caller cutover)
- `skills/shared/scripts/oos-serialize.{sh,md}`, `normalize-oos-block-header.{sh,md}`, `test-oos-serialize.{sh,md}`, `test-normalize-oos-block-header.{sh,md}` (deleted)
- `python/migrated-scripts.tsv`, `Makefile` (two shard entries removed), `agent-lint.toml`, `scripts/relevant-checks.sh`

### Open questions
- None.
