### FINDING_2: Read path normalization drops committed transcript path shapes
- **Reviewer(s)**: Cursor-Arch, Codex-Arch, Cursor-Requirements
- **Severity**: blocking
- **Concern**: Committed run-log transcripts record reference `Read` paths as `<OPERATOR_REPO_PATH>/skills/...` and `<OPERATOR_REPO_PATH>/plugins/cache/larch-local/larch/<version>/skills/...`. Current `_normalize_read_path` (and related renderer logic) rejects paths starting with `<` before redaction, mishandles redacted/cache/session prefixes (e.g. `/skills/...` or `run-1/skills/...`), and the existing `_CACHE_READ_PATH_RE` only strips `/larch/<segment>/` tails—not `plugins/cache/larch-local/larch/<version>/`. After `REDACTED_OPERATOR_REPO` stripping, plugin-cache paths remain `plugins/cache/.../skills/...` and fail `is_in_scope_reference_path`, so `measure-references-heatmap` and `measure-realized-cost` stay zero or undercount despite acceptance requiring non-zero implement/design reference reads from existing v3 `tool_call` transcripts.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Pin in ### UPDATED: python/larch/report/tokens.py that REDACTED_OPERATOR_REPO is stripped before the angle-bracket guard and add a regression asserting <OPERATOR_REPO_PATH>/plugins/cache/larch-local/larch/48.2.0/skills/implement/references/conflict-resolution.md normalizes to skills/implement/references/conflict-resolution.md. ## Findings ### 1. correctness — Design capture never gets a Claude source snapshot (blocking) The plan wires `design_publish.publish_core` to load `LARCH_CLAUDE_SOURCE_FILE` from `$DESIGN_TMPDIR/source-env.sh` and call `run-log capture-transcript`. That matches implement Step 7a semantics for **reading** the key, but design never **writes** it. Today: - `session write-design-env` only allows keys in `WRITE_DESIGN_ENV_KEYS` (`python/larch/state/session_env.py:60-71`). `LARCH_CLAUDE_SOURCE_FILE` is not included. - Design Step 0 calls `write-design-env` after `session setup` (`python/larch/design/design_step0.py:187-192`) with no `token claude-source` snapshot. - Implement’s equivalent is `bootstrap._write_claude_source_snapshot` (`python/larch/state/bootstrap.py:330-340`), which writes `$TMPDIR/claude-source.env` before session env materialization. Wrappers may **read** `LARCH_CLAUDE_SOURCE_FILE` from `source-env.sh` if present (`design_session._SESSION_ENV_ALLOWLIST`), but nothing in the design pipeline populates it. The planned `test_design_publish.py` cases seed `LARCH_CLAUDE_SOURCE_FILE` in fixtures. They would pass while production always skips capture with `source-file-missing`, leaving design reference measurement at zero and failing issue acceptance after the first post-merge `/design` run. **Suggested revision:** In `### UPDATED: python/larch/design/design_publish.py`, add a snapshot step immediately before capture: read `SESSION_ID` from `source-env.sh`, invoke `python/cli.py token claude-source` with `LARCH_TOKEN_SESSION_ID` set, write `$DESIGN_TMPDIR/claude-source.env`, and pass that path to `--source-file`. Update tests to cover this path without pre-seeding the key. ### 2. correctness — Redacted path normalization must be explicit in tokens.py (important) Committed implement transcripts already contain reference `Read` events with redacted paths, for example: {"turn":5,"role":"assistant","blocks":[{"type":"tool_call",...,"name":"Read","input":{"file_path":"<OPERATOR_REPO_PATH>/plugins/cache/larch-local/larch/48.2.1/skills/implement/scripts/step-name-registry.tsv"}}]} and: ...,"name":"Read","input":{"file_path":"<OPERATOR_REPO_PATH>/skills/implement/references/stall-recovery.md",...} Current `_normalize_read_path` rejects any path starting with `<` before redaction (`python/larch/report/tokens.py:1338-1339`). The plan’s Approach section requires stripping `REDACTED_OPERATOR_REPO` first; acceptance tests mention redacted and plugin-cache paths. The `### UPDATED: python/larch/report/tokens.py` section should state that ordering explicitly so implement heatmap smoke on the committed corpus actually works. **Suggested revision:** Pin “strip `config.REDACTED_OPERATOR_REPO` before the `<` guard” in the tokens.py plan bullets and keep the plugin-cache fixture path from round 3/4 reviews.
  - From Codex-Arch: Add a canonicalizer that strips the redaction token and cache/session prefix down to the repo-relative suffix, then assert the exact normalized path in fixtures.
  - From Cursor-Requirements: In `tokens.py` (and the matching renderer normalizer), document and implement an explicit plugin-cache rewrite such as stripping a `plugins/cache/larch-local/larch/<version>/` prefix (or otherwise extracting the trailing `skills/**/references/*.md` / `skills/shared/*.md` segment). Remove or correct the Approach bullet that claims the existing cache regex already covers plugin-cache paths; add a fixture using the committed redacted plugin-cache shape.


Vote tally: YES=1 NO=2 JUDGE_ERROR=0 Result=neutral (neutral-rescued)

### OOS_1: Design transcript capture is wired only through `publish_core`, not clarify or pause `log-publish`
- **Description**: Design transcript capture is wired only through `publish_core`, not clarify or pause `log-publish`. Scenario: Clarify and pause call `design log-publish` directly and bypass `publish_core`, so successful clarify/pause publishes still lack `session-transcript.jsonl` and stay zero-reference in heatmap/realized-cost even after the main Gate C hook lands.
- **Reviewer**: Cursor-Innovation
- **Severity**: latent
- **Focus area**: architecture
- **Location**: python/larch/design/clarify.py
- **Phase**: design




Vote tally: YES=0 NO=3 JUDGE_ERROR=0 Result=rejected

### OOS_2: [OUT_OF_SCOPE] Clarify and pause design log-publish paths bypass publish_core transcript capture.
- **Description**: [OUT_OF_SCOPE] Clarify and pause design log-publish paths bypass publish_core transcript capture.. Scenario: Those flows call design log-publish directly without the planned design_publish publish_core hook, so resumed or clarify-published design runs still lack session-transcript.jsonl and stay unmeasured.
- **Reviewer**: Cursor-Pragmatic
- **Severity**: latent
- **Focus area**: architecture
- **Location**: python/larch/design/clarify.py; python/larch/design/design_pause.py
- **Phase**: design

Vote tally: YES=0 NO=3 JUDGE_ERROR=0 Result=rejected

