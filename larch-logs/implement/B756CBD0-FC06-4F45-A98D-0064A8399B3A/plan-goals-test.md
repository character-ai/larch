## Goal
Implement issue #6154: [IMPLEMENTING] md-to-py-XII: repair session-transcript capture; zero transcripts committed since 2026-07-01.

## Implementation Plan
## Plan

## Approach

Honor the approved outline. Treat `LARCH_TOKEN_SESSION_ID` as the larch token-ledger key only. Do not use it to locate Claude Code transcript files.

Update transcript discovery to:

1. Prefer `LARCH_CLAUDE_SESSION_ID` when set, as the explicit test/operator override.
2. Then use ambient `CLAUDE_CODE_SESSION_ID` when set, as the real Claude session UUID.
3. Fall back to newest `*.jsonl` only when neither sid source is requested.
4. Keep sid-miss fail-closed behavior when a requested sid has no matching `<sid>.jsonl`.

Stop passing larch run IDs into `token claude-source`. Let the token command see the ambient Claude session UUID, or use the no-sid newest-jsonl fallback when no real UUID is present.

Keep the v3 no-backfill policy. Do not rewrite committed logs.

## Files to modify/create

### UPDATED: python/larch/report/tokens.py

Change `_find_latest_claude_transcript` so it checks only sid sources that name a Claude transcript UUID:

- `LARCH_CLAUDE_SESSION_ID`
- `CLAUDE_CODE_SESSION_ID`

Do not check `LARCH_TOKEN_SESSION_ID` here.

Keep `resolve_session_id()` unchanged. Its `LARCH_TOKEN_SESSION_ID` behavior is token-ledger keying and remains valid.

Consider a small helper such as `_requested_claude_session_id(env_map)` if it makes the distinction clear.

### UPDATED: python/larch/design/design_publish.py

Update `_fetch_claude_source_snapshot`:

- Remove `env={**os.environ, "LARCH_TOKEN_SESSION_ID": session_id}` from the `token claude-source` call.
- Remove the `snapshot_uuid != session_id` rejection branch.
- Keep the existing failure warning when the command fails or emits no `TRANSCRIPT_PATH=`.
- Keep writing `claude-source.env` atomically after a successful token command.

Update `_reuse_cached_claude_source_snapshot` and `_materialize_claude_source_snapshot` as needed so cached snapshots are not rejected just because `SESSION_UUID` differs from the larch run-id. If retaining cache validation, validate only that the snapshot has `TRANSCRIPT_PATH`, `SESSION_DIR`, and `SESSION_UUID`, not equality with `session_id`.

### UPDATED: python/larch/state/bootstrap.py

Update `_write_claude_source_snapshot`:

- Remove the `LARCH_TOKEN_SESSION_ID=st.session_id` override when calling `_cli("token", "claude-source")`.
- Keep the current best-effort behavior: return silently on command failure or missing `TRANSCRIPT_PATH=`.
- Keep persisting the successful stdout to `$IMPLEMENT_TMPDIR/claude-source.env`.

Do not change `session-env.sh` writers directly except through the existing `--claude-source-file` path.

### UPDATED: skills/review/SKILL.md

Update Step 0 standalone review transcript materialization prose. It currently gates materialization on `LARCH_TOKEN_SESSION_ID` being non-empty and requires the returned `SESSION_UUID` to equal `LARCH_TOKEN_SESSION_ID` before binding `LARCH_CLAUDE_SOURCE_FILE` — the same broken run-id-as-sid assumption being removed elsewhere in this plan. A real Claude UUID resolved via the no-sid or ambient-sid path never equals that run-id, so this mismatch clause silently drops every successful resolution.

- Remove the `LARCH_TOKEN_SESSION_ID`-non-empty precondition entirely. Materialize whenever `SESSION_ENV_PATH` is empty and `LARCH_CLAUDE_SOURCE_FILE` is empty; no session-id check gates the attempt.
- Remove the `SESSION_UUID == LARCH_TOKEN_SESSION_ID` mismatch clause outright. Do not compare the returned `SESSION_UUID` against any larch-side value.
- Call `python3 "${CLAUDE_PLUGIN_ROOT}/python/cli.py" token claude-source` with no `LARCH_TOKEN_SESSION_ID` override in its invocation.
- Bind `LARCH_CLAUDE_SOURCE_FILE` whenever that command succeeds and its stdout contains `TRANSCRIPT_PATH=`, full stop.
- Leave `LARCH_CLAUDE_SOURCE_FILE` empty on command failure or missing `TRANSCRIPT_PATH=` so Step 4 skips transcript capture.

Keep nested review behavior unchanged.

### UPDATED: python/tests/report/test_tokens.py

Add regression tests for `_find_latest_claude_transcript` or `token_claude_source` using a temp Claude project dir:

- sid-hit: with `CLAUDE_CODE_SESSION_ID=<sid>` and `<sid>.jsonl` present, resolve that file.
- sid-miss: with `CLAUDE_CODE_SESSION_ID=<sid>` and no matching file, return unavailable rather than newest fallback.
- no-sid fallback: with neither `CLAUDE_CODE_SESSION_ID` nor `LARCH_CLAUDE_SESSION_ID`, choose the newest `*.jsonl`.
- legacy run-id isolation: with only `LARCH_TOKEN_SESSION_ID=<run-id>` and no real sid override, use newest fallback instead of looking for `<run-id>.jsonl`.

If testing `token_claude_source`, monkeypatch `subprocess.check_output` or the repo/project resolution seam so the test stays offline and side-effect-free.

### MAY_UPDATE: python/tests/design/test_design_publish.py

Update existing fake CLI expectations only if the design publish tests assume `token claude-source` receives `LARCH_TOKEN_SESSION_ID` or that `SESSION_UUID` equals the larch run-id.

A small assertion can pin that `_capture_design_transcript` still captures when `SESSION_UUID` differs from `ctx.session_id`.

### MAY_UPDATE: python/tests/state/test_bootstrap.py

Update or add a narrow test only if existing bootstrap coverage assumes `_write_claude_source_snapshot` passes `LARCH_TOKEN_SESSION_ID`.

A useful pin is that `_write_claude_source_snapshot` calls `token claude-source` without injecting `st.session_id` as an env override.

## Edge cases

- If `LARCH_CLAUDE_SESSION_ID` is set and invalid, keep current safe-session filtering. Do not use unsafe values in paths.
- If `LARCH_CLAUDE_SESSION_ID` is set but missing on disk, fail closed and report unavailable.
- If only `LARCH_TOKEN_SESSION_ID` is set, do not sid-match. Use newest fallback if no real Claude sid is present.
- If multiple transcripts exist and no real sid is present, newest-jsonl fallback remains best effort.
- Cached `claude-source.env` from older broken runs may contain a run-id `SESSION_UUID`. Do not reuse it unless it points at a real transcript path.

## Failure modes

- Ambient `CLAUDE_CODE_SESSION_ID` may be absent in some Claude Code contexts. The no-sid fallback covers this.
- Newest-jsonl fallback can choose the wrong concurrent session when no real sid is available. This is existing documented fallback behavior and is safer than always missing.
- Standalone review instructions are prompt-side prose. Keep them short and exact so the orchestrator does not reintroduce the run-id equality check.
- Design and implement capture can still skip if `token claude-source` cannot find the Claude project dir or transcript file. The existing warning path should surface that.

## Testing strategy

Run focused Python tests:

```bash
python3 -m pytest python/tests/report/test_tokens.py
python3 -m pytest python/tests/design/test_design_publish.py python/tests/state/test_bootstrap.py
```

Run relevant repo checks for the changed paths if dependencies are available:

python3 python/cli.py checks run-relevant

Manual smoke after merge should use fresh runs only:

- Run `/design`, `/implement`, and standalone `/review`.
- Confirm each new committed run has `session-transcript.jsonl`.
- Run `python3 python/cli.py token measure-references-heatmap`.
- Confirm `transcript_runs_observed` is nonzero for `design`, `implement`, and `review`.

## Acceptance

Run focused Python tests:

```bash
python3 -m pytest python/tests/report/test_tokens.py
python3 -m pytest python/tests/design/test_design_publish.py python/tests/state/test_bootstrap.py
```

Run relevant repo checks for the changed paths if dependencies are available:

python3 python/cli.py checks run-relevant

Manual smoke after merge should use fresh runs only:

- Run `/design`, `/implement`, and standalone `/review`.
- Confirm each new committed run has `session-transcript.jsonl`.
- Run `python3 python/cli.py token measure-references-heatmap`.
- Confirm `transcript_runs_observed` is nonzero for `design`, `implement`, and `review`.

diff_lines: 170

## Test plan
(no test plan section in plan-file)
