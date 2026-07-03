## Proposed Design Outline

### Goals
- Make standalone review Step 4 transcript capture/commit durable: define `review_log_root` unconditionally and validate `RUN_ID` before capture, so `SCOUT_STATUS=na` runs no longer stage transcripts under a wrong relative path or fail commit.
- Correct execution-issue warning labels for design log-publish's `pause` reason so operators see "pause" instead of a hardcoded "5c".
- Remove the redundant `execution-issues flush-safety-net` call in Step 18 so the same execution-issues content is not double-appended to the NDJSON audit log on every finalize run.

### Non-goals
- No new review Step 4 regression harness (Finding #3) — deferred, not a recommended item this round.
- No heatmap TSV compatibility-note changes (Finding #4) — already documented in `docs/run-logs.md` by the same PR (#6084) that introduced the sectioned format.
- No new `clarify` reason value for `log_publish_main` — the clarify publish call keeps defaulting to `final`/`5c`.

### Approach sketch
- `skills/review/SKILL.md`: hoist `review_log_root="${LARCH_LOG_ROOT:-$REVIEW_TMPDIR/larch-logs}"` so it's defined unconditionally before all Step 4 log-phase/transcript/commit calls (not just inside the scout-manifest branch), and validate `RUN_ID` against the existing slug contract before capture.
- `python/larch/design/design_publish.py` + `design_log_publish_flow.py`: add a `warning_step_label` field to the existing frozen `_TranscriptCaptureContext` dataclass, derived from `log_publish_main`'s `--reason` (`final`→`5c`, `pause`→`pause`), replacing the hardcoded `"5c"` literal at the `run-log capture-transcript` call site.
- `skills/implement/scripts/step-18.sh`: remove the redundant explicit `execution-issues flush-safety-net` call in `run_finalize` — the unconditional trailing `implement-finalize teardown` call already performs the equivalent flush via `finalize.py`'s `_teardown_log_flush` on every path, including bail/stall-direct-to-teardown paths that never reach step-18.sh's finalize phase at all.

### Surfaces in scope
- `skills/review/SKILL.md`
- `python/larch/design/design_publish.py`
- `python/larch/design/design_log_publish_flow.py`
- `skills/implement/scripts/step-18.sh`
- Test siblings: `python/tests/design/test_design_publish.py`, `python/tests/design/test_design_log_publish_flow.py`, `skills/implement/scripts/test-step-18.sh`

### Open questions
- None.
