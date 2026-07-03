#!/usr/bin/env bash
# Structural guard for non-stable content in prompt-construction surfaces.
set -euo pipefail
export LC_ALL=C

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

FAIL=0

report_violation() {
  local file="$1"
  local line_no="$2"
  local reason="$3"
  local text="$4"

  FAIL=$((FAIL + 1))
  printf 'FAIL: %s:%s %s\n' "$file" "$line_no" "$reason" >&2
  printf '  %s\n' "$text" >&2
}

has_nearby_annotation() {
  local file="$1"
  local line_no="$2"
  local start
  local end

  start=$((line_no - 3))
  if (( start < 1 )); then
    start=1
  fi
  end=$((line_no - 1))
  if (( end < start )); then
    return 1
  fi

  sed -n "${start},${end}p" "$REPO_ROOT/$file" | grep -qF '# intentionally non-stable:'
}

line_contains_unstable_pattern() {
  local line="$1"

  [[ "$line" == *"\$(date"* ]] && return 0
  [[ "$line" == *"\$(uuidgen"* ]] && return 0
  [[ "$line" == *"\$(openssl rand"* ]] && return 0
  [[ "$line" == *'$$'* ]] && return 0
  [[ "$line" =~ (^|[^A-Za-z0-9_])\$RANDOM([^A-Za-z0-9_]|$) ]] && return 0

  return 1
}

check_unstable_patterns_in_range() {
  local file="$1"
  local start="$2"
  local end="$3"
  local line_no
  local text

  while IFS=: read -r line_no text; do
    [[ -n "$line_no" ]] || continue
    if line_contains_unstable_pattern "$text" && ! has_nearby_annotation "$file" "$line_no"; then
      report_violation "$file" "$line_no" "non-stable prompt content lacks '# intentionally non-stable:' within 3 preceding lines" "$text"
    fi
  done < <(awk -v start="$start" -v end="$end" 'NR >= start && NR <= end { printf "%d:%s\n", NR, $0 }' "$REPO_ROOT/$file")
}

check_unstable_patterns_in_file() {
  local file="$1"
  local line_no
  local text

  while IFS=: read -r line_no text; do
    [[ -n "$line_no" ]] || continue
    if line_contains_unstable_pattern "$text" && ! has_nearby_annotation "$file" "$line_no"; then
      report_violation "$file" "$line_no" "non-stable prompt content lacks '# intentionally non-stable:' within 3 preceding lines" "$text"
    fi
  done < <(awk '{ printf "%d:%s\n", NR, $0 }' "$REPO_ROOT/$file")
}

check_annotated_literal_lines() {
  local file="$1"
  local literal="$2"
  local reason="$3"
  local line_no
  local text

  while IFS=: read -r line_no text; do
    [[ -n "$line_no" ]] || continue
    if ! has_nearby_annotation "$file" "$line_no"; then
      report_violation "$file" "$line_no" "$reason" "$text"
    fi
  done < <(grep -nF -- "$literal" "$REPO_ROOT/$file" || true)
}

check_render_specialist_prompt_paths() {
  local file="python/larch/rendering/rendering.py"

  [[ -f "$REPO_ROOT/$file" ]] || {
    report_violation "$file" 1 "renderer source file missing" "$file"
    return
  }

  while IFS=: read -r line_no text; do
    [[ "$text" == *'Review all code changes'* ]] || continue
    if ! has_nearby_annotation "$file" "$line_no"; then
      report_violation "$file" "$line_no" "per-session diff path in rendered external prompt lacks annotation" "$text"
    fi
  done < <(grep -nF -- "args.diff_file" "$REPO_ROOT/$file" || true)

  while IFS=: read -r line_no text; do
    [[ "$text" == *'canonical file list'* ]] || continue
    if ! has_nearby_annotation "$file" "$line_no"; then
      report_violation "$file" "$line_no" "per-session scope-file path in rendered external prompt lacks annotation" "$text"
    fi
  done < <(grep -nF -- "args.scope_files" "$REPO_ROOT/$file" || true)
}

prompt_block_bounds() {
  local file="$1"

  awk '
    /^PROMPT=/ && start == 0 { start = NR }
    /^PROMPT_FILE_SIDECAR=/ && start != 0 { print start, NR - 1; exit }
  ' "$REPO_ROOT/$file"
}

check_launcher_prompt_block() {
  local file="$1"
  local tool_name="$2"
  local bounds
  local start
  local end
  local block

  bounds="$(prompt_block_bounds "$file")"
  if [[ -z "$bounds" ]]; then
    report_violation "$file" 1 "missing PROMPT block for $tool_name launcher" ""
    return
  fi

  start="${bounds%% *}"
  end="${bounds##* }"
  block="$(sed -n "${start},${end}p" "$REPO_ROOT/$file")"

  if [[ "$block" == *"\$PLAN_FILE"* || "$block" == *"\$FEATURE_FILE"* || "$block" == *"\$SESSION_TMPDIR"* || "$block" == *"\$MANIFEST_PATH"* || "$block" == *"\$QA_PENDING_PATH"* ]]; then
    if ! has_nearby_annotation "$file" "$start"; then
      report_violation "$file" "$start" "per-session path variables in $tool_name initial prompt lack annotation" "$(sed -n "${start}p" "$REPO_ROOT/$file")"
    fi
  fi

  check_unstable_patterns_in_range "$file" "$start" "$end"
}

check_skill_prompt_literals() {
  local file="skills/implement/SKILL.md"
  local line_no
  local text

  while IFS=: read -r line_no text; do
    if [[ "$text" == *"\$DIFF_FILE"* ]] && ! has_nearby_annotation "$file" "$line_no"; then
      report_violation "$file" "$line_no" "per-session diff path in inline external Codex prompt lacks annotation" "$text"
    fi
  done < <(grep -nF -- '--prompt "Review all code changes' "$REPO_ROOT/$file" || true)

  check_unstable_patterns_in_file "$file"
}

check_agent_prompt_literals() {
  local file

  for file in "$REPO_ROOT"/agents/*.md; do
    [[ -f "$file" ]] || continue
    check_unstable_patterns_in_file "${file#"$REPO_ROOT/"}"
  done
}

check_python_prompt_surfaces() {
  local file

  for file in \
    "python/larch/implement/checks_lint_fix.py" \
    "python/larch/review/coder_runner.py" \
    "python/larch/review/review_dispatch_panel.py" \
    "python/larch/review/round_runner.py"
  do
    if [[ ! -f "$REPO_ROOT/$file" ]]; then
      report_violation "$file" 1 "prompt construction source file missing" "$file"
      continue
    fi
    check_unstable_patterns_in_file "$file"
  done
}

check_render_specialist_prompt_paths
check_skill_prompt_literals
check_agent_prompt_literals
check_python_prompt_surfaces

if (( FAIL > 0 )); then
  printf '\n%s cache-key discipline violation(s) found.\n' "$FAIL" >&2
  printf 'Add a nearby "# intentionally non-stable:" comment only when the dynamic content targets an external tool prompt and cannot be stabilized.\n' >&2
  exit 1
fi

printf 'PASS: cache-key discipline guard\n'
