#!/usr/bin/env bash
# Offline harness for the /larch:pause skill Bash block.

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd -P)"
SKILL_MD="$REPO_ROOT/skills/pause/SKILL.md"
TMP=$(mktemp -d "${TMPDIR:-/tmp}/test-pause-skill.XXXXXX")
trap 'rm -rf "$TMP"' EXIT

fail() {
  echo "FAIL: $1" >&2
  exit 1
}

BLOCK="$TMP/pause-skill.sh"
awk '
  in_block && /^```$/ { exit }
  in_block { print }
  /^```bash$/ { in_block=1 }
' "$SKILL_MD" >"$BLOCK"
[[ -s "$BLOCK" ]] || fail "could not extract Bash block from skills/pause/SKILL.md"

run_block() {
  local home_dir="$1"
  local env_src="${2:-}"
  HOME="$home_dir" bash -c '
    set -euo pipefail
    if [[ -n "$1" ]]; then
      cp "$1" "$HOME/.cache/larch/sessions/current-design-env-$PPID.sh"
    fi
    exec bash "$2"
  ' _ "$env_src" "$BLOCK"
}

echo "=== no env file exits cleanly ==="
HOME1="$TMP/home-no-env"
mkdir -p "$HOME1"
out_no_env=$(run_block "$HOME1")
[[ "$out_no_env" == "**ℹ /larch:pause: no live /design session detected on this PID; nothing to pause.**" ]] \
  || fail "no-env output mismatch: $out_no_env"

echo "=== incomplete env exits cleanly without save helper ==="
HOME2="$TMP/home-incomplete"
PLUGIN2="$TMP/plugin-incomplete"
mkdir -p "$HOME2/.cache/larch/sessions" "$PLUGIN2/scripts"
cat >"$PLUGIN2/scripts/design-pause-save.sh" <<'EOF_SAVE2'
#!/usr/bin/env bash
set -euo pipefail
echo "UNEXPECTED_SAVE"
EOF_SAVE2
chmod +x "$PLUGIN2/scripts/design-pause-save.sh"
ENV2="$TMP/env2.sh"
cat >"$ENV2" <<EOF_ENV2
export CLAUDE_PLUGIN_ROOT="$PLUGIN2"
export ISSUE_NUMBER=9
EOF_ENV2
out_incomplete=$(run_block "$HOME2" "$ENV2")
[[ "$out_incomplete" == "**ℹ /larch:pause: no live /design session detected on this PID; nothing to pause.**" ]] \
  || fail "incomplete-env output mismatch: $out_incomplete"

echo "=== live session save succeeds ==="
HOME3="$TMP/home-live"
PLUGIN3="$TMP/plugin-live"
DESIGN3="$TMP/design-live"
mkdir -p "$HOME3/.cache/larch/sessions" "$PLUGIN3/scripts" "$DESIGN3"
cat >"$PLUGIN3/scripts/resolve-repo.sh" <<'EOF_REPO3'
#!/usr/bin/env bash
set -euo pipefail
printf 'owner/repo\n'
EOF_REPO3
chmod +x "$PLUGIN3/scripts/resolve-repo.sh"
cat >"$PLUGIN3/scripts/design-pause-save.sh" <<'EOF_SAVE3'
#!/usr/bin/env bash
set -euo pipefail
printf 'PAUSE_OK=true\nSTEP=2b\nRUN_ID=RUNPAUSE3\n'
EOF_SAVE3
chmod +x "$PLUGIN3/scripts/design-pause-save.sh"
ENV3="$TMP/env3.sh"
cat >"$ENV3" <<EOF_ENV3
export CLAUDE_PLUGIN_ROOT="$PLUGIN3"
export DESIGN_TMPDIR="$DESIGN3"
export ISSUE_NUMBER=9
EOF_ENV3
out_live=$(run_block "$HOME3" "$ENV3")
[[ "$out_live" == *"🛑 /larch:pause: saving state for issue #9..."* ]] || fail "live save banner missing: $out_live"
[[ "$out_live" == *"✅ /larch:pause: state saved (STEP=2b, RUN_ID=RUNPAUSE3) — re-invoke /design 9 to resume"* ]] \
  || fail "live success output mismatch: $out_live"
[[ -f "$DESIGN3/pause-save.out" ]] || fail "pause-save.out missing on success"
! [[ -f "$DESIGN3/.pause-requested" ]] || fail ".pause-requested should not be created by /larch:pause"

echo "=== live session save failure surfaces parsed error ==="
HOME4="$TMP/home-fail"
PLUGIN4="$TMP/plugin-fail"
DESIGN4="$TMP/design-fail"
mkdir -p "$HOME4/.cache/larch/sessions" "$PLUGIN4/scripts" "$DESIGN4"
cat >"$PLUGIN4/scripts/resolve-repo.sh" <<'EOF_REPO4'
#!/usr/bin/env bash
set -euo pipefail
printf 'owner/repo\n'
EOF_REPO4
chmod +x "$PLUGIN4/scripts/resolve-repo.sh"
cat >"$PLUGIN4/scripts/design-pause-save.sh" <<'EOF_SAVE4'
#!/usr/bin/env bash
set -euo pipefail
printf 'PAUSE_OK=false\nERROR=publish-and-recovery-failed\n'
EOF_SAVE4
chmod +x "$PLUGIN4/scripts/design-pause-save.sh"
ENV4="$TMP/env4.sh"
cat >"$ENV4" <<EOF_ENV4
export CLAUDE_PLUGIN_ROOT="$PLUGIN4"
export DESIGN_TMPDIR="$DESIGN4"
export ISSUE_NUMBER=9
EOF_ENV4
set +e
out_fail=$(run_block "$HOME4" "$ENV4")
rc_fail=$?
set -e
[[ "$rc_fail" == "1" ]] || fail "expected failing exit from live save failure, got $rc_fail"
[[ "$out_fail" == *"**⚠ /larch:pause: save failed — publish-and-recovery-failed; see $DESIGN4/execution-issues.md**"* ]] \
  || fail "live failure output mismatch: $out_fail"

echo "PASS: /larch:pause skill block"
