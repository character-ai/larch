# Review Round 1

- Mode: `diff`
- 2 accepted, 1 rejected (0 neutral)

## Accepted Findings

### FINDING_1: PARSE_FAILED_COUNT not forwarded from tally to review-core
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt, cursor-specialist-testing-output.txt, codex-specialist-correctness-output.txt, codex-specialist-edge-cases-output.txt, codex-specialist-testing-output.txt
- **Severity**: important
- **Concern**: `PARSE_FAILED_COUNT` is emitted by `tally_code_votes` but not forwarded into `review-core.env` (`python/review_pipeline.py:2349-2358` tally KV forward list, unlike `UNDER_QUORUM_COUNT`). `_surface_parse_failed_warning` reads from review-core output and always sees `0` or a missing key. After a degraded retry that still has parse failures, `degraded_this_round` may be true but no parse-failed run-summary warning reaches `execution-issues.md` / the final run summary.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Address the concern above.
  - From cursor-specialist-edge-cases-output.txt: Add PARSE_FAILED_COUNT to the tally→core key propagation tuple beside UNDER_QUORUM_COUNT and UNDER_QUORUM_ITEMS.
  - From cursor-specialist-testing-output.txt: Add PARSE_FAILED_COUNT to the tally KV forward list alongside UNDER_QUORUM_COUNT; add a pipeline or _run_round test asserting the warning surfaces when final PARSE_FAILED_COUNT > 0 and degraded_this_round is true.
  - From codex-specialist-correctness-output.txt: Propagate PARSE_FAILED_COUNT through review_pipeline rows, emit it from the main-agent-vote-required branch, and add an integration test that runs _run_round with real review-core output after a degraded retry.
  - From codex-specialist-edge-cases-output.txt: Add PARSE_FAILED_COUNT to the forwarded tally keys in python/review_pipeline.py and cover the end-to-end degraded retry path.
  - From codex-specialist-testing-output.txt: Propagate PARSE_FAILED_COUNT through review_pipeline, emit it from the effective==0 tally branch, and add an _run_round integration test for successful and still-degraded parse-failed retries.


### FINDING_3: effective==0 tally branch omits PARSE_FAILED_COUNT from emitted KVs
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt, codex-specialist-correctness-output.txt, codex-specialist-testing-output.txt
- **Severity**: important
- **Concern**: In `python/review_tally.py:656-677`, the `effective==0` early-return path omits `PARSE_FAILED_COUNT` from emitted KVs despite writing parse-failure / degraded banner text. When all voters fail parse-rate checks (effective quorum 0) on the main-agent-vote-required path, callers cannot surface a parse-failed run-summary warning even after pipeline forwarding is fixed.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Address the concern above.
  - From cursor-specialist-edge-cases-output.txt: Include PARSE_FAILED_COUNT in the zero-effective KV emit block, matching the main return path.
  - From codex-specialist-correctness-output.txt: Propagate PARSE_FAILED_COUNT through review_pipeline rows, emit it from the main-agent-vote-required branch, and add an integration test that runs _run_round with real review-core output after a degraded retry.
  - From codex-specialist-testing-output.txt: Propagate PARSE_FAILED_COUNT through review_pipeline, emit it from the effective==0 tally branch, and add an _run_round integration test for successful and still-degraded parse-failed retries.


