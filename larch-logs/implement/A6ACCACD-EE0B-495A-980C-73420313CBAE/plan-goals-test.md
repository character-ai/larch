## Goal
Implement issue #5871: [IMPLEMENTING] md-to-py-X: instrument realized reference-read cost (heatmap + realized-cost).

## Implementation Plan
## Plan

## Approach

Add a small run-log corpus helper, teach transcript parsing to count real reference `Read` events per run (including the committed v3 corpus), preserve sanitized reference `Read` blocks in future renders, and capture design session transcripts before log publish so new design runs become measurable.

Keep the change measurement-only:
- Do not edit reference prose.
- Do not rewrite committed `larch-logs/`.
- Do not infer reads from narration, file names in findings, or SKILL.md directives.

Parse only `Read` tool invocations whose normalized repo-relative path is:
- `skills/**/references/*.md`
- `skills/shared/*.md`

Support these transcript shapes:
- Raw Claude Code JSONL: `message.content[]` contains `{"type":"tool_use","name":"Read","input":{"file_path":...}}`.
- Rendered v3 JSONL: `blocks[]` contains `{"type":"tool_call","name":"Read","input":{"file_path":...}}` (the shape already present in committed implement logs).
- Future rendered JSONL after renderer update: sanitized `blocks[]` `tool_use` `Read` blocks with normalized `input.file_path` only.
- Existing v3 transcripts with no `Read` blocks contribute zero reference reads for that run.

Extend path normalization so redacted committed paths work:
- Strip `config.REDACTED_OPERATOR_REPO` (`<OPERATOR_REPO_PATH>`) prefix before the angle-bracket guard.
- Keep absolute repo paths and installed plugin cache paths already handled by the cache regex.

Update `render-session-transcript` so future committed transcripts keep sanitized `Read` invocations for runtime reference files only. Store no file contents. Store only the tool name and normalized `file_path`.

**Materialize the Claude source snapshot before design capture.** Production `/design` never pre-seeds `LARCH_CLAUDE_SOURCE_FILE` in `source-env.sh` today (`WRITE_DESIGN_ENV_KEYS` omits it; Step 0 does not run `token claude-source`). Mirror implement bootstrap at publish time:
- Load `SESSION_ID` from `$DESIGN_TMPDIR/source-env.sh` via `design_step0_env._load_source_env` (not `session-env.sh`).
- When `$DESIGN_TMPDIR/claude-source.env` is absent or empty, invoke `python/cli.py token claude-source` with `LARCH_TOKEN_SESSION_ID` set to that `SESSION_ID`, atomically write stdout KV lines to `$DESIGN_TMPDIR/claude-source.env` (same snapshot contract as `bootstrap._write_claude_source_snapshot`).
- Pass the snapshot path as `--source-file` to `run-log capture-transcript`.
- After a successful snapshot, refresh `source-env.sh` with `LARCH_CLAUDE_SOURCE_FILE=$DESIGN_TMPDIR/claude-source.env` via a targeted `session write-design-env` extension (`--claude-source-file`) so wrapper allowlists and later fences see the same path implement uses.

Add design transcript capture before `design log-publish`, mirroring implement Step 7a defer-commit semantics but landing at the publish-visible tmpdir root:
- **Mandatory stale-root removal:** before any capture attempt, remove any preexisting `$DESIGN_TMPDIR/session-transcript.jsonl`. If removal fails, abort publish before `design log-publish` so a prior run or failed attempt cannot be republished.
- Render and write `$DESIGN_TMPDIR/session-transcript.jsonl` only after successful capture **and** hoist; on capture skip paths, keep the root file absent.
- **Publish topology:** `design_log_publish_flow._publish_design_logs` copies each top-level `$DESIGN_TMPDIR` child flat into `larch-logs/design/<run_id>/`. The transcript must exist at `$DESIGN_TMPDIR/session-transcript.jsonl`, not under a nested staging subtree.
- Invoke `python/cli.py run-log capture-transcript` with `--defer-commit true`, then **hoist** the staged file from `<log-root>/design/<run-id>/session-transcript.jsonl` to `$DESIGN_TMPDIR/session-transcript.jsonl` via atomic replace **only when capture reports success**. If capture succeeds but hoist fails, delete any partial root file and **abort publish** (do not proceed to `log-publish` with a missing or stale transcript when capture succeeded).
- When capture skips (`source-file-missing`, `transcript-path-missing`, `render-failed`, `render-empty`, snapshot materialization failure, etc.), ensure root `session-transcript.jsonl` stays absent and publish still proceeds (warning only for the skip itself).
- If capture leaves a staging `larch-logs/` subtree under `$DESIGN_TMPDIR`, add `larch-logs` to `_PUBLISH_EXCLUDE_DIRS` so publish cannot copy nested staging artifacts.

Guard transcript reads at measurement time:
- Before opening `session-transcript.jsonl` inside a safe run dir, reject symlinked transcript files and require resolved path containment within the already-validated run directory (same containment pattern as `cleanup_implement_logs._contained` / corpus run-dir checks).

Guard run-directory enumeration at measurement time:
- The committed corpus contains manifest-less children such as `larch-logs/design/46595BE9-8272-4F3E-858D-12E7DB2D3818`, `larch-logs/implement/hEI3r1`, and `larch-logs/shared/archetypes`. Do not count these as runs.
- `run_dirs()` returns only symlink-safe, containment-validated directories that also pass `is_valid_run_dir()`: a regular (non-symlink) `manifest.json` whose contents parse as a **non-empty JSON object with numeric `issue_number` > 0**, matching the manifest gate `report_tokens_scan._record()` already applies before accepting a run.
- Extract a shared manifest-acceptance helper (for example `manifest_accepts_run(manifest: Mapping) -> bool` or `load_run_manifest(run_dir) -> dict | None`) used by both `_record()` and `is_valid_run_dir()` so scan and measure commands walk the same denominators.
- Emit optional warnings when skipping manifest-less or invalid-manifest children, matching `report_tokens_scan` warning style.

For metrics:
- `measure-references-heatmap` emits one row per `skill + reference_path`.
- Include `reads_observed`, `runs_observed`, `loads_per_run`, `bytes`, and `tokens`.
- Define `runs_observed` as the count of validated run directories from the shared corpus helper for that skill, regardless of transcript presence.
- Define `loads_per_run` as `reads_observed / runs_observed` (0 when `runs_observed` is 0).
- `measure-realized-cost` computes each run as `SKILL.md tokens + sum(tokens for each observed reference Read event in that run)`.
- Keep `realized_tokens` as the total across runs.
- Make `tokens_per_invocation` the average realized tokens per run.
- Add supporting columns such as `skill_md_tokens`, `reference_tokens_per_invocation`, and `reference_reads_observed`.

Use batched `_tiktoken_count_texts` and cache token counts by path so repeated reads do not re-tokenize the same file.

**Acceptance (aligned with deliverables).**
- **Binding in CI:** pytest fixtures prove reference-read extraction and realized-cost math for design paths (`approval-gates.md`, `plan-review.md`, `finalize-step5.md`) using raw `tool_use`, v3 `tool_call`, future rendered `blocks[]` `tool_use`, absolute paths, cache paths, and `<OPERATOR_REPO_PATH>`-redacted paths. Heatmap tests assert non-zero `reads_observed` for **all three** acceptance-named design references individually.
- **Shared scope in CI:** a dedicated transcript fixture includes a `Read` of `skills/shared/*.md` (for example `skills/shared/topology.md`) and asserts non-zero `reads_observed` / correct `loads_per_run` in the heatmap plus matching `reference_reads_observed` / `reference_tokens_per_invocation` in realized-cost output.
- **Corpus hygiene:** heatmap and realized-cost fixtures prove manifest-less sibling directories **and** directories with `{}` or issue-less manifests do not inflate `runs_observed` or `invocations`.
- **Design publish hygiene:** publish-path tests exercise the production snapshot path (`token claude-source` → `claude-source.env` → `capture-transcript`) without hand-seeding `LARCH_CLAUDE_SOURCE_FILE` in fixtures. Tests prove mandatory stale-root removal, that capture does not read `session-env.sh`, that publish aborts when stale-root removal fails or capture succeeds but hoist fails, and that root `session-transcript.jsonl` exists only after successful capture+hoist.
- **Committed implement corpus:** post-merge smoke may show non-zero implement reference reads from existing v3 `tool_call` transcripts without log backfill.
- **Committed design corpus:** historical design runs without `session-transcript.jsonl` remain zero-reference by design; non-zero design heatmap and above-floor design realized-cost require a new design run after the capture hook lands (not backfilled in this child).

## Files to modify/create

### NEW: python/larch/report/run_log_corpus.py

Create a tiny shared helper for safe run-directory enumeration.

- Move the symlink and containment checks now embedded in `report_tokens_scan._run_dirs` into this module.
- Expose `run_dirs(log_base: Path, warn: Callable[[str], None] | None = None) -> list[Path]` returning only directories passing safety checks **and** `is_valid_run_dir(run_dir)`.
- Add `is_valid_run_dir(run_dir: Path) -> bool` delegating manifest acceptance to a shared helper that mirrors `report_tokens_scan._record()`:
  - `run_dir / "manifest.json"` must be a regular file (not a symlink).
  - Contents must parse as a JSON object.
  - Manifest must be non-empty **or** carry a positive numeric `issue_number` (same empty-manifest rejection as `_record`).
  - `issue_number` must parse to an integer `> 0`.
- Add `load_run_manifest(run_dir: Path) -> dict[str, Any] | None` (or equivalent) as the single manifest gate used by both `is_valid_run_dir()` and `report_tokens_scan._record()` so scan and measure denominators stay aligned.
- Warn (when `warn` is provided) on manifest-less or invalid-manifest children skipped during enumeration, e.g. `manifest for {path} lacks numeric issue_number; skipping`.
- Add `safe_transcript_path(run_dir: Path) -> Path | None` returning `run_dir / "session-transcript.jsonl"` only when the file is a regular file (not a symlink) and resolves inside the already-safe `run_dir`.
- Keep `report_tokens_scan.scan()` record output unchanged: validated `run_dirs()` is a superset filter of what `_record()` already accepted via manifest checks.
- Do not import `tokens.py` or `report_tokens_scan.py` from this helper.

### UPDATED: python/larch/report/report_tokens_scan.py

Replace the private `_run_dirs` implementation with the shared helper.

- Replace inline manifest acceptance in `_record()` with the shared `load_run_manifest` / `manifest_accepts_run` helper from `run_log_corpus.py` (preserve existing warning text and ordering as much as practical).
- Keep scan behavior unchanged except for the helper location and manifest-less / invalid-manifest directory exclusion at enumeration time.
- This makes the measurement commands and `/report-tokens analyze` walk the same committed run-log corpus rules.

### UPDATED: python/larch/rendering/render_session_transcript.py

Preserve sanitized Read tool invocations for runtime reference files.

- Add a helper that normalizes a Read `file_path` to repo-relative form when it targets:
  - `skills/**/references/*.md`
  - `skills/shared/*.md`
- Reuse the same scope rules as the measurement normalizer (including `REDACTED_OPERATOR_REPO`, absolute repo paths, and plugin-cache paths).
- In assistant rendering, emit only safe Read reference tool-use blocks, for example:
  - `{"type":"tool_use","name":"Read","input":{"file_path":"skills/design/references/approval-gates.md"}}`
- Continue dropping all other tool calls.
- Update the module docstring and policy note so the transcript contract no longer claims all tool calls are omitted.
- Do not include tool results, file contents, tmpdir paths, offset/limit fields, or arbitrary non-reference reads.

### UPDATED: python/larch/state/session_env.py

Extend design env writer so publish can persist the Claude source snapshot path.

- Add `LARCH_CLAUDE_SOURCE_FILE` to `WRITE_DESIGN_ENV_KEYS`.
- Add optional `--claude-source-file` to `session write-design-env`; when set, emit `LARCH_CLAUDE_SOURCE_FILE=<path>` into `source-env.sh` alongside existing keys.
- Keep validation consistent with implement `write-env` (`_validate_writer_keys` allowlist only).

### UPDATED: python/larch/design/design_publish.py

Capture design session transcripts before committed log publish.

- After plan write succeeds and before `design log-publish`, run a dedicated capture helper (inline or extracted) that:
  1. **Mandatory stale-root cleanup:** attempt to remove `$DESIGN_TMPDIR/session-transcript.jsonl`. On failure, return a publish-blocking error before `log-publish` (append bounded warning to `execution-issues.md`).
  2. Load `SESSION_ID` from `$DESIGN_TMPDIR/source-env.sh` using `design_step0_env._load_source_env` with an allowlist that includes `SESSION_ID`. Do not open `session-env.sh`.
  3. **Snapshot materialization:** when `$DESIGN_TMPDIR/claude-source.env` is absent or empty, invoke `python/cli.py token claude-source` with `LARCH_TOKEN_SESSION_ID=$SESSION_ID`, atomically write stdout to `$DESIGN_TMPDIR/claude-source.env` when `TRANSCRIPT_PATH=` is present (mirror `bootstrap._write_claude_source_snapshot`). Skip capture with warning when snapshot materialization fails.
  4. Refresh `source-env.sh` with `LARCH_CLAUDE_SOURCE_FILE` pointing at the snapshot via `session write-design-env --claude-source-file ...` (other keys unchanged).
  5. When the snapshot path is present and non-empty, invoke `python/cli.py run-log capture-transcript` with:
     - `--source-file` set to `$DESIGN_TMPDIR/claude-source.env`
     - `--skill design`
     - `--run-id` from `--session-id`
     - `--log-root` pointing at `$DESIGN_TMPDIR/larch-logs` (staging root)
     - `--defer-commit true`
     - `--execution-issues-log` for bounded warnings on skip paths
     - `--warning-step-label` appropriate for design publish (for example `5c`)
  6. On successful capture only, **hoist** the staged transcript to `$DESIGN_TMPDIR/session-transcript.jsonl` with atomic replace. If hoist fails after capture success, delete any partial root file and **abort publish** before `log-publish`.
  7. On capture skip statuses or snapshot failure: ensure root `session-transcript.jsonl` remains absent; publish still proceeds (warning only).
- Relay `SESSION_TRANSCRIPT_STATUS=` lines to publish stdout when emitted.
- Mirror implement Step 7a defer-commit semantics so `design_log_publish_flow` commits the rendered `session-transcript.jsonl` with the rest of the run tree when present.

### UPDATED: python/larch/design/design_log_publish_flow.py

Exclude capture staging subtrees from publish copy.

- Add `larch-logs` to `_PUBLISH_EXCLUDE_DIRS` so any capture staging tree under `$DESIGN_TMPDIR/larch-logs/` is not copied flat into the committed run directory after hoist.

### UPDATED: python/larch/report/tokens.py

Add reference-read extraction and realized-cost accounting.

- Add a frozen dataclass for observed reference reads, with fields like `skill`, `run_id`, `run_dir`, and `reference_path`.
- Add helpers:
  - `is_in_scope_reference_path(rel: str) -> bool` for `skills/**/references/*.md` and `skills/shared/*.md` only.
  - normalize Read paths (strip `REDACTED_OPERATOR_REPO`, repo prefix, cache tail; reject escapes and unrelated `.md`).
  - iterate Read tool uses from:
    - raw `message.content[]` `tool_use` records;
    - rendered v3 `blocks[]` `tool_call` records;
    - future rendered `blocks[]` `tool_use` sanitized records.
  - collect reference reads per run.
  - open transcripts only through `run_log_corpus.safe_transcript_path` (skip symlink escapes and out-of-run resolves).
  - batch token-count repo paths with caching.
- Update `measure_references_heatmap()`:
  - walk `larch-logs/<skill>/` validated run dirs through the shared corpus helper;
  - derive `skill` from the log parent directory name;
  - count reads by `skill + reference_path`;
  - set `runs_observed` to the full validated run-dir count for that skill;
  - compute `loads_per_run = reads_observed / runs_observed`;
  - include token counts for each reference.
- Update `measure_realized_cost()`:
  - derive invocations from validated run dirs only (parent dir = skill);
  - calculate per-run realized tokens as skill floor plus observed reference read tokens;
  - count each validated run in `invocations` even when transcript is missing (zero reference tokens);
  - keep existing timing/manifest fallback only if needed for nonstandard logs;
  - emit average `tokens_per_invocation` and total `realized_tokens` plus `skill_md_tokens`, `reference_tokens_per_invocation`, and `reference_reads_observed`.
- Do not synthesize reads from prose. Historical design runs without transcripts remain zero-reference runs. Manifest-less pseudo-directories and issue-less manifests never enter denominators.

### UPDATED: python/tests/report/test_tokens.py

Extend measurement tests.

- Add a fixture repo with:
  - `skills/design/SKILL.md`
  - `skills/design/references/approval-gates.md`
  - `skills/design/references/plan-review.md`
  - `skills/design/references/finalize-step5.md`
  - `skills/shared/topology.md` (or another shared Markdown fixture under `skills/shared/*.md`)
  - a non-reference Markdown file that must be ignored.
- Test `measure_references_heatmap()` with raw Claude `tool_use` transcript records.
- Test v3 rendered `tool_call` `Read` parsing (committed implement shape).
- Test future rendered `blocks[]` `tool_use` `Read` parsing (sanitized design transcript shape).
- Test `<OPERATOR_REPO_PATH>/skills/...` paths normalize to repo-relative paths.
- Test absolute repo paths and plugin-cache-style paths normalize to repo-relative paths.
- Test non-reference Markdown Reads are ignored.
- Test `runs_observed` includes transcript-missing validated runs and `loads_per_run` uses that denominator.
- Test manifest-less sibling directories under a skill log root are excluded from `runs_observed`.
- Test directories with `{}` manifest or manifest missing `issue_number` are excluded from `runs_observed` and do not dilute `loads_per_run`.
- Assert non-zero `reads_observed` separately for `approval-gates.md`, `plan-review.md`, and `finalize-step5.md` in dedicated heatmap fixtures.
- Add a dedicated heatmap fixture whose transcript includes a `Read` of `skills/shared/topology.md` (or the chosen shared fixture) and assert non-zero `reads_observed` and correct `loads_per_run` for that `skill + reference_path` row.
- Add a realized-cost fixture that includes the same shared `Read` event and assert `reference_reads_observed` and `reference_tokens_per_invocation` reflect the shared file load (not only design `references/` paths).
- Test symlinked `session-transcript.jsonl` inside a run dir is skipped (zero reads, no escape read).
- Update `test_measure_realized_cost_writes_schema` for the new columns and semantics.
- Add a realized-cost test with **two** validated runs where one has a reference `Read` transcript and the **other omits `session-transcript.jsonl` entirely**, then assert:
  - both runs count in `invocations`;
  - the transcript-missing run contributes zero reference tokens;
  - `realized_tokens` includes exactly one reference token load;
  - `tokens_per_invocation` is the average across both runs;
  - reference-read columns match the observed events.

### UPDATED: python/tests/report/test_report_tokens_scan.py

Adjust tests only if the helper move changes private patch points or warning assertions.

- Keep existing scan behavior expectations.
- Add one targeted assertion that `scan()` still skips symlinked run dirs through the shared helper.
- Add one assertion that manifest-less child directories are not enumerated as runs.
- Add one assertion that a child with `{}` manifest or missing `issue_number` is not enumerated as a run.

### NEW: python/tests/rendering/test_render_session_transcript.py

Add focused renderer coverage.

- Verify a raw assistant `tool_use` for `Read` of `skills/design/references/approval-gates.md` is preserved as a sanitized block.
- Verify a raw assistant `tool_use` for `Read` of a non-reference Markdown file is dropped.
- Verify a raw assistant `tool_use` for a non-Read tool is still dropped.
- Verify emitted Read blocks contain only `type`, `name`, and normalized `input.file_path`.
- Verify a raw assistant `tool_use` for `Read` of `skills/shared/topology.md` (or equivalent shared fixture) is preserved as a sanitized block.

### UPDATED: python/tests/design/test_design_publish.py

Add publish-path coverage for design transcript capture.

- Build realistic `source-env.sh` fixtures containing `SESSION_ID` but **not** pre-seeded `LARCH_CLAUDE_SOURCE_FILE`; mock `token claude-source` to write `claude-source.env`, then assert `run-log capture-transcript` receives `--source-file` pointing at that snapshot **before** `design log-publish`.
- Assert capture does not read `session-env.sh`.
- Assert any preexisting `$DESIGN_TMPDIR/session-transcript.jsonl` is removed before capture begins.
- Assert publish **aborts** when stale-root removal fails (mock `unlink`/`OSError`).
- Assert `$DESIGN_TMPDIR/session-transcript.jsonl` exists at the publish-visible tmpdir root before `log-publish` runs only on successful capture+hoist.
- When snapshot materialization fails or capture skips, assert publish still proceeds, skip is warning-only, and root `session-transcript.jsonl` is absent after the capture attempt.
- When capture succeeds but hoist fails, assert publish **aborts** and root `session-transcript.jsonl` is absent so a stale transcript cannot be committed.
- Assert `session write-design-env` refresh persists `LARCH_CLAUDE_SOURCE_FILE` after snapshot materialization.

## Edge cases

- **Historical v3 design transcripts:** absent because design never published `session-transcript.jsonl`; treat as no observed reads until the capture hook lands.
- **Historical v3 implement transcripts:** may already contain `tool_call` `Read` blocks; parse them without backfill or log rewrite.
- **Design publish flat copy:** only top-level `$DESIGN_TMPDIR/session-transcript.jsonl` is measurement-visible after publish; nested staging trees must be hoisted or excluded.
- **Stale root transcript:** resume or retry must not republish an old root file; mandatory unlink before capture; publish aborts if unlink fails; promote only on successful hoist.
- **Claude source snapshot:** production design runs materialize `$DESIGN_TMPDIR/claude-source.env` at publish time; hand-seeding `LARCH_CLAUDE_SOURCE_FILE` in tests hides the production gap.
- **Design env filename:** `SESSION_ID` and refreshed `LARCH_CLAUDE_SOURCE_FILE` live in `source-env.sh`; reading `session-env.sh` is wrong for design.
- **Manifest-less pseudo-runs:** directories like `shared/archetypes` or orphan UUID folders without a valid manifest are not runs for heatmap or realized-cost denominators.
- **Invalid manifests:** `{}` or manifests without positive numeric `issue_number` are excluded, matching `/report-tokens analyze`.
- **Duplicate Reads:** count each Read event. A repeated load in one run adds repeated realized reference tokens.
- **Missing transcript:** count the validated run in `runs_observed` and `invocations`, but add zero reference tokens.
- **Symlinked transcript file:** skip reads for that run via `safe_transcript_path`; do not follow escapes outside the run dir.
- **Missing reference file:** count the read in `reads_observed`; use `bytes=0` and `tokens=0`.
- **Symlinked run dirs:** skip through the shared corpus helper, matching `/report-tokens analyze`.
- **Path escapes:** ignore absolute paths outside repo/cache/`OPERATOR_REPO_PATH` normalization, `../`, and unrelated angle-bracket placeholders.
- **Dev-only refs:** do not count `.claude/skills/**` unless scope later expands.
- **`loads_per_run`:** always divide by full skill validated `runs_observed`, never by transcript-present runs only.

## Failure modes

- If `tiktoken` is unavailable, the commands should fail the same way current measurement commands fail.
- If a transcript line is malformed JSON, skip that line.
- If design snapshot materialization fails or capture skips because render is empty, publish still succeeds; root transcript stays absent; only future design runs gain measurable transcripts.
- If mandatory stale-root removal fails, publish aborts before `log-publish`.
- If capture succeeds but hoist fails, publish aborts; partial root transcript is deleted.
- If a future renderer schema changes, raw Claude parsing and v3 `tool_call` parsing should still work for older committed fixtures.
- Do not compensate for missing design transcripts with inferred reads.
- Do not let manifest-less or issue-less corpus children deflate `loads_per_run` or inflate invocation denominators.

## Testing strategy

Run targeted Python tests:

```bash
cd python && pytest tests/report/test_tokens.py tests/report/test_report_tokens_scan.py tests/rendering/test_render_session_transcript.py tests/design/test_design_publish.py tests/state/test_session_env.py
```

Run lint/type checks for changed Python files when the local toolchain is available:

make py-lint

Optionally smoke the commands after implementation, knowing they write measurement TSVs under `larch-logs/measure-*`:

python3 python/cli.py token measure-references-heatmap
python3 python/cli.py token measure-realized-cost

Expect implement reference rows from committed v3 transcripts; design reference rows remain zero until a new design run publishes `session-transcript.jsonl`. Do not commit generated measurement TSVs unless the implementer intentionally updates run-log artifacts in a separate log-only change.

## Acceptance

Run targeted Python tests:

```bash
cd python && pytest tests/report/test_tokens.py tests/report/test_report_tokens_scan.py tests/rendering/test_render_session_transcript.py tests/design/test_design_publish.py tests/state/test_session_env.py
```

Run lint/type checks for changed Python files when the local toolchain is available:

make py-lint

Optionally smoke the commands after implementation, knowing they write measurement TSVs under `larch-logs/measure-*`:

python3 python/cli.py token measure-references-heatmap
python3 python/cli.py token measure-realized-cost

Expect implement reference rows from committed v3 transcripts; design reference rows remain zero until a new design run publishes `session-transcript.jsonl`. Do not commit generated measurement TSVs unless the implementer intentionally updates run-log artifacts in a separate log-only change.

diff_added: 765
diff_deleted: 120
mechanical_churn: false
diff_lines: 885

## Test plan
(no test plan section in plan-file)
