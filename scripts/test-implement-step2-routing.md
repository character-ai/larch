# test-implement-step2-routing.sh

Structural regression harness for `/implement` Step 2 implementer routing.

It pins the `diff_lines < 30` Claude inline carve-out, omitted-`--coder`
waterfall order (Codex → Cursor → Claude), explicit-coder bypass, both-down
warning and `coder_fallback=true` manifest flag, `/design` `diff-lines.txt`
export, and `/review` `WHOLESALE_REJECTED=true` protocol criteria.

Wired into `make lint` via `make test-implement-step2-routing`.
