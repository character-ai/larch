# scripts/lib-phantom-probe.sh — contract

Sourced-only library loaded by `python/cli.py push checkpoint-probe` compatibility callers that need the historical `phantom_probe_with_warn <step-token>` shell function.

The library derives the plugin root from its own `SCRIPT_DIR` and delegates to `python3 "$SCRIPT_DIR/../python/cli.py" git phantom-probe --step <step-token>`. It parses and re-emits only `PHANTOM_STATUS`, `PHANTOM_REASON`, `PHANTOM_COUNT`, `PHANTOM_PATHS_FILE`, and `PHANTOM_APPEND_WARN_ERROR` keys for callers that source the library.

Warning append behavior lives in `python/phantom.py`; this library must not append execution-issues warnings itself. All advisory outcomes return 0 so checkpoint callers continue to route on the emitted keys.

When changing this library, update `python/phantom.py`, `python/test_phantom.py`, and any Step 8 ship harness expectations in the same PR.
