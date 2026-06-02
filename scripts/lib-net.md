# lib-net.sh

Sourced-only helper library carrying the canonical transient-network signature classifier and generic retry wrapper shared by `scripts/collect-agent-results.sh`, `scripts/ship-pr.sh`, and network-touching gap callsites across the repo.

Exposes:

- `is_transient_net_signature <text>` — returns 0 when the text contains a known transient network or network-adjacent retry signature; returns 1 otherwise. Current signatures cover DNS / access failures, connection refusal or reset, temporary failures, timeouts, TLS handshake failures, HTTP 5xx text, `network/auth issue`, `EOF` paired with `during`, `context deadline exceeded`, `no valid output 3 times`, `git fetch` paired with `failed`, `lookup ... no such host`, and bare `no such host`. The classifier fail-opens for the distinct `no such hosted` phrase so hosted-runner naming diagnostics do not get misclassified as transient DNS failures.
- `transient_envelope_predicate_none <envelope>` — always returns 1 (no envelope hint). Use as the predicate for bare git/gh verbs.
- `with_transient_retry <predicate> <fail_file> <cmd> <args...>` — up to three attempts with 2s/4s backoff between retries (via `sleep-seconds.sh` when present). Sets globals `_WTR_OUT` and `_WTR_RC`. Returns the final exit code on exhaustion (does not call `exit_transient_net`; `ship-pr.sh` wraps with `ship_pr_with_transient_retry` for terminal-exit semantics).

The library is sourced-only (no shebang, no `set -e`); callers own exit semantics. Loaded once per shell via the `LARCH_LIB_NET_LOADED` guard.

## Wrapper pattern

Allocate a per-call capture file, invoke the helper, then read globals before any other command runs:

```bash
fail_file=$(mktemp "${TMPDIR:-/tmp}/my-script-net.XXXXXX")
if with_transient_retry transient_envelope_predicate_none "$fail_file" git fetch origin main --quiet; then
    : # success path uses _WTR_OUT
else
    rc=$_WTR_RC
    # failure path uses _WTR_OUT / _WTR_RC / "$(cat "$fail_file")"
fi
rm -f "$fail_file"
```

Under `set -e`, use the `if with_transient_retry ...; then` shape above or a `set +e` capture block so errexit does not fire before `_WTR_RC` / `_WTR_OUT` are read.

**Edit-in-sync**: `scripts/collect-agent-results.sh`, `scripts/collect-agent-results.md`, `scripts/ship-pr.sh`, `scripts/ship-pr.md`, `scripts/test-collect-agent-results.sh`, `scripts/test-lib-net.sh`, and every script that sources `lib-net.sh` for gap callsite wraps.
