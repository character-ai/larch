# test-capture-session-transcript.sh contract

Regression harness for `scripts/capture-session-transcript.sh`. The primary contract lives in `scripts/capture-session-transcript.md`; this harness covers the wrapper's status enum and verifies that each outcome is both printed to stdout and appended to the execution-issues log.

Run with:

```bash
scripts/test-capture-session-transcript.sh
```
