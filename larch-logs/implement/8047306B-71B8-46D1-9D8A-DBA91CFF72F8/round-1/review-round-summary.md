# Review Round 1

- Mode: `diff`
- 14 accepted, 0 rejected (0 neutral)

## Accepted Findings

### FINDING_1: `_materialize_oos` succeeds when helper is missing
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, dyn-dispatch-parity-output.txt
- **Severity**: important
- **Concern**: `_materialize_oos` returns early with no bail when `materialize-manifest-oos.sh` is missing or not runnable. A manifest with `oos_observations` on a tree where the helper is absent or `plugin_root` is wrong can complete with `STATUS=complete` while OOS items are never materialized. The retired shell ran `--count-only` first and bailed with `manifest-oos-materialization-failed` when the count precheck failed or count was `> 0`, breaking the Step 8b / Step 9a OOS disposition contract on partial checkout, packaging mistakes, or path drift.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Mirror bash: always run --count-only first; if helper missing/non-executable or materialize fails while count>0 or count-precheck fails return manifest-oos-materialization-failed.
  - From dyn-dispatch-parity-output.txt: mirror the shell fail-closed rule: if the helper is missing or not runnable, run `--count-only` when possible and return `manifest-oos-materialization-failed` when the count is unavailable or `> 0`; only skip when the probe proves zero OOS blocks.


### FINDING_13: Dispatcher ignores `git add -A` failures before `git commit`
- **Reviewer(s)**: codex-specialist-edge-cases-output.txt
- **Severity**: important
- **Concern**: The dispatcher ignores `git add -A` failures before `git commit`. `git add` can fail or partially stage while unrelated index entries remain, then `git commit` can succeed and Step 2 reports complete for the wrong commit.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-edge-cases-output.txt: Capture git add output and return commit-failed before git commit when staging fails.


### FINDING_14: Cursor config copy errors escape launcher without KV envelope
- **Reviewer(s)**: codex-specialist-edge-cases-output.txt
- **Severity**: important
- **Concern**: Cursor config copy errors escape the launcher. An unreadable or racing `~/.cursor/cli-config.json` raises an exception, producing no deterministic launcher KV envelope.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-edge-cases-output.txt: Catch OSError around the copy and continue without the copied config, or emit a controlled launcher envelope.


### FINDING_15: `SKILL.md` cites missing Test 11a/11b for `ORCHESTRATOR_EDIT_AUTHORITY` invariant
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: important
- **Concern**: `SKILL.md` cites pytest Test 11a/11b for `ORCHESTRATOR_EDIT_AUTHORITY` pair invariant but those tests are absent. A bail path could emit `AUTH=allowed` or duplicate `AUTH` lines without failing CI; breaks NEVER #9 enforcement.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Add Test 11a (claude_fallback allowed once) and Test 11b (external bail forbidden once)


### FINDING_16: `docs/linting.md` overclaims launcher/dispatcher pytest coverage
- **Reviewer(s)**: cursor-specialist-testing-output.txt, dyn-reference-sweep-output.txt
- **Severity**: important
- **Concern**: Linting docs overclaim launcher/dispatcher coverage that pytest does not implement. Harness table rows for `make test-codex-implementer` and `make test-cursor-implementer` still describe deleted bash harness behaviors ("tests 11/12", multi-digit `0`/`00`/`000` timeout rejection, parent-mismatch fail-fast, resume-block prompt composition, transcript capture). `python/test_implement_dispatch.py` has ~15–17 tests and does not pin most of the old numbered matrix. Maintainers assume CI guards missing-input rejection, parent-mismatch, cursor-wrap-prompt, etc.; regressions slip through.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Add missing pytest cases or narrow docs to match actual assertions
  - From dyn-reference-sweep-output.txt: Rewrite both rows to list only behaviors actually asserted in `python/test_implement_dispatch.py`, or add the missing pytest cases before keeping the old prose.


### FINDING_17: `implement commit` pathspec forwarding has no pytest coverage
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: important
- **Concern**: `implement commit --pathspec-from-file`/`--pathspec-file-nul` has no pytest coverage after `test-commit-implementation.sh` deletion. Recovery Step 4 commit can break on NUL pathspec forwarding without CI failure.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Add pathspec integration test with spaced paths and COMMITTED/SHA envelope checks


### FINDING_2: Step 2 dispatcher pytest coverage far below deleted shell harness
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt, codex-specialist-testing-output.txt, dyn-dispatch-parity-output.txt, cursor-specialist-testing-output.txt
- **Severity**: important
- **Concern**: Pytest coverage in `python/test_implement_dispatch.py` is far thinner than the deleted `test-step2-dispatch.sh` harness despite plan requiring 1:1 ports of key assertions. Regressions in `needs_qa` repair, scout KV emission, branch guards, `qa-loop-exceeded`, `main-branch-prohibited`, `detached-head-prohibited`, dirty-state-after-timeout retry gating, Codex nonzero salvage, cap/resume flows, recovery-path protected/submodule rejection, wrapper validation, and envelope invariants can ship without CI catching them. Current tests mostly cover happy-path `complete`, one malformed-manifest recovery, and launcher argv edges.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Port remaining harness scenarios (Tests 5-7 11 13-19 22-26 from old test-step2-dispatch.sh) into python/test_implement_dispatch.py.
  - From cursor-specialist-testing-output.txt: Port deleted harness inventory into parametrized pytest with stub launchers and scratch git repos
  - From codex-specialist-testing-output.txt: Add pytest cases for each retired harness contract and each STATUS/REASON/ORCHESTRATOR_EDIT_AUTHORITY combination
  - From dyn-dispatch-parity-output.txt: port the old harness cases above into `python/test_implement_dispatch.py`, especially cap/branch/retry/salvage/AUTH-envelope tests, using the same stub-launcher pattern the shell harness used.


### FINDING_22: Codex `--add-dir` grant path omits POSIX control-character rejection
- **Reviewer(s)**: dyn-launcher-grants-output.txt
- **Severity**: important
- **Concern**: `_canonical_existing_nonsymlink_dir()` omits the POSIX control-character rejection that the retired `launch-codex-implement.sh` enforced via `_codex_add_dir_has_control_chars` before granting Codex `--add-dir`. A manifest/qa/scout/transcript parent path containing embedded newlines or other `[:cntrl:]` bytes can pass validation and reach the `codex exec` argv surface, weakening parity with the bash grant hardening contract.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-launcher-grants-output.txt: Reject any candidate parent with `_CTRL_RE.search(str(path))` (the helper already exists at `python/agents.py:59`) before `resolve()`, mirror the bash fail-fast message shape, and add pytest cases ported from old harness tests 11c/11d.


### FINDING_23: Launcher grant/auth security pytest gaps after harness retirement
- **Reviewer(s)**: dyn-launcher-grants-output.txt
- **Severity**: important
- **Concern**: The branch retires `test-codex-implementer.sh` and routes `make test-codex-implementer` / `make test-cursor-implementer` to pytest, but new tests only cover timeout rejection, tmpdir-root grant rejection, and happy-path argv shape. They do not port symlink parent rejection, cross-path parent mismatch for transcript/qa, `CODEX_HOME` isolation outside `IMPLEMENT_TMPDIR`, or env-key-only `openai-larch-env` argv auth with stripped temp config. A regression in `launch_codex_implement_main` / `launch_cursor_implement_main` sandbox or auth handling could merge without CI detection despite docs claiming parity.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-launcher-grants-output.txt: Port the deleted harness’s security-relevant cases into `python/test_implement_dispatch.py` (symlink parent, parent-directory mismatch, env-key argv-only auth, per-invocation `CODEX_HOME` placement) so grant and auth contracts stay mechanically pinned.


### FINDING_28: Makefile harness targets, `agent-lint.toml`, and `docs/linting.md` out of sync
- **Reviewer(s)**: dyn-reference-sweep-output.txt
- **Severity**: important
- **Concern**: `test-run-step2-dispatch`, `test-step2-dispatch`, and `test-commit-implementation` remain `make lint` prerequisites but `docs/linting.md` has no harness-table rows for them. All five retired Step 2 targets now run identical `python3 -m pytest python/test_implement_dispatch.py -q` with no `-k` filter, so distinct target names imply separate coverage that does not exist. `agent-lint.toml` still claims a sibling `test-step2-dispatch.md` contract and documentation that were deleted.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-reference-sweep-output.txt: Add three linting.md rows explaining the consolidated pytest surface (or collapse Makefile targets and update shard lists), delete the stale `test-step2-dispatch.md` reference from `agent-lint.toml`, and add a `python/test_implement_dispatch.md` sibling if repo convention requires one.


### FINDING_29: `step2-dispatch.md` shows bare `python3` instead of `larch-run.sh` fence
- **Reviewer(s)**: dyn-reference-sweep-output.txt
- **Severity**: important
- **Concern**: The Step 4 usage block in `skills/implement/references/step2-dispatch.md` shows bare `python3 python/cli.py implement commit …` from repo root, but `skills/implement/SKILL.md` mandates post-Step-0 fences through `bash "$IMPLEMENT_TMPDIR/larch-run.sh" python/cli.py implement commit …` for plugin-root rehydration. Copy-paste from the contract doc bypasses the launcher operators are told to use.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-reference-sweep-output.txt: Retarget the examples to the `larch-run.sh` fence shape used in `skills/implement/SKILL.md`, and note that bare `python3 …/python/cli.py` is only for pre-bootstrap call sites.


### FINDING_3: `_materialize_oos` materialize failures lack run-log logging and can complete incorrectly
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt, dyn-dispatch-parity-output.txt
- **Severity**: important
- **Concern**: On materialize helper failure, `_materialize_oos` does not call `run-log append-failure` the way bash did before `manifest-oos-materialization-failed` bail, so operators lose Tool Failures entries in `execution-issues.md` even when the run bails. Additionally, bail logic only triggers when `--count-only` itself fails or returns a digit `> 0`; if `--count-only` returns `0` while the full materialize run fails (helper bug, partial write, race), the dispatcher can return `STATUS=complete` and leave accepted OOS blocks unmaterialized.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: On non-zero materialize exit invoke python/cli.py run-log append-failure with materialize-manifest-oos.log before returning the bail reason matching bash site step2-materialize-manifest-oos.
  - From cursor-specialist-edge-cases-output.txt: Invoke python/cli.py run-log append-failure with the materialize log before returning manifest-oos-materialization-failed, matching deleted step2-implement.sh behavior.
  - From dyn-dispatch-parity-output.txt: treat any non-zero materialize rc as fatal when the sanitized manifest’s `oos_observations` is non-empty (or when `--count-only` is unreadable), and always append the redacted failure log through `run-log append-failure` before bailing.


### FINDING_5: Codex implement auth retries ignore stderr sidecar
- **Reviewer(s)**: codex-specialist-correctness-output.txt, codex-specialist-edge-cases-output.txt
- **Severity**: important
- **Concern**: Codex implement auth retries do not inspect the passed `stderr_path` sidecar. With `LARCH_EXTERNAL_AUTH_RETRIES=5`, auth failures written to `$IMPLEMENT_TMPDIR/codex-impl.log` are not classified, so the launcher stops before later retry attempts that could succeed.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-correctness-output.txt: Include stderr_path and stdout_path in auth retry classifier candidates, or pass the implement sidecar as output.with_suffix(...".sidecar").
  - From codex-specialist-edge-cases-output.txt: Include stderr_path/stdout_path in auth verdict candidates or use the derived sidecar path and mirror it to the contract path.


### FINDING_6: `CODEX_HOME` can be created inside repo via `TMPDIR`
- **Reviewer(s)**: codex-specialist-correctness-output.txt
- **Severity**: important
- **Concern**: Codex implement `CODEX_HOME` can be created under `PWD` or `IMPLEMENT_TMPDIR` because `tempfile` honors `TMPDIR`. If `TMPDIR=$PWD/.tmp`, `CODEX_HOME` lands inside the repo while Codex is granted `--add-dir "$PWD"`, violating the documented isolation contract.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-correctness-output.txt: Create CODEX_HOME under a resolved safe system temp outside both cwd and IMPLEMENT_TMPDIR, and fail closed if that invariant is not true.


