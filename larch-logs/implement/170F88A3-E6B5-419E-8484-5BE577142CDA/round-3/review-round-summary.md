# Review Round 3

- Mode: `diff`
- 4 accepted, 4 rejected (1 neutral)

## Accepted Findings

### FINDING_1: correctness: python/closeout.py:225-227
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [important] Step 17 --no-print-stdout failure path requires had_backup to treat a non-empty summary as success, diverging from retired step-17.sh. No prior summary-final.md; final-report write renders summary locally then upsert fails; step_17 returns non-zero and step_16_17 skips marker emission despite a valid fresh summary. Restore bash parity: if _summary_nonempty(tmpdir) after failure, delete backup when present and return 0; restore backup only when summary is empty.
- **Suggested revision**: Address the concern above.


### FINDING_10: risk-integration: python/test_finalize.py / python/finalize.py:945-1053
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [important] New finalize CLI path/state-file validation added in this PR lacks negative tests. A bad --state-file or --implement-tmpdir path could be accepted or rejected with the wrong exit code/message vs the retired bash contract. Add teardown/postbump CLI tests for disallowed roots, tmpdir outside roots, and state-file not under tmpdir.
- **Suggested revision**: Address the concern above.


### FINDING_17: **risk-integration** `python/closeout.py:225-231` — The `--no-print-stdout` failure handoff in `step_17` only returns exit `0` when both `had_backup` and `_summary_nonempty(tmpdir)` are true. The retired `step-17.sh` handoff used only `[ -s "$summary_path" ]`, with no backup requirement. If `summary-final.md` did not exist before Step 17 and `final-report write` renders a body but fails later (tracking upsert, manifest stamp, or similar), Bash still handed off `0` and `step-16-17` emitted markers. Python returns the non-zero `write` rc, `step_16_17` skips marker emission, and the orchestrator gets no Step 17 summary in chat even though a fresh `summary-final.md` is on disk. `python/test_closeout.py` only covers the upsert-failure path when a pre-existing summary created a backup. **Suggested fix:** Match Bash: on non-zero `write` rc, after logging Tool Failures, return `0` whenever `_summary_nonempty(tmpdir)` is true (unlink backup only when `had_backup`), then restore from backup only when the summary is still empty.
- **Reviewer**: dyn-closeout-flow-output.txt
- **Concern**: - **risk-integration** `python/closeout.py:225-231` — The `--no-print-stdout` failure handoff in `step_17` only returns exit `0` when both `had_backup` and `_summary_nonempty(tmpdir)` are true. The retired `step-17.sh` handoff used only `[ -s "$summary_path" ]`, with no backup requirement. If `summary-final.md` did not exist before Step 17 and `final-report write` renders a body but fails later (tracking upsert, manifest stamp, or similar), Bash still handed off `0` and `step-16-17` emitted markers. Python returns the non-zero `write` rc, `step_16_17` skips marker emission, and the orchestrator gets no Step 17 summary in chat even though a fresh `summary-final.md` is on disk. `python/test_closeout.py` only covers the upsert-failure path when a pre-existing summary created a backup. **Suggested fix:** Match Bash: on non-zero `write` rc, after logging Tool Failures, return `0` whenever `_summary_nonempty(tmpdir)` is true (unlink backup only when `had_backup`), then restore from backup only when the summary is still empty.
- **Suggested revision**: Address the concern above.


### FINDING_9: risk-integration: python/preflight.py:68-228 / python/test_preflight.py
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [important] Emergency lifecycle-prefix title fallback and empty-title abort paths ported from bash are untested. Emergency run with empty body and title [IMPLEMENTING] Foo could write the wrong plan text, or accept an empty title when body and stripped title are blank. Add tests for prefix-stripped title fallback and empty-title abort (rc==2, no plan file).
- **Suggested revision**: Address the concern above.


