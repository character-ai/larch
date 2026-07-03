### FINDING_1:
- **Reviewer(s)**: Codex-Pragmatic
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/review/SKILL.md:106-117; python/larch/review/review_tally.py:1244-1284
- **Concern**: Dash-leading RUN_IDs still fail after the new guard. Scenario: The current plan fixes `--run-id=` only for `run-log validate-run-id` but says to keep the log-phase, transcript, and commit calls otherwise unchanged. A valid `RUN_ID=-abc123` then produces `VALID=true`, but `review log-phase --run-id "$RUN_ID"`, `run-log capture-transcript --run-id "$RUN_ID"`, `run-log commit --run-id "$RUN_ID"`, and `review_tally.log_phase`'s internal `["--run-id", args.run_id]` forwarding are argparse-backed and parse `-abc123` as an option or missing value, so Step 4 fails the actual larch-log write path.
- **Proposed resolution**: Apply the `--run-id="${RUN_ID:-}"` form to every Step 4 argparse CLI call, not only the validator, and add `python/larch/review/review_tally.py` to the plan so its internal run-log subprocess args use `f"--run-id={args.run_id}"` for both normal and sibling writes.



