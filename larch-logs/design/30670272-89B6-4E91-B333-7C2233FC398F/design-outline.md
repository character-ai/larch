## Proposed Design Outline

### Goals
- Make `make lint` finish without hanging when Codex/Cursor is installed but unavailable (auth/quota/network).
- Stop `test-plan-review-loop.sh` from ever launching a real `codex`/`cursor` binary.
- Keep the loop's control-flow coverage intact (complete / bailed / needs-qa paths).

### Non-goals
- No production-code change (`run-external-agent.sh`, `plan-review-loop.sh`, launcher libs).
- No health-probe or degrade-to-Claude production logic; no new `check-codex-health.sh`.
- No rewrite of the harness's existing script-level `LARCH_*_SH` stubs.

### Approach sketch
- Add a `STUB_BIN` dir with minimal `codex`/`cursor`/`claude` stubs; prepend it to `PATH` at the top of the at-risk harness (the `test-codex-implementer.sh:218-287` pattern).
- Stubs honor the launcher output contract (e.g. write the `--output-last-message` target) and exit 0 fast, so `run-external-agent.sh` records a completed launch instead of blocking.
- The PATH stub is path-agnostic: it neutralizes every real-binary launch (revise default at `test-plan-review-loop.sh:818/2715`, or any other) without enumerating each site.
- Re-run the audit grep over make-lint harnesses; apply the same stub only where a real launch can still be reached.

### Surfaces in scope
- `skills/design/scripts/test-plan-review-loop.sh` (primary fix).
- Audit sweep of make-lint test harnesses that pass `--codex-present`/`--cursor-present true` or reach a real launcher.
- Optional small shared stub helper only if a second at-risk harness surfaces.

### Open questions
- Whether the re-audit surfaces a second at-risk harness needing the same stub (resolved during implementation; current audit finds only `test-plan-review-loop.sh`).
