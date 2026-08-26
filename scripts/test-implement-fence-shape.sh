#!/usr/bin/env bash
# Validate /implement SKILL.md Bash fences are thin script-call wrappers.

# shellcheck disable=SC2016 # single-quoted strings are intentional fence/prose literals
unset IMPLEMENT_TMPDIR DESIGN_TMPDIR REVIEW_TMPDIR RESEARCH_TMPDIR SESSION_TMPDIR
set -euo pipefail

REPO_ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd -P)"
SKILL_PATH="$REPO_ROOT/skills/implement/SKILL.md"
RESUME_PATH="$REPO_ROOT/skills/implement/references/bootstrap-recovery.md"
WORK_DIR="$(mktemp -d "${TMPDIR:-/tmp}/test-implement-fence-shape.XXXXXX")"
ERRORS_FILE="$WORK_DIR/errors"
FENCE_STATS="$WORK_DIR/fence-stats"
trap 'rm -rf "$WORK_DIR"' EXIT

: >"$ERRORS_FILE"

CANONICAL_GUARD='[ -z "${CLAUDE_PLUGIN_ROOT:-}" ] && [ -n "${IMPLEMENT_TMPDIR:-}" ] && [ -f "$IMPLEMENT_TMPDIR/plugin-root.env" ] && . "$IMPLEMENT_TMPDIR/plugin-root.env"'
ROOT_FALLBACK_PREFIX='[ -z "${CLAUDE_PLUGIN_ROOT:-}" ] && [ -n "${IMPLEMENT_TMPDIR:-}" ] && [ -x "$IMPLEMENT_TMPDIR/larch-run.sh" ] && CLAUDE_PLUGIN_ROOT=$("$IMPLEMENT_TMPDIR/larch-run.sh" --print-plugin-root'
LAUNCHER_PREFIX='"$HOME/.cache/larch/sessions/implement-run-$PPID.sh" '
EXPECTED_OLD=2
EXPECTED_NEW=32
BEST_EFFORT_TIMING='"$HOME/.cache/larch/sessions/implement-run-$PPID.sh" scripts/larch.sh timing telemetry-mark --implement-tmpdir "$IMPLEMENT_TMPDIR" --label "Step 5 — code review" || true'

add_error() {
  printf '%s\n' "$1" >>"$ERRORS_FILE"
}

awk \
  -v errors_file="$ERRORS_FILE" \
  -v stats_file="$FENCE_STATS" \
  -v canonical_guard="$CANONICAL_GUARD" \
  -v root_fallback_prefix="$ROOT_FALLBACK_PREFIX" \
  -v launcher_prefix="$LAUNCHER_PREFIX" \
  -v best_effort_timing="$BEST_EFFORT_TIMING" \
  -v expected_old="$EXPECTED_OLD" \
  -v expected_new="$EXPECTED_NEW" \
  '
function ltrim(s) {
  sub(/^[ \t]+/, "", s)
  return s
}
function rtrim(s) {
  sub(/[ \t]+$/, "", s)
  return s
}
function trim(s) {
  return rtrim(ltrim(s))
}
function add_error(msg) {
  print msg >> errors_file
}
function count_occurrences(text, needle,    count, pos, rest) {
  count = 0
  rest = text
  while ((pos = index(rest, needle)) > 0) {
    count++
    rest = substr(rest, pos + length(needle))
  }
  return count
}
function has_inline_control_logic(cmd) {
  return (cmd ~ /(^|[ \t;])(\|\||&&|;|if[ \t]|while[ \t]|until[ \t]|case[ \t])/)
}
function has_telemetry_script(cmd) {
  return (cmd ~ /\/(token-ledger|timing-ledger|token-report|timing-report)\.sh([^a-zA-Z0-9_]|$)/)
}
function has_guard_in_body(body,    lines, n, i) {
  split(body, lines, "\n")
  n = length(lines)
  for (i = 1; i <= n; i++) {
    if (trim(lines[i]) == canonical_guard) {
      return 1
    }
  }
  return 0
}
function has_root_fallback_in_body(body,    lines, n, i, stripped) {
  split(body, lines, "\n")
  n = length(lines)
  for (i = 1; i <= n; i++) {
    stripped = trim(lines[i])
    if (index(stripped, root_fallback_prefix) == 1) {
      return 1
    }
  }
  return 0
}
function shell_split(line, tokens,    n, i, c, buf, in_dq, in_sq, esc) {
  n = 0
  buf = ""
  in_dq = 0
  in_sq = 0
  esc = 0
  for (i = 1; i <= length(line); i++) {
    c = substr(line, i, 1)
    if (esc) {
      buf = buf c
      esc = 0
      continue
    }
    if (!in_dq && !in_sq && c == "\\") {
      esc = 1
      continue
    }
    if (!in_dq && !in_sq && (c == " " || c == "\t")) {
      if (length(buf) > 0) {
        n++
        tokens[n] = buf
        buf = ""
      }
      continue
    }
    if (!in_dq && c == "'\''") {
      in_sq = 1 - in_sq
      continue
    }
    if (!in_sq && c == "\"") {
      in_dq = 1 - in_dq
      continue
    }
    buf = buf c
  }
  if (length(buf) > 0) {
    n++
    tokens[n] = buf
  }
  return n
}
function old_logical_commands(body, commands,    lines, n, i, stripped, part_n, parts, j, joined, cmd_n) {
  split(body, lines, "\n")
  n = length(lines)
  part_n = 0
  cmd_n = 0
  for (i = 1; i <= n; i++) {
    stripped = trim(lines[i])
    if (stripped == "" || substr(stripped, 1, 1) == "#") {
      continue
    }
    if (stripped == canonical_guard) {
      continue
    }
    if (index(stripped, root_fallback_prefix) == 1) {
      continue
    }
    if (stripped == "export IMPLEMENT_TMPDIR" || stripped == "export CLAUDE_PLUGIN_ROOT") {
      continue
    }
    if (substr(stripped, length(stripped), 1) == "\\") {
      stripped = trim(substr(stripped, 1, length(stripped) - 1))
      part_n++
      parts[part_n] = stripped
      continue
    }
    part_n++
    parts[part_n] = stripped
    joined = parts[1]
    for (j = 2; j <= part_n; j++) {
      joined = joined " " parts[j]
    }
    cmd_n++
    commands[cmd_n] = joined
    part_n = 0
  }
  if (part_n > 0) {
    joined = parts[1]
    for (j = 2; j <= part_n; j++) {
      joined = joined " " parts[j]
    }
    cmd_n++
    commands[cmd_n] = joined
  }
  return cmd_n
}
function join_commands(commands, cmd_n,    i, cmd) {
  if (cmd_n <= 0) {
    return ""
  }
  cmd = commands[1]
  for (i = 2; i <= cmd_n; i++) {
    cmd = cmd " " commands[i]
  }
  return cmd
}
function old_target_kind(cmd) {
  if (index(cmd, "scripts/larch.sh") && index(cmd, "pr closes-issue")) {
    return "structured-invocation"
  }
  if (index(cmd, "larch.sh") && index(cmd, "implement preflight")) {
    return "preflight-helper"
  }
  if (index(cmd, "larch.sh") && index(cmd, "plan-block read")) {
    return "preflight-plan-direct"
  }
  if (index(cmd, "skills/implement/scripts/step-0-bootstrap.sh") && index(cmd, "--mode initial")) {
    return "step-0-initial"
  }
  if (index(cmd, "skills/implement/scripts/step-0-bootstrap.sh") && index(cmd, "--mode resume")) {
    return "dirty-tree-resume"
  }
  return ""
}
function validate_preflight_helper(start, end, body, cmd) {
  if (!has_guard_in_body(body)) {
    add_error("fence " start "-" end ": preflight-helper missing canonical plugin-root.env guard")
  }
  if (has_root_fallback_in_body(body)) {
    add_error("fence " start "-" end ": preflight-helper must not use a plugin-root fallback")
  }
  if (count_occurrences(cmd, "larch.sh") != 1 || index(cmd, "implement preflight") == 0) {
    add_error("fence " start "-" end ": preflight-helper must invoke scripts/larch.sh implement preflight exactly once")
  }
  needles[1] = "\"${CLAUDE_PLUGIN_ROOT}/scripts/larch.sh\" implement preflight"
  needles[2] = "--issue \"$TARGET_ISSUE_NUMBER\""
  needles[3] = "--preflight-tmpdir \"$PREFLIGHT_TMPDIR\""
  needles[4] = "preflight_args=("
  needles[5] = "\"${preflight_args[@]}\""
  for (i = 1; i <= 5; i++) {
    if (index(cmd, needles[i]) == 0) {
      add_error("fence " start "-" end ": preflight-helper missing " needles[i])
    }
  }
  if (index(cmd, "--repo \"$UPSTREAM_REPO\"") == 0 || index(cmd, "[ -n \"${UPSTREAM_REPO:-}\" ]") == 0) {
    add_error("fence " start "-" end ": preflight-helper must add --repo only inside the UPSTREAM_REPO non-empty branch")
  }
  if (index(cmd, "--force") == 0 || index(cmd, "[ \"${force_requested:-false}\" = true ]") == 0) {
    add_error("fence " start "-" end ": preflight-helper must add --force only inside the force_requested=true branch")
  }
  if (index(cmd, "${force_requested:+--force}") > 0) {
    add_error("fence " start "-" end ": preflight-helper must not use parameter-expansion force argv")
  }
}
function validate_old(start, end, body, commands, cmd_n, cmd, kind) {
  if (kind == "preflight-plan-direct") {
    add_error("fence " start "-" end ": direct Preflight plan-block read fence is forbidden")
    return
  }
  if (kind == "preflight-helper") {
    validate_preflight_helper(start, end, body, cmd)
    return
  }
  if (cmd_n != 1) {
    add_error("fence " start "-" end ": old-shape " kind " must have exactly one logical command, found " cmd_n)
  }
  if (!has_guard_in_body(body)) {
    add_error("fence " start "-" end ": old-shape " kind " missing canonical plugin-root.env guard")
  }
  root_fallback = has_root_fallback_in_body(body)
  requires_root_fallback = (kind == "structured-invocation" || kind == "step-0-initial" || kind == "dirty-tree-resume")
  if (requires_root_fallback && !root_fallback) {
    add_error("fence " start "-" end ": old-shape " kind " missing larch-run.sh --print-plugin-root fallback")
  }
  if (!requires_root_fallback && root_fallback) {
    add_error("fence " start "-" end ": old-shape " kind " must remain guard-only without a plugin-root fallback")
  }
  if (kind == "step-0-initial" && index(cmd, "--mode initial") == 0) {
    add_error("fence " start "-" end ": Step 0 initial old-shape target missing --mode initial")
  }
  if (kind == "step-0-initial" && index(cmd, "LARCH_CLAUDE_PID=\"$PPID\" ") == 0) {
    add_error("fence " start "-" end ": Step 0 initial old-shape target missing LARCH_CLAUDE_PID prefix")
  }
  if (kind == "dirty-tree-resume" && index(cmd, "--mode resume") == 0) {
    add_error("fence " start "-" end ": dirty-tree resume old-shape target missing --mode resume")
  }
  if (kind == "dirty-tree-resume" && index(cmd, "LARCH_CLAUDE_PID=\"$PPID\" ") == 0) {
    add_error("fence " start "-" end ": dirty-tree resume old-shape target missing LARCH_CLAUDE_PID prefix")
  }
  if (has_inline_control_logic(cmd)) {
    add_error("fence " start "-" end ": inline shell control logic is not allowed: " cmd)
  }
}
function validate_new(start, end, body,    lines, n, i, stripped, physical_count, raw, tokens, token_n, token0, token1) {
  split(body, lines, "\n")
  n = length(lines)
  physical_count = 0
  raw = ""
  for (i = 1; i <= n; i++) {
    stripped = trim(lines[i])
    if (stripped != "") {
      physical_count++
      raw = lines[i]
    }
  }
  if (physical_count != 1) {
    add_error("fence " start "-" end ": new-shape fence must have exactly one nonblank physical line, found " physical_count)
    return
  }
  if (substr(ltrim(raw), 1, 1) == "#") {
    add_error("fence " start "-" end ": new-shape fence must not contain comments")
    return
  }
  stripped = trim(raw)
  if (substr(stripped, length(stripped), 1) == "\\") {
    add_error("fence " start "-" end ": new-shape fence must not use a line continuation")
    return
  }
  if (index(stripped, launcher_prefix) != 1) {
    add_error("fence " start "-" end ": new-shape command must start with '" launcher_prefix "': " stripped)
    return
  }
  token_n = shell_split(stripped, tokens)
  if (token_n < 2) {
    add_error("fence " start "-" end ": new-shape launcher call missing script target: " stripped)
    return
  }
  token0 = tokens[1]
  token1 = tokens[2]
  if (token0 != "$HOME/.cache/larch/sessions/implement-run-$PPID.sh") {
    add_error("fence " start "-" end ": launcher path must be exactly \"$HOME/.cache/larch/sessions/implement-run-$PPID.sh\": " stripped)
  }
  if (substr(token1, 1, 1) == "/" || index(token1, "..") > 0) {
    add_error("fence " start "-" end ": launcher target must be repo-relative without ..: " token1)
  }
  if (token1 !~ /\.sh$/) {
    add_error("fence " start "-" end ": launcher target must be a .sh path: " token1)
  }
  if (has_inline_control_logic(stripped) && stripped != best_effort_timing) {
    add_error("fence " start "-" end ": inline shell control logic is not allowed: " stripped)
  }
  if (has_telemetry_script(stripped)) {
    add_error("fence " start "-" end ": telemetry-only script invocation is not allowed: " stripped)
  }
}
function validate_fence_body(start, end, body,    commands, cmd_n, cmd, kind) {
  if (index(body, "8-pre-ship") && index(body, "step-8-ship.sh") == 0) {
    add_error("fence " start "-" end ": standalone orchestrator 8-pre-ship fence is forbidden")
  }
  if (index(body, "ship seed-initial-state") > 0) {
    add_error("fence " start "-" end ": Step 8 seed fences must delegate to step-8-seed-initial.sh")
  }
  if (index(body, "session read-key") > 0) {
    add_error("fence " start "-" end ": inline session read-key is not allowed")
  }
  if (index(body, "larch.sh") && index(body, "plan-block read")) {
    add_error("fence " start "-" end ": direct Preflight plan-block read call is forbidden")
  }
  if (index(body, "gh issue view") > 0) {
    add_error("fence " start "-" end ": direct Preflight gh issue view call is forbidden")
  }
  cmd_n = old_logical_commands(body, commands)
  cmd = join_commands(commands, cmd_n)
  kind = old_target_kind(cmd)
  if (kind != "") {
    old_count++
    validate_old(start, end, body, commands, cmd_n, cmd, kind)
  } else {
    new_count++
    validate_new(start, end, body)
  }
}
function extract_slice(text, start_marker, end_marker,    pos, after, end_pos) {
  pos = index(text, start_marker)
  if (pos == 0) {
    return ""
  }
  after = substr(text, pos + length(start_marker))
  end_pos = index(after, end_marker)
  if (end_pos == 0) {
    return ""
  }
  return substr(after, 1, end_pos - 1)
}
function first_index(text, needle,    pos) {
  pos = index(text, needle)
  if (pos == 0) {
    return -1
  }
  return pos - 1
}
function validate_document_slices(skill_text,    reship_slice, reship_pre_fix, reship_continue, ci_fix_slice, ci_fix_pre_fix, ci_fix_loop, assessments_slice, normalization, materialize, assessor, submit, relaunch, forbidden, i) {
  reship_slice = extract_slice(skill_text, "- **`reship`**:", "- **`oos-pipeline`**:")
  if (reship_slice == "") {
    add_error("reship branch must document ship pre-fix-rebase ordering: substring not found")
  } else {
    reship_pre_fix = first_index(reship_slice, "ship pre-fix-rebase --implement-tmpdir \"$IMPLEMENT_TMPDIR\"")
    reship_continue = first_index(reship_slice, "`NEXT_ACTION=continue` proceeds to the Step 8 bgjob `step-8-ship.sh` relaunch")
    if (reship_pre_fix < 0 || reship_continue < 0) {
      add_error("reship branch must document ship pre-fix-rebase ordering: substring not found")
    } else if (reship_pre_fix > reship_continue) {
      add_error("reship branch must require ship pre-fix-rebase before stale-handoff clear")
    }
  }

  ci_fix_slice = extract_slice(skill_text, "- **`ci-fix`**:", "- **`conflict-fix`**")
  if (ci_fix_slice == "") {
    add_error("ci-fix branch must document ship pre-fix-rebase before the subagent loop: substring not found")
  } else {
    ci_fix_pre_fix = first_index(ci_fix_slice, "ship pre-fix-rebase --implement-tmpdir \"$IMPLEMENT_TMPDIR\"")
    ci_fix_loop = first_index(ci_fix_slice, "`larch:ci-fixer`")
    if (ci_fix_pre_fix < 0 || ci_fix_loop < 0) {
      add_error("ci-fix branch must document ship pre-fix-rebase before the subagent loop: substring not found")
    } else if (ci_fix_pre_fix > ci_fix_loop) {
      add_error("ci-fix branch must run ship pre-fix-rebase before the ci-fixer subagent loop")
    }
  }

  assessments_slice = extract_slice(skill_text, "- **`assessments`**, **`invariants-assessment`**, or **`guidelines-assessment`**:", "- **`reship`**:")
  if (assessments_slice == "") {
    add_error("assessment branch must document subagent-first ordering: substring not found")
  } else {
    normalization = first_index(assessments_slice, "scripts/larch.sh ship normalize-assessment-handoff --implement-tmpdir \"$IMPLEMENT_TMPDIR\"")
    materialize = first_index(assessments_slice, "scripts/larch.sh architectural-assessment materialize")
    assessor = first_index(assessments_slice, "`larch:arch-assessor`")
    submit = first_index(assessments_slice, "scripts/larch.sh architectural-assessment submit")
    relaunch = first_index(assessments_slice, "return to the Step 8 ship launcher above exactly once")
    if (normalization < 0 || materialize < 0 || assessor < 0 || submit < 0 || relaunch < 0) {
      add_error("assessment branch must document subagent-first ordering: substring not found")
    } else if (!(normalization < materialize && materialize < assessor && assessor < submit && submit < relaunch)) {
      add_error("assessment branch must normalize, materialize, spawn one arch-assessor subagent, submit, then allow one Step 8 ship relaunch")
    } else {
      if (count_occurrences(assessments_slice, "scripts/larch.sh ship normalize-assessment-handoff --implement-tmpdir \"$IMPLEMENT_TMPDIR\"") != 1) {
        add_error("assessment branch must contain exactly one normalize-assessment-handoff launcher")
      }
      if (index(assessments_slice, "For clean state, use the canonical one-sentence note with no G-* or I-* identifier.") == 0) {
        add_error("assessment branch must remind arch-assessor that clean notes are identifier-free")
      }
      if (index(assessments_slice, "scripts/larch.sh bgjob wait --step implement-step8-assessment") > 0) {
        add_error("assessment branch must not expose a prompt-side assessment wait fence")
      }
      forbidden[1] = "step-architectural-invariants-write-compose.sh"
      forbidden[2] = "step-architectural-guidelines-write-compose.sh"
      forbidden[3] = "architectural-invariant-assessment-draft.md"
      forbidden[4] = "architectural-guideline-assessment-draft.md"
      for (i = 1; i <= 4; i++) {
        if (index(assessments_slice, forbidden[i]) > 0) {
          add_error("assessment branch must not retain legacy prompt-side work: " forbidden[i])
        }
      }
    }
  }
}
function is_fence_open(line) {
  return (ltrim(line) ~ /^```bash/)
}
function is_fence_close(line) {
  return (ltrim(line) == "```")
}
BEGIN {
  in_fence = 0
  fence_start = 0
  prev_end = 0
  old_count = 0
  new_count = 0
  body = ""
  skill_text = ""
}
{
  line = $0
  skill_text = skill_text line "\n"
  t = ltrim(line)
  if (is_fence_open(line)) {
    if (prev_end > 0) {
      blank = 1
      for (i = prev_end + 1; i < NR; i++) {
        if (ltrim(lines[i]) != "") {
          blank = 0
          break
        }
      }
      if (blank) {
        add_error("fences " prev_end " and " NR " are separated only by blank lines")
      }
    }
    in_fence = 1
    fence_start = NR
    body = ""
    next
  }
  if (in_fence && is_fence_close(line)) {
    validate_fence_body(fence_start, NR, body)
    in_fence = 0
    prev_end = NR
    next
  }
  if (in_fence) {
    if (body != "") {
      body = body "\n"
    }
    body = body line
  }
  if (!is_fence_open(line)) {
    lines[NR] = line
  }
}
END {
  if (old_count != expected_old || new_count != expected_new) {
    add_error("expected old=" expected_old " new=" expected_new " bash fences, found old=" old_count " new=" new_count)
  }
  validate_document_slices(skill_text)
  print "old_count=" old_count > stats_file
  print "new_count=" new_count >> stats_file
}
' "$SKILL_PATH"

old_count=
new_count=
# shellcheck disable=SC1090
source "$FENCE_STATS"
: "${old_count:?missing old_count from fence stats}"
: "${new_count:?missing new_count from fence stats}"

resume_text="$(cat "$RESUME_PATH")"
if [[ "$resume_text" != *'LARCH_CLAUDE_PID="$PPID" "${CLAUDE_PLUGIN_ROOT}/skills/implement/scripts/step-0-bootstrap.sh" --mode resume'* ]]; then
  add_error 'bootstrap-recovery resume fence must prefix step-0-bootstrap.sh with LARCH_CLAUDE_PID="$PPID"'
fi

if [[ -s "$ERRORS_FILE" ]]; then
  cat "$ERRORS_FILE" >&2
  exit 1
fi
printf 'PASS: test-implement-fence-shape.sh (old=%s new=%s)\n' "$old_count" "$new_count"
