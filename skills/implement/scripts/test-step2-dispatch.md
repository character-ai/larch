# test-step2-dispatch.sh

**Purpose**: Offline regression harness for `skills/implement/scripts/step2-implement.sh` covering the dispatcher branches that do not require spawning an external implementer. Runs in <1s with no `codex`/`cursor` binary and no network.

**Coverage** (22 assertions):
1. `--coder claude` emits `STATUS=claude_fallback` with no other KV keys, and writes no baseline files.
1b. Default coder (no flag) emits `STATUS=claude_fallback`.
1c. Legacy `--codex-available false` still emits `STATUS=claude_fallback` and prints a deprecation warning to stderr.
2. Missing required flag (`--auto-mode`) exits with code 2.
3. Bad `--coder` enum value exits with code 2 and names `{claude,codex,cursor}`.
3b. `--coder cursor --cursor-healthy false` emits `STATUS=bailed REASON=cursor-unhealthy TOOL=cursor` with no baseline-file leak.
3b2. `--coder cursor` with no `--cursor-healthy` defaults to false and emits `cursor-unhealthy`.
3b3. `--coder cursor --cursor-healthy ""` treats empty as false and emits `cursor-unhealthy`.
3b4. `--coder cursor --cursor-healthy bogus` exits with code 2.
3b5. `--coder claude --cursor-healthy ""` remains `STATUS=claude_fallback`; the Claude path ignores Cursor health noise.
3b6. Outside a git work-tree, `--coder cursor --cursor-healthy false` emits `cursor-unhealthy` before `REPO_ROOT` lookup.
3c. `--coder` and `--codex-available` together exit with code 2 and stderr says `mutually exclusive`.
3d. Bad `--codex-available` enum value exits with code 2.
4. Bad `--tmpdir` (not a directory) exits with code 2.
5. Resume cap: pre-seeding `codex-resume-count.txt` to 5 and invoking with `--answers` produces `STATUS=bailed REASON=qa-loop-exceeded` before any Codex spawn.
5b. Codex resume paths still use `codex-resume-count.txt`, pinning the per-tool filename refactor for byte-identical Codex behavior.
6. `--answers` pointing at a non-existent file exits with code 2.
7. Corrupt resume counter (non-numeric) emits `STATUS=bailed REASON=manifest-schema-invalid`.
8. `--coder codex` invoked with cwd outside any git working tree exits with code 2 and stderr containing `must be invoked from within a git working tree`.
8b. The non-git-tree Codex exit-2 path does not leak a baseline file into `$TMPDIR_ARG`.

All `--coder codex` invocations that proceed past argument parsing are run with cwd pinned to `$REPO_ROOT` so the dispatcher's git resolution targets the harness's own git tree. Cursor health-gate tests also use `cd "$REPO_ROOT"` unless the assertion specifically covers outside-git ordering.

**Out of scope**:
- Manifest schema validation for real implementer output.
- Path normalization (`..` / leading `/` / `.claude-plugin/plugin.json` / submodule paths).
- Sanitization via `scripts/redact-secrets.sh`.
- Single-retry on transient launcher failure with clean-state guard.
- `branch-changed` / `protected-path-modified` / `submodule-dirty` / `cursor-modified-history` post-implementer checks.
- Dispatcher-side commit (`git add -A && git commit -F …`) and `commit-failed` recovery.

**Invariants**:
- Tests run against the live dispatcher in the repo, not a copy.
- Cursor unhealthy bails do not write baseline files and include `TOOL=cursor`.
- The Claude fallback branch short-circuits before plugin / git resolution and ignores empty Cursor health input.
- Scratch directory is created via `mktemp -d` and removed via `trap` on exit.

**Call sites**:
- `make test-step2-dispatch`.
- `make test-harnesses`.
- `make lint`.

**Edit-in-sync**:
- `skills/implement/scripts/step2-implement.sh` — argument parsing, fallback branching, health gate ordering, baseline-file handling, or resume counter behavior must be exercised here.
- `skills/implement/scripts/step2-implement.md` — sibling dispatcher contract.
- `scripts/test-implement-structure.sh` — structural pins for the dispatcher and implementer launchers.

**Running locally**: `make test-step2-dispatch` or `bash skills/implement/scripts/test-step2-dispatch.sh`.
