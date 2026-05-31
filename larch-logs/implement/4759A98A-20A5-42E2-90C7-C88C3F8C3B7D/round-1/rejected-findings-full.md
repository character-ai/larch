### [rejected] FINDING_1

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_1: code-quality: scripts/test-launch-review.sh:99-110,1512-1523
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [nit] Identical assert_meta_stderr_sink_before_outer_launcher is duplicated in codex and cursor subshells; test-collect-agent-retry.sh has a third near-copy with a generic before_prefix. If ordering rules change (e.g. also assert before CMD_JSON on primary launch), maintainers must update three copies and subshells can drift. Hoist one shared assert_meta_key_before_key helper at file scope or in a sourced test lib; reuse from both lanes and test-collect-agent-retry.sh.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_10

**Rejected subtype:** dismissed (no acceptance threshold met)

### FINDING_10: Static source greps (`_RUN_EXTERNAL_SINK_ARGS`, `_outer_sink_args`, `RETRY_ARGS`) are correctly replaced with runtime `.meta` artifact checks at the `run-external-agent.sh` boundary.
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: - Static source greps (`_RUN_EXTERNAL_SINK_ARGS`, `_outer_sink_args`, `RETRY_ARGS`) are correctly replaced with runtime `.meta` artifact checks at the `run-external-agent.sh` boundary.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=3 EXON=0 JUDGE_ERROR=0

### [rejected] FINDING_11

**Rejected subtype:** dismissed (no acceptance threshold met)

### FINDING_11: Ordering helpers (`assert_meta_stderr_sink_before*`) implement the FINDING_2 mitigation: first `^STDERR_SINK=` must precede first `^OUTER_LAUNCHER=` (or `^CMD_JSON=`), catching outer-only duplicates that would false-green a source grep.
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: - Ordering helpers (`assert_meta_stderr_sink_before*`) implement the FINDING_2 mitigation: first `^STDERR_SINK=` must precede first `^OUTER_LAUNCHER=` (or `^CMD_JSON=`), catching outer-only duplicates that would false-green a source grep.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=3 EXON=0 JUDGE_ERROR=0

### [rejected] FINDING_12

**Rejected subtype:** dismissed (no acceptance threshold met)

### FINDING_12: Outer-retry cases use canonical `$REPO_ROOT/scripts/launch-review.sh` with leaf CLI stubs only — aligned with FINDING_3 constraints.
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: - Outer-retry cases use canonical `$REPO_ROOT/scripts/launch-review.sh` with leaf CLI stubs only — aligned with FINDING_3 constraints.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=3 EXON=0 JUDGE_ERROR=0

### [rejected] FINDING_13

**Rejected subtype:** dismissed (no acceptance threshold met)

### FINDING_13: CMD_JSON retry uses valid vendor-shaped `json_array bash "$HELPER" …` — aligned with FINDING_4 constraints; fail-closed `..` and sink-absent cases preserved unchanged.
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: - CMD_JSON retry uses valid vendor-shaped `json_array bash "$HELPER" …` — aligned with FINDING_4 constraints; fail-closed `..` and sink-absent cases preserved unchanged.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=3 EXON=0 JUDGE_ERROR=0

### [rejected] FINDING_14

**Rejected subtype:** dismissed (no acceptance threshold met)

### FINDING_14: `--risk` round-trip tests cover both lanes (`low` + default `high`), directly guarding the discarded-flag regression (FINDING_12).
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: - `--risk` round-trip tests cover both lanes (`low` + default `high`), directly guarding the discarded-flag regression (FINDING_12).
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=3 EXON=0 JUDGE_ERROR=0

### [rejected] FINDING_15

**Rejected subtype:** dismissed (no acceptance threshold met)

### FINDING_15: Both harnesses are wired into CI (`Makefile`: `test-collect-agent-retry` in `test-harnesses-2`, `test-launch-review` in `test-harnesses-9`).
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: - Both harnesses are wired into CI (`Makefile`: `test-collect-agent-retry` in `test-harnesses-2`, `test-launch-review` in `test-harnesses-9`). **Regression risk:** Low. FINDING_12 is the only behavior change (discarded flag → functional). FINDING_6 is documentary. Test changes strengthen coverage without weakening collector allowlists. ---
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=3 EXON=0 JUDGE_ERROR=0

### [rejected] FINDING_2

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_2: code-quality: scripts/test-collect-agent-retry.sh:852-876
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [nit] New codex sink-outer-retry case inlines the same TOOL=codex meta printf block as case Q2 instead of a helper. Future meta field additions for codex outer-retry fixtures require editing multiple inline blocks; risk of Q2 and sink-retry diverging. Extract write_codex_outer_meta (or parameterize write_outer_meta by TOOL) and use it for Q2 and sink-outer-retry.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_22

**Rejected subtype:** dismissed (no acceptance threshold met)

### FINDING_22: **`launch-review.sh`**: Both lanes initialize `RISK=""`, capture `--risk` in argv parsing, and pass `"$RISK"` as the 5th arg to `*_launcher_append_outer_meta` (empty → `${5:-${RISK:-high}}` → `high`, unchanged default).
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: - **`launch-review.sh`**: Both lanes initialize `RISK=""`, capture `--risk` in argv parsing, and pass `"$RISK"` as the 5th arg to `*_launcher_append_outer_meta` (empty → `${5:-${RISK:-high}}` → `high`, unchanged default).
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=3 EXON=0 JUDGE_ERROR=0

### [rejected] FINDING_23

**Rejected subtype:** dismissed (no acceptance threshold met)

### FINDING_23: **`launch-cursor-implement.sh` / `launch-cursor-ci.sh`**: Explicit `"" ""` for risk/stderr slots (behavior-neutral today).
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: - **`launch-cursor-implement.sh` / `launch-cursor-ci.sh`**: Explicit `"" ""` for risk/stderr slots (behavior-neutral today).
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=3 EXON=0 JUDGE_ERROR=0

### [rejected] FINDING_24

**Rejected subtype:** dismissed (no acceptance threshold met)

### FINDING_24: **Tests**: Static source greps removed; runtime checks assert `STDERR_SINK=` on retry `.meta`, ordering vs `OUTER_LAUNCHER` / `CMD_JSON`, and `--risk` round-trip (`low` / default `high`) in both launch-review lanes; collector outer-retry + CMD_JSON cases mirror case Q / case A without weakening canonical launcher or CMD_JSON validation.
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: - **Tests**: Static source greps removed; runtime checks assert `STDERR_SINK=` on retry `.meta`, ordering vs `OUTER_LAUNCHER` / `CMD_JSON`, and `--risk` round-trip (`low` / default `high`) in both launch-review lanes; collector outer-retry + CMD_JSON cases mirror case Q / case A without weakening canonical launcher or CMD_JSON validation.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=3 EXON=0 JUDGE_ERROR=0

### [rejected] FINDING_25

**Rejected subtype:** dismissed (no acceptance threshold met)

### FINDING_25: **`launch-review.md`**: Documents `--risk` → `OUTER_LAUNCHER_RISK`.
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: - **`launch-review.md`**: Documents `--risk` → `OUTER_LAUNCHER_RISK`. Wiring is symmetric across codex/cursor lanes; fail-closed risk normalization remains in `external_launcher_append_outer_meta`; ordering assertions correctly require `run-external-agent.sh` to own the first `STDERR_SINK=` (append-only sink after `OUTER_LAUNCHER=` would fail the test).
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=3 EXON=0 JUDGE_ERROR=0

### [rejected] FINDING_3

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_3: code-quality: scripts/test-launch-review.sh:99-110
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [nit] assert_meta_stderr_sink_before_outer_launcher calls fail "$label" with no meta context on mismatch. A ordering regression shows only the label string, not which line numbers were found, slowing harness debugging. On failure, emit sink_ln, outer_ln, and a short head of the meta file like other asserts in these harnesses.
- **Suggested revision**: Address the concern above.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0

### [rejected] FINDING_7

**Rejected subtype:** dismissed (no acceptance threshold met)

### FINDING_7: `--risk` is forwarded through top-level `ARGS` into `_launch_codex` / `_launch_cursor` (lines 42–48, 1129–1130), then into `external_launcher_append_outer_meta` (lines 605, 1030).
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: - `--risk` is forwarded through top-level `ARGS` into `_launch_codex` / `_launch_cursor` (lines 42–48, 1129–1130), then into `external_launcher_append_outer_meta` (lines 605, 1030).
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=3 EXON=0 JUDGE_ERROR=0

### [rejected] FINDING_8

**Rejected subtype:** dismissed (no acceptance threshold met)

### FINDING_8: `STDERR_SINK` ordering tests align with the real contract: `run-external-agent.sh` writes base meta (`STDERR_SINK` before `CMD_JSON`, lines 199–202), then `external_launcher_append_outer_meta` appends `OUTER_LAUNCHER=…` (lines 27–31 in `lib-external-launcher-common.sh`). Pairing `grep -Fxq` presence with “first `STDERR_SINK=` before first `OUTER_LAUNCHER=`” avoids false greens from a sink line only appended by the launcher block.
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: - `STDERR_SINK` ordering tests align with the real contract: `run-external-agent.sh` writes base meta (`STDERR_SINK` before `CMD_JSON`, lines 199–202), then `external_launcher_append_outer_meta` appends `OUTER_LAUNCHER=…` (lines 27–31 in `lib-external-launcher-common.sh`). Pairing `grep -Fxq` presence with “first `STDERR_SINK=` before first `OUTER_LAUNCHER=`” avoids false greens from a sink line only appended by the launcher block.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=3 EXON=0 JUDGE_ERROR=0

### [rejected] FINDING_9

**Rejected subtype:** dismissed (no acceptance threshold met)

### FINDING_9: Collector already replays `--risk "$META_OUTER_LAUNCHER_RISK"` and `--stderr-sink` on outer retry; the bug was launch-review discarding `--risk` before meta emission—now fixed.
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: - Collector already replays `--risk "$META_OUTER_LAUNCHER_RISK"` and `--stderr-sink` on outer retry; the bug was launch-review discarding `--risk` before meta emission—now fixed. Tests were not executed in this read-only session; static review only. ---
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=3 EXON=0 JUDGE_ERROR=0

