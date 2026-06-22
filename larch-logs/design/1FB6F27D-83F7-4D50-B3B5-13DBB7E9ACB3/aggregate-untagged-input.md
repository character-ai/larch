### FINDING_1:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: python/finalize.py:577-580
- **Concern**: Manifest constructor compatibility not planned. Scenario: Plan adds `Manifest.reserved` but only lists `python/run_logs.py` under UPDATED. `finalize.teardown` still constructs `run_logs.Manifest(status=..., version="1", run_id=..., steps_ran={})` with no `reserved` argument. A required `reserved` field breaks stall teardown at import/construct time before manifest tests run.
- **Proposed resolution**: Add an explicit plan step: give `reserved` a `field(default_factory=dict)` default (and copy-on-read in `from_json`), or add `### MAY_UPDATE: python/finalize.py` to pass `reserved={}` at the fallback constructor site.

### FINDING_2:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/run_logs.py:785-812
- **Concern**: `update_manifest` reserved-key routing not specified. Scenario: Today unknown kwargs such as `stalled_at_step` go to `extra` and `_manifest_v2_merge` promotes them. After `stalled_at_step` moves into `Manifest.reserved`, leaving the `else: extra[key] = value` loop unchanged can write the new stall step to `extra` while `reserved` stays stale; `to_json(existing=...)` may re-emit the old top-level value from `existing` and stall manifests stay wrong (regresses `test_finalize.py::test_teardown_stall_preserves_tmpdir_and_writes_manifest`).
- **Proposed resolution**: In the `python/run_logs.py` section, add an explicit `update_manifest` step: copy `reserved` from the loaded manifest, route registry-classified top-level keys (`stalled_at_step`, `pr_number`, etc.) into `reserved` instead of `extra`, then rebuild via `to_json(existing=read_data)`.

### FINDING_3:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: important
- **Focus area**: architecture
- **Location**: python/run_logs.py:733-751
- **Concern**: Registry inventory anchor missing. Scenario: Plan asks for a v2 key registry but does not point implementers at the authoritative parse exclude set in `_dict_to_manifest` (`status`, `schema_version`, `skill`, `flags`, `operator_cwd`, `larch_version`, `model_roster`, `effort`, `attempt`, `superseded_by`, `stalled_at_step`, etc.). Omitting any of these reserved keys drops them on `from_json` and causes manifest byte drift.
- **Proposed resolution**: Add one plan bullet: seed the registry from the current `_dict_to_manifest` v2 exclude list plus merge-promotion rules in `_manifest_v2_merge`, and keep the planned registry parity test keyed to that full set.

### FINDING_4:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/voting.py:138-151
- **Concern**: `JudgeSeverity` is defined in both `review_types.py` and the voting.py update section. Scenario: The voting.py section says "Define `JudgeSeverity`" while `review_types.py` already owns it; two enums or divergent member sets can break `valid_panel_severity` / tally parity
- **Proposed resolution**: Change the voting.py step to import `JudgeSeverity` from `review_types` and keep only string constant re-exports for backward-compatible imports

### FINDING_5:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: python/run_logs.py:785-823
- **Concern**: `update_manifest` reserved-key routing is unspecified after adding `Manifest.reserved`. Scenario: Today `finalize.teardown` passes `stalled_at_step=` into `update_manifest`, which stores it in `extra`; parse currently drops `stalled_at_step` from `Manifest`, so a `reserved`-only `from_json` without matching kwargs routing can lose stall metadata on the next read/write cycle
- **Proposed resolution**: Spell out that `update_manifest` and `_update_manifest_v2` map registry-classified top-level keys (at least `stalled_at_step`) into `Manifest.reserved`, not `extra`, before `to_json(existing=read_data)`

### FINDING_6:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/review_types.py:15-47
- **Concern**: `Finding.block` slice boundary is ambiguous on whether the `### FINDING_N:` heading line is included. Scenario: `review_aggregate._finding_blocks` and `_extract_finding_block` today include the heading line; a body-only `Finding.block` breaks prune/renumber bytes and skipped-finding extraction parity
- **Proposed resolution**: State explicitly that `Finding.block` is the raw slice from the heading line through the line before the next boundary (heading included, no global strip)

### FINDING_7:
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: python/run_logs.py:861-881
- **Concern**: load_or_recover_manifest_checked JSONDecodeError / run_dir recovery rewrites bypass Manifest factory. Scenario: Corrupt or missing manifest.json recovery still calls _synthesize_manifest_v2 plus _write_manifest_v2 directly. That path is not named with init_run / _recover_manifest_from_run_dir / larch_log_init_main factory routing, so reserved-key defaults and emit shape can drift from normal init/update writers.
- **Proposed resolution**: Add explicit plan steps for load_or_recover_manifest_checked branches at 861-867 and 875-881: build via the same Manifest factory used by init_run, then persist with Manifest.to_json(existing=None) before _write_manifest_v2. Pin byte parity in python/test_run_logs.py for corrupt-json recovery rewrite.

### FINDING_8:
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: python/run_logs.py:1890-1893
- **Concern**: _commit_run updated_at-only manifest touch omitted from write-path inventory. Scenario: _commit_run calls _update_manifest_v2(manifest, {}) before copying larch-logs into the repo. The plan lists update_manifest, larch_log_manifest_main, post-merge refresh, terminal reconcile, and pre-commit refresh, but not this commit-time rewrite. A to_json refactor that requires existing=read_data or mishandles reserved/extra promotion could drop top-level keys during run-log commit.
- **Proposed resolution**: Enumerate _commit_run in the required write-path list and route it through read → Manifest.from_json → Manifest.to_json(existing=read_data) → _write_manifest_v2. Add a byte-parity test that an updated_at-only commit preserves reserved keys, extension keys, and promotable fields such as pr_number and stalled_at_step. **1. load_or_recover recovery rewrites (risk-integration)** `load_or_recover_manifest_checked` still has two branches that synthesize and write raw v2 dicts after recovery. The plan centralizes init/recovery through `Manifest.to_json`, but these branches are easy to miss and are a classic reserved-key drift surface. **2. `_commit_run` manifest touch (risk-integration)** Every run-log commit bumps `updated_at` via `_update_manifest_v2(..., {})`. That rewrite is not on the plan’s write-path checklist. If `to_json` is wrong without `existing=read_data`, committed manifest bytes can lose fields silently during an otherwise routine log flush.

### FINDING_9:
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: important
- **Focus area**: architecture
- **Location**: python/review_types.py:48-51 python/voting.py:138-144
- **Concern**: JudgeSeverity ownership is ambiguous across review_types and voting.py. Scenario: The plan adds JudgeSeverity in review_types and also tells voting.py to "Define JudgeSeverity" without an import rule, so two enum definitions can drift while the issue asks for one shared typed layer
- **Proposed resolution**: Import JudgeSeverity (and ReviewVote) from review_types in voting.py; delete local severity constants after re-exporting string aliases for tests

### FINDING_11:
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/review_and_fix.py:207-210 python/review_types.py:40-47
- **Concern**: _count_findings parity is unspecified when adopting parse_findings. Scenario: Today _count_findings increments on every ^### FINDING_[0-9]+: line; len(parse_findings(...)) counts blocks and ignores nested heading tokens inside a body, so accepted-count / FIX_COUNT / coder routing can change on the nested-heading fixture the plan already cares about for _filter_in_scope
- **Proposed resolution**: Pin _count_findings to today's line-count semantics (dedicated heading-line helper or explicit test), or document and test that block-count replaces line-count only when nested in-body headings are absent

### FINDING_12:
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/review_types.py:49-50 python/review_and_fix.py:45 python/review_and_fix.py:2418-2440
- **Concern**: ReviewCoreStatus member set is not anchored to existing REVIEW_CORE_STATUS tokens. Scenario: Acceptance requires key status sets as StrEnum; without an explicit member list tied to ok/fix-required/cap-reached/zero-findings/panel-failed/aggregator-validation-exhausted/main-agent-vote-required/prune-skipped/error/exception/unknown and _SETTLING_CORE_STATUSES, partial conversion can leave string literals and fail the acceptance intent
- **Proposed resolution**: Enumerate ReviewCoreStatus members from current tokens in review_types and convert _SETTLING_CORE_STATUSES plus the Step-5 status branch to enum-backed comparisons while keeping unknown passthrough
