### FINDING_1: Manifest constructor compatibility not planned for finalize.teardown
- **Reviewer(s)**: Cursor-Arch
- **Severity**: important
- **Concern**: Manifest constructor compatibility not planned. Scenario: Plan adds `Manifest.reserved` but only lists `python/run_logs.py` under UPDATED. `finalize.teardown` still constructs `run_logs.Manifest(status=..., version="1", run_id=..., steps_ran={})` with no `reserved` argument. A required `reserved` field breaks stall teardown at import/construct time before manifest tests run.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Add an explicit plan step: give `reserved` a `field(default_factory=dict)` default (and copy-on-read in `from_json`), or add `### MAY_UPDATE: python/finalize.py` to pass `reserved={}` at the fallback constructor site.

### FINDING_2: update_manifest reserved-key routing not specified after Manifest.reserved
- **Reviewer(s)**: Cursor-Arch, Cursor-Innovation
- **Severity**: important
- **Concern**: `update_manifest` reserved-key routing is unspecified after adding `Manifest.reserved`. Scenario: Today unknown kwargs such as `stalled_at_step` go to `extra` and `_manifest_v2_merge` promotes them. After `stalled_at_step` moves into `Manifest.reserved`, leaving the `else: extra[key] = value` loop unchanged can write the new stall step to `extra` while `reserved` stays stale; `to_json(existing=...)` may re-emit the old top-level value from `existing` and stall manifests stay wrong (regresses `test_finalize.py::test_teardown_stall_preserves_tmpdir_and_writes_manifest`). Today `finalize.teardown` passes `stalled_at_step=` into `update_manifest`, which stores it in `extra`; parse currently drops `stalled_at_step` from `Manifest`, so a `reserved`-only `from_json` without matching kwargs routing can lose stall metadata on the next read/write cycle.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: In the `python/run_logs.py` section, add an explicit `update_manifest` step: copy `reserved` from the loaded manifest, route registry-classified top-level keys (`stalled_at_step`, `pr_number`, etc.) into `reserved` instead of `extra`, then rebuild via `to_json(existing=read_data)`.
  - From Cursor-Innovation: Spell out that `update_manifest` and `_update_manifest_v2` map registry-classified top-level keys (at least `stalled_at_step`) into `Manifest.reserved`, not `extra`, before `to_json(existing=read_data)`.

### FINDING_3: Registry inventory anchor missing for v2 key registry
- **Reviewer(s)**: Cursor-Arch
- **Severity**: important
- **Concern**: Registry inventory anchor missing. Scenario: Plan asks for a v2 key registry but does not point implementers at the authoritative parse exclude set in `_dict_to_manifest` (`status`, `schema_version`, `skill`, `flags`, `operator_cwd`, `larch_version`, `model_roster`, `effort`, `attempt`, `superseded_by`, `stalled_at_step`, etc.). Omitting any of these reserved keys drops them on `from_json` and causes manifest byte drift.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Add one plan bullet: seed the registry from the current `_dict_to_manifest` v2 exclude list plus merge-promotion rules in `_manifest_v2_merge`, and keep the planned registry parity test keyed to that full set.

### FINDING_4: JudgeSeverity ownership ambiguous across review_types and voting.py
- **Reviewer(s)**: Cursor-Innovation, Cursor-Requirements
- **Severity**: important
- **Concern**: `JudgeSeverity` ownership is ambiguous across `review_types` and `voting.py`. Scenario: The plan adds `JudgeSeverity` in `review_types` and also tells `voting.py` to "Define `JudgeSeverity`" without an import rule; `review_types.py` already owns it. Two enums or divergent member sets can break `valid_panel_severity` / tally parity while the issue asks for one shared typed layer.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Innovation: Change the voting.py step to import `JudgeSeverity` from `review_types` and keep only string constant re-exports for backward-compatible imports.
  - From Cursor-Requirements: Import JudgeSeverity (and ReviewVote) from review_types in voting.py; delete local severity constants after re-exporting string aliases for tests.

### FINDING_5: Finding.block slice boundary ambiguous on heading inclusion
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Concern**: `Finding.block` slice boundary is ambiguous on whether the `### FINDING_N:` heading line is included. Scenario: `review_aggregate._finding_blocks` and `_extract_finding_block` today include the heading line; a body-only `Finding.block` breaks prune/renumber bytes and skipped-finding extraction parity.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Innovation: State explicitly that `Finding.block` is the raw slice from the heading line through the line before the next boundary (heading included, no global strip).

### FINDING_6: load_or_recover_manifest_checked recovery rewrites bypass Manifest factory
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: important
- **Concern**: `load_or_recover_manifest_checked` JSONDecodeError / run_dir recovery rewrites bypass Manifest factory. Scenario: Corrupt or missing manifest.json recovery still calls `_synthesize_manifest_v2` plus `_write_manifest_v2` directly. That path is not named with `init_run` / `_recover_manifest_from_run_dir` / `larch_log_init_main` factory routing, so reserved-key defaults and emit shape can drift from normal init/update writers.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Pragmatic: Add explicit plan steps for load_or_recover_manifest_checked branches at 861-867 and 875-881: build via the same Manifest factory used by init_run, then persist with Manifest.to_json(existing=None) before _write_manifest_v2. Pin byte parity in python/test_run_logs.py for corrupt-json recovery rewrite.

### FINDING_7: _commit_run updated_at-only manifest touch omitted from write-path inventory
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: important
- **Concern**: `_commit_run` updated_at-only manifest touch omitted from write-path inventory. Scenario: `_commit_run` calls `_update_manifest_v2(manifest, {})` before copying larch-logs into the repo. The plan lists `update_manifest`, `larch_log_manifest_main`, post-merge refresh, terminal reconcile, and pre-commit refresh, but not this commit-time rewrite. A `to_json` refactor that requires `existing=read_data` or mishandles reserved/extra promotion could drop top-level keys during run-log commit.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Pragmatic: Enumerate _commit_run in the required write-path list and route it through read → Manifest.from_json → Manifest.to_json(existing=read_data) → _write_manifest_v2. Add a byte-parity test that an updated_at-only commit preserves reserved keys, extension keys, and promotable fields such as pr_number and stalled_at_step.

### FINDING_8: _count_findings parity unspecified when adopting parse_findings
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: important
- **Concern**: `_count_findings` parity is unspecified when adopting `parse_findings`. Scenario: Today `_count_findings` increments on every `^### FINDING_[0-9]+:` line; `len(parse_findings(...))` counts blocks and ignores nested heading tokens inside a body, so accepted-count / FIX_COUNT / coder routing can change on the nested-heading fixture the plan already cares about for `_filter_in_scope`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Requirements: Pin `_count_findings` to today's line-count semantics (dedicated heading-line helper or explicit test), or document and test that block-count replaces line-count only when nested in-body headings are absent.

### FINDING_9: ReviewCoreStatus member set not anchored to existing REVIEW_CORE_STATUS tokens
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: important
- **Concern**: `ReviewCoreStatus` member set is not anchored to existing `REVIEW_CORE_STATUS` tokens. Scenario: Acceptance requires key status sets as `StrEnum`; without an explicit member list tied to `ok`/`fix-required`/`cap-reached`/`zero-findings`/`panel-failed`/`aggregator-validation-exhausted`/`main-agent-vote-required`/`prune-skipped`/`error`/`exception`/`unknown` and `_SETTLING_CORE_STATUSES`, partial conversion can leave string literals and fail the acceptance intent.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Requirements: Enumerate ReviewCoreStatus members from current tokens in review_types and convert _SETTLING_CORE_STATUSES plus the Step-5 status branch to enum-backed comparisons while keeping unknown passthrough.
```

**Merge notes**

| Merged IDs | Rationale |
|---|---|
| Input 2 + 5 | Same `update_manifest` / `stalled_at_step` → `reserved` routing gap |
| Input 4 + 9 | Same `JudgeSeverity` dual-definition risk |
| Input 7 vs 8 | Split: `load_or_recover` recovery vs `_commit_run` commit-time rewrite (distinct code paths and fixes) |

No `[OUT_OF_SCOPE]` tags in source; `LARCH_AGGREGATOR_EMPTY_MERGE_ATTESTED` not included (non-empty merge).

### FINDING_10:
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/review_types.py:33-37 python/review_aggregate.py:246-248
- **Concern**: [SCOPE-REDUCTION] Finding.title is specified without a parse contract and callers today use raw blocks only. Scenario: Implementers may invent title parsing or ship a dead field; aggregate still derives IDs via _finding_id_from_block separately, adding churn without acceptance benefit
- **Proposed resolution**: Omit Finding.title from the frozen dataclass unless a caller needs it; document that parse_findings sets finding_id from the heading token and stores the raw heading line inside block
