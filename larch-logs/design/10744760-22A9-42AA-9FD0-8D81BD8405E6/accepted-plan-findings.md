### FINDING_1: Design publish never produces `LARCH_CLAUDE_SOURCE_FILE`
- **Reviewer(s)**: Cursor-Arch, Cursor-Innovation, Cursor-Pragmatic
- **Severity**: blocking
- **Concern**: The plan wires `design_publish.publish_core` to read `LARCH_CLAUDE_SOURCE_FILE` from `$DESIGN_TMPDIR/source-env.sh` and call `run-log capture-transcript`, but the design pipeline never writes that key. `session write-design-env` only emits `WRITE_DESIGN_ENV_KEYS` (which omits `LARCH_CLAUDE_SOURCE_FILE`); design Step 0 never runs `token claude-source` or passes `--claude-source-file`; and design has no implement-style `_write_claude_source_snapshot`. Planned tests pre-seed the key in fixtures, so they pass while production `/design` Step 5c publishes always hit `source-file-missing`, design reference capture stays at zero, and post-merge acceptance (non-zero design reference reads, realized-cost above the `SKILL.md` floor) cannot be met.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Add a minimum snapshot step before capture: load SESSION_ID from source-env.sh, run python/cli.py token claude-source with LARCH_TOKEN_SESSION_ID set, write $DESIGN_TMPDIR/claude-source.env, pass that path to capture-transcript (optionally refresh source-env). Wire in design_publish.py or design_step0.py and extend test_design_publish.py to exercise the production snapshot path without pre-seeding LARCH_CLAUDE_SOURCE_FILE.
  - From Cursor-Innovation: Add a minimal materialization step before `capture-transcript`: mirror implement by running `python/cli.py token claude-source` into `$DESIGN_TMPDIR/claude-source.env` (use `SESSION_ID` from `source-env.sh`), then pass that path as `--source-file`. Optionally also extend `write-design-env` / `design_step0.py` to persist `LARCH_CLAUDE_SOURCE_FILE` for wrapper parity; publish-path tests should use a realistic Step 0 `source-env.sh`, not a hand-seeded key.
  - From Cursor-Pragmatic: In design_publish capture (or a single helper it calls), mirror implement bootstrap: invoke python/cli.py token claude-source to write $DESIGN_TMPDIR/claude-source.env when absent, pass that path to capture-transcript, and optionally persist LARCH_CLAUDE_SOURCE_FILE into source-env.sh via a minimal write-design-env extension or a targeted source-env refresh before capture.


### FINDING_4: `is_valid_run_dir` is weaker than scan `_record` manifest gate
- **Reviewer(s)**: Cursor-Innovation, Cursor-Requirements
- **Severity**: important
- **Concern**: The planned `is_valid_run_dir()` accepts any parseable JSON-object `manifest.json`, but `report_tokens_scan._record()` also rejects empty manifests and manifests without a positive numeric `issue_number`. Orphan dirs would still enter `runs_observed` / `invocations`, deflating `loads_per_run` and `tokens_per_invocation` versus the corpus `/report-tokens analyze` already walks, breaking parity between measurement commands and scan.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Innovation: Make `is_valid_run_dir` reuse the same manifest gate as `_record` (regular non-symlink `manifest.json`, non-empty object, numeric `issue_number` > 0). Add a fixture with a manifest-less sibling plus a `{}` or issue-less manifest child proving only `_record`-eligible dirs affect denominators.
  - From Cursor-Requirements: Make `is_valid_run_dir()` apply the same manifest gate as `_record()` (JSON object plus numeric `issue_number`), or have `run_dirs()` delegate manifest acceptance to a shared helper used by both scan and measure. Add a corpus-hygiene fixture with a manifest object but no `issue_number` and assert it is excluded from `runs_observed`.


### FINDING_5: Best-effort stale root transcript cleanup can corrupt published design logs
- **Reviewer(s)**: Codex-Pragmatic
- **Severity**: blocking
- **Concern**: If `session-transcript.jsonl` already exists at the run root and pre-capture unlink fails, or capture later skips or hoist fails, `design log-publish` can still copy a stale root transcript into the committed run log, silently corrupting published design transcripts and reference metrics derived from them.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Pragmatic: Make the root transcript removal mandatory for the publish path. If the old file cannot be removed, stop before `design log-publish`. Also require the hoist to produce a fresh root file before publish proceeds.


