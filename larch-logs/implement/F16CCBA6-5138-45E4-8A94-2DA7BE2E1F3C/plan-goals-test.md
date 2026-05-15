## Goal
Convert 27 scripts to use lib-quiet.sh quiet-by-default pattern

## Implementation Plan

Convert 27 scripts + 2 library audits to use lib-quiet.sh, following the identical pattern from Phases 1–3.

### Conversion Pattern (same for all scripts)

For each script in `skills/X/scripts/`:
1. Add `SCRIPT_DIR` (if missing) and `PLUGIN_ROOT="${CLAUDE_PLUGIN_ROOT:-$(cd "$SCRIPT_DIR/../../.." && pwd -P)}"` near top
2. Add `# shellcheck source=scripts/lib-quiet.sh` + `source "$PLUGIN_ROOT/scripts/lib-quiet.sh"` + `larch_quiet_init`
3. Convert contract-emitting `echo "KEY=VAL"` / `printf 'KEY=%s\n' "$VAL"` → `emit_kv KEY "$VAL"`
4. Convert diagnostic/progress `echo "msg" >&2` → leave as-is (goes to log after quiet init, which is correct)
5. For scripts where KV contract is on stderr (only write-sentinel.sh): replace `echo "KEY=VAL" >&2` with `larch_err "KEY=VAL"`

For `scripts/verify-skill-called.sh`: `source "$SCRIPT_DIR/lib-quiet.sh"` (same-dir, no PLUGIN_ROOT needed).

### Library Audits (no changes needed)
- `skills/umbrella/scripts/helpers.sh` — sourced library, no shebang exec, verify no contract-shaped stdout
- `skills/set-up-forked-open-source-repo/scripts/lib-remotes.sh` — sourced library, verify no contract-shaped stdout

### Test Updates
Add `LARCH_QUIET_DISABLE=1` to each test file's helper invocation environment (either via `export LARCH_QUIET_DISABLE=1` at test top, or per-invocation env prefix). This makes `emit_kv` behave identically to `echo "KEY=VAL"` so existing assertions pass unchanged.

### Files

**skills/issue/scripts/** (8 scripts):
- add-blocked-by.sh: PLUGIN_ROOT from existing REPO_ROOT; emit_kv for BLOCKED_BY_*/CLIENT/BLOCKER/ERROR
- allocate-candidates.sh: emit_kv for CANDIDATES=
- cleanup-failed-issue.sh: emit_kv for CLOSED/ISSUE/ERROR
- create-one.sh: emit_kv for ISSUE_FAILED/ISSUE_ERROR/DRY_RUN*/ISSUE_NUMBER/ISSUE_URL/ISSUE_ID
- fetch-issue-details.sh: emit_kv for FETCH_STATUS_N (file-backed corpus echoes untouched)
- list-issues.sh: emit_kv for LIST_STATUS/ISSUE_*/REPO/TOTAL
- parse-input.sh: emit_kv for ITEM_*/ITEMS_TOTAL
- write-sentinel.sh: larch_err for WROTE/ERROR (preserves stderr contract channel discipline)

**skills/umbrella/scripts/** (4 scripts):
- parse-args.sh: emit_kv for all printf 'KEY=%s\n' lines
- render-batch-input.sh: emit_kv for BATCH_INPUT_FILE/PIECES_TOTAL/PIECE_*
- render-umbrella-body.sh: emit_kv for UMBRELLA_BODY_FILE/UMBRELLA_TITLE_HINT
- validate-pieces-json.sh: emit_kv for VALID/ERROR

**skills/alias/scripts/** (2 scripts):
- generate-alias.sh: emit for full markdown content (non-KV stdout); emit_kv for error KV
- resolve-target.sh: emit_kv for SKILL/FLAGS/ERROR

**skills/cleanup/scripts/** (1): cleanup.sh: emit_kv for KV outputs

**skills/compress-skill/scripts/** (2):
- build-feature-description.sh: emit_kv for KV outputs
- discover-md-set.sh: emit_kv for KV outputs (minimal)

**skills/create-skill/scripts/** (5):
- parse-args.sh: emit_kv for KV outputs
- post-scaffold-hints.sh: emit_kv for KV outputs
- prepare-description.sh: emit_kv for KV outputs
- render-skill-md.sh: emit_kv for KV outputs; emit for non-KV markdown content
- validate-args.sh: emit_kv for KV outputs

**skills/report-tokens/scripts/** (1):
- run-analysis.sh (819 lines): emit_kv for KV contract outputs; emit_breadcrumb for progress

**skills/set-up-forked-open-source-repo/scripts/** (1):
- setup-forked-open-source-repo.sh: emit_kv for KV outputs

**skills/show-skill/scripts/** (1):
- show.sh: emit for full skill content (non-KV stdout); emit_kv for KV outputs

**skills/upgrade-larch/scripts/** (1):
- upgrade-larch.sh: emit_kv for KV outputs

**scripts/** (1):
- verify-skill-called.sh: same-dir lib-quiet; emit_kv for VERIFIED/ERROR contract outputs


## Test plan
- `make test` passes (existing unit tests pass via LARCH_QUIET_DISABLE=1)
- End-to-end smoke: `/larch:issue --dry-run` and `/larch:umbrella` show envelope-only stdout
