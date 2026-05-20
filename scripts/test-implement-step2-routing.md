# test-implement-step2-routing.sh

Structural regression harness for `/implement` Step 1 implementer selection
(`### Implementer waterfall`; Step 2 dispatch consumes the resolved `--coder`).

It pins the `### Implementer waterfall` section, omitted-`--coder`
waterfall order (Cursor → Codex → Claude), explicit-coder bypass, both-down
warning and `coder_fallback=true` manifest flag, `/design` `diff-lines.txt`
export, the clause that exported `diff_lines` / `diff-lines.txt` do not select
the implementer, denylisted removed carve-out literals, and review-health routing pins.

Wired into `make lint` via `make test-implement-step2-routing`.
