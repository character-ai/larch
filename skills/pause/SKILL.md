---
name: pause
description: Use when the operator wants to pause a live /design session and save resumable state to the issue.
---

# /larch:pause

Pause a running `/design` session on this Claude PID. Takes no arguments.

## Verification

After running the script, verify the parsed `PAUSE_OK` value. `PAUSE_OK=true`
is the only success path for a live session; it prints the saved `STEP` and
`RUN_ID`. `PAUSE_OK=false` prints the helper `ERROR=` token and exits non-zero.
When no live `/design` env is present, verify that the script prints the
"nothing to pause" info line and exits 0 without invoking the save helper.

Run this single foreground Bash block:

```bash
set -euo pipefail

ENV_FILE="$HOME/.cache/larch/sessions/current-design-env-$PPID.sh"
if [ ! -f "$ENV_FILE" ]; then
  printf '%s\n' "**ℹ /larch:pause: no live /design session detected on this PID; nothing to pause.**"
  exit 0
fi

# shellcheck disable=SC1090
source "$ENV_FILE" || true
if [ -z "${DESIGN_TMPDIR:-}" ] || [ -z "${ISSUE_NUMBER:-}" ]; then
  printf '%s\n' "**ℹ /larch:pause: no live /design session detected on this PID; nothing to pause.**"
  exit 0
fi

REPO=""
if [ -x "${CLAUDE_PLUGIN_ROOT:-}/scripts/resolve-repo.sh" ]; then
  REPO=$("${CLAUDE_PLUGIN_ROOT}/scripts/resolve-repo.sh" 2>/dev/null || true)
fi
if [ -z "$REPO" ]; then
  REPO=$(gh repo view --json nameWithOwner --jq '.nameWithOwner' 2>/dev/null || true)
fi

printf '%s\n' "🛑 /larch:pause: saving state for issue #${ISSUE_NUMBER}..."
mkdir -p "$DESIGN_TMPDIR"
: > "$DESIGN_TMPDIR/.pause-requested"
pause_args=(
  "${CLAUDE_PLUGIN_ROOT}/scripts/design-pause-save.sh"
  --design-tmpdir "$DESIGN_TMPDIR"
  --issue "$ISSUE_NUMBER"
)
if [ -n "$REPO" ]; then
  pause_args+=(--repo "$REPO")
fi

pause_out=$("${pause_args[@]}")
printf '%s\n' "$pause_out" > "$DESIGN_TMPDIR/pause-save.out"

pause_ok=$(printf '%s\n' "$pause_out" | awk -F= '$1=="PAUSE_OK"{print $2}' | tail -1)
step=$(printf '%s\n' "$pause_out" | awk -F= '$1=="STEP"{print $2}' | tail -1)
run_id=$(printf '%s\n' "$pause_out" | awk -F= '$1=="RUN_ID"{print $2}' | tail -1)
err=$(printf '%s\n' "$pause_out" | awk -F= '$1=="ERROR"{print $2}' | tail -1)

if [ "$pause_ok" = "true" ]; then
  printf '%s\n' "✅ /larch:pause: state saved (STEP=${step}, RUN_ID=${run_id}) — re-invoke /design ${ISSUE_NUMBER} to resume"
  exit 0
fi

printf '%s\n' "**⚠ /larch:pause: save failed — ${err:-unknown}; see $DESIGN_TMPDIR/execution-issues.md**"
exit 1
```
