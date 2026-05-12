# test-step2-dispatch.sh

**Purpose**: Offline regression harness for `skills/implement/scripts/step2-implement.sh`. Most tests cover dispatcher branches that do not require spawning a real external implementer; a small number (Test 12, Test 13) inject a stub `codex` binary on PATH to exercise the spawn → manifest → Step 6/7 → dispatcher-side commit flow. Runs in <1s with no real `codex`/`cursor`/`gemini` binary and no network.

**Coverage**:
1. `--coder claude` emits `STATUS=claude_fallback` and `ORCHESTRATOR_EDIT_AUTHORITY=allowed` (and no other KV keys — no `MANIFEST=`, no `TRANSCRIPT=`, etc.), and writes no baseline files.
1b. Default coder (no flag) is codex — verified via non-git cwd exit 2 with the git-tree message (the claude default would early-return `STATUS=claude_fallback` instead).
1c. Legacy `--codex-available false` still emits `STATUS=claude_fallback` and prints a deprecation warning to stderr.
2. Missing required flag (`--auto-mode`) exits with code 2.
3. Bad `--coder` enum value exits with code 2 and names `{claude,codex,cursor,gemini}`.
3b. `--coder cursor --cursor-healthy false` emits `STATUS=claude_fallback` with no baseline-file leak (cursor unhealthy → claude fallback).
3b2. `--coder cursor` with no `--cursor-healthy` defaults to false and falls back to `STATUS=claude_fallback`.
3b3. `--coder cursor --cursor-healthy ""` treats empty as false and falls back to `STATUS=claude_fallback`.
3b4. `--coder cursor --cursor-healthy bogus` exits with code 2.
3b5. `--coder claude --cursor-healthy ""` remains `STATUS=claude_fallback`; the Claude path ignores Cursor health noise.
3b6. Outside a git work-tree, `--coder cursor --cursor-healthy false` emits `STATUS=claude_fallback` before `REPO_ROOT` lookup.
3g. `--coder gemini --gemini-healthy false` emits `STATUS=claude_fallback` with no baseline-file leak (Gemini unhealthy → Claude fallback).
3g2. `--coder gemini` with no `--gemini-healthy` defaults to false and falls back to `STATUS=claude_fallback`.
3g3. `--coder gemini --gemini-healthy ""` treats empty as false and falls back to `STATUS=claude_fallback`.
3g4. `--gemini-healthy bogus` exits with code 2 even when `--coder=codex`, pinning validation outside the Gemini path.
3g5. Outside a git work-tree, `--coder gemini --gemini-healthy false` emits `STATUS=claude_fallback` before `REPO_ROOT` lookup.
3c. `--coder` and `--codex-available` together exit with code 2 and stderr says `mutually exclusive`.
3d. Bad `--codex-available` enum value exits with code 2.
4. Bad `--tmpdir` (not a directory) exits with code 2.
5. Resume cap: pre-seeding `codex-resume-count.txt` to 5 and invoking with `--answers` produces `STATUS=bailed REASON=qa-loop-exceeded` before any Codex spawn.
5b. Codex resume paths still use `codex-resume-count.txt`, pinning the per-tool filename refactor for byte-identical Codex behavior.
6. `--answers` pointing at a non-existent file exits with code 2.
7. Corrupt resume counter (non-numeric) emits `STATUS=bailed REASON=manifest-schema-invalid`.
8. `--coder codex` invoked with cwd outside any git working tree exits with code 2 and stderr containing `must be invoked from within a git working tree`.
8b. The non-git-tree Codex exit-2 path does not leak a baseline file into `$TMPDIR_ARG`.
9. First Codex invocation (reusing the resume-cap setup that bails on `qa-loop-exceeded`) writes `step2-spawn-coder.txt` with content `codex` BEFORE the resume-counter logic runs — pins the cross-coder guard's "first writer" behavior.
10. Second invocation against a tmpdir whose `step2-spawn-coder.txt` recorded a different coder (`codex` pre-seeded; invocation passes `--coder=cursor --cursor-healthy true`) emits `STATUS=bailed REASON=coder-mismatch-tmpdir-reuse TOOL=cursor`. The pre-seeded sentinel value MUST be unchanged on bail, and the `cursor-resume-count.txt` MUST NOT have been written — pins the cross-coder guard's "fail before any per-tool state mutation" ordering. Also asserts `ORCHESTRATOR_EDIT_AUTHORITY=forbidden` on this bail path.
10b. Gemini variant of the same cross-coder guard (`cursor` pre-seeded; invocation passes `--coder=gemini --gemini-healthy true`) emits `TOOL=gemini`, leaves the sentinel unchanged, and does not write `gemini-resume-count.txt`.
11. `ORCHESTRATOR_EDIT_AUTHORITY` pair invariant: on every reachable exit-0 outcome the dispatcher emits exactly one `ORCHESTRATOR_EDIT_AUTHORITY=` line, with `allowed` iff `STATUS=claude_fallback` and `forbidden` on every external-implementer outcome. Test 11a re-runs the `--coder claude` claude_fallback path and asserts `AUTH=allowed`; test 11b re-runs the resume-cap bail (`--coder codex --answers` with pre-seeded `codex-resume-count.txt=5`) and asserts `AUTH=forbidden`. Tests 1, 1c, 3b, 3b2, 3b3, 3b5, 3b6, 5, 7, and 10 also pin the AUTH key on their respective branches; this is the central mechanical gate that lets `SKILL.md` Step 2 enforce NEVER #10 (`ORCHESTRATOR_EDIT_AUTHORITY=allowed` ⇔ `STATUS=claude_fallback`).
12. Canonical `--tmpdir`/`session-id` overwrites stale token-session env before the launcher subprocess runs. Test 12a writes a fresh `session-id` to a clean tmpdir, sets a stale `LARCH_TOKEN_SESSION_ID` in the dispatcher's environment, and asserts the stub Codex sees the tmpdir's `session-id` (not the stale env value). Test 12b re-runs against a separate tmpdir with no inherited env to confirm each tmpdir exports its own session id. Both use the stub Codex pattern (PATH override) shared with Test 13.
13. `.claude-plugin/plugin.json` absent-then-still-absent regression (issue #1475): in a scratch git repo without `plugin.json`, a stub Codex that performs a benign edit on a non-protected file and writes a valid `status=complete` manifest must reach `STATUS=complete` (not bail with `REASON=protected-path-modified`), AND emit `ORCHESTRATOR_EDIT_AUTHORITY=forbidden` plus `MANIFEST=` per NEVER #10. Pins the Step 6b absent-sentinel-equality fix where both the baseline write and the post-implementer comparison use the empty-string canonical sentinel for "absent".
15a. `--workflow SIMPLE` is accepted; dispatcher emits `STATUS=claude_fallback` as normal.
15b. `--workflow HARD` is accepted; dispatcher emits `STATUS=claude_fallback` as normal.
15c. `--workflow bogus` exits with code 2 and stderr contains `--workflow must be 'SIMPLE' or 'HARD'`.

All `--coder codex` invocations that proceed past argument parsing are run with cwd pinned to `$REPO_ROOT` so the dispatcher's git resolution targets the harness's own git tree. Cursor and Gemini health-gate tests also use `cd "$REPO_ROOT"` unless the assertion specifically covers outside-git ordering.

**Out of scope**:
- Manifest schema validation for real implementer output.
- Path normalization (`..` / leading `/` / `.claude-plugin/plugin.json` / submodule paths).
- Sanitization via `scripts/redact-secrets.sh`.
- Single-retry on transient launcher failure with clean-state guard.
- `branch-changed` / `submodule-dirty` / `cursor-modified-history` post-implementer checks. (Test 13 covers only the Step 6b absent-`plugin.json` sentinel case from issue #1475; Step 7a path-validation `protected-path-modified` paths and the other Step 6 post-implementer rejections remain out of scope here.)
- `commit-failed` recovery on the dispatcher-side commit. (Test 13 exercises the happy path of `git add -A && git commit -F …` end-to-end via stub Codex; failure-recovery branches remain out of scope.)

**Invariants**:
- Tests run against the live dispatcher in the repo, not a copy.
- Cursor/Gemini unhealthy fallback emits `STATUS=claude_fallback` and does not write baseline files.
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
