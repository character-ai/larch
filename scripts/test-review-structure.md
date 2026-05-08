# scripts/test-review-structure.sh — contract

`scripts/test-review-structure.sh` is the structural regression guard for the `/review` skill's progressive-disclosure topology. It pins invariants covering reference binding, mode activation, anti-halt reminders, substantive-validation wiring, specialist prompt rendering, description/diff output parsing contracts, `--pieces-json` forwarding, Gemini machinery preservation, and accepted-OOS security exclusion in `references/voting.md`.

Assertion 19 verifies that `/review` no longer launches Gemini reviewers in the panel (the call sites were removed deliberately while preserving the launcher and probe machinery): Step 0 still passes `--check-gemini-reviewer` to `session-setup.sh` (positive pin 19a), but `launch-gemini-review.sh` must not reappear (negative pin 19b) and `gemini-output.txt` must not reappear in the collector argv (negative pin 19c).

Assertion 20 pins both halves of the security OOS boundary in `references/voting.md`: diff mode excludes security-tagged findings from `oos-accepted-review.md` using the canonical `focus-area\s*=\s*security` token match, and the existing description-mode guard remains present.

Wired into `make lint` via the `test-review-structure` target. Update this contract with the harness whenever adding or renumbering assertions.
