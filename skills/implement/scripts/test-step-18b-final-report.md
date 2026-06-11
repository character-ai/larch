# test-step-18b-final-report.sh

Offline harness for `skills/implement/scripts/step-18b-final-report.sh`. Uses a stub `CLAUDE_PLUGIN_ROOT` tree (not bare `PATH` hijack) with a stub `python3 python/cli.py token report` and an implement-dir stub for `write-final-report.sh`. Covers absent/unchanged/changed Step 17 sentinels, snapshot-copy failure promotion after a successful write, token/write-final-report failure envelopes, session-env rehydration, plugin-root fallback, and the real `write-final-report.sh` integration fixture.
