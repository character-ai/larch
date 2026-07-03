## Plan

Approach

- Keep the change test-only. Do not edit `skills/implement/scripts/step-5-review.sh` or `skills/implement/scripts/step-5-resume.sh`.
- Add execution-based pytest coverage in the existing Step 5 review test file.
- Run each real shell wrapper with:
  - `IMPLEMENT_TMPDIR` pointing at a pytest temp directory.
  - `CLAUDE_PLUGIN_ROOT` pointing at the repo root.
  - A temp `python3` shim first in `PATH`.
- Make the shim intercept only `python/cli.py review-and-fix step5`.
  - Capture argv one token per line.
  - Exit `0`.
  - Delegate every other `python3` call to the real interpreter, including `session read-key` and timing calls.
- Add parameterized coverage for both wrappers:
  - `step-5-review.sh` expects `--starting-round 1`.
  - `step-5-resume.sh --final-round-num 2` expects `--starting-round 3`.
- Add two cases per wrapper:
  - `run-flags.sh` contains `DIFFICULTY_OVERRIDE=HARD`, so captured argv includes `--difficulty HARD`.
  - `run-flags.sh` is absent, so captured argv contains no `--difficulty`.

Files to modify/create

### UPDATED: python/tests/review/test_review_and_fix.py

- Add needed test imports, likely `subprocess` and `sys`.
- Add a small helper that:
  - Creates a temp `bin/python3` shim.
  - Writes minimal `session-env.sh`, `plan.txt`, and `feature-description.txt` under `IMPLEMENT_TMPDIR`.
  - Optionally writes `run-flags.sh`.
  - Runs the target wrapper with a controlled env.
  - Returns captured argv lines plus process output for assertions.
- Add one parameterized test that covers wrapper and flag presence combinations.
- Assert:
  - Wrapper exit code is `0`.
  - Captured call starts with `python/cli.py review-and-fix step5`.
  - `--implement-tmpdir` uses the temp implement dir.
  - `--mode loop` is present.
  - Expected `--starting-round` is present.
  - `--difficulty HARD` is present only when `DIFFICULTY_OVERRIDE=HARD`.
  - No `--difficulty` appears when `run-flags.sh` is absent.

Edge cases

- Robustly bootstrap the shim so it cannot recurse or fail before argv capture: before prepending the shim's temp bin dir to `PATH`, resolve the real interpreter once via `sys.executable` in the test process and pass it to the subprocess as `REAL_PYTHON3` in the env. The shim script must reference `"$REAL_PYTHON3"` directly when delegating non-intercepted calls (never re-resolve via `PATH` or `command -v python3`, which would recurse back into the shim). If `REAL_PYTHON3` is unset or empty when the shim runs, it must fail loudly (non-zero exit, clear stderr message) rather than silently falling through. Make the shim file executable (`chmod 0o755`) and name it exactly `python3` in a dedicated temp bin directory.
- Preserve real `run-flags.sh` parsing by delegating `session read-key` to the real CLI.
- Keep temp artifacts under `tmp_path`.
- Avoid depending on human-facing banner text beyond process success.
- For `step-5-resume.sh`, pass a valid `--final-round-num` and avoid `--ready-to-commit` or `--record-only`, so the wrapper reaches the review loop.

Failure modes

- The shim may intercept too much and hide failures in `session read-key`; restrict interception to `review-and-fix step5`.
- The wrapper may inherit noisy larch quiet-stream env from the test process; set `LARCH_QUIET_DISABLE=1` and use a controlled env.
- `step-5-resume.sh` can exit before review if invoked with commit flags; do not pass them.
- A future wrapper regression that drops `DIFFICULTY_OVERRIDE` forwarding should fail by missing `--difficulty HARD` in captured argv.

Testing strategy

- Run the focused pytest target:
  - `python3 -m pytest python/tests/review/test_review_and_fix.py -q -k 'step5_shell or difficulty_override'`
- If the final test name differs, run the specific new test by name.
- Run the full changed-file review test if time allows:
  - `python3 -m pytest python/tests/review/test_review_and_fix.py -q`
- Run changed-file lint if available in the environment:
  - `cd python && ruff check tests/review/test_review_and_fix.py`

difficulty: MODERATE
confidence: high

## Acceptance

See Testing strategy in plan.

review_status: complete
rounds_completed: 2
difficulty: MODERATE
diff_lines: 120
