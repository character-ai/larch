# scripts/test-review-structure.sh — contract

`scripts/test-review-structure.sh` is the structural regression guard for the `/review` skill's progressive-disclosure topology. It pins 19 invariants covering reference binding, mode activation, anti-halt reminders, substantive-validation wiring, specialist prompt rendering, description/diff output parsing contracts, `--pieces-json` forwarding, and Gemini additive reviewer wiring.

Assertion 19 verifies the Gemini-specific contract: `/review` opts into Gemini probing, derives `gemini_available` with a strict false default, omits the Gemini status-table column when unavailable, includes `gemini-output.txt` only conditionally in collector argv, and extends rounds 4+ to `Cursor → Codex → Gemini → Claude`.

Wired into `make lint` via the `test-review-structure` target. Update this contract with the harness whenever adding or renumbering assertions.
