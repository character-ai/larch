### FINDING_17: [OUT_OF_SCOPE] architecture: scripts/larch-log.sh:100
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [latent] Retry-suffixed dynamic Codex outputs are not in the explicit allow clause or larch-log.md enumeration. Retry shapes rely solely on broad *-output-*.txt patterns; narrowing that arm could drop retry forensics. Intentional per plan since no retry producers exist yet. Revisit when dispatch emits dyn-*-codex-output-retry*.txt; add explicit patterns and fixtures then.
- **Suggested revision**: Address the concern above.


Vote tally: YES=1 NO=1 EXON=1 JUDGE_ERROR=0 Result=neutral

### FINDING_18: [OUT_OF_SCOPE] risk-integration: scripts/test-larch-log.sh:150-155
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [nit] No unit-level assert_round_artifact_included pins for dynamic Codex basenames. Integration-only coverage predates this branch; not removed by this diff. Extend assert_round_artifact_included when adding contract pins (see in-scope latent finding).
- **Suggested revision**: Address the concern above.


Vote tally: YES=1 NO=1 EXON=1 JUDGE_ERROR=0 Result=neutral

### FINDING_21: **risk-integration** `python/test_ship.py:573-631` — Every `main()`-level contract test stubs out `quiet_init`, while production always calls it when `--tmpdir` passes `_tmpdir_under_allowed_root()`. That leaves the highest-risk integration surface—the combination of fd 3 JSON delivery, fd 1/2 redirection, and fd 4 diagnostics—untested on the actual `main()` entry path that `/implement` Step 8+ invokes. A regression in inherited `LARCH_QUIET_*` handling or contract-stream selection would pass CI but break orchestration invisibly. **Suggested fix:** Add at least one subprocess-based `main()` test (mirroring `test_quiet_init_routes_contract_and_breadcrumb_fds`) that does not mock `quiet_init`, asserts exactly one JSON line on captured stdout, and asserts traceback/breadcrumb text lands on fd 4 or the quiet log.
- **Reviewer**: dyn-quiet-fds-output.txt
- **Concern**: - **risk-integration** `python/test_ship.py:573-631` — Every `main()`-level contract test stubs out `quiet_init`, while production always calls it when `--tmpdir` passes `_tmpdir_under_allowed_root()`. That leaves the highest-risk integration surface—the combination of fd 3 JSON delivery, fd 1/2 redirection, and fd 4 diagnostics—untested on the actual `main()` entry path that `/implement` Step 8+ invokes. A regression in inherited `LARCH_QUIET_*` handling or contract-stream selection would pass CI but break orchestration invisibly. **Suggested fix:** Add at least one subprocess-based `main()` test (mirroring `test_quiet_init_routes_contract_and_breadcrumb_fds`) that does not mock `quiet_init`, asserts exactly one JSON line on captured stdout, and asserts traceback/breadcrumb text lands on fd 4 or the quiet log.
- **Suggested revision**: Address the concern above.


Vote tally: YES=2 NO=0 EXON=1 JUDGE_ERROR=0 Result=accepted

### FINDING_22: [OUT_OF_SCOPE] The dynamic Codex log changes in `scripts/larch-log.sh` and `scripts/test-larch-log-write-round.sh` match the plan: explicit allow is ordered after prompt/telemetry/static-Codex denies and before the broad `*-output.txt` allow; negative fixtures guard `.prompt`, vote-prompt-shaped names, and `.events.jsonl`. No new risk-integration defect identified there—the clause documents behavior already provided by the broad allow.
- **Reviewer**: dyn-quiet-fds-output.txt
- **Concern**: - The dynamic Codex log changes in `scripts/larch-log.sh` and `scripts/test-larch-log-write-round.sh` match the plan: explicit allow is ordered after prompt/telemetry/static-Codex denies and before the broad `*-output.txt` allow; negative fixtures guard `.prompt`, vote-prompt-shaped names, and `.events.jsonl`. No new risk-integration defect identified there—the clause documents behavior already provided by the broad allow.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=3 EXON=0 JUDGE_ERROR=0 Result=rejected

### FINDING_23: [OUT_OF_SCOPE] `python/conftest.py`’s autouse `LARCH_QUIET_DISABLE=1` plus `reset_quiet_state()` correctly fixes pytest runs launched under `run-relevant-checks-captured.sh` (which calls `larch_quiet_init` at line 10); that is a positive integration fix, not a regression.
- **Reviewer**: dyn-quiet-fds-output.txt
- **Concern**: - `python/conftest.py`’s autouse `LARCH_QUIET_DISABLE=1` plus `reset_quiet_state()` correctly fixes pytest runs launched under `run-relevant-checks-captured.sh` (which calls `larch_quiet_init` at line 10); that is a positive integration fix, not a regression.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=3 EXON=0 JUDGE_ERROR=0 Result=rejected

### FINDING_24: [OUT_OF_SCOPE] `scripts/restore-finalize-state.sh` preserving prewritten `STALL_TRACKING=true` closes a real Python-path stall downgrade risk during Step 18 teardown; also positive, not a finding.
- **Reviewer**: dyn-quiet-fds-output.txt
- **Concern**: - `scripts/restore-finalize-state.sh` preserving prewritten `STALL_TRACKING=true` closes a real Python-path stall downgrade risk during Step 18 teardown; also positive, not a finding.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=3 EXON=0 JUDGE_ERROR=0 Result=rejected

### FINDING_25: [OUT_OF_SCOPE] `python/ship.py:884-886` now unconditionally assigns `IMPLEMENT_TMPDIR` after the allowlist gate (replacing `setdefault`), addressing the stale-env quiet-log path concern from earlier review rounds.
- **Reviewer**: dyn-quiet-fds-output.txt
- **Concern**: - `python/ship.py:884-886` now unconditionally assigns `IMPLEMENT_TMPDIR` after the allowlist gate (replacing `setdefault`), addressing the stale-env quiet-log path concern from earlier review rounds.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=3 EXON=0 JUDGE_ERROR=0 Result=rejected

### FINDING_3: [OUT_OF_SCOPE] architecture: scripts/lib-design-round-artifacts.sh:8-9
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [latent] Design vs implement round allowlists treat dyn-* outputs oppositely (deny vs retain). Editors comparing the two files may apply implement retention rules to design staging or vice versa. Document the cross-skill asymmetry in both contract docs when either file is next touched.
- **Suggested revision**: Address the concern above.


Vote tally: YES=2 NO=0 EXON=1 JUDGE_ERROR=0 Result=accepted

### FINDING_32: [OUT_OF_SCOPE] architecture
- **Reviewer**: dyn-ship-protocol-output.txt
- **Concern**: - **architecture** `python/ship.py:763-769` — `_state_file_kv()` reads `ship-pr-state.sh` through `finalize.read_finalize_state()`, which is named and validated for finalize-state semantics; it works today only because both files share `KEY=value` lines, but the cross-file reuse is easy to misread when debugging the new dual-state Python contract (`finalize-state.sh` for stall/PR continuation vs `ship-pr-state.sh` for orchestrator gates). A dedicated ship-state reader would reduce future contract drift.
- **Suggested revision**: Address the concern above.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0 Result=exonerated

### FINDING_33: [OUT_OF_SCOPE] architecture
- **Reviewer**: dyn-ship-protocol-output.txt
- **Concern**: - **architecture** `scripts/larch-log.sh:69-88` — The new explicit dynamic-Codex allow clause matches the plan ordering (denies first, narrow allow, then broad `*-output.txt` allow) and deliberately omits retry-suffixed shapes; this is documentation/regression hardening rather than a ship-protocol defect, and the added harness coverage in `scripts/test-larch-log-write-round.sh` looks aligned with the stated contract.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=3 EXON=0 JUDGE_ERROR=0 Result=rejected

### FINDING_4: [OUT_OF_SCOPE] code-quality: scripts/test-larch-log-write-round.sh:71-99
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [nit] Unphased dynamic Codex meta/json lack CMD_JSON and .result stripping assertions that phased fixtures now have. Regression in unphased sidecar redaction would not be caught while phased paths stay covered. Add assert_not_grep/assert_json_result_stripped for unphased dyn-api-contract-codex-output fixtures.
- **Suggested revision**: Address the concern above.


Vote tally: YES=2 NO=0 EXON=1 JUDGE_ERROR=0 Result=accepted

