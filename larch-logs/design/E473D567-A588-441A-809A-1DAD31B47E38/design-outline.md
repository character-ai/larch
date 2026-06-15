## Proposed Design Outline

### Goals
- Port `scripts/collect-agent-results.sh` to `python/collect_results.py` as a library + CLI.
- Preserve the stdout block grammar (`REVIEWER_FILE=`, `TOOL=`, `STATUS=`, etc.) exactly.
- Replace three bash harnesses with `python/test_collect_results.py`.

### Non-goals
- No shim or transitional wrapper for the retired script.
- No new retry modes, validation modes, or output fields.
- No changes to bash 3.2 portability elsewhere; the bash32 harness is deleted, not ported.

### Approach sketch
- Implement `python/collect_results.py` with `CollectorOptions`, `CollectorRecord`, `RetryMeta`, `RetryPlan` classes.
- Register `agent collect-results` verb in `python/cli.py`.
- Reuse `review_dispatch.wait_reviewers()`, `retry.is_transient_net_signature()`, `logging_util`, and `agents._COLLECTOR_NS_STRONG_HEADER`.
- Update live callers: `scripts/dispatch-with-waterfall.sh` and `skills/design/scripts/design-step1d5.sh`.
- Update ~15 doc/reference `.md` files to name the new CLI.
- Delete `scripts/collect-agent-results.sh`, `.md`, and three bash harnesses.

### Surfaces in scope
- `python/collect_results.py` (new)
- `python/cli.py` (add verb)
- `scripts/dispatch-with-waterfall.sh`
- `skills/design/scripts/design-step1d5.sh`
- `python/test_collect_results.py` (new)
- ~15 doc/reference `.md` files (prose updates only)
- `scripts/collect-agent-results.sh` + three harnesses (retire)
- `SECURITY.md`

### Open questions
- None.
