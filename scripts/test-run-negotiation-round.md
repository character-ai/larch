# test-run-negotiation-round.sh

Purpose: regression-test the Darwin serial-lock spawn guards in `scripts/run-negotiation-round.sh`.

Covers:
- Codex branch acquires the per-tool lock before `codex exec` and still emits the `RESPONSE_FILE=` stdout envelope.
- Cursor branch acquires the per-tool lock before `cursor agent`, preserves the `RESPONSE_FILE=` stdout envelope, and passes `--api-key` when `CURSOR_API_KEY` is set.

Primary caller: `make test-run-negotiation-round`.

Edit in sync: update this harness with `scripts/run-negotiation-round.sh`, `scripts/run-negotiation-round.md`, and `.claude/rules/external-tool-launcher-parity.md` when changing negotiation-round spawn ordering or serial-lock coverage.
