## Goal
Implement issue #4458: [IMPLEMENTING] [BUG] implement-preflight.sh exits 2 on initial run when CLAUDE_PLUGIN_ROOT is not set — missing self-location fallback.

## Implementation Plan
## Summary

`scripts/implement-preflight.sh` fails on any initial `/implement` run where `CLAUDE_PLUGIN_ROOT` is not already in the environment. The script tries to resolve the plugin root from `$IMPLEMENT_TMPDIR/plugin-root.env`, but `IMPLEMENT_TMPDIR` does not exist yet (Step 0 creates it after preflight). With no self-location fallback, the script exits 2 with `**❌ /implement preflight: cannot resolve CLAUDE_PLUGIN_ROOT/python/cli.py.**` before doing any real work. The SKILL.md fence has the same gap: its source guard is also gated on `IMPLEMENT_TMPDIR` being non-empty.

## Original report

Operator ran `/implement --merge 4426` in a fresh Claude session. The first Bash call to `implement-preflight.sh` failed immediately:

```
**❌ /implement preflight: cannot resolve CLAUDE_PLUGIN_ROOT/python/cli.py.**
EXIT=2
```

A second call with `CLAUDE_PLUGIN_ROOT` set explicitly succeeded. Root cause was identified as the script having no fallback to self-locate when `IMPLEMENT_TMPDIR` is absent.

## Reproduction scenario

1. Open a fresh Claude Code session (no prior `/implement` run in the session).
2. Run `/implement <issue-N>` or `/im <issue-N>`.
3. The orchestrator executes the SKILL.md Preflight fence without `CLAUDE_PLUGIN_ROOT` set in the environment and without `IMPLEMENT_TMPDIR` pointing to an existing dir.
4. `implement-preflight.sh` reaches line 67 (`if [ -z "${CLAUDE_PLUGIN_ROOT:-}" ] || [ ! -f ... ]`), finds `CLAUDE_PLUGIN_ROOT` empty, and exits 2.

The failure does **not** occur on resume runs (where `IMPLEMENT_TMPDIR` already points to a live session dir containing `plugin-root.env`).

## Expected behavior

`implement-preflight.sh` resolves its own plugin root without any precondition on external environment variables. Since the script lives at `$CLAUDE_PLUGIN_ROOT/scripts/implement-preflight.sh`, it can always derive the root from `$0`.

## Observed behavior

The script exits 2 with a misleading error message (`cannot resolve CLAUDE_PLUGIN_ROOT/python/cli.py`) that implies a configuration problem rather than a missing self-location fallback. The user must set `CLAUDE_PLUGIN_ROOT` manually for the run to proceed.

## Root cause analysis

**Confirmed root cause.** `implement-preflight.sh` resolves `CLAUDE_PLUGIN_ROOT` in exactly one way (lines 64–65):

```bash
if [ -z "${CLAUDE_PLUGIN_ROOT:-}" ] && [ -n "${IMPLEMENT_TMPDIR:-}" ] && [ -f "$IMPLEMENT_TMPDIR/plugin-root.env" ]; then
  . "$IMPLEMENT_TMPDIR/plugin-root.env"
fi
```

This guard requires `IMPLEMENT_TMPDIR` to be set and contain `plugin-root.env`. `IMPLEMENT_TMPDIR` is created by `step-0-bootstrap.sh`, which runs **after** the preflight. So on every initial run the guard is a no-op and `CLAUDE_PLUGIN_ROOT` stays unset.

The SKILL.md Preflight fence (item 1, line 197) has the same conditional:

```bash
[ -z "${CLAUDE_PLUGIN_ROOT:-}" ] && [ -n "${IMPLEMENT_TMPDIR:-}" ] && [ -f "$IMPLEMENT_TMPDIR/plugin-root.env" ] && . "$IMPLEMENT_TMPDIR/plugin-root.env"
```

On initial runs this line does nothing, and line 208 expands `${CLAUDE_PLUGIN_ROOT}` to the empty string, which would also cause a path error if the orchestrator hadn't hardcoded the script path. Either way, the environment lacks `CLAUDE_PLUGIN_ROOT` when the script needs it.

## Evidence

- `scripts/implement-preflight.sh` lines 64–70: only source guard is gated on `IMPLEMENT_TMPDIR`; no `$0`-based self-location fallback exists.
- `skills/implement/SKILL.md` lines 197–208 (Preflight item 1 fence): source guard also gated on `IMPLEMENT_TMPDIR`.
- `step-0-bootstrap.sh` creates `IMPLEMENT_TMPDIR` after preflight completes; therefore `plugin-root.env` cannot exist inside it before preflight runs.
- Observed exit on initial run: `EXIT=2` with `cannot resolve CLAUDE_PLUGIN_ROOT/python/cli.py`.
- Observed success after explicitly setting `CLAUDE_PLUGIN_ROOT="<OPERATOR_REPO_PATH>/plugins/cache/larch-local/larch/50.1.1"` before the call.

## Affected files

- `scripts/implement-preflight.sh` — missing self-location fallback; fix belongs here.
- `skills/implement/SKILL.md` — Preflight item 1 fence has the same `IMPLEMENT_TMPDIR`-gated guard; may need a parallel fix or a note that the orchestrator must set `CLAUDE_PLUGIN_ROOT` before calling the fence.

## Suggested fix(es)

**Primary fix (in `scripts/implement-preflight.sh`)**: Add a `$0`-based self-location fallback between the existing source guard and the error check:

```bash
# existing source guard (resume path)
if [ -z "${CLAUDE_PLUGIN_ROOT:-}" ] && [ -n "${IMPLEMENT_TMPDIR:-}" ] && [ -f "$IMPLEMENT_TMPDIR/plugin-root.env" ]; then
  . "$IMPLEMENT_TMPDIR/plugin-root.env"
fi
# NEW: self-locate from script's own path (initial-run fallback)
if [ -z "${CLAUDE_PLUGIN_ROOT:-}" ]; then
  CLAUDE_PLUGIN_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
  export CLAUDE_PLUGIN_ROOT
fi
# existing error check
if [ -z "${CLAUDE_PLUGIN_ROOT:-}" ] || [ ! -f "${CLAUDE_PLUGIN_ROOT}/python/cli.py" ]; then
  printf '**❌ /implement preflight: cannot resolve CLAUDE_PLUGIN_ROOT/python/cli.py.**\n'
  exit 2
fi
```

This works because `implement-preflight.sh` is invoked as `bash "<absolute-path>/scripts/implement-preflight.sh"`, so `$0` is the absolute script path and `dirname "$0"/..` is the plugin root.

**Secondary fix (in `skills/implement/SKILL.md`)**: The SKILL.md Preflight fence could also set `CLAUDE_PLUGIN_ROOT` explicitly before calling the script, since the full plugin path is already hardcoded in the fence (line 208). However, fixing the script is the more robust approach because it removes the dependency on orchestrator discipline.

**Test**: `make test-implement-preflight` (existing harness at `scripts/test-implement-preflight.sh`) should include a case where neither `CLAUDE_PLUGIN_ROOT` nor `IMPLEMENT_TMPDIR` is set, and assert the script succeeds via the self-location path.

## Open questions

- Should the `make test-implement-preflight` harness add an explicit "initial run without env vars" test case, or is the existing harness coverage sufficient once the fix is in?
- Should the SKILL.md fence be updated in parallel to remove the `IMPLEMENT_TMPDIR`-gated guard (since the script no longer needs it), or leave both as defense-in-depth?

## Test plan
(no test plan section in plan-file)
