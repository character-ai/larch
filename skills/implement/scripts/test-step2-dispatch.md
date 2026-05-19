# test-step2-dispatch.sh

**Coverage**:
1. `--coder claude` emits `STATUS=claude_fallback` and `ORCHESTRATOR_EDIT_AUTHORITY=allowed` (and no other KV keys — no `MANIFEST=`, no `TRANSCRIPT=`, etc.), and writes no baseline files.
1b. Default coder (no flag) is cursor — verified via non-git cwd with no `--cursor-present`: dispatcher exits 0 with `STATUS=claude_fallback` (cursor presence check fires before git-tree lookup; codex default would exit 2 instead).
1c. Legacy `--codex-available false` still emits `STATUS=claude_fallback` and prints a deprecation warning to stderr.
2. Missing required flag (`--auto-mode`) exits with code 2.
3b. `--coder cursor --cursor-present false` emits `STATUS=claude_fallback` with no baseline-file leak (cursor unavailable → claude fallback).
3b2. `--coder cursor` with no `--cursor-present` defaults to false and falls back to `STATUS=claude_fallback`.
3b3. `--coder cursor --cursor-present ""` treats empty as false and falls back to `STATUS=claude_fallback`.
3b4. `--coder cursor --cursor-present bogus` exits with code 2.
3b5. `--coder claude --cursor-present ""` remains `STATUS=claude_fallback`; the Claude path ignores Cursor presence noise.
3b6. Outside a git work-tree, `--coder cursor --cursor-present false` emits `STATUS=claude_fallback` before `REPO_ROOT` lookup.
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
10. Second invocation against a tmpdir whose `step2-spawn-coder.txt` recorded a different coder (`codex` pre-seeded; invocation passes `--coder=cursor --cursor-present true`) emits `STATUS=bailed REASON=coder-mismatch-tmpdir-reuse TOOL=cursor`. The pre-seeded sentinel value MUST be unchanged on bail, and the `cursor-resume-count.txt` MUST NOT have been written — pins the cross-coder guard's "fail before any per-tool state mutation" ordering. Also asserts `ORCHESTRATOR_EDIT_AUTHORITY=forbidden` on this bail path.
11. `ORCHESTRATOR_EDIT_AUTHORITY` pair invariant: on every reachable exit-0 outcome the dispatcher emits exactly one `ORCHESTRATOR_EDIT_AUTHORITY=` line, with `allowed` iff `STATUS=claude_fallback` and `forbidden` on every external-implementer outcome. Test 11a re-runs the `--coder claude` claude_fallback path and asserts `AUTH=allowed`; test 11b re-runs the resume-cap bail (`--coder codex --answers` with pre-seeded `codex-resume-count.txt=5`) and asserts `AUTH=forbidden`. Tests 1, 1c, 3b, 3b2, 3b3, 3b5, 3b6, 5, 7, and 10 also pin the AUTH key on their respective branches; this is the central mechanical gate that lets `SKILL.md` Step 2 enforce NEVER #10 (`ORCHESTRATOR_EDIT_AUTHORITY=allowed` ⇔ `STATUS=claude_fallback`).
12. Canonical `--tmpdir`/`session-id` overwrites stale token-session env before the launcher subprocess runs. Test 12a writes a fresh `session-id` to a clean tmpdir, sets a stale `LARCH_TOKEN_SESSION_ID` in the dispatcher's environment, and asserts the stub Codex sees the tmpdir's `session-id` (not the stale env value). Test 12b re-runs against a separate tmpdir with no inherited env to confirm each tmpdir exports its own session id. Both use the stub Codex pattern (PATH override) shared with Test 13.
13. `.claude-plugin/plugin.json` absent-then-still-absent regression (issue #1475): in a scratch git repo without `plugin.json`, a stub Codex that performs a benign edit on a non-protected file and writes a valid `status=complete` manifest must reach `STATUS=complete` (not bail with `REASON=protected-path-modified`), AND emit `ORCHESTRATOR_EDIT_AUTHORITY=forbidden` plus `MANIFEST=` per NEVER #10. Pins the Step 6b absent-sentinel-equality fix where both the baseline write and the post-implementer comparison use the empty-string canonical sentinel for "absent".
14. (cap-hit path) No stub coder — covered without spawning a real implementer; see the test comment.
15a. `--workflow SIMPLE` is accepted; dispatcher emits `STATUS=claude_fallback` as normal.
15b. `--workflow HARD` is accepted; dispatcher emits `STATUS=claude_fallback` as normal.
15c. `--workflow bogus` exits with code 2 and stderr contains `--workflow must be 'SIMPLE' or 'HARD'`.
16. `needs_qa` repair path (issue #1883): stub Codex writes a manifest with `status=needs_qa` but no `needs_qa.questions`, and a `qa-pending.json` with non-standard `items[]` format. The dispatcher must normalize `items[]` to canonical `questions[]` and emit `STATUS=needs_qa` (not `STATUS=bailed REASON=manifest-schema-invalid`). Two assertions: (a) dispatcher stdout contains `STATUS=needs_qa` and `QA_PENDING=` with `ORCHESTRATOR_EDIT_AUTHORITY=forbidden`; (b) the repaired `qa-pending.json` contains `questions[]` and no `items[]`.
17. Timeout-selection wiring (`--workflow` → launcher `--timeout`): stub Codex that writes a `status=bailed` manifest; the `.meta` sidecar written by `run-external-agent.sh` before subprocess launch records `TIMEOUT=$TIMEOUT_SECONDS`. Test 17a asserts `--workflow SIMPLE` results in `TIMEOUT=3600`; Test 17b asserts `--workflow HARD` results in `TIMEOUT=7200`; Test 17c asserts that omitting `--workflow` (default SIMPLE) results in `TIMEOUT=3600`. Regression coverage for the `LAUNCHER_TIMEOUT=7200 / 3600` branch in `step2-implement.sh` that tests 15a–15c did not exercise (those use `--coder claude`, which early-returns before the launcher is spawned).
18. OOS-bundled path warning: stub Codex writes a valid `status=complete` manifest declaring `README.md` while also creating `undeclared.txt`. The dispatcher must still reach `STATUS=complete`, but before `git add -A && git commit` it appends a Warning to `execution-issues.md` naming the undeclared path. This pins the diagnostic-only cross-check between working-tree paths and manifest-declared paths.

**Out of scope**:
- Manifest schema validation for real implementer output.
- Path normalization (`..` / leading `/` / `.claude-plugin/plugin.json` / submodule paths).
- Sanitization via `scripts/redact-secrets.sh`.
- Single-retry on transient launcher failure with clean-state guard.
- `branch-changed` / `submodule-dirty` / `cursor-modified-history` post-implementer checks. (Test 13 covers only the Step 6b absent-`plugin.json` sentinel case from issue #1475; Step 7a path-validation `protected-path-modified` paths and the other Step 6 post-implementer rejections remain out of scope here.)
- `commit-failed` recovery on the dispatcher-side commit. (Tests 13 and 18 exercise the happy path of `git add -A && git commit -F …` end-to-end via stub Codex; failure-recovery branches remain out of scope.)

**Invariants**:
- Tests run against the live dispatcher in the repo, not a copy.
- The Claude fallback branch short-circuits before plugin / git resolution and ignores empty Cursor presence input.
- Scratch directory is created via `mktemp -d` and removed via `trap` on exit.

**Call sites**:
- `make test-step2-dispatch`.
- `make test-harnesses`.
- `make lint`.

**Edit-in-sync**:
- `skills/implement/scripts/step2-implement.sh` — argument parsing, fallback branching, presence gate ordering, baseline-file handling, or resume counter behavior must be exercised here.
- `skills/implement/scripts/step2-implement.md` — sibling dispatcher contract.
- `scripts/test-implement-structure.sh` — structural pins for the dispatcher and implementer launchers.

**Running locally**: `make test-step2-dispatch` or `bash skills/implement/scripts/test-step2-dispatch.sh`.
