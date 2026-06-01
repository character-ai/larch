# test-implement-step2-routing.sh

Structural regression harness for `/implement` Step 0 implementer selection
(`phase_coder_select`; Step 2 dispatch consumes the resolved `--coder`).

It pins the script-side coder selection pointer, omitted-`--coder`
waterfall order (Codex → Cursor → Claude), explicit-coder unavailable bails,
fallback warnings and `coder_fallback=true` manifest flag, `/design` `diff-lines.txt`
export, the clause that `diff_lines` / `diff-lines.txt` do not select
the implementer, denylisted removed carve-out literals, and review-health routing pins.
Removed `/implement` argv (for example `--design-only`) are not asserted once dropped from `skills/implement/SKILL.md`.

Wired into `make lint` via `make test-implement-step2-routing`.
