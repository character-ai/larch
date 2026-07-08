## Goal
Implement issue #6590: [IMPLEMENTING] [BUG] bgjob wait with empty --tmpdir resolves to cwd and returns missing-registry for live daemons.

## Implementation Plan
## Summary

When `python/cli.py bgjob wait` is called with an empty `--tmpdir ""` argument (which happens in Claude Code's ephemeral-shell Bash tool when `$IMPLEMENT_TMPDIR` is unset between tool calls), `Path("").resolve()` returns the repository root (cwd) instead of the session tmpdir. `registry.read_for` then computes a wrong `default_run_id` hash and looks for a registry file that does not exist, returning `BGJOB_STATUS=DEAD BGJOB_DIAG=missing-registry` — even though the daemon is alive and registered under the correct hash. Every `bgjob wait` call in an ephemeral shell without `$IMPLEMENT_TMPDIR` pre-set silently fails this way.

## Original report

Root cause of review failure during `/implement` session on `larch3`. After the rebase was resolved and the implementation committed, the `bgjob wait` for `implement-step3-checks` and `implement-step5-review` repeatedly returned `BGJOB_STATUS=DEAD BGJOB_DIAG=missing-registry`. Investigation revealed the daemon was started successfully (confirmed by `BGJOB_STATUS=STARTED PGID=<n>`) but the subsequent `bgjob wait` call used a different registry path because `$IMPLEMENT_TMPDIR` was empty in the fresh Bash tool shell.

## Reproduction scenario

1. Start a `/implement` session; Step 0 bootstrap creates `IMPLEMENT_TMPDIR=/path/to/session-tmpdir`.
2. In a fresh Claude Code Bash tool call (shell state not preserved), run:
   ```bash
   "$HOME/.cache/larch/sessions/implement-run-$PPID.sh" python/cli.py bgjob wait \
     --step implement-step3-checks \
     --tmpdir "$IMPLEMENT_TMPDIR" \   # expands to "" because IMPLEMENT_TMPDIR is unset
     --max-wait-s 270
   ```
3. The `--tmpdir ""` argument causes `Path("").resolve()` → cwd (e.g. `<OPERATOR_REPO_PATH>
4. `default_run_id(tmpdir=cwd)` produces hash A (e.g. `a2dcc0cf66e1ec53`).
5. The daemon was started by `run-step-checks.sh` with `IMPLEMENT_TMPDIR` from the exported env, producing hash B (e.g. `7c9d31c66ac75ed0`).
6. Registry lookup for hash-A file fails → `BGJOB_STATUS=DEAD BGJOB_DIAG=missing-registry`.
7. The daemon continues running; subsequent `bgjob start` launches a second parallel daemon for the same step, competing with the first.

The problem is absent in interactive shells where `$IMPLEMENT_TMPDIR` persists across commands.

## Expected behavior

`bgjob wait` should locate the live registry entry. When `--tmpdir ""` (or absent) is passed, it should fall back to `$IMPLEMENT_TMPDIR` env var (which `implement-run-$PPID.sh` exports correctly before exec-ing `larch-run.sh`), the same way `run-step-checks.sh` uses the env var for `bgjob start`.

## Observed behavior

`bgjob wait --tmpdir ""` resolves the tmpdir to cwd, computes a hash that does not match any live registry entry, and immediately returns `BGJOB_STATUS=DEAD BGJOB_DIAG=missing-registry` with a path like `<OPERATOR_REPO_PATH>/larch/daemons/a2dcc0cf66e1ec53-implement-step3-checks.env`.

Concrete hashes observed in this session:
- Actual session tmpdir `claude-implement-larch3-fuv77x1l` → hash `7c9d31c66ac75ed0`
- cwd `/Users/zhupanov/larch3` (empty-arg resolution) → hash `a2dcc0cf66e1ec53`

## Root cause analysis

`python/larch/bgjob/cli.py` `wait_main` uses `tmpdir=Path(args.tmpdir)` with no env-var fallback. When `args.tmpdir` is the empty string (because `$IMPLEMENT_TMPDIR` was unset in the calling shell), `Path("")` evaluates to `Path(".")` which `.resolve()` turns into the cwd. `registry.read_for` then calls `model.default_run_id(tmpdir=cwd)` which hashes the cwd path, not the session tmpdir.

Meanwhile, `bgjob start` is invoked from `run-step-checks.sh` which reads `IMPLEMENT_TMPDIR` directly from the environment (the launcher exports it before exec), so it uses the correct hash.

The mismatch is specific to Claude Code's tool-call model: each Bash tool call starts a fresh shell where `$IMPLEMENT_TMPDIR` is not set unless the fence explicitly hardcodes the path. The `implement-run-$PPID.sh` launcher correctly exports `IMPLEMENT_TMPDIR` to the subprocess's environment, but the `--tmpdir "$IMPLEMENT_TMPDIR"` CLI argument expands to `""` in the calling shell before the subprocess runs, overriding the env var.

## Evidence

- `python3 -c "from pathlib import Path; print(Path('').resolve())"` → `/Users/zhupanov/larch3` (cwd)
- `model.default_run_id(tmpdir=Path('').resolve(), ...)` → `a2dcc0cf66e1ec53`
- `model.default_run_id(tmpdir=Path('<TMPDIR>'), ...)` → `7c9d31c66ac75ed0`
- `bgjob wait` source: `tmpdir=Path(args.tmpdir)` — no env-var fallback in `wait_main`
- `run-step-checks.sh` line 29: `IMPLEMENT_TMPDIR="${IMPLEMENT_TMPDIR:?IMPLEMENT_TMPDIR required}"` — uses env var, always correct
- `implement-run-$PPID.sh`: exports `IMPLEMENT_TMPDIR` from env file before exec — correct for child env, but `$@` args already expanded
- Session observed: three consecutive `bgjob start` calls returned `STARTED`; all three `bgjob wait` calls (with wrong tmpdir) returned `missing-registry`; only after hardcoding `--tmpdir /path/to/session` did `bgjob wait` find the registry

## Affected files

- `python/larch/bgjob/cli.py` — `wait_main`: no env-var fallback for empty `--tmpdir`
- `python/larch/bgjob/wait.py` — `wait_once`: receives wrong `tmpdir`, computes wrong `run_id` via `registry.read_for`
- `python/larch/bgjob/model.py` — `default_run_id`: hashes `tmpdir.resolve()`, giving cwd when tmpdir is empty
- `skills/implement/SKILL.md` — bgjob wait fence template uses `--tmpdir "$IMPLEMENT_TMPDIR"` which expands to `""` in ephemeral shells

## Suggested fix(es)

**Option A (preferred)**: In `wait_main`, fall back to the `IMPLEMENT_TMPDIR` env var when `args.tmpdir` is empty or missing:
```python
tmpdir_str = args.tmpdir or os.environ.get("IMPLEMENT_TMPDIR", "")
if not tmpdir_str:
    print("BGJOB_ERROR=missing-tmpdir")
    return 2
tmpdir = Path(tmpdir_str)
```

**Option B**: In `larch-run.sh` (or `implement-run-$PPID.sh`), intercept `--tmpdir ""` in `$@` and replace it with the known `IMPLEMENT_TMPDIR` value before passing to the Python script.

**Option C**: Update the fence template in SKILL.md to require a hardcoded path for the `--tmpdir` argument, with a note that `$IMPLEMENT_TMPDIR` must be set before the fence runs (e.g., via a one-line `IMPLEMENT_TMPDIR=<path>` prefix guard).

Option A is the simplest and most robust fix; it aligns with how `run-step-checks.sh` already uses the env var.

## Open questions

- Should `bgjob start` also adopt an env-var fallback for consistency, or is the shell-script caller (`run-step-checks.sh`) sufficient?
- Does the same empty-arg issue affect `bgjob start` when called through a `.py` fence (if any such fence exists)?
- Is there a test for `wait_main` with an empty `--tmpdir` arg?

## Test plan
(no test plan section in plan-file)
