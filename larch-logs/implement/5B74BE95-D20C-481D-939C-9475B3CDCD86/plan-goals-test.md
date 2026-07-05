## Goal
Implement issue #6374: [IMPLEMENTING] architectural-guidelines-III [BUG] Design architectural-guideline assessment silently skipped on ~12% of --skip-approve runs.

## Implementation Plan
## Plan

Approach

Capture the repo root once during `/design` Step 0, while the caller cwd is still trusted. Persist it in `source-env.sh` as `REPO_ROOT`. Bind that value in-fence and pass it to every design-side architectural guideline presentation and persistence call.

Preserve `REPO_ROOT` across every later `write-design-env` refresh. The dominant `ROUTE=proceed` path runs a second `write-design-env` from `init_runparams_main` that currently rebuilds `source-env.sh` without `REPO_ROOT`, silently clobbering the Step 0 capture. Fix this in the writer itself: when `--repo-root` and the environment fallback are both empty, recover the prior `REPO_ROOT` from the existing `source-env.sh`. This covers every `write-design-env` caller (Step 0a session, Step 0b init-runparams, later refreshes) without duplicating repo-root resolution at each call site.

Bind `REPO_ROOT` in-fence at each consuming Bash fence. Bash state does not persist across `/design` fences, so a bare `--repo-root "$REPO_ROOT"` would expand to an empty root and fall back to ambient cwd. Each guideline-helper fence must source `$DESIGN_TMPDIR/source-env.sh` (or inline-read the `export REPO_ROOT=` line) before the first helper call, then repair-stop when the bound value is empty.

Keep `_resolve_repo_root(None)` unchanged. The fix avoids ambient cwd fallback by passing an in-fence-bound `--repo-root "$REPO_ROOT"` at the call sites that own the design flow.

Preserve the Gate C fail-closed contract. If `persist-design-assessment` exits non-zero, Gate C must still append the bounded `Warnings` line and stop before prompt, approval, auto-approval, or Step 5.

Files to modify/create

### UPDATED: python/larch/design/design_step0.py

Resolve the authoritative repo root at Step 0 and thread it into the session env.

- Reuse the existing `larch.git.repo_roots.consumer_repo_root(Path.cwd())` resolver (already the design-flow idiom in `design_step2b` / `design_publish` / `design_postplan`) instead of adding a parallel `git rev-parse` helper.
- Fall back to `Path.cwd().resolve()` only when `consumer_repo_root` returns `None`.
- Thread the resolved root into `session write-design-env` with `--repo-root <root>`.

Keep the existing session setup, degraded-tools gate, and parse-KV ordering unchanged.

### UPDATED: python/larch/state/session_env.py

Extend `session write-design-env` to accept `--repo-root` and preserve it across refreshes.

- Add the `--repo-root` flag to the parser.
- Validate it as an absolute single-line path before export.
- Prefer explicit `--repo-root` over the old `CLAUDE_PROJECT_DIR` / `REPO_ROOT` environment fallback.
- When `--repo-root` and both env fallbacks are empty, recover `REPO_ROOT` from the prior `source-env.sh` at the output path, mirroring the existing `CODEX_BINARY_FOUND` recovery flow. Parse the persisted `export REPO_ROOT=...` line with the existing allowlisted/shlex-aware env-line parser, not a bool-style regex, so quoted paths are recovered. This keeps a later `init_runparams_main` refresh from clobbering the Step 0 capture.
- Keep `REPO_ROOT` in the existing `WRITE_DESIGN_ENV_KEYS` design env allowlist so the recovered/threaded value survives writer validation.

Add focused tests for explicit root export, prior-value recovery, and bad root rejection.

### UPDATED: skills/design/references/approval-gates.md

Bind `REPO_ROOT` in-fence, then pass it to every Gate C guideline helper.

- Because Bash state does not persist across fences, each Gate C guideline-helper fence must first bind `REPO_ROOT` in-fence: source `$DESIGN_TMPDIR/source-env.sh` (or inline-read the `export REPO_ROOT=` line) before the first `present-note` / `persist-design-assessment` call. `session read-key` is unreliable here because the line is `export`-prefixed.
- `present-note` becomes `present-note --repo-root "$REPO_ROOT"`.
- `present-note --assessment clean` also passes `--repo-root "$REPO_ROOT"`.
- Every `persist-design-assessment` branch passes `--repo-root "$REPO_ROOT"`.
- State that Gate C must stop for repair if `REPO_ROOT` is empty or unavailable after binding, before any guideline helper call.

Do not weaken absent or invalid guideline behavior.

### UPDATED: skills/design/references/design-outline.md

Bind and use the same explicit root for Step 1d.7 guideline presentation.

- Source `$DESIGN_TMPDIR/source-env.sh` in the Step 1d.7 guideline fence to bind `REPO_ROOT` before the helpers (same in-fence rule as Gate C).
- Pass `--repo-root "$REPO_ROOT"` to `present-note` and `present-note --assessment clean`.
- Keep the empty-`REPO_ROOT` repair stop and outline auto-approval behavior unchanged.

### UPDATED: python/larch/git/pr_body.py

Fix the run-summary Larch version fallback.

- Correct `_plugin_version_local()` so it reads `.claude-plugin/plugin.json` from the plugin root, not `python/larch/.claude-plugin/plugin.json`.
- Use `config.PLUGIN_JSON_PATH`.
- Keep explicit kwargs and manifest identity as higher priority than the live fallback.

### UPDATED: python/larch/state/_report.py

Make the stall and failure report version helper read the plugin manifest as a fallback.

- Keep current `VERSION` and `package.json` attempts if needed for compatibility.
- Add `.claude-plugin/plugin.json` version fallback from the same resolved plugin root.
- Validate the value with the existing safe version regex.

### UPDATED: python/tests/design/test_design_lifecycle.py

Add Step 0 regression coverage, including the dominant proceed-path refresh.

- Assert `step0_session_main()` passes `--repo-root` (the resolved `consumer_repo_root` toplevel) to `session write-design-env`.
- Simulate a subdirectory launch and verify the git toplevel, not the subdirectory, is passed when git resolves.
- After `step0_session_main()` then `init_runparams_main()` on a `ROUTE=proceed` path, assert `source-env.sh` still exports the git-toplevel `REPO_ROOT` (the init refresh must not clobber it), even though init-runparams omits `--repo-root`.
- Keep existing fake setup and degraded-tools tests passing.

### UPDATED: python/tests/state/test_session_env.py

Add writer tests.

- `write-design-env --repo-root <absolute>` writes `export REPO_ROOT=...`.
- Explicit `--repo-root` wins over ambient `CLAUDE_PROJECT_DIR`.
- A refresh that omits `--repo-root` recovers the quoted `REPO_ROOT` from the prior `source-env.sh` instead of dropping it.
- Invalid or relative `--repo-root` returns non-zero and emits one `ERROR=` line.

### UPDATED: python/tests/core/test_architectural_guidelines.py

Add the main regression, the fail-closed negative path, and the Gate C branch contract.

- Create a temp repo with `ARCHITECTURAL_GUIDELINES.md`.
- Create an allowed temp design tmpdir.
- Change cwd to a separate plugin-cache-like directory and clear `CLAUDE_PROJECT_DIR`.
- Drive the `--skip-approve` Gate C helper sequence with explicit `--repo-root`: `present-note`, optional clean assessment, then `persist-design-assessment`.
- Assert `architectural-guideline-assessment.md` exists and contains the clean note.
- Add a paired assertion that omitting explicit root from the wrong cwd resolves absent, to document the bug shape without relying on production prompt code.
- Add a negative fail-closed regression: force `persist_design_assessment_main` to a non-zero exit (guidelines present but the assessment target cannot be written, e.g. a non-regular-file / symlink target), and assert the helper returns non-zero.
- Pin the skip-approve Gate C branch contract directly (no executable Gate C harness exists): a narrow markdown contract assertion that `approval-gates.md` Gate C `--skip-approve` carve-out and `design-outline.md` Step 1d.7 both source `source-env.sh`, invoke `present-note` and `persist-design-assessment` with `--repo-root "$REPO_ROOT"`, and keep the bounded-warning repair stop before any auto-approval / Step 5 transition.

### UPDATED: python/tests/git/test_pr_body.py

Add version fallback coverage.

- Exercise `render_run_summary()` with no manifest identity and a plugin root containing `.claude-plugin/plugin.json`.
- Assert the summary prints the manifest version instead of `unknown`.

### MAY_UPDATE: python/skill-closure-baseline.json

Update only if `python3 python/cli.py lint skill-closure-growth --skill design` fails because of the `approval-gates.md` or `design-outline.md` wording change.

Edge cases

- Repos without `ARCHITECTURAL_GUIDELINES.md` still produce no assessment artifact and no warning.
- Invalid guidelines still remove stale design assessment artifacts and continue without deviation assessment.
- Gate C re-entry overwrites the assessment with the latest clean or deviation result.
- A plugin-cache cwd no longer makes a repo with guidelines look absent.
- The `ROUTE=proceed` init-runparams refresh no longer drops `REPO_ROOT` from `source-env.sh`.
- A guideline fence that forgot to source `source-env.sh` binds an empty `REPO_ROOT` and repair-stops rather than silently resolving absent.

Failure modes

- If Step 0 cannot resolve or write `REPO_ROOT` and no prior value exists to recover, later Gate C calls bind an empty root and repair-stop; treat this as a repair stop, not as absent guidelines.
- If a refresh silently dropped `REPO_ROOT` (the current bug), Gate C would fall back to cwd and skip the assessment; the writer-side recovery closes this path and the lifecycle test guards it.
- If `persist-design-assessment` fails, preserve the existing warning append and Gate C stop; the negative regression and branch-contract test guard against a future edit that skips it.
- If the design closure ratchet trips, update only the baseline row required by the prompt wording change.

Testing strategy

Run targeted tests, then the design closure lint:

```bash
python3 -m pytest python/tests/design/test_design_lifecycle.py python/tests/state/test_session_env.py python/tests/core/test_architectural_guidelines.py python/tests/git/test_pr_body.py
python3 python/cli.py lint skill-closure-growth --skill design
python3 python/cli.py checks run-relevant
```

## Acceptance

- A `--skip-approve` design run in a repo that has `ARCHITECTURAL_GUIDELINES.md` always commits `architectural-guideline-assessment.md` (clean or deviation).
- If persistence genuinely cannot run, the run records the contracted bounded `Warnings` line and Gate C stops before auto-approval or Step 5, rather than finishing silently.
- A regression drives the `skip_approve_requested=true` Gate C path and asserts the assessment artifact is present; a negative test forces a non-zero persist and asserts the fail-closed warning behavior.
- The design final-summary resolves the real Larch version (not `unknown`) through the corrected `_plugin_version_local` plugin.json path.

diff_lines: 410

## Test plan
(no test plan section in plan-file)
