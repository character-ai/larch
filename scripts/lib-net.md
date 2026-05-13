# lib-net.sh

Sourced-only helper library carrying the canonical transient-network signature classifier shared by `scripts/collect-agent-results.sh` and `scripts/ship-pr.sh`.

Exposes:

- `is_transient_net_signature <text>` — returns 0 when the text contains a known transient network or network-adjacent retry signature; returns 1 otherwise. Current signatures cover DNS / access failures, connection refusal or reset, temporary failures, timeouts, TLS handshake failures, HTTP 5xx text, `network/auth issue`, `EOF` paired with `during`, `context deadline exceeded`, `no valid output 3 times`, and `git fetch` paired with `failed`.

The library is sourced-only (no shebang, no `set -e`); callers own exit semantics. Loaded once per shell via the `LARCH_LIB_NET_LOADED` guard.

**Edit-in-sync**: `scripts/collect-agent-results.sh`, `scripts/collect-agent-results.md`, `scripts/ship-pr.sh`, `scripts/ship-pr.md`, `scripts/test-collect-agent-results.sh`, and `scripts/test-ship-pr.sh`.
