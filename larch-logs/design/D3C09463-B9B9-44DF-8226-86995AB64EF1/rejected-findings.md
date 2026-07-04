### [Plan Review] FINDING_2

### FINDING_2: Step 3 teardown helper CLI contract needs canonical dispatcher pinning
- **Reviewer(s)**: Cursor-Arch, Cursor-Innovation, Codex-Innovation, Codex-Pragmatic
- **Severity**: important
- **Concern**: The plan still leaves the Step 3 teardown helper’s CLI surface underspecified and may register it in the wrong layer, so the Bash fence cannot deterministically call the identity-validated helper from the canonical dispatcher.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Pin one contract in the plan: verb (e.g. `plan-review teardown-loop`), required flags (`--design-tmpdir`, optional `--pid`), handler module/function, `cli.py` dispatch row, the exact `design-step3-review.sh` invocation for trap-only cleanup, and quiet stdout/stderr rules so the existing KV envelope stays stable.
  - From Cursor-Innovation: Pin one registration row (for example plan-review kill-loop-group -> larch.review.plan_review.kill_loop_group_main or a thin process_identity wrapper) with required flags (--design-tmpdir, sidecar path from config), exit codes, and no-envelope stdout; mirror it in design-step3-review.sh and test-design-step3-review.sh pins.
  - From Codex-Innovation: Update the plan's file list and registration step to modify `python/larch/cli.py` for the new helper verb, leaving `python/cli.py` unchanged unless a shim-facing test must change.
  - From Codex-Pragmatic: Add `### UPDATED: python/larch/cli.py` for the new registry entry and leave `python/cli.py` unchanged unless the shim itself needs a real change


