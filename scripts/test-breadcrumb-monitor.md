# test-breadcrumb-monitor.sh

Regression harness for the Stage 3 `scripts/breadcrumb-monitor.sh`
compatibility shim. It verifies the shim exits 0 for `--help`, a
representative full known-flag invocation, and malformed truncated paired flags
such as a lone `--stream` or `--paired-pid-file`. The harness also asserts the
shim stays quiet on stdout so removed live-monitor behavior is not
reintroduced.

Wired into `make test-breadcrumb-monitor` and `scripts/relevant-checks.sh`.
Keep this harness in sync with `scripts/breadcrumb-monitor.md` and any change
to the shim's flag parser or exit-0 compatibility contract.
