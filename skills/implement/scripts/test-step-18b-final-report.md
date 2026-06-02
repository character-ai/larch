# test-step-18b-final-report.sh

Offline harness for `skills/implement/scripts/step-18b-final-report.sh`. Uses a stub `CLAUDE_PLUGIN_ROOT` tree (not bare `PATH` hijack) with stub `scripts/token-report.sh` and implement-dir stubs for `write-final-report.sh` and `append-tool-failure.sh`. Covers absent/unchanged/changed Step 17 sentinels, snapshot-copy failure promotion after a successful write, token/write-final-report failure envelopes, session-env rehydration, plugin-root fallback, and the real `write-final-report.sh` integration fixture.
