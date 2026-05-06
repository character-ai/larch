# scripts/test-review-structure.sh — contract

`scripts/test-review-structure.sh` is the structural regression guard for the `/review` skill's progressive-disclosure topology. It pins 19 invariants covering reference binding, mode activation, anti-halt reminders, substantive-validation wiring, specialist prompt rendering, description/diff output parsing contracts, `--pieces-json` forwarding, and Gemini machinery preservation.

Assertion 19 verifies that `/review` no longer launches Gemini reviewers in the panel (the call sites were removed deliberately while preserving the launcher and probe machinery): Step 0 still passes `--check-gemini-reviewer` to `session-setup.sh` (positive pin 19a), but `launch-gemini-review.sh` must not reappear (negative pin 19b) and `gemini-output.txt` must not reappear in the collector argv (negative pin 19c).

Wired into `make lint` via the `test-review-structure` target. Update this contract with the harness whenever adding or renumbering assertions.
