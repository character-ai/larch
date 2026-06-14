## Proposed Design Outline

### Goals
- Port `scripts/collect-agent-results.sh` (1590 lines) to `python/collect_results.py` with importable library + `agent collect-results` CLI verb.
- Add pytest parity (`python/test_collect_results.py`), replacing three bash harnesses.
- Retarget all bash callers to the Python CLI verb; retire the shell script and harnesses.

### Non-goals
- Porting `dispatch-with-waterfall.sh` itself (Piece 5, #4169).
- Changing the stdout block grammar (`REVIEWER_FILE=|TOOL=|STATUS=|EXIT_CODE=|STRUCTURED_SIDECAR=|FAILURE_REASON=`).
- Adding new validation modes or retry strategies beyond current bash behavior.

### Approach sketch
- New `python/collect_results.py`: port all logical sections (wait phase, status classification, empty-output retry, substantive/structured validation, NS retry, stderr-tail dedup, emit) as Python functions.
- Reuse `review_dispatch.wait_reviewers()` (Piece 1), `retry.is_transient_net_signature()`, `logging_util`, and `agents` subprocess helpers.
- Register `("agent", "collect-results")` in `cli.py`.
- Retarget `dispatch-with-waterfall.sh` (2 call sites) and `legacy_review_shell/collect-findings.sh`.
- Update skill `.md` references; retire bash files; add to `migrated-scripts.tsv`.

### Surfaces in scope
- `python/collect_results.py` (new)
- `python/test_collect_results.py` (new)
- `python/cli.py` (register verb + allowlist)
- `scripts/dispatch-with-waterfall.sh` (retarget 2 collect calls)
- `python/legacy_review_shell/collect-findings.sh` (retarget collector call)
- `Makefile` (swap harness targets)
- `scripts/relevant-checks.sh` (update case pattern)
- `scripts/test-review-structure.sh` (update pin 13)
- `python/migrated-scripts.tsv` (add retired paths)
- `docs/external-reviewers.md`, `docs/review-agents.md` (update collector path prose)
- Skill `.md` references: `plan-review.md`, `brainstorm.md`, `research-phase.md`, `validation-phase.md`, `external-reviewers.md`, `voting-protocol.md`, `dialectic-protocol.md`
- Retire: `scripts/collect-agent-results.sh`, `.md`, `test-collect-agent-results.sh`, `test-collect-agent-retry.sh`, `test-collect-agent-bash32.sh`

### Open questions
- None.
