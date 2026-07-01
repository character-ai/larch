### FINDING_1:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: blocking
- **Focus area**: correctness
- **Location**: python/larch/design/design_publish.py:488-610
- **Concern**: Design transcript capture has no producer for LARCH_CLAUDE_SOURCE_FILE in source-env.sh. Scenario: Implement bootstrap writes claude-source.env via token claude-source and stores its path in session-env.sh (python/larch/state/bootstrap.py:330-340, WRITE_IMPLEMENT keys). Design step0 only calls session write-design-env (python/larch/design/design_step0.py:187-192; WRITE_DESIGN_ENV_KEYS in python/larch/state/session_env.py:60-71) and never emits LARCH_CLAUDE_SOURCE_FILE. The plan only adds a publish_core reader plus tests that pre-seed the key in fixtures, so production /design runs still hit capture-transcript source-file-missing, publish warning-only, and design heatmap/realized-cost stay at the SKILL.md floor after merge.
- **Proposed resolution**: Add a minimum snapshot step before capture: load SESSION_ID from source-env.sh, run python/cli.py token claude-source with LARCH_TOKEN_SESSION_ID set, write $DESIGN_TMPDIR/claude-source.env, pass that path to capture-transcript (optionally refresh source-env). Wire in design_publish.py or design_step0.py and extend test_design_publish.py to exercise the production snapshot path without pre-seeding LARCH_CLAUDE_SOURCE_FILE.

### FINDING_2:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/larch/report/tokens.py:1334-1349
- **Concern**: Redacted committed Read paths are still dropped by the current normalizer. Scenario: The committed corpus records reference Reads as <OPERATOR_REPO_PATH>/skills/... and <OPERATOR_REPO_PATH>/plugins/cache/.../skills/.../references/.... _normalize_read_path returns None for any path starting with < before redaction (line 1338-1339), so implement heatmap rows stay zero until fixed. The plan states the REDACTED_OPERATOR_REPO strip in Approach but tokens.py UPDATED bullets only list normalize helpers generically.
- **Proposed resolution**: Pin in ### UPDATED: python/larch/report/tokens.py that REDACTED_OPERATOR_REPO is stripped before the angle-bracket guard and add a regression asserting <OPERATOR_REPO_PATH>/plugins/cache/larch-local/larch/48.2.0/skills/implement/references/conflict-resolution.md normalizes to skills/implement/references/conflict-resolution.md. ## Findings ### 1. correctness — Design capture never gets a Claude source snapshot (blocking) The plan wires `design_publish.publish_core` to load `LARCH_CLAUDE_SOURCE_FILE` from `$DESIGN_TMPDIR/source-env.sh` and call `run-log capture-transcript`. That matches implement Step 7a semantics for **reading** the key, but design never **writes** it. Today: - `session write-design-env` only allows keys in `WRITE_DESIGN_ENV_KEYS` (`python/larch/state/session_env.py:60-71`). `LARCH_CLAUDE_SOURCE_FILE` is not included. - Design Step 0 calls `write-design-env` after `session setup` (`python/larch/design/design_step0.py:187-192`) with no `token claude-source` snapshot. - Implement’s equivalent is `bootstrap._write_claude_source_snapshot` (`python/larch/state/bootstrap.py:330-340`), which writes `$TMPDIR/claude-source.env` before session env materialization. Wrappers may **read** `LARCH_CLAUDE_SOURCE_FILE` from `source-env.sh` if present (`design_session._SESSION_ENV_ALLOWLIST`), but nothing in the design pipeline populates it. The planned `test_design_publish.py` cases seed `LARCH_CLAUDE_SOURCE_FILE` in fixtures. They would pass while production always skips capture with `source-file-missing`, leaving design reference measurement at zero and failing issue acceptance after the first post-merge `/design` run. **Suggested revision:** In `### UPDATED: python/larch/design/design_publish.py`, add a snapshot step immediately before capture: read `SESSION_ID` from `source-env.sh`, invoke `python/cli.py token claude-source` with `LARCH_TOKEN_SESSION_ID` set, write `$DESIGN_TMPDIR/claude-source.env`, and pass that path to `--source-file`. Update tests to cover this path without pre-seeding the key. ### 2. correctness — Redacted path normalization must be explicit in tokens.py (important) Committed implement transcripts already contain reference `Read` events with redacted paths, for example: {"turn":5,"role":"assistant","blocks":[{"type":"tool_call",...,"name":"Read","input":{"file_path":"<OPERATOR_REPO_PATH>/plugins/cache/larch-local/larch/48.2.1/skills/implement/scripts/step-name-registry.tsv"}}]} and: ...,"name":"Read","input":{"file_path":"<OPERATOR_REPO_PATH>/skills/implement/references/stall-recovery.md",...} Current `_normalize_read_path` rejects any path starting with `<` before redaction (`python/larch/report/tokens.py:1338-1339`). The plan’s Approach section requires stripping `REDACTED_OPERATOR_REPO` first; acceptance tests mention redacted and plugin-cache paths. The `### UPDATED: python/larch/report/tokens.py` section should state that ordering explicitly so implement heatmap smoke on the committed corpus actually works. **Suggested revision:** Pin “strip `config.REDACTED_OPERATOR_REPO` before the `<` guard” in the tokens.py plan bullets and keep the plugin-cache fixture path from round 3/4 reviews. --- **Out of scope (not filed):** Updating `docs/run-logs.md` for preserved reference `Read` blocks; clarify/pause `log-publish` bypassing `publish_core`; duplicate-read fixture coverage.

### FINDING_3:
- **Reviewer(s)**: Codex-Arch
- **Severity**: blocking
- **Focus area**: correctness
- **Location**: python/larch/report/tokens.py:1334-1348, python/larch/rendering/render_session_transcript.py:93-101
- **Concern**: Read path normalization still drops required cache and redacted forms. Scenario: A `<OPERATOR_REPO_PATH>/skills/...` read can still become `/skills/...`, and a cache-backed read can still become `run-1/skills/...`; both fail the scope check, so the required reference load never reaches the metrics.
- **Proposed resolution**: Add a canonicalizer that strips the redaction token and cache/session prefix down to the repo-relative suffix, then assert the exact normalized path in fixtures.

### FINDING_4:
- **Reviewer(s)**: Codex-Arch
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/larch/design/design_publish.py:107-118
- **Concern**: Design publish should pass claude_pid into source-env loading. Scenario: If `source-env.sh` is symlinked, `_load_source_env` returns {} without `claude_pid`, so design publish skips capture and the new run stays unmeasured.
- **Proposed resolution**: Thread the parsed `--claude-pid` into `_load_source_env` and add a regression test with a trusted symlinked `source-env.sh`.

### FINDING_5:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/larch/design/design_publish.py
- **Concern**: Design capture never materializes `LARCH_CLAUDE_SOURCE_FILE` into `source-env.sh`. Scenario: The plan loads `LARCH_CLAUDE_SOURCE_FILE` from `$DESIGN_TMPDIR/source-env.sh` at publish, but `write-design-env` only writes `WRITE_DESIGN_ENV_KEYS` (no `LARCH_CLAUDE_SOURCE_FILE`) and design Step 0 never runs `token claude-source` or passes `--claude-source-file`. Implement persists a `claude-source.env` snapshot in bootstrap (`bootstrap._write_claude_source_snapshot` + `session write-env`). Every design capture path returns `source-file-missing`, so new design runs stay zero-reference and acceptance cannot be met post-merge.
- **Proposed resolution**: Add a minimal materialization step before `capture-transcript`: mirror implement by running `python/cli.py token claude-source` into `$DESIGN_TMPDIR/claude-source.env` (use `SESSION_ID` from `source-env.sh`), then pass that path as `--source-file`. Optionally also extend `write-design-env` / `design_step0.py` to persist `LARCH_CLAUDE_SOURCE_FILE` for wrapper parity; publish-path tests should use a realistic Step 0 `source-env.sh`, not a hand-seeded key.

### FINDING_6:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: python/larch/report/run_log_corpus.py
- **Concern**: `is_valid_run_dir` is weaker than `report_tokens_scan._record`. Scenario: Planned `is_valid_run_dir` accepts any JSON-object manifest. `_record` rejects empty manifests and manifests without a positive numeric `issue_number` before a run counts in `/report-tokens analyze`. Those orphan dirs would still enter `runs_observed` / `invocations`, deflating `loads_per_run` and `tokens_per_invocation` versus the corpus `report-tokens analyze` already walks.
- **Proposed resolution**: Make `is_valid_run_dir` reuse the same manifest gate as `_record` (regular non-symlink `manifest.json`, non-empty object, numeric `issue_number` > 0). Add a fixture with a manifest-less sibling plus a `{}` or issue-less manifest child proving only `_record`-eligible dirs affect denominators.

### FINDING_7:
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: blocking
- **Focus area**: correctness
- **Location**: python/larch/design/design_publish.py; python/larch/state/session_env.py:60-71; python/larch/design/design_step0.py:187-192
- **Concern**: Design transcript capture has no producer for LARCH_CLAUDE_SOURCE_FILE or claude-source.env.. Scenario: The plan only reads LARCH_CLAUDE_SOURCE_FILE from $DESIGN_TMPDIR/source-env.sh before capture, but write-design-env never writes that key (WRITE_DESIGN_ENV_KEYS omits it; design step0/route refresh pass no --claude-source-file), and design has no bootstrap _write_claude_source_snapshot equivalent. capture-transcript therefore always gets source-file-missing on real /design Step 5c publishes; new design runs stay zero-reference despite the capture hook.
- **Proposed resolution**: In design_publish capture (or a single helper it calls), mirror implement bootstrap: invoke python/cli.py token claude-source to write $DESIGN_TMPDIR/claude-source.env when absent, pass that path to capture-transcript, and optionally persist LARCH_CLAUDE_SOURCE_FILE into source-env.sh via a minimal write-design-env extension or a targeted source-env refresh before capture.

### FINDING_8:
- **Reviewer(s)**: Codex-Pragmatic
- **Severity**: blocking
- **Focus area**: correctness
- **Location**: python/larch/design/design_publish.py:598-639
- **Concern**: Best-effort stale-transcript cleanup is not enough. Scenario: If `session-transcript.jsonl` already exists and the pre-capture unlink fails, or capture later skips or hoist fails, `design log-publish` can still copy the stale root transcript into the committed run and silently corrupt the published design log.
- **Proposed resolution**: Make the root transcript removal mandatory for the publish path. If the old file cannot be removed, stop before `design log-publish`. Also require the hoist to produce a fresh root file before publish proceeds.

### FINDING_9:
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/larch/report/tokens.py:1287-1349
- **Concern**: Plugin-cache reference Read paths are not actually normalized by the cited cache regex. Scenario: The Approach still says installed plugin-cache paths are handled by `_CACHE_READ_PATH_RE`, but that regex only strips `/larch/<segment>/` session-cache tails. Committed implement transcripts already record reads like `<OPERATOR_REPO_PATH>/plugins/cache/larch-local/larch/48.2.0/skills/implement/references/conflict-resolution.md` (for example `larch-logs/implement/B8C6997D-7ABB-4397-BCD4-49232EC63D02/session-transcript.jsonl`). After stripping `REDACTED_OPERATOR_REPO`, the path remains `plugins/cache/.../skills/...`, which fails `is_in_scope_reference_path`, so implement heatmap and realized-cost stay zero or undercount despite acceptance expecting non-zero implement reference reads from existing v3 `tool_call` transcripts.
- **Proposed resolution**: In `tokens.py` (and the matching renderer normalizer), document and implement an explicit plugin-cache rewrite such as stripping a `plugins/cache/larch-local/larch/<version>/` prefix (or otherwise extracting the trailing `skills/**/references/*.md` / `skills/shared/*.md` segment). Remove or correct the Approach bullet that claims the existing cache regex already covers plugin-cache paths; add a fixture using the committed redacted plugin-cache shape.

### FINDING_10:
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/larch/report/run_log_corpus.py
- **Concern**: The planned `is_valid_run_dir()` is weaker than `report_tokens_scan._record()`. Scenario: The plan requires only a parseable JSON-object `manifest.json`, but `_record()` also rejects manifests without a positive numeric `issue_number` (`report_tokens_scan.py` lines 252-255). The plan states measurement commands and `/report-tokens analyze` should walk the same corpus. Dirs with `{}` or object manifests lacking `issue_number` would inflate `runs_observed` and `invocations` and deflate `loads_per_run` / `tokens_per_invocation` relative to scan-qualified runs.
- **Proposed resolution**: Make `is_valid_run_dir()` apply the same manifest gate as `_record()` (JSON object plus numeric `issue_number`), or have `run_dirs()` delegate manifest acceptance to a shared helper used by both scan and measure. Add a corpus-hygiene fixture with a manifest object but no `issue_number` and assert it is excluded from `runs_observed`.
