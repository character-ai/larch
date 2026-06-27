### FINDING_1:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/larch/state/stall_recovery.py:966-983; python/larch/state/stall_recovery.py:2079-2088
- **Concern**: Newest sidecar selection across ledger and fallback is unspecified. Scenario: When canonical ledger append fails, `record_escalation` writes the row with the truncated sidecar only to `stall-recovery-escalation-fallback.tsv` while older rows remain in the ledger. Scanning only the ledger newest-first can return an older valid sidecar or an empty newer row and never reach the fallback row with the current sidecar.
- **Proposed resolution**: Define selection as one reverse-chronological pass over all rows from both prefixed ledger and fallback (compare `utc=`), taking the first row whose `failure_detail_log` resolves to a validated sidecar; do not stop after the ledger file alone.



### FINDING_2:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/test_stall_recovery.py:1051-1063; python/test_stall_recovery.py:1271-1294
- **Concern**: Classify regression test should prove evidence changed classification, not only path emission. Scenario: A test that only asserts `FAILURE_DETAIL_LOG` points at the sidecar can pass while `_classify_text` still runs with `detail_log_valid=false` if the helper wiring is wrong. The dominant oversize bug is missing lint detail in classification and reports.
- **Proposed resolution**: Use stall state whose bail/step would not alone yield lint classification, put lint/test tokens only in the oversize prefix (and thus the truncated sidecar), and assert `FAILURE_CLASS` / `MATCHED_CLASSIFIER_PATTERN` reflect that content plus the emitted absolute sidecar path.



### FINDING_3:
- **Reviewer(s)**: Codex-Arch
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/larch/state/stall_recovery.py:1421-1458,571-590
- **Concern**: Generic sidecar fallback is blocked by terminal-state validation. Scenario: `_validated_terminal_state_values()` still rejects any non-empty `FAILURE_DETAIL_LOG` that is not already a valid local file, so the new `_classify_generic_from_terminal_state()` fallback never gets a chance to consult the ledger sidecar. A prefixed design terminal state with an oversized detail log would keep returning `VALID=false` instead of classifying from the truncated evidence.
- **Proposed resolution**: Defer generic `FAILURE_DETAIL_LOG` validation until after the sidecar helper runs, or bypass that check when the generic classifier is supposed to recover from a ledger-backed sidecar.



### FINDING_4:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/larch/state/stall_recovery.py:480-567
- **Concern**: Newest ledger row fallback can bind the wrong sidecar when multiple record-escalation rows exist. Scenario: A run can record lint-fix evidence for checks log A, then classify with a different oversize --failure-detail-log B that never got its own ledger row. Newest-row selection would classify and report using A's truncated evidence, mislabeling the dominant failure.
- **Proposed resolution**: When --failure-detail-log is set and primary validation fails with oversize, first derive the expected sidecar rel path via _materialize_truncated_failure_detail_log (or equivalent digest) and prefer ledger/fallback rows whose failure_detail_log matches that path; only then fall back to newest valid row.



### FINDING_5:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/test_stall_recovery.py:1051-1063
- **Concern**: Planned classify regression test omits required stall state seeding. Scenario: classify() returns FAILURE_CLASS=unrecoverable with MATCHED_CLASSIFIER_PATTERN=no-stall when every STALL_TRACKING layer is false, even if sidecar evidence is read. A test that only calls record_escalation_main() and classify_main() with an oversize log will not prove sidecar evidence changed classification.
- **Proposed resolution**: In the planned classify regression test, call _write_state (or equivalent) so STALL_TRACKING=true, and assert FAILURE_CLASS / MATCHED_CLASSIFIER_PATTERN reflect the sidecar prefix (e.g. lint-failure), not only FAILURE_DETAIL_LOG path emission.



### FINDING_6:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: python/larch/state/stall_recovery.py:2180-2221
- **Concern**: Compose fallback must use the ledger/fallback paths already passed into _compose_tier_a_issue. Scenario: compose_report_main() resolves ledger and fallback via _compose_path (artifact-prefix and optional --escalation-ledger-file). A helper that only reconstructs _DEFAULT_ESCALATION_* names would miss prefixed design-failure ledgers and any explicit compose overrides, so Tier A could still omit evidence on those paths.
- **Proposed resolution**: Define the shared resolver as taking tmpdir plus explicit ledger: Path and fallback: Path arguments; classify derives those via _artifact_path(prefix=...), and _compose_tier_a_issue passes its existing ledger/fallback parameters through unchanged.



### FINDING_7:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: python/test_stall_recovery.py:1271-1294
- **Concern**: Planned Tier A compose regression test omits _tier_a_allowed fixtures. Scenario: test_compose_report_tier_a_skips_oversize shows issue-input compose fails without CLAUDE_PROJECT_DIR plus skills/implement/SKILL.md (and typically LARCH_STALL_RECOVERY_DRY_RUN). The planned compose_report_main(... --surface issue-input ...) test will exit non-zero before asserting ## Validated failure-detail log.
- **Proposed resolution**: Mirror the skip test harness in the new Tier A compose regression test: monkeypatch CLAUDE_PROJECT_DIR to tmp_path, create skills/implement/SKILL.md, set LARCH_STALL_RECOVERY_DRY_RUN=1, and seed root-cause artifacts like the existing compose tests.



### FINDING_8:
- **Reviewer(s)**: Codex-Innovation
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/larch/state/stall_recovery.py:571-620,2180-2225
- **Concern**: Fallback sidecar lookup can pick stale fallback.tsv evidence instead of the current canonical ledger row. Scenario: A reused tmpdir that still has an old fallback.tsv from a previous record_escalation failure can make classify or Tier A compose-report render the wrong truncated log
- **Proposed resolution**: Prioritize the canonical ledger first and only consult fallback.tsv when the canonical ledger has no usable sidecar row, or compare the row timestamps explicitly



### FINDING_9:
- **Reviewer(s)**: Codex-Innovation
- **Severity**: important
- **Focus area**: architecture
- **Location**: python/larch/state/stall_recovery.py:571-620
- **Concern**: [SCOPE-REDUCTION] Keep the sidecar recovery out of generic prefixed classification. Scenario: The issue only asks for standard classify and Tier A compose-report recovery. Adding `_classify_generic_from_terminal_state()` and prefixed generic artifact scans broadens the fix into a new unneeded execution path.
- **Proposed resolution**: Drop the generic-prefixed sidecar branch unless a separate generic regression proves it is required



### FINDING_10:
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/test_stall_recovery.py
- **Concern**: The planned classify sidecar regression test does not require stall-state setup or classification outcome assertions. Scenario: Without `STALL_TRACKING=true` (for example via existing `_write_state`), `classify()` short-circuits to `FAILURE_CLASS=unrecoverable` / `MATCHED_CLASSIFIER_PATTERN=no-stall` even when a ledger sidecar is read. A test that only checks `FAILURE_DETAIL_LOG` path emission can pass while the OOS bug (sidecar evidence not driving classification) remains unfixed
- **Proposed resolution**: In the classify test spec, seed `ship-pr-state.sh` with `STALL_TRACKING=true` and a stall step/phase (mirror `test_classify_relevant_checks_failed_detail_log`), put lint markers in the first 64 KiB of the oversize log, call `record_escalation_main()` then `classify_main()` with the oversize `--failure-detail-log`, and assert `FAILURE_CLASS=lint-failure`, `MATCHED_CLASSIFIER_PATTERN=lint-output` (or equivalent), plus `FAILURE_DETAIL_LOG` equals the resolved absolute sidecar path



### FINDING_11:
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/test_stall_recovery.py
- **Concern**: The planned Tier A compose-report regression test omits required compose harness fixtures. Scenario: `compose_report_main(... --surface issue-input)` fails closed without a valid `stall-recovery-root-cause.md` (and Tier A gating/dry-run setup). Following the plan literally can yield a non-zero compose rc before the ledger sidecar fallback is exercised
- **Proposed resolution**: In the compose test spec, copy the fixture pattern from `test_compose_report_tier_a_skips_oversize_detail_log`: set `LARCH_STALL_RECOVERY_DRY_RUN=1`, write `stall-recovery-root-cause.md`, provide Tier A dev-clone scaffolding when using an isolated tmpdir (`skills/implement/SKILL.md` plus `CLAUDE_PROJECT_DIR`), seed oversize `FAILURE_DETAIL_LOG` in classification env, create the ledger sidecar via `record_escalation_main()`, then assert issue-input contains `## Validated failure-detail log` and sidecar evidence



### FINDING_12:
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/larch/state/stall_recovery.py:2180-2220
- **Concern**: Tier A ledger sidecar fallback must use compose_report's resolved ledger and fallback paths, not default stall-recovery ledger filenames. Scenario: `_compose_tier_a_issue()` already receives `ledger` and `fallback` resolved by `compose_report()` with `--artifact-prefix` (for example `design-failure-escalation-ledger.tsv` per `design_lifecycle._stall_args()`). The plan's shared sidecar helper only names `_DEFAULT_ESCALATION_LEDGER` / `_DEFAULT_ESCALATION_FALLBACK` plus optional prefix. `_compose_tier_a_issue` has no `artifact_prefix` parameter, so a helper that re-derives default filenames will scan `stall-recovery-escalation-ledger.tsv` and miss prefixed sidecars. `/design` Tier A auto-filed reports would still omit `## Validated failure-detail log` when classification `FAILURE_DETAIL_LOG` points at an oversize original path.
- **Proposed resolution**: In `_compose_tier_a_issue()`, pass the existing `ledger` and `fallback` arguments into the sidecar lookup helper (add optional `ledger_paths` to the helper rather than re-resolving defaults). Add a compose regression with `--profile generic --artifact-prefix design-failure` mirroring the design failure-report path.



### FINDING_13:
- **Reviewer(s)**: Codex-Requirements
- **Severity**: important
- **Focus area**: security
- **Location**: plan.txt:39-50,67-80
- **Concern**: The regression matrix only exercises the default implement happy path. It never proves the new sidecar reader rejects escaped or symlinked ledger values, and it never locks the required absolute-path contract or the prefixed generic branch.. Scenario: A malformed or prefixed ledger row can regress the new fallback path undetected, or classify can emit a relative sidecar path that later fails compose-report validation and drops the evidence.
- **Proposed resolution**: Add a prefixed generic regression that asserts the emitted FAILURE_DETAIL_LOG equals sidecar.resolve(), and add one malicious-ledger regression that seeds an outside-tmpdir or symlink target and confirms it is ignored.



### FINDING_14:
- **Reviewer(s)**: Codex-Generic
- **Severity**: important
- **Focus area**: security
- **Location**: python/larch/state/stall_recovery.py:513-518
- **Concern**: New classify sidecar lookup lacks a ledger-file locality check. Scenario: A symlinked default ledger under IMPLEMENT_TMPDIR can be read from outside tmpdir and drive classification via failure_detail_log, widening the read surface beyond the tmpdir sidecar
- **Proposed resolution**: Before parsing each ledger or fallback candidate in the new helper, require it to be a non-symlink regular file under tmpdir, for example with _validate_tmpdir_local_file; otherwise skip it



### FINDING_15:
- **Reviewer(s)**: Cursor-dyn-Evidence Path Correctness
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/larch/state/stall_recovery.py:514-518 python/larch/state/stall_recovery.py:586-590 python/test_stall_recovery.py:1051-1063
- **Concern**: Shared ledger sidecar helper omits classify guard for empty primary path. Scenario: Plan edge case forbids inventing ledger evidence when `--failure-detail-log` / terminal `FAILURE_DETAIL_LOG` is empty, but the shared helper only says primary-then-fallback. A stale `failure_detail_log=` row from an earlier `record_escalation_main()` in the same tmpdir could change `FAILURE_CLASS` on a later `classify_main()` call that omits `--failure-detail-log`.
- **Proposed resolution**: Add an explicit gate: ledger fallback runs in classify/generic only when a non-empty primary path was supplied and failed validation (oversize for classify per Approach). Tier A compose may still fall back on empty/invalid classification `FAILURE_DETAIL_LOG`. Add `python/test_stall_recovery.py` coverage: record a sidecar, classify without `--failure-detail-log`, assert classification ignores ledger evidence.



### FINDING_16:
- **Reviewer(s)**: Cursor-dyn-Evidence Path Correctness
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/larch/state/stall_recovery.py:1026-1036 python/larch/state/stall_recovery.py:2079-2088 python/test_stall_recovery.py:1531-1550
- **Concern**: Newest-sidecar selection does not define cross-file `utc=` ordering. Scenario: Plan requires the newest valid sidecar, but `record_escalation()` can leave older rows in the canonical ledger and append newer rows only to fallback when the ledger is not writable (`test_record_escalation_nonwritable_ledger_writes_fallback`). Scanning each file independently or preferring canonical ledger last row can pick a stale sidecar.
- **Proposed resolution**: Collect rows from both caller-supplied ledger and fallback paths, parse `utc=`, and choose the newest row whose tmpdir-relative `failure_detail_log` passes existing validation. Add `python/test_stall_recovery.py` regression with an older ledger sidecar plus a newer fallback sidecar.



### FINDING_17:
- **Reviewer(s)**: Cursor-dyn-Evidence Path Correctness
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/larch/state/stall_recovery.py:1051-1073 python/larch/state/stall_recovery.py:2180-2221 python/test_stall_recovery.py:1271-1294
- **Concern**: Tier A fallback must use compose-supplied ledger paths, not only default names. Scenario: `compose_report()` already resolves prefix-aware or override ledger/fallback paths and passes them into `_compose_tier_a_issue()`. Re-deriving sidecars only from `_DEFAULT_ESCALATION_LEDGER` / prefix would miss custom `--escalation-ledger-file` sidecars and break the existing compose contract.
- **Proposed resolution**: Wire the shared sidecar lookup to accept `ledger: Path` and `fallback: Path` from `_compose_tier_a_issue()` (and prefix-aware `_artifact_path()` inside `classify()`). Do not hardcode default filenames inside Tier A compose.



### FINDING_18:
- **Reviewer(s)**: Cursor-dyn-Evidence Path Correctness
- **Severity**: important
- **Focus area**: architecture
- **Location**: python/larch/state/stall_recovery.py:253-268 python/larch/state/stall_recovery.py:2215-2219 python/test_stall_recovery.py:1271-1294
- **Concern**: Classify vs Tier A fallback rules are asymmetric but not encoded in the helper API. Scenario: Approach limits classify consumption to oversize primaries; Tier A may fall back on any invalid/empty `FAILURE_DETAIL_LOG`. A single unconditional helper risks either missing oversize classify fixes or widening classify to consume sidecars for missing/outside primaries.
- **Proposed resolution**: Document and implement an explicit mode (e.g. classify: primary non-empty and `classify_failure_detail_log` suffix `oversize`; Tier A: invalid/empty classification value). Keep fail-closed validation on every resolved path.



### FINDING_19:
- **Reviewer(s)**: Cursor-dyn-Evidence Path Correctness
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/larch/state/stall_recovery.py:517-518 python/larch/state/stall_recovery.py:589-590 python/test_stall_recovery.py:227-247
- **Concern**: Sidecar consumption must emit absolute `FAILURE_DETAIL_LOG` consistently. Scenario: Plan requires absolute sidecar paths, but classify/generic currently persist the original primary string when valid. After sidecar fallback, emitting a tmpdir-relative ledger token would fail `_read_validated_failure_detail_log()` (`classify_failure_detail_log` rejects non-absolute paths at python/larch/state/stall_recovery.py:254-255) and regress `test_compose_report_tier_a_skips_oversize_detail_log` fixes.
- **Proposed resolution**: Set `FAILURE_DETAIL_LOG` to `str((tmpdir / rel).resolve())` (or equivalent) whenever a ledger sidecar is consumed; keep the oversize primary path out of the classification env. Assert absolute sidecar path in the new classify regression in `python/test_stall_recovery.py`.



### FINDING_20:
- **Reviewer(s)**: Codex-dyn-Evidence Path Correctness
- **Severity**: blocking
- **Focus area**: security
- **Location**: <TMPDIR>/plan.txt:5-9,25-33
- **Concern**: [SCOPE-REDUCTION] Narrow the sidecar fallback to oversize-only cases. Scenario: At python/larch/state/stall_recovery.py:315-333, 513-567, and 571-630, the current code rejects non-absolute, symlink, outside-tmpdir, missing, unreadable, and oversize failure-detail logs before any read, and python/test_stall_recovery.py:1051-1079 locks that behavior in. The plan's broad "when that path is invalid, look in the ledger" wording would let classify() or _classify_generic_from_terminal_state() recover from malformed input via an unrelated sidecar instead of preserving the current fail-closed rejection path.
- **Proposed resolution**: Only consult the ledger after the direct path fails with oversize or truncation. Keep every other validation failure on the current hard-fail path.



### FINDING_21:
- **Reviewer(s)**: Codex-dyn-Evidence Path Correctness
- **Severity**: important
- **Focus area**: correctness
- **Location**: <TMPDIR>/plan.txt:21-24,29-33
- **Concern**: [SCOPE-REDUCTION] Do not let prefixed runs probe unprefixed ledgers. Scenario: At python/larch/state/stall_recovery.py:480-567 and 2180-2221, the proposed shared lookup can be used by implement classify() and Tier A compose-report, and the candidate list still names _DEFAULT_ESCALATION_LEDGER and _DEFAULT_ESCALATION_FALLBACK even when artifact_prefix is set. That makes a prefixed run vulnerable to stale unprefixed rows from another invocation, despite the prefix-scoped artifact expectations already asserted in python/test_stall_recovery.py:645-678 and 1599-1658.
- **Proposed resolution**: When artifact_prefix is set, restrict the helper to the prefixed ledger and fallback files for that run. Do not consult the unprefixed defaults, and keep row selection inside the active prefix scope.



