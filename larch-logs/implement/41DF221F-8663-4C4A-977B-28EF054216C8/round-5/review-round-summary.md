# Review Round 5

- Mode: `diff`
- 3 accepted, 7 rejected (3 neutral)

## Accepted Findings

### FINDING_9: _pointer-only plan detection is too narrow
- **Reviewer(s)**: codex-specialist-correctness-output.txt
- **Severity**: important
- **Concern**: Placeholder plans such as `TODO: fill in plan` or `see plan.txt for details` can pass validation and drive `dispatch-voters` with non-production plan context.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-correctness-output.txt: Broaden the placeholder detector to reject common pointer-only forms and suffixes, or require substantive plan structure before accepting a fixture plan.


### FINDING_11: _dispatch_voters_for_row passes source row round_num instead of fixed round 1
- **Reviewer(s)**: codex-specialist-edge-cases-output.txt
- **Severity**: important
- **Concern**: `_dispatch_voters_for_row()` passes the source row’s `round_num` through to `dispatch-voters`, but calibration replay is supposed to run with a fixed `--round-num 1`. For round-2 cohort rows, that silently changes the voter path and round-conditioned context, so replay no longer matches the intended production-parity baseline.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-edge-cases-output.txt: hard-code `--round-num 1` for calibration replay and keep the manifest round only for locating the historical ballot and classification inputs.


### FINDING_12: rebuild_ballot_main does not assert implement run-root boundary
- **Reviewer(s)**: codex-specialist-edge-cases-output.txt
- **Severity**: important
- **Concern**: `rebuild_ballot_main()` never asserts that `--run-root` is the committed `larch-logs/implement/<RUN_ID>` directory before reading `round-N/findings.md` or `review-findings-full.jsonl`. A caller can point it at an arbitrary local directory and reconstruct a ballot from unrelated files, poisoning replay evidence and reading unintended local content.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-edge-cases-output.txt: reuse `_assert_implement_run_root()` here and reject any run root outside the expected implement-log tree.


