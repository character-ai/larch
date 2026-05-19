# test-implement-step2-routing.sh

Structural regression harness for `/implement` Step 2 implementer routing.

It pins the `diff_lines <= 3` Claude inline carve-out, omitted-`--coder`
waterfall order (Cursor → Codex → Claude), explicit-coder bypass, both-down
warning and `coder_fallback=true` manifest flag, `/design` `diff-lines.txt`
export, and review-health routing pins.

Wired into `make lint` via `make test-implement-step2-routing`.
