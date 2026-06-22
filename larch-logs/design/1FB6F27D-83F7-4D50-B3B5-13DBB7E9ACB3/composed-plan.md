## Plan

Use the smallest shared type layer that removes duplicated parsing without changing wire formats.

- Add one review-domain module for:
  - `Finding` (minimal fields only).
  - `parse_findings(path, *, boundary=...) -> list[Finding]`.
  - Named `StrEnum` sets for review core status, votes, and judge severities.
- Keep every serialized value identical.
  - `StrEnum.value` must equal the existing literal.
  - Emit `.value` at every `KEY=value`, markdown, TSV, and JSON boundary.
- Keep the finding markdown layout unchanged.
  - Preserve `### FINDING_N:` headings.
  - Preserve block body text when callers rewrite or copy blocks.
- Define an explicit `Finding.block` contract.
  - `Finding.block` is the raw slice from the `### FINDING_N:` heading line through the line before the next boundary (heading included; no global `.strip()`).
  - `parse_findings` returns that slice for each finding block.
  - Callers that already strip or append trailing newlines keep that behavior locally.
- Make `Manifest.from_json` and `Manifest.to_json` the sole manifest representation.
  - Delete `_dict_to_manifest`, `_manifest_to_dict`, and `_manifest_v2_merge`.
  - Replace duplicated v2 key literals with one keyed registry; derive parse vs emit filters from it.
  - Route `_update_manifest_v2`, `update_manifest`, post-merge refresh, and `larch_log_manifest_main` through `from_json` / `to_json`.
  - Route v2 creation (`_synthesize_manifest_v2`, `init_run`, recovery, `larch_log_init_main`) through `Manifest` + `to_json(existing=None)` before `_write_manifest_v2`.
  - Route `load_or_recover_manifest_checked` JSONDecodeError and missing-manifest recovery rewrites through the same Manifest factory before `_write_manifest_v2`.
  - Convert every other in-memory manifest read path in `run_logs.py` through `Manifest.from_json` immediately after `_read_manifest_v2` or equivalent JSON load.
  - Keep raw `dict[str, Any]` use only at `_read_manifest_v2` / `_write_manifest_v2` IO boundaries or as a narrow adapter for external helpers that cannot accept `Manifest`.
  - Preserve `json.dumps(..., sort_keys=True, indent=2) + "\n"` exactly on v2 paths.

## Files to modify/create

### NEW: python/review_types.py

Create a small stdlib-only module.

- Add `Finding` as a frozen dataclass with only:
  - `finding_id: str`
  - `title: str`
  - `block: str`
- Do **not** add `Finding.severity`, `FindingSeverity`, or shared markdown/judge severity enums on `Finding`.
  - Judge ballot severities stay in `JudgeSeverity` only.
  - Markdown `blocking|important|latent|nit` parsing stays inline where `_SEVERITY_RE` already runs.
- Add `parse_findings(path: Path | str, *, boundary: Literal["finding_heading", "any_heading"] = "any_heading") -> list[Finding]`.
  - Return `[]` when the path is missing, matching existing count helpers.
  - Read file paths with `encoding="utf-8", errors="replace"` so malformed reviewer output does not raise `UnicodeDecodeError`.
  - Accept in-memory text via an internal helper; file reads are the public adoption point.
  - `boundary="finding_heading"`: stop each block only at the next `^### FINDING_[0-9]+:` line; keep interior `### ` subheadings inside the block.
  - `boundary="any_heading"`: stop each block at the next markdown heading that starts a new top-level `### ` block (default for aggregate-style consumers).
  - Parse only valid `^### FINDING_[0-9]+:` block starts.
  - Store the raw block text in `Finding.block` from the heading line through the line before the next boundary (heading included; no caller-specific normalization).
- Add `StrEnum` classes for named sets only:
  - `ReviewCoreStatus` with members matching today's `REVIEW_CORE_STATUS` tokens:
    - `ok`
    - `fix_required` (`"fix-required"`)
    - `cap_reached` (`"cap-reached"`)
    - `zero_findings` (`"zero-findings"`)
    - `panel_failed` (`"panel-failed"`)
    - `aggregator_validation_exhausted` (`"aggregator-validation-exhausted"`)
    - `main_agent_vote_required` (`"main-agent-vote-required"`)
    - `prune_skipped` (`"prune-skipped"`)
    - `error`
    - `exception`
    - `unknown`
  - `ReviewVote`
  - `JudgeSeverity` with members matching today's `_SEVERITY_VALUES`: `blocker`, `major`, `minor`, `nit`, `uncertain`
- Add small parse helpers such as `ReviewCoreStatus.from_wire(value: str)`.
  - Unknown values should remain serializable.
  - Prefer returning the raw string for unknowns over failing closed where current code passes unknown through.
- Add a shared text-read helper (for example `read_finding_text(path) -> str`) so callers with custom segment logic can reuse UTF-8-tolerant file reads without adopting `parse_findings` block splitting.

### UPDATED: python/review_and_fix.py

Adopt the shared parser and status enum without changing emitted output.

- Replace `_FINDING_RE` based block scans with `parse_findings` in:
  - `_count_findings`
  - `_extract_finding_block`
- Use `parse_findings(..., boundary="finding_heading")` for `_filter_in_scope` only.
  - Do **not** route `_filter_in_scope` through the default `any_heading` splitter.
- Use `parse_findings(..., boundary="any_heading")` for `_extract_finding_block` and other call sites that already stop at the next interior `### ` heading.
- **Do not** route `_nit_count` through `parse_findings` block splitting.
  - Today's `_nit_count` uses a dedicated line scan with different segment semantics than either boundary mode.
  - Preserve today's rules exactly:
    - A segment is active from a `### FINDING_N:` line until the next `_FINDING_RE` match or an interior `### ` heading.
    - Count at most one `- **Severity**: nit` per active segment.
    - When an interior `### ` heading ends a segment, lines after that heading and before the next `### FINDING_N:` are outside any segment and must not contribute to the nit total.
    - Do not count every nit line in a finding body and do not treat `boundary="finding_heading"` whole-finding blocks as nit segments.
  - Reuse the shared UTF-8-tolerant file read helper from `review_types` if helpful; keep the segment loop local to `_nit_count`.
- Rewrite `_filter_in_scope` to preserve leading preamble.
  - Copy any text before the first `### FINDING_N:` line verbatim into the output.
  - Parse only finding blocks with `boundary="finding_heading"`.
  - Filter parsed `Finding` blocks for `[OUT_OF_SCOPE]` / `[OOS]` heading tags.
  - Re-emit accepted in-scope blocks using each caller's existing whitespace rules.
- Keep `_extract_finding_block` behavior.
  - Read `Finding.block` raw from the parser (`boundary="any_heading"`); the block includes the heading line.
  - Preserve line structure and force a trailing newline when non-empty, as today.
- Keep `_HIGH_RE` and preserve today's **line-sum** semantics for `_high_severity_count`.
  - Count every `_HIGH_RE` line match across the scanned text.
  - Do not switch to "one per finding block" counting.
  - If moving the scan onto `Finding.block` slices, sum matches per block and still count preamble/section lines outside finding blocks when today's whole-file scan would.
- Convert core status comparisons to `ReviewCoreStatus` where values come from `REVIEW_CORE_STATUS`.
  - Convert `_SETTLING_CORE_STATUSES` and the Step-5 status branch (`panel-failed`, `aggregator-validation-exhausted`, `main-agent-vote-required`, `fix-required`, `cap-reached`, `prune-skipped`, `zero-findings`, `ok`) to enum-backed comparisons.
  - Keep unknown status passthrough behavior.
  - Emit `REVIEW_CORE_STATUS` and result status as the same strings as today.
- Keep `RoundResult` public behavior stable.
  - If changing `core_status` type causes churn, use `ReviewCoreStatus | str` internally and serialize with a helper.

### UPDATED: python/review_aggregate.py

Use `Finding` blocks for existing finding-file operations.

- Replace `_FINDING_BLOCK_RE` uses with `parse_findings` where the input is a file.
  - Use default `boundary="any_heading"` unless a call site already matched FINDING-only grouping.
- For text-only helpers, route through the same parser implementation rather than keeping a second regex.
- Keep `.strip()` only at call sites that already strip today (for example `_finding_blocks`).
  - Do not assume one global `Finding.block` normalization fits all outputs.
  - `Finding.block` includes the heading line; caller-local strip/re-emit rules stay unchanged.
- Update:
  - `_finding_blocks`
  - `_count_finding_blocks`
  - `_finding_id_from_block`
  - `_input_blocks`
  - `_output_blocks`
  - `_renumber_findings`
  - prune-nit block partitioning
- Keep `_OOS_BLOCK_RE` unless an OOS parser already exists in the new module.
  - Do not broaden this change into an OOS format refactor.
- Preserve exact output spacing for aggregate, prune, and renumber outputs.

### MAY_UPDATE: python/review_pipeline.py

Only change this file if the current branch still contains a duplicate parser for the same `### FINDING_N:` finding-file format.

- Do not change collection output generation just to use `Finding`.
- Do not alter reviewer output parsing.
- If a same-format scan remains, replace it with `parse_findings`.

### UPDATED: python/review_tally.py

Adopt enums for vote and severity handling only; keep mixed OOS/FINDING scans local.

- Replace hard-coded vote and severity membership checks with the shared enums.
- Keep TSV cells as strings.
- Keep `voting.parse_judge_vote` return compatibility unless a contained internal helper can use enums without affecting callers.
- **Do not** route `_seed_oos_seq` through `parse_findings`.
  - `_seed_oos_seq` counts both `### OOS_N:` and `### FINDING_N:` blocks in `accumulated-oos.md` via a local line scan (`^###[ \t]+(OOS_[0-9]+:|FINDING_[0-9]+:)`).
  - `parse_findings` recognizes only `### FINDING_N:`; adopting it here would under-count blocks and under-seed `oos_seq`, risking OOS renumber collisions with existing IDs.
  - Leave `_seed_oos_seq` on its current mixed OOS/FINDING line scan unless a dedicated OOS-aware parser is added and byte-parity tested for `accumulated-oos.md` seeding.
- Limit any `parse_findings` adoption in this file to **FINDING-only** block scans that do not also match `OOS_N` headings.
  - After inspection, if no such FINDING-only scan remains beyond `_seed_oos_seq`, make no parser adoption changes here.
- Avoid replacing `voting.split_ballot` unless needed, because it also handles `OOS_N` ballot items.
- Avoid replacing OOS-specific block helpers (for example `emit-tally` OOS rebuild paths) unless a dedicated OOS parser is added and tested.

### UPDATED: python/voting.py

Convert the named vote and severity sets to the shared enums while preserving public APIs.

- Import `JudgeSeverity` and `ReviewVote` from `review_types`; do **not** define a second `JudgeSeverity` in this module.
- Replace `_SEVERITY_VALUES`, `SEVERITY_BLOCKER`, and `SEVERITY_MAJOR` with enum-backed values.
- Keep `HIGH_SEVERITIES` limited to `blocker` and `major` only.
- Keep exported constants as strings if tests or callers import them (re-export string aliases from enum `.value` where needed).
- Keep `parse_judge_vote` returning `tuple[str, str, str, str, str]`.
- Keep `classify_result` returning the same strings.
- Keep `valid_panel_severity` returning `str | None`.
  - Use enums only behind that public boundary.
  - `SEVERITY=nit` and `SEVERITY=uncertain` must continue to validate and tally exactly as today.
- Use enum values only for validation and internal comparisons.

### UPDATED: python/run_logs.py

Make `Manifest` own JSON parsing and emission on every mutation, creation, and read path.

- Add one module-level v2 key registry (not one flat exclude set reused for both directions).
  - Classify each v2 key by role: core mapped field, reserved top-level round-trip, extension `extra`, extra-promotable reserved.
  - Derive parse filters and emit/merge filters from that registry.
  - Preserve today's asymmetry: `stalled_at_step` is excluded from parse into core attrs and `extra`, but is **not** excluded from merge/emit promotion from `extra` to top-level JSON.
  - Include `pr_number` and other promotable reserved keys in the same role model.
- Extend `Manifest` enough to preserve v2 metadata.
  - Keep current core attrs.
  - Add `reserved: dict[str, Any] = field(default_factory=dict)` holding every v2 reserved key named in the registry (including mutable `stalled_at_step`).
    - Use `default_factory=dict` so existing constructor call sites (for example `finalize.teardown` fallback `Manifest(status=..., version="1", run_id=..., steps_ran={})`) keep working without a `reserved=` argument.
    - `from_json` must copy reserved data into a fresh dict (no shared mutable alias with parsed input).
  - Keep `extra` for non-reserved extension keys only.
  - Document which reserved keys are immutable vs mutable.
- Add:
  - `@classmethod Manifest.from_json(cls, data: Mapping[str, Any]) -> Manifest`
  - `Manifest.to_json(existing: Mapping[str, Any] | None = None) -> dict[str, Any]`
- Replace `_dict_to_manifest(data)` with `Manifest.from_json(data)`.
- Replace `_manifest_to_dict(manifest)` and `_manifest_v2_merge(...)` with `manifest.to_json(existing=...)`.
- Route every v2 write through:
  - read raw JSON dict at the file boundary
  - `manifest = Manifest.from_json(data)`
  - apply existing allowed updates, immutable-field checks, and `steps_ran.*` semantics (including `update_manifest` kwargs and `_update_manifest_v2` direct key writes)
  - write `manifest.to_json(existing=data)` via `_write_manifest_v2`
- Explicit `update_manifest` / `_update_manifest_v2` reserved-key routing after `Manifest.reserved`:
  - Copy `reserved` from the loaded manifest before applying updates.
  - Route registry-classified top-level keys (`stalled_at_step`, `pr_number`, and other reserved/promotable keys) into `manifest.reserved`, not `extra`.
  - Keep non-reserved unknown kwargs in `extra` only when the registry classifies them as extension keys.
  - Rebuild with `to_json(existing=read_data)` so promoted top-level keys and mutable reserved fields (`stalled_at_step`) round-trip exactly as today's `_manifest_v2_merge` does.
- Required write paths:
  - `_write_manifest` / `update_manifest` read-merge-write
  - `_update_manifest_v2`
  - `larch_log_manifest_main`
  - post-merge refresh (`flush_logs_post` / `finalize_postmerge_logs`)
  - terminal reconcile (`_reconcile_terminal_manifest_from_ctx`)
  - pre-commit refresh
  - `_commit_run` updated_at-only touch (`_update_manifest_v2(manifest, {})` before copying larch-logs into the repo)
- Route v2 creation through `Manifest`:
  - Move `_synthesize_manifest_v2` under `Manifest` as a factory (or equivalent) that builds a `Manifest`, then emit with `to_json(existing=None)` before `_write_manifest_v2`.
  - Make `init_run`, `_recover_manifest_from_run_dir`, and `larch_log_init_main` use that factory instead of raw dict assembly.
  - Make `load_or_recover_manifest_checked` JSONDecodeError and missing-manifest recovery branches (corrupt-json rewrite and run-dir recovery rewrite) build via the same Manifest factory, then persist with `Manifest.to_json(existing=None)` before `_write_manifest_v2`.
- Convert remaining in-memory manifest read paths through `Manifest.from_json` immediately after JSON load:
  - `_step9a1_heuristic`: replace `json.loads(...)` + dict helpers with `Manifest.from_json(_read_manifest_v2(...))` (or equivalent read-then-from_json).
  - `verify-completeness` (`verify_completeness_main`): after `_read_manifest_v2`, bind `manifest = Manifest.from_json(manifest_data)` and use `Manifest` accessors for the rest of the function.
  - Replace `_manifest_field`, `_manifest_step9a1_explicitly_skipped`, `_manifest_step9a1_explicitly_ran`, `_manifest_steps_ran_empty`, and `_manifest_steps_ran_nonempty_without_step9a1` dict helpers with `Manifest`-based accessors (or thin wrappers on `Manifest` that preserve today's return shapes).
  - Pass `Manifest` (or `manifest.to_json()` only at external-helper boundaries) through `_verify_condition_reached` and `_final_summary_bail_signal_without_pr_evidence` instead of keeping a parallel dict representation.
  - Keep `_read_manifest_v2` and `_write_manifest_v2` as the only routine producers/consumers of raw manifest dicts on disk.
- v2 emission rules:
  - Never emit v1 key names `version` or `created_at` on v2 files.
  - Map `Manifest.version` → `schema_version` and `Manifest.created_at` → `started_at`.
  - Emit v1-only keys only when `schema_version != 2`.
  - Require `to_json(existing=read_data)` on every v2 update/merge write path.
  - Never use `to_json(existing=None)` on update paths where reserved keys from disk would be lost.
- Keep `init_run`, recovery, and update behavior byte-compatible.
  - `to_json` must preserve `schema_version`, `skill`, `run_id`, `started_at`, immutable fields, reserved fields, and unknown extension keys.
  - `updated_at` should change only where it changes today.
  - `status`, `steps_ran`, `issue_number`, recovery fields, and mutable reserved keys such as `stalled_at_step` must land in the same JSON keys as today.

### MAY_UPDATE: python/finalize.py

Only if constructor-default changes are insufficient.

- Prefer `Manifest.reserved: field(default_factory=dict)` so the existing fallback constructor at `finalize.teardown` keeps working without edits.
- If a required `reserved` field is introduced without a default, pass `reserved={}` at the fallback `run_logs.Manifest(...)` site.

### UPDATED: python/test_review_and_fix.py

Add focused parser adoption coverage.

- Cover counting, extraction, and high-severity counting through the new parser path.
- Add `_nit_count` byte-parity coverage separate from parser block splitting:
  - fixture with `- **Severity**: nit`, an interior `### Details` subheading, and optional duplicate nit lines after the interior heading
  - assert `_nit_count` stays `1` (interior `### ` ends the active segment; post-heading nit lines are ignored)
  - assert `converged-small-changes` routing unchanged for the representative accepted-count / nit-total combination
- Add `_filter_in_scope` byte-parity coverage:
  - preamble before `### FINDING_1:`
  - interior generic `### Subsection` / `### Details` / `### Context` heading inside one finding
  - nested `### FINDING_2:` token inside a body to pin current block-boundary behavior
  - OOS heading case
- Add `_high_severity_count` parity fixture where one finding has two `_HIGH_RE` line hits and `HIGH_SEVERITY_COUNT` stays `2`.
- Add fixture with a matching `_HIGH_RE` line outside any finding block if preamble scanning remains part of the gate.
- Add UTF-8 tolerance coverage: malformed bytes in a finding file still parse/count without raising.
- Add coverage that `Finding.block` includes the heading line for extraction/aggregate parity.

### UPDATED: python/test_review_aggregate.py

Pin aggregate parser parity.

- Add or update tests for:
  - prune-nit code mode
  - prune-nit plan mode
- Assert output bytes for representative renumber/prune cases stay unchanged.
- Assert `.strip()` behavior remains caller-local, not parser-global.
- Assert `Finding.block` heading inclusion preserves prune/renumber bytes.

### UPDATED: python/test_review_tally.py

Pin enum-backed vote and severity behavior; preserve OOS seeding.

- Test accepted/rejected/neutral tally output still matches current `KEY=value` and TSV strings.
- Test invalid vote and severity values still sanitize to empty values.
- Test `JUDGE_ERROR`, `YES`, `NO`, and accepted severity scoring stay unchanged.
- Test `SEVERITY=nit` and `SEVERITY=uncertain` voter lines still validate and tally exactly as before.
- Add `_seed_oos_seq` byte-parity coverage:
  - fixture `accumulated-oos.md` with mixed `### OOS_N:` and `### FINDING_N:` headings
  - assert seed count matches today's local line-scan behavior (both heading kinds counted)
  - assert accepted OOS renumbering does not collide with pre-existing IDs when the accumulated file already contains OOS blocks

### UPDATED: python/test_voting.py

Add direct enum compatibility tests.

- Assert `parse_judge_vote` still returns strings.
- Assert `valid_panel_severity` still returns `str | None`.
- Assert exported severity constants compare equal to existing literal strings.
- Assert `valid_panel_severity("nit")` and `valid_panel_severity("uncertain")` still return those strings.
- Assert invalid values still sanitize or default as before.
- Assert `JudgeSeverity` is imported from `review_types` (single enum definition).

### UPDATED: python/test_run_logs.py

Pin manifest representation and byte stability.

- Add direct `Manifest.from_json(...).to_json(existing=original)` round-trip tests for v2 manifests.
- Assert `json.dumps(manifest.to_json(existing=...), indent=2, sort_keys=True) + "\n"` matches the previous committed shape.
- Assert v2 output never contains `version` or `created_at`.
- Cover v2 extension keys and reserved keys.
- Cover legacy v1 input if current tests still exercise it.
- Cover `update_manifest` preserving immutable v2 fields, extension keys, and mutable reserved keys such as `stalled_at_step`.
- Add regression that fails if the v2 reserved-key registry drifts between parse and emit filters.
- Add byte-parity coverage for `_update_manifest_v2` and terminal manifest reconcile paths.
- Pin `update_manifest` → `_write_manifest` read-merge-write: `stalled_at_step` and `pr_number` promotion from `extra` survives when `existing=read_data` is supplied.
- Pin `update_manifest(stalled_at_step=...)` writes the new stall step to top-level JSON (not a stale value from `existing` when `reserved` was left stale).
- Pin post-merge refresh (`flush_logs_post`) byte shape for `pr_number` top-level promotion.
- Add coverage that `_step9a1_heuristic` and `verify-completeness` read manifests through `Manifest.from_json` (no parallel dict-only code path left in those functions).
- Add byte-parity coverage for `load_or_recover_manifest_checked` corrupt-json recovery rewrite through the Manifest factory.
- Add byte-parity coverage for `_commit_run` updated_at-only rewrite preserving reserved keys, extension keys, and promotable fields such as `pr_number` and `stalled_at_step`.

### UPDATED: python/test_finalize.py

Pin stall teardown manifest writes through the new Manifest path.

- Keep `test_teardown_stall_preserves_tmpdir_and_writes_manifest` green.
- Assert `manifest["stalled_at_step"]` remains the stall step after `finalize.teardown` writes through `update_manifest` / `_write_manifest`.

## Edge cases

- Missing finding files should keep returning zero findings.
- Malformed UTF-8 in finding files should keep parsing via `errors="replace"` instead of raising.
- Malformed or duplicate finding headings should keep existing caller behavior.
- `Finding.block` must include the `### FINDING_N:` heading line; body-only slices break aggregate prune/renumber and extraction parity.
- Interior `### ` subheadings inside a finding must stay inside that finding for `_filter_in_scope`.
- Interior `### ` subheadings must end the active nit-count segment in `_nit_count`; nit lines after them must not increment the total.
- Preamble text before the first finding must survive in-scope filtering output.
- OOS blocks should not be silently converted into in-scope findings.
- `_seed_oos_seq` must count both `OOS_N` and `FINDING_N` headings in `accumulated-oos.md`; FINDING-only parsing must not replace this helper.
- Unknown review core statuses should keep passing through instead of crashing.
- `ReviewCoreStatus` must cover all current `REVIEW_CORE_STATUS` tokens used by `_SETTLING_CORE_STATUSES` and the Step-5 status branch.
- Invalid vote or severity tokens should sanitize exactly as today.
- `valid_panel_severity` must not start returning enum instances.
- `JudgeSeverity` must have a single definition in `review_types`; `voting.py` imports it.
- Judge severities accepted by `parse_judge_vote` and `valid_panel_severity` are `blocker`, `major`, `minor`, `nit`, and `uncertain`.
- `HIGH_SEVERITIES` remains `blocker` and `major` only.
- Markdown severities (`blocking|important|latent|nit`) must not share one enum with judge severities.
- `Manifest.reserved` must default safely for constructor call sites that omit `reserved=` (for example `finalize.teardown`).
- Legacy manifest JSON should still load if current callers/tests depend on it.
- V2 manifest extension and reserved keys must not be dropped when updating status, steps, or `stalled_at_step`.
- `to_json(existing=None)` on a v2 update path must not be used when reserved keys from disk would be lost.
- Parse-exclude and emit-exclude roles must stay distinct; a single flat constant must not replace the registry.
- `stalled_at_step` must round-trip through `Manifest.reserved` and promote from `extra` on emit exactly as today's `_manifest_v2_merge` does.
- `update_manifest` kwargs for registry-classified reserved keys must update `reserved`, not only `extra`, before `to_json(existing=read_data)`.
- V2 creation paths must not bypass `Manifest.to_json`, or reserved-key handling will drift between init and update.
- `load_or_recover_manifest_checked` recovery rewrites must not bypass the Manifest factory.
- `_commit_run` updated_at-only manifest touch must preserve reserved/extension/promotable keys on disk.
- `_step9a1_heuristic` and `verify-completeness` must not keep a second dict-only manifest representation after `_read_manifest_v2`.

## Failure modes

- **Manifest byte drift:** `to_json` may reorder, drop, rename fields, or emit v1 keys on v2 files. Pin with exact JSON text tests on every write path.
- **Reserved-key loss:** dropping `skill`, `operator_cwd`, `flags`, or mutable `stalled_at_step` when `existing` is omitted. Pin `from_json` + `to_json(existing=original)`, `update_manifest`, and `finalize.teardown` byte tests.
- **Parse/emit registry drift:** reusing one exclude set for both directions can drop `stalled_at_step` on parse or block promotion on emit. Pin registry parity test and stall/`pr_number` byte cases.
- **Update routing drift:** leaving `stalled_at_step=` kwargs in `extra` while `reserved` stays stale can re-emit the old top-level stall step from `existing`. Pin `update_manifest(stalled_at_step=...)` and `test_finalize.py::test_teardown_stall_preserves_tmpdir_and_writes_manifest`.
- **Init/update divergence:** raw dict creation outside `Manifest.to_json` can emit different reserved defaults than update paths. Route `init_run`, recovery, `larch_log_init_main`, and `load_or_recover_manifest_checked` recovery rewrites through the Manifest factory.
- **Commit-time drift:** `_commit_run` updated_at-only rewrite omitted from the Manifest path can drop reserved/extension keys during run-log commit. Pin updated_at-only byte test.
- **Dual manifest representation:** leaving `_step9a1_heuristic` or `verify-completeness` on raw dict helpers reintroduces drift from write paths. Pin Manifest adoption in those read paths.
- **Constructor breakage:** required `reserved` without a default breaks `finalize.teardown` fallback construction before manifest tests run. Use `field(default_factory=dict)` or explicit `reserved={}` at the call site.
- **Parser boundary drift:** headings mentioned inside finding bodies may split differently across call sites. Pin FINDING-only and any-heading modes separately; keep `_nit_count` on its own segment loop.
- **Heading exclusion drift:** body-only `Finding.block` breaks prune/renumber and extraction bytes. Pin heading-inclusive block contract in aggregate and extraction tests.
- **Nit-count drift:** adopting `parse_findings` block splitting or counting every nit line can change `converged-small-changes` routing. Pin interior-`###` truncation and single-count fixture.
- **Preamble loss:** `_filter_in_scope` rewrite may omit leading non-finding text and skip coder work. Pin accepted-in-scope output bytes.
- **Block normalization drift:** one shared `.strip()` on `Finding.block` may change aggregate renumber/prune bytes or `_extract_finding_block` trailing-newline shape. Keep normalization caller-local.
- **High-severity gate drift:** switching from line-sum to per-block counting may change round continuation. Pin `HIGH_SEVERITY_COUNT=2` fixture.
- **UTF-8 decode regression:** centralizing reads without `errors="replace"` can turn malformed reviewer files into hard failures. Pin tolerant-read test.
- **Enum leakage:** writing enum reprs instead of values can break `KEY=value`, TSV, or JSON consumers. Serialize through `.value` or `str(...)` helpers and test outputs.
- **Dual enum drift:** defining `JudgeSeverity` in both `review_types` and `voting.py` can diverge member sets and break tally parity. Pin single-source import in `test_voting.py`.
- **Judge severity regression:** omitting `nit` or `uncertain` from `JudgeSeverity` can sanitize valid voter output to empty. Pin `valid_panel_severity` and tally cases for both tokens.
- **OOS seq under-seed:** routing `_seed_oos_seq` through FINDING-only `parse_findings` drops `OOS_N` blocks from the count, under-seeding `oos_seq` and renumbering accepted OOS items onto existing IDs. Keep the mixed OOS/FINDING line scan; pin with mixed-heading fixture.
- **OOS regression:** replacing too much tally parsing may break `OOS_N` ballot handling. Keep OOS-specific code unless a dedicated parser is added and tested.

## Testing strategy

Run focused tests first:

- `python3 -m pytest python/test_run_logs.py`
- `python3 -m pytest python/test_finalize.py::test_teardown_stall_preserves_tmpdir_and_writes_manifest`
- `python3 -m pytest python/test_review_and_fix.py`
- `python3 -m pytest python/test_review_aggregate.py`
- `python3 -m pytest python/test_review_tally.py`
- `python3 -m pytest python/test_voting.py`

Then run required repo checks for Python changes:

- `make py-lint`
- `make py-test`
- `make lint`

## Non-goals

- Do not change finding markdown layout.
- Do not change any `KEY=value` grammar.
- Do not change committed `manifest.json` bytes.
- Do not sweep unrelated string sets.
- Do not unify markdown and judge severity vocabularies into one enum.
- Do not refactor OOS parsing beyond what is needed to preserve existing behavior.
- Do not add a dedicated OOS parser or replace `_seed_oos_seq` in this change.
- Do not split review pipeline god functions in this change.

## Acceptance

- One `Finding` type and one `parse_findings(path, *, boundary=...)` parser live in `python/review_types.py`; `review_and_fix` and `review_aggregate` adopt them, and the duplicate `### FINDING_N:` regex re-scans on the same finding-file format are retired (kept only where no same-format scan remains).
- `Manifest.from_json` / `Manifest.to_json` is the sole manifest representation; `_dict_to_manifest`, `_manifest_to_dict`, and `_manifest_v2_merge` are deleted; the duplicated v2 exclude-set literal collapses to one role-classified key registry.
- The named internal sets are `StrEnum` (`ReviewCoreStatus`, `ReviewVote`, `JudgeSeverity`), each member `.value` equal to today's literal; `JudgeSeverity` has a single definition in `review_types`, imported by `voting.py`.
- Byte-stable on the wire and on disk: committed `manifest.json` bytes (`sort_keys=True`, `indent=2`, trailing newline), every `KEY=value` format, and the `### FINDING_N:` markdown layout are unchanged.
- `make py-lint`, `make py-test`, and `make lint` pass (parity and unit tests green).

review_status: complete
rounds_completed: 5
diff_added: 780
diff_deleted: 330
mechanical_churn: false
diff_lines: 1110
