#!/usr/bin/env bash
# Structural regression guard for the /design two-tier contract.
# shellcheck disable=SC2016,SC2317 # harness intentionally pins literal Markdown/shell snippets; self-test fixture helpers are indirectly reached.
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd -P)"
# shellcheck source=scripts/lib-p3119-fence-absence.sh
source "$REPO_ROOT/scripts/lib-p3119-fence-absence.sh"
SKILL_MD="$REPO_ROOT/skills/design/SKILL.md"
FLAGS_MD="$REPO_ROOT/skills/design/references/flags.md"
CONFIG_MD="$REPO_ROOT/docs/configuration-and-permissions.md"
APPROVAL_MD="$REPO_ROOT/skills/design/references/approval-gates.md"
PLAN_REVIEW_MD="$REPO_ROOT/skills/design/references/plan-review.md"
DISCUSSION_MD="$REPO_ROOT/skills/design/references/discussion-rounds.md"
PLAN_LOOP_SH="$REPO_ROOT/skills/design/scripts/plan-review-loop.sh"
PLAN_REVIEW_LOOP_SH="$PLAN_LOOP_SH"
RUN_STEP3_SH="$REPO_ROOT/skills/design/scripts/run-step3-review.sh"
RUN_STEP3_MD="$REPO_ROOT/skills/design/scripts/run-step3-review.md"
DESIGN_POSTPLAN_EMIT_SH="$REPO_ROOT/skills/design/scripts/design-postplan-emit.sh"
PARSE_DESIGN_ARGV_SH="$REPO_ROOT/skills/design/scripts/parse-design-argv.sh"
DESIGN_ROUTE_SH="$REPO_ROOT/skills/design/scripts/design-route.sh"
DESIGN_INIT_SH="$REPO_ROOT/skills/design/scripts/design-init-runparams.sh"
MAKEFILE="$REPO_ROOT/Makefile"
DIALEXEC_MD="$REPO_ROOT/skills/design/references/dialectic-execution.md"

fail() {
  printf 'FAIL: %s\n' "$1" >&2
  exit 1
}

assert_cancel_route_stdout_kv_only() {
  local tmp plugin body route_out line
  tmp=$(mktemp -d "${TMPDIR:-/tmp}/test-design-route-cancel.XXXXXX")
  plugin="$tmp/plugin"
  mkdir -p "$plugin/scripts" "$plugin/skills/design/scripts"
  body="$tmp/issue-body.txt"
  printf '%s\n' 'cancel route fixture' >"$body"
  cat >"$plugin/scripts/lib-title-eligibility.sh" <<'EOF_FIXTURE'
title_has_lifecycle_reject_prefix() {
  case "$1" in
    "[IMPLEMENTING]"*) printf '%s\n' '[IMPLEMENTING]'; return 0 ;;
    *) return 1 ;;
  esac
}
title_has_archival_report_prefix() { return 1; }
title_starts_with_brainstorm() { return 1; }
EOF_FIXTURE
  cat >"$plugin/skills/design/scripts/render-final-summary.sh" <<'EOF_FIXTURE'
#!/usr/bin/env bash
printf '%s\n' 'SENTINEL_RENDER_STDOUT'
exit 0
EOF_FIXTURE
  chmod +x "$plugin/skills/design/scripts/render-final-summary.sh"

  if ! route_out=$(CLAUDE_PLUGIN_ROOT="$plugin" "$DESIGN_ROUTE_SH" \
    --design-tmpdir "$tmp" \
    --issue 1 \
    --issue-title "[IMPLEMENTING] fixture" \
    --issue-body-file "$body" \
    --has-clarify-label false \
    --claude-pid "$$" \
    --session-id "test-session" 2>"$tmp/stderr.log"); then
    rm -rf "$tmp"
    fail "design-route.sh cancel smoke fixture failed"
  fi
  if printf '%s\n' "$route_out" | grep -Fq 'SENTINEL_RENDER_STDOUT'; then
    rm -rf "$tmp"
    fail "design-route.sh cancel render stdout leaked into KV stream"
  fi
  while IFS= read -r line || [[ -n "$line" ]]; do
    [[ "$line" == *=* ]] || { rm -rf "$tmp"; fail "design-route.sh cancel stdout must contain only KEY=VALUE lines"; }
  done <<<"$route_out"
  rm -rf "$tmp"
}

assert_design_route_pause_integration() {
  local tmp plugin body route_out
  tmp=$(mktemp -d "${TMPDIR:-/tmp}/test-design-route-pause.XXXXXX")
  plugin="$tmp/plugin"
  mkdir -p "$plugin/scripts" "$plugin/skills/design/scripts"
  cp "$REPO_ROOT/scripts/lib-title-eligibility.sh" "$plugin/scripts/lib-title-eligibility.sh"
  cp "$REPO_ROOT/skills/design/scripts/step-name-registry.tsv" "$plugin/skills/design/scripts/step-name-registry.tsv"
  cat >"$plugin/scripts/lib-design-reentry-guard.sh" <<'EOF_FIXTURE'
design_reentry_marker_hit() {
  printf '%s\n' 'MARKER_HIT=false'
  return 0
}
design_reentry_marker_path() {
  printf '%s\n' '/tmp/no-reentry-marker'
}
EOF_FIXTURE
  cat >"$plugin/scripts/design-pause-load.sh" <<'EOF_FIXTURE'
#!/usr/bin/env bash
case "${STUB_PAUSE_LOAD_MODE:-ok}" in
  ok)
    printf '%s\n' \
      'LOAD_OK=true' \
      'STEP=1d' \
      'SESSION_ID=RUNTEST' \
      'RUN_ID=RUNTEST' \
      'TIER=SIMPLE' \
      'BRAINSTORM_DONE=false' \
      'MARKER_CLEARED=true'
    ;;
  stale)
    printf '%s\n' \
      'LOAD_OK=true' \
      'STEP=1d' \
      'SESSION_ID=RUNTEST' \
      'RUN_ID=RUNTEST' \
      'TIER=SIMPLE' \
      'BRAINSTORM_DONE=false' \
      'MARKER_CLEARED=false' \
      'WARN=marker-delete-failed'
    ;;
  fail)
    printf '%s\n' 'LOAD_OK=false' 'ERROR=missing-restored-artifact'
    ;;
  *)
    printf '%s\n' 'LOAD_OK=false' 'ERROR=stub-unknown-mode'
    ;;
esac
EOF_FIXTURE
  chmod +x "$plugin/scripts/design-pause-load.sh"
  cat >"$plugin/scripts/write-design-current-env.sh" <<'EOF_FIXTURE'
#!/usr/bin/env bash
out=""
while [[ $# -gt 0 ]]; do
  printf '%s\n' "$1" >>"${WDCE_ARG_LOG:?}"
  case "$1" in
    --output) out="$2"; shift 2 ;;
    *) shift ;;
  esac
done
[[ -n "$out" ]] && printf 'export SESSION_ID=RUNTEST\n' >"$out"
exit 0
EOF_FIXTURE
  chmod +x "$plugin/scripts/write-design-current-env.sh"
  body="$tmp/issue-body.txt"
  printf '%s\n' 'fixture body' \
    '<!-- larch:design-pause:start -->' \
    'ISSUE_NUMBER=1' \
    'RUN_ID=RUNTEST' \
    'STEP=1d' \
    '<!-- larch:design-pause:end -->' >"$body"
  mkdir -p "$tmp/design-tmpdir"
  printf '{"manual_gate_b":true}\n' >"$tmp/design-tmpdir/run-params.json"
  export WDCE_ARG_LOG="$tmp/wdce-args.log"

  if ! route_out=$(STUB_PAUSE_LOAD_MODE=ok CLAUDE_PLUGIN_ROOT="$plugin" "$DESIGN_ROUTE_SH" \
    --design-tmpdir "$tmp/design-tmpdir" \
    --issue 1 \
    --issue-title "[DESIGNING] paused fixture" \
    --issue-body-file "$body" \
    --has-clarify-label false \
    --claude-pid "$$" \
    --session-id "test-session"); then
    rm -rf "$tmp"
    fail "design-route.sh pause-resume lifecycle fixture failed"
  fi
  printf '%s\n' "$route_out" | grep -Fq 'ROUTE=resume@1d' \
    || { rm -rf "$tmp"; fail "design-route.sh must resume on lifecycle title when pause load succeeds: $route_out"; }
  printf '%s\n' "$route_out" | grep -Fq 'ROUTE=cancel-title-filter' \
    && { rm -rf "$tmp"; fail "design-route.sh must not title-filter when pause resume succeeds: $route_out"; }
  grep -Fq -- '--manual-requested' "$WDCE_ARG_LOG" \
    && { rm -rf "$tmp"; fail "design-route.sh resume must ignore stale manual_gate_b and omit --manual-requested"; }
  grep -Fq 'MANUAL_REQUESTED' "$tmp/design-tmpdir/source-env.sh" \
    && { rm -rf "$tmp"; fail "design-route.sh resume source-env must omit MANUAL_REQUESTED"; }

  mkdir -p "$tmp/design-tmpdir-stale"
  if ! route_out=$(STUB_PAUSE_LOAD_MODE=stale CLAUDE_PLUGIN_ROOT="$plugin" "$DESIGN_ROUTE_SH" \
    --design-tmpdir "$tmp/design-tmpdir-stale" \
    --issue 1 \
    --issue-title "[DESIGNING] stale marker" \
    --issue-body-file "$body" \
    --has-clarify-label false \
    --claude-pid "$$" \
    --session-id "test-session"); then
    rm -rf "$tmp"
    fail "design-route.sh stale-marker fixture failed"
  fi
  printf '%s\n' "$route_out" | grep -Fq 'ROUTE=cancel-pause-load' \
    || { rm -rf "$tmp"; fail "design-route.sh must cancel when MARKER_CLEARED=false: $route_out"; }
  printf '%s\n' "$route_out" | grep -Fq 'ROUTE=resume@' \
    && { rm -rf "$tmp"; fail "design-route.sh must not resume when MARKER_CLEARED=false: $route_out"; }

  mkdir -p "$tmp/design-tmpdir-fail"
  if ! route_out=$(STUB_PAUSE_LOAD_MODE=fail CLAUDE_PLUGIN_ROOT="$plugin" "$DESIGN_ROUTE_SH" \
    --design-tmpdir "$tmp/design-tmpdir-fail" \
    --issue 1 \
    --issue-title "[DESIGNING] load fail" \
    --issue-body-file "$body" \
    --has-clarify-label false \
    --claude-pid "$$" \
    --session-id "test-session"); then
    rm -rf "$tmp"
    fail "design-route.sh pause-load-fail fixture failed"
  fi
  printf '%s\n' "$route_out" | grep -Fq 'ROUTE=cancel-pause-load' \
    || { rm -rf "$tmp"; fail "design-route.sh must cancel when pause load fails: $route_out"; }
  printf '%s\n' "$route_out" | grep -Fq 'ROUTE=proceed' \
    && { rm -rf "$tmp"; fail "design-route.sh must not proceed when pause marker load fails: $route_out"; }
  printf '%s\n' "$route_out" | grep -Fq 'ROUTE=cancel-title-filter' \
    && { rm -rf "$tmp"; fail "design-route.sh must not title-filter when pause load fails: $route_out"; }

  rm -rf "$tmp"
}

contains() {
  local file="$1" needle="$2" label="$3"
  grep -Fq -- "$needle" "$file" || fail "$label"
}

absent() {
  local file="$1" needle="$2" label="$3"
  if grep -Fq -- "$needle" "$file"; then
    fail "$label"
  fi
}

extract_first_bash_fence_after() {
  local file="$1" marker="$2"
  awk -v marker="$marker" '
    index($0, marker) { start=1; next }
    start && /^```bash$/ { in_fence=1; next }
    start && in_fence && /^```$/ { exit }
    start && in_fence { print }
  ' "$file"
}

assert_degraded_tools_gate_fence() {
  local tmp
  tmp=$(mktemp "${TMPDIR:-/tmp}/design-degraded-gate.XXXXXX")
  awk '
    /\*\*Degraded-tools gate \(#3207\)\.\*\*/ { start = 1; next }
    start && /^```bash$/ { in_fence = 1; next }
    start && in_fence && /^```$/ { exit }
    start && in_fence { print }
  ' "$SKILL_MD" >"$tmp"
  [[ -s "$tmp" ]] || fail "SKILL Degraded-tools gate region missing bash fence"
  grep -Fq 'export DESIGN_TMPDIR="${DESIGN_TMPDIR:?DESIGN_TMPDIR required}"' "$tmp" \
    || { rm -f "$tmp"; fail 'SKILL Degraded-tools gate fence must export DESIGN_TMPDIR prelude'; }
  grep -Fq '. "$DESIGN_TMPDIR/source-env.sh"' "$tmp" \
    || { rm -f "$tmp"; fail 'SKILL Degraded-tools gate fence must source durable design env'; }
  if grep -Fq 'from the session-setup parse above' "$SKILL_MD"; then
    rm -f "$tmp"
    fail 'SKILL Degraded-tools gate prose must not refer to session-setup parse above'
  fi
  for needle in \
    '"$CLAUDE_PLUGIN_ROOT/scripts/degraded-tools-gate.sh" --skill design' \
    '--codex-present "${CODEX_PRESENT:-false}"' \
    '--cursor-present "${CURSOR_PRESENT:-false}"' \
    '--codex-binary-found "${CODEX_BINARY_FOUND:-false}"' \
    '--cursor-binary-found "${CURSOR_BINARY_FOUND:-false}"'
  do
    grep -Fq -- "$needle" "$tmp" || { rm -f "$tmp"; fail "SKILL Degraded-tools gate fence missing: $needle"; }
  done
  rm -f "$tmp"
}

assert_step2a_entry_simple_guard() {
  local tmp guard_line closing_fi_line first_artifact_line last_artifact_line first_completion_line completion_line artifact_line pause_line last_simple_completion_line
  tmp=$(mktemp "${TMPDIR:-/tmp}/step2a-entry.XXXXXX")
  extract_first_bash_fence_after "$SKILL_MD" '<!-- step:2a —' >"$tmp"
  grep -Fq '${CLAUDE_PLUGIN_ROOT}/scripts/read-design-classification.sh' "$tmp" \
    || fail 'Step 2a entry fence missing qualified read-design-classification.sh'
  grep -Fq 'if [ "$_design_classification" = SIMPLE ]; then' "$tmp" \
    || fail 'Step 2a entry fence missing SIMPLE guard before sentinel writes'
  grep -Fq 'set -e' "$tmp" \
    || fail 'Step 2a SIMPLE entry branch must use fail-fast set -e'
  grep -Fq "NO_SKETCHES_CLASSIFIED_SIMPLE" "$tmp" \
    || fail 'Step 2a entry fence missing approach sentinel write'
  grep -Fq "NO_CONTESTED_DECISIONS" "$tmp" \
    || fail 'Step 2a entry fence missing contested sentinel write'
  grep -Fq ': > "$DESIGN_TMPDIR/dialectic-resolutions.md"' "$tmp" \
    || fail 'Step 2a entry fence missing dialectic-resolutions empty write'
  grep -Fq ': > "$DESIGN_TMPDIR/.completed/step-2a"' "$tmp" \
    || fail 'Step 2a entry fence missing step-2a completion marker'
  grep -Fq ': > "$DESIGN_TMPDIR/.completed/step-2a.5"' "$tmp" \
    || fail 'Step 2a entry fence missing step-2a.5 completion marker'
  pause_line=$(grep -nF 'design-pause-save.sh' "$tmp" | head -1 | cut -d: -f1)
  last_simple_completion_line=$(grep -nF ': > "$DESIGN_TMPDIR/.completed/step-2a.5"' "$tmp" | head -1 | cut -d: -f1)
  [[ -n "$pause_line" && -n "$last_simple_completion_line" ]] \
    || fail 'Step 2a entry fence missing pause-check or SIMPLE completion markers'
  (( last_simple_completion_line < pause_line )) \
    || fail 'Step 2a entry fence pause-check must come after SIMPLE completion markers'
  guard_line=$(grep -nF 'if [ "$_design_classification" = SIMPLE ]; then' "$tmp" | head -1 | cut -d: -f1)
  closing_fi_line=$(awk -v start="$guard_line" 'NR > start && $0 == "fi" { line=NR } END { if (line) print line }' "$tmp")
  first_artifact_line=$(grep -m 1 -nF "NO_SKETCHES_CLASSIFIED_SIMPLE" "$tmp" | cut -d: -f1)
  last_artifact_line=$(grep -nF ': > "$DESIGN_TMPDIR/dialectic-resolutions.md"' "$tmp" | head -1 | cut -d: -f1)
  first_completion_line=$(grep -nF ': > "$DESIGN_TMPDIR/.completed/step-2a"' "$tmp" | head -1 | cut -d: -f1)
  [[ -n "$closing_fi_line" ]] || fail 'Step 2a entry fence missing closing fi for SIMPLE guard'
  (( guard_line < first_artifact_line )) \
    || fail 'Step 2a entry fence writes SIMPLE artifacts before the SIMPLE guard'
  (( last_artifact_line < first_completion_line )) \
    || fail 'Step 2a entry fence must write completion markers after all SIMPLE artifacts'
  while IFS=: read -r completion_line _; do
    (( guard_line < completion_line && completion_line < closing_fi_line )) \
      || fail 'Step 2a entry fence completion markers must stay inside the SIMPLE guard'
  done < <(grep -nF ': > "$DESIGN_TMPDIR/.completed/step-2a' "$tmp")
  for _artifact in \
    "NO_SKETCHES_CLASSIFIED_SIMPLE" \
    "NO_CONTESTED_DECISIONS" \
    ': > "$DESIGN_TMPDIR/dialectic-resolutions.md"'
  do
    artifact_line=$(grep -m 1 -nF "$_artifact" "$tmp" | cut -d: -f1)
    [[ -n "$artifact_line" ]] || fail "Step 2a entry fence missing SIMPLE artifact write: $_artifact"
    (( guard_line < artifact_line && artifact_line < closing_fi_line )) \
      || fail 'Step 2a entry fence SIMPLE artifact writes must stay inside the SIMPLE guard'
  done
  rm -f "$tmp"
}

assert_simple_branch_has_no_sentinel_fence() {
  if awk '
    /^### SIMPLE branch/ { in_section=1; next }
    in_section && /^### Regular mode/ { in_section=0 }
    in_section && /^```bash$/ { in_fence=1; next }
    in_section && in_fence && /^```$/ { in_fence=0; next }
    in_section && in_fence && /NO_SKETCHES_CLASSIFIED_SIMPLE/ { found=1 }
    END { exit found ? 0 : 1 }
  ' "$SKILL_MD"; then
    fail 'SIMPLE branch subsection must not contain a standalone NO_SKETCHES_CLASSIFIED_SIMPLE bash fence'
  fi
}

assert_step3b_finalize_boundary() {
  local step3b_line step4_line step3b_between step4b_line step4_between action_line rc_line exit_line marker_line
  step3b_line=$(grep -nF '<!-- step:3b' "$SKILL_MD" | head -1 | cut -d: -f1 || true)
  step4_line=$(grep -nF '<!-- step:4 —' "$SKILL_MD" | head -1 | cut -d: -f1 || true)
  step4b_line=$(grep -nF '<!-- step:4b' "$SKILL_MD" | head -1 | cut -d: -f1 || true)
  [[ -n "$step3b_line" && -n "$step4_line" && -n "$step4b_line" ]] || fail 'missing Step 3b/4/4b marker for FINALIZE boundary assertions'
  step3b_between=$(sed -n "$((step3b_line + 1)),$((step4_line - 1))p" "$SKILL_MD")
  step4_between=$(sed -n "$((step4_line + 1)),$((step4b_line - 1))p" "$SKILL_MD")
  grep -Fq 'ACTION=FINALIZE' <<<"$step3b_between" \
    || fail 'Step 3b completion boundary must emit ACTION=FINALIZE before Step 4'
  grep -Fq 'design-driver.sh' <<<"$step3b_between" \
    || fail 'Step 3b completion boundary must invoke design-driver.sh'
  grep -Fq 'exit "$_finalize_rc"' <<<"$step3b_between" \
    || fail 'Step 3b FINALIZE failure branch must exit non-zero'
  grep -Fq '**⚠ FINALIZE failed; repair the missing artifact before Step 5.**' <<<"$step3b_between" \
    || fail 'Step 3b FINALIZE failure branch must print repair warning'
  grep -Fq ': > "$DESIGN_TMPDIR/.completed/step-3b"' <<<"$step3b_between" \
    || fail 'Step 3b completion boundary must write step-3b after FINALIZE'
  action_line=$(grep -nF 'ACTION=FINALIZE' <<<"$step3b_between" | head -1 | cut -d: -f1)
  rc_line=$(grep -nF '_finalize_rc=$?' <<<"$step3b_between" | head -1 | cut -d: -f1)
  exit_line=$(grep -nF 'exit "$_finalize_rc"' <<<"$step3b_between" | head -1 | cut -d: -f1)
  marker_line=$(grep -nF ': > "$DESIGN_TMPDIR/.completed/step-3b"' <<<"$step3b_between" | head -1 | cut -d: -f1)
  (( action_line < rc_line && rc_line < exit_line && exit_line < marker_line )) \
    || fail 'Step 3b completion boundary must write step-3b only after FINALIZE rc capture and failure exit branch'
  if grep -Fq '1. Emit `ACTION=FINALIZE`' <<<"$step4_between"; then
    fail 'Step 4 must not retain the standalone FINALIZE item'
  fi
  grep -Fq '[ ! -f "$DESIGN_TMPDIR/.completed/finalize" ]' <<<"$step4_between" \
    || fail 'Step 4 compatibility FINALIZE must be gated on missing .completed/finalize'
  grep -Fq 'ACTION=FINALIZE' <<<"$step4_between" \
    || fail 'Step 4 compatibility guard missing ACTION=FINALIZE'
  grep -Fq 'set +e' <<<"$step4_between" \
    || fail 'Step 4 compatibility FINALIZE must capture non-zero under set +e'
  grep -Fq '_finalize_rc=$?' <<<"$step4_between" \
    || fail 'Step 4 compatibility FINALIZE missing _finalize_rc capture'
  grep -Fq 'exit "$_finalize_rc"' <<<"$step4_between" \
    || fail 'Step 4 compatibility FINALIZE failure branch must exit non-zero'
  grep -Fq '**⚠ FINALIZE failed; repair the missing artifact before Step 5.**' <<<"$step4_between" \
    || fail 'Step 4 compatibility FINALIZE failure branch must print repair warning'
}

assert_no_direct_step3b_step4_routes() {
  local label="$1" subject_file="$2" start_marker="${3:-}" end_marker="${4:-}" tmp scoped=false bad
  tmp="$subject_file"
  if [[ -n "$start_marker" || -n "$end_marker" ]]; then
    [[ -n "$start_marker" && -n "$end_marker" ]] || fail "$label route guard markers must be paired"
    local start_line end_line
    start_line=$(grep -nF -- "$start_marker" "$subject_file" | head -1 | cut -d: -f1 || true)
    end_line=$(grep -nF -- "$end_marker" "$subject_file" | awk -F: -v s="${start_line:-0}" '$1 > s {print $1; exit}' || true)
    [[ -n "$start_line" && -n "$end_line" ]] || fail "$label route guard missing marker"
    tmp=$(mktemp "${TMPDIR:-/tmp}/step3b-route.XXXXXX")
    sed -n "${start_line},$((end_line - 1))p" "$subject_file" >"$tmp"
    scoped=true
  fi
  bad=$(awk '
    {
      line = $0
      lower = tolower($0)
    }
    lower ~ /step 3b completion boundary/ { next }
    lower ~ /step 3b[[:space:]]*(->|→|⇒|, then|,|\/)[[:space:]]*step 4/ { print line; next }
    lower ~ /step 3b\/4/ { print line; next }
    lower ~ /step 3b[[:space:]]+\/[[:space:]]+step 4/ { print line; next }
    lower ~ /(continue|proceed|auto-continue|route|jump|enter|go)/ && lower ~ /step 3b/ && lower ~ /step 4/ { print line; next }
  ' "$tmp")
  [[ -z "$bad" ]] || fail "$label has direct Step 3b-to-Step 4 route without completion boundary: $bad"
  [[ "$scoped" == false ]] || rm -f "$tmp"
}

assert_thin_fence() {
  local file="$1" label="$2" start_marker="${3:-}" end_marker="${4:-}"
  local subject="$file" scoped=false
  if [[ -n "$start_marker" || -n "$end_marker" ]]; then
    [[ -n "$start_marker" && -n "$end_marker" ]] || fail "$label region markers must be supplied together"
    local start_line end_line
    start_line=$(grep -nF -- "$start_marker" "$file" | head -1 | cut -d: -f1 || true)
    end_line=$(grep -nF -- "$end_marker" "$file" | awk -F: -v s="${start_line:-0}" '$1 > s {print $1; exit}' || true)
    [[ -n "$start_line" ]] || fail "$label missing start marker: $start_marker"
    [[ -n "$end_line" ]] || fail "$label missing end marker after $start_marker: $end_marker"
    (( end_line > start_line )) || fail "$label end marker must follow start marker"
    subject=$(mktemp "${TMPDIR:-/tmp}/test-design-structure-region.XXXXXX")
    sed -n "${start_line},$((end_line - 1))p" "$file" >"$subject"
    scoped=true
  fi

  grep -Fq 'set +e' "$subject" || fail "$label missing set +e child capture"
  grep -Fq '$?' "$subject" || fail "$label missing explicit rc capture"
  if grep -Fq '2>&1 | tail -n 1' "$subject"; then
    fail "$label must not merge stdout/stderr for scalar parsing"
  fi
  if [[ "$scoped" == true ]]; then
    if grep -Fq 'is a symlink; refusing to source' "$subject"; then
      fail "$label must not carry fat-fence symlink-source handling"
    fi
    if grep -Fq 'phase_driver_read_result_env' "$subject"; then
      fail "$label must not call phase_driver_read_result_env"
    fi
    local entry_guard_line
    entry_guard_line=$(awk '/read-design-classification\.sh/ { exit } /\.pause-requested/ && /design-pause-save\.sh/ { print; exit }' "$subject")
    [[ -n "$entry_guard_line" ]] || fail "$label missing entry pause-save guard before classification"
    # shellcheck disable=SC2016 # literal repo passthrough syntax is pinned.
    [[ "$entry_guard_line" == *'${REPO:+--repo "$REPO"}'* ]] || fail "$label entry pause-save guard must thread REPO"
  fi
  [[ "$subject" == "$file" ]] || rm -f "$subject"
}

assert_postplan_thin_fence() {
  local file="$1" label="$2" start_marker="${3:-}" end_marker="${4:-}"
  local subject="$file" scoped=false
  if [[ -n "$start_marker" || -n "$end_marker" ]]; then
    [[ -n "$start_marker" && -n "$end_marker" ]] || fail "$label region markers must be supplied together"
    local start_line end_line
    start_line=$(grep -nF -- "$start_marker" "$file" | head -1 | cut -d: -f1 || true)
    end_line=$(grep -nF -- "$end_marker" "$file" | awk -F: -v s="${start_line:-0}" '$1 > s {print $1; exit}' || true)
    [[ -n "$start_line" ]] || fail "$label missing start marker: $start_marker"
    [[ -n "$end_line" ]] || fail "$label missing end marker after $start_marker: $end_marker"
    (( end_line > start_line )) || fail "$label end marker must follow start marker"
    subject=$(mktemp "${TMPDIR:-/tmp}/test-design-structure-postplan-region.XXXXXX")
    sed -n "${start_line},$((end_line - 1))p" "$file" >"$subject"
    scoped=true
  fi
  grep -Fq -- '--with-plan-size' "$subject" || fail "$label missing --with-plan-size"
  grep -Fq -- 'env LARCH_QUIET_DISABLE=1' "$subject" || fail "$label missing LARCH_QUIET_DISABLE display capture"
  # shellcheck disable=SC2016 # Markdown/bash fence literals must stay unexpanded.
  grep -Fq '${_postplan_out:-}' "$subject" || fail "$label missing postplan out display variable"
  grep -Fq 'printf' "$subject" || fail "$label missing postplan display printf"
  # shellcheck disable=SC2016 # Markdown/bash fence literals must stay unexpanded.
  grep -Fq 'case "${_postplan_rc:-1}" in' "$subject" || fail "$label missing postplan rc case"
  for arm in 0 10 11 12 13 14 2 1; do
    grep -Fq "  ${arm})" "$subject" || fail "$label missing case arm ${arm}"
  done
  grep -Fq 'DRIFT_' "$subject" || fail "$label missing drift trigger parse"
  grep -Fq 'BASELINE_' "$subject" || fail "$label missing drift baseline parse"
  grep -Fq '  *)' "$subject" || fail "$label missing default-abort *) arm"
  # shellcheck disable=SC2016 # Markdown/bash fence literals must stay unexpanded.
  if grep -Fq '<<<"${_postplan_out:-}"' "$subject"; then
    fail "$label must not merge stdout KVs via <<< heredoc"
  fi
  if awk '/design-postplan-emit\.sh/ && /--repo/ && !/\$\{REPO:\+--repo/ { bad=1 } END { exit bad ? 0 : 1 }' "$subject"; then
    fail "$label must not pass --repo to design-postplan-emit.sh"
  fi
  [[ "$scoped" == true ]] || return 0
  local pause_line
  pause_line=$(awk '/\.pause-requested/ && /design-pause-save\.sh/ && /\$\{REPO:\+--repo/ {print; exit}' "$subject")
  [[ -n "$pause_line" ]] || fail "$label pause-save must thread REPO"
  rm -f "$subject"
}

assert_postplan_reference_thin_fence() {
  local file="$1" label="$2" start_marker="$3" end_marker="$4"
  local start_line end_line subject
  start_line=$(grep -nF -- "$start_marker" "$file" | head -1 | cut -d: -f1 || true)
  end_line=$(grep -nF -- "$end_marker" "$file" | awk -F: -v s="${start_line:-0}" '$1 > s {print $1; exit}' || true)
  [[ -n "$start_line" ]] || fail "$label missing start marker: $start_marker"
  [[ -n "$end_line" ]] || fail "$label missing end marker after $start_marker: $end_marker"
  subject=$(mktemp "${TMPDIR:-/tmp}/test-design-structure-postplan-reference.XXXXXX")
  sed -n "${start_line},$((end_line - 1))p" "$file" >"$subject"
  grep -Fq 'env LARCH_QUIET_DISABLE=1' "$subject" || fail "$label missing LARCH_QUIET_DISABLE display capture"
  grep -Fq -- '--with-plan-size' "$subject" || fail "$label missing --with-plan-size"
  # shellcheck disable=SC2016 # Markdown/bash fence literals must stay unexpanded.
  grep -Fq '${_postplan_out:-}' "$subject" || fail "$label missing postplan out display variable"
  # shellcheck disable=SC2016 # Markdown/bash fence literals must stay unexpanded.
  grep -Fq 'case "${_postplan_rc:-1}" in' "$subject" || fail "$label missing postplan rc case"
  for arm in 0 10 11 12 13 14 2 1; do
    grep -Fq "\`${arm}\`" "$subject" || fail "$label missing delegated case arm ${arm}"
  done
  grep -Fq 'DRIFT_' "$subject" || fail "$label missing drift trigger parse"
  grep -Fq 'BASELINE_' "$subject" || fail "$label missing drift baseline parse"
  # shellcheck disable=SC2016 # Markdown literal contains a default case marker.
  grep -Fq 'default-abort `*` arm' "$subject" || fail "$label missing default-abort *) arm"
  # shellcheck disable=SC2016 # Markdown/bash fence literal must stay unexpanded.
  grep -Fq '${REPO:+--repo "$REPO"}' "$subject" || fail "$label pause-save must thread REPO"
  # shellcheck disable=SC2016 # Markdown/bash fence literal must stay unexpanded.
  if grep -Fq '<<<"${_postplan_out:-}"' "$subject"; then
    fail "$label must not merge stdout KVs via heredoc"
  fi
  if awk '/design-postplan-emit\.sh/ && /--repo/ && !/\$\{REPO:\+--repo/ { bad=1 } END { exit bad ? 0 : 1 }' "$subject"; then
    fail "$label must not pass --repo to design-postplan-emit.sh"
  fi
  rm -f "$subject"
}

run_postplan_thin_fence_self_tests() {
  local fixture
  fixture=$(mktemp "${TMPDIR:-/tmp}/test-design-structure-postplan-self.XXXXXX")
  awk '/^<!-- step:2b /,/^### Step 2b\.5/' "$SKILL_MD" | grep -v '^  14)$' >"$fixture"
  if (assert_postplan_thin_fence "$fixture" 'postplan thin-fence negative fixture missing rc14') >/dev/null 2>&1; then
    rm -f "$fixture"
    fail "postplan thin-fence self-test must fail when a case arm is missing"
  fi
  rm -f "$fixture"
}

assert_gate_b_bypass_branch_sentinels() {
  local file="$1" label="${2:-Gate-B-bypass branch matrix}" start_marker="${3:-**Post-loop branch matrix**}" end_marker="${4:-<!-- step:3.5}"
  local start_line end_line subject
  start_line=$(grep -nF -- "$start_marker" "$file" | head -1 | cut -d: -f1 || true)
  end_line=$(grep -nF -- "$end_marker" "$file" | awk -F: -v s="${start_line:-0}" '$1 > s {print $1; exit}' || true)
  [[ -n "$start_line" ]] || fail "$label missing start marker: $start_marker"
  [[ -n "$end_line" ]] || fail "$label missing end marker after $start_marker: $end_marker"
  subject=$(mktemp "${TMPDIR:-/tmp}/test-design-structure-gate-b-bypass.XXXXXX")
  sed -n "${start_line},$((end_line - 1))p" "$file" >"$subject"
  grep -Fq 'design-step3-state.sh' "$subject" || fail "$label missing design-step3-state helper"
  grep -Fq -- '--gate-b-bypass' "$subject" || fail "$label missing --gate-b-bypass helper action"
  grep -Fq 'refused-partial-gate-b-bypass' "$subject" || fail "$label missing refused partial state handling"
  grep -Fq 'STEP3_STATE=' "$subject" || fail "$label missing STEP3_STATE parse"
  if grep -Fq ': > "$DESIGN_TMPDIR/.completed/step-3.5"' "$subject"; then
    fail "$label must not use inline Gate-B-bypass sentinel writes"
  fi
  rm -f "$subject"
}

assert_step3b_entry_guard_threads_repo() {
  local file="$1" result line
  result=$(awk '
    /<!-- step:3b/ { in_region=1; next }
    in_region && /<!-- step:4 / { end_marker_seen=1; in_region=0; exit }
    in_region && line == "" && /\.pause-requested/ && /design-pause-save\.sh/ { line=$0 }
    END {
      if (!end_marker_seen) {
        print "MISSING_END"
      } else if (line != "") {
        print line
      }
    }
  ' "$file")
  [[ "$result" != MISSING_END ]] || fail "SKILL Step 3b missing end marker <!-- step:4"
  line="$result"
  [[ -n "$line" ]] || fail "SKILL Step 3b missing entry pause-save guard"
  # shellcheck disable=SC2016 # literal repo passthrough syntax is pinned.
  [[ "$line" == *'${REPO:+--repo "$REPO"}'* ]] || fail "SKILL Step 3b entry pause-save guard must thread REPO"
}

run_thin_fence_self_tests() {
  local tmp base missing_repo
  tmp=$(mktemp -d "${TMPDIR:-/tmp}/test-design-structure-self.XXXXXX")
  trap 'rm -rf "$tmp"' RETURN
  base="$tmp/base.md"
  cat >"$base" <<'EOF_SELF'
<!-- step:X.test — Synthetic test step -->
[ -f "$DESIGN_TMPDIR/.pause-requested" ] && exec "$CLAUDE_PLUGIN_ROOT/scripts/design-pause-save.sh" --design-tmpdir "$DESIGN_TMPDIR" --issue "$ISSUE_NUMBER" ${REPO:+--repo "$REPO"}
set +e
_out=$(driver)
_rc=$?
set -e
<!-- step:3b — Architecture Diagram -->
EOF_SELF
  assert_thin_fence "$base" 'self-test valid thin fence' '<!-- step:X.test' '<!-- step:3b'

  missing_repo="$tmp/missing-repo.md"
  cat >"$missing_repo" <<'EOF_SELF'
<!-- step:X.test — Synthetic test step -->
[ -f "$DESIGN_TMPDIR/.pause-requested" ] && exec "$CLAUDE_PLUGIN_ROOT/scripts/design-pause-save.sh" --design-tmpdir "$DESIGN_TMPDIR" --issue "$ISSUE_NUMBER"
set +e
_out=$(driver)
_rc=$?
exec "$CLAUDE_PLUGIN_ROOT/scripts/design-pause-save.sh" --design-tmpdir "$DESIGN_TMPDIR" --issue "$ISSUE_NUMBER" ${REPO:+--repo "$REPO"}
set -e
<!-- step:3b — Architecture Diagram -->
EOF_SELF
  if (assert_thin_fence "$missing_repo" 'self-test missing entry repo' '<!-- step:X.test' '<!-- step:3b') 2>/dev/null; then
    fail 'self-test: first entry pause-save guard without REPO should fail'
  fi
}


run_gate_b_bypass_branch_sentinel_self_tests() {
  local fixture
  fixture=$(mktemp "${TMPDIR:-/tmp}/test-design-structure-gate-b-bypass-self.XXXXXX")
  cat >"$fixture" <<'EOF_SELF'
**Post-loop branch matrix**
- `LOOP_STATUS=tally-error` — run `"$CLAUDE_PLUGIN_ROOT/skills/design/scripts/design-step3-state.sh" --design-tmpdir "$DESIGN_TMPDIR" --gate-b-bypass`, parse `STEP3_STATE=`, and abort on `STEP3_STATE=refused-partial-gate-b-bypass`.
### Step 3.5
EOF_SELF
  assert_gate_b_bypass_branch_sentinels "$fixture" 'gate-b-bypass self-test valid' '**Post-loop branch matrix**' '### Step 3.5'
  sed 's/refused-partial-gate-b-bypass/missing-state/' "$fixture" >"$fixture.bad"
  if (assert_gate_b_bypass_branch_sentinels "$fixture.bad" 'gate-b-bypass self-test invalid' '**Post-loop branch matrix**' '### Step 3.5') >/dev/null 2>&1; then
    rm -f "$fixture" "$fixture.bad"
    fail 'gate-b-bypass self-test must fail when refused state handling is missing'
  fi
  rm -f "$fixture" "$fixture.bad"
}

run_thin_fence_self_tests
run_gate_b_bypass_branch_sentinel_self_tests

contains "$SKILL_MD" '[--hard]' 'SKILL argument hint must expose --hard as the sole tier flag'
absent "$SKILL_MD" '[--simple|' 'SKILL argument hint must not restore [--simple|--hard] tier alternation'
contains "$SKILL_MD" 'The default tier is SIMPLE' 'SKILL must document default SIMPLE tier resolution'
contains "$SKILL_MD" '**Tier resolution**' 'SKILL must document non-interactive Tier resolution sub-step'
grep -Fq 'default tier: SIMPLE (no --hard)' "$REPO_ROOT/skills/design/scripts/design-init-runparams.sh" \
  || fail 'design-init-runparams.sh must pin default-tier write-run-params reason string'
absent "$SKILL_MD" '**Tier gate**' 'SKILL must not retain retired Step 0 Tier gate sub-step'
absent "$SKILL_MD" 'cancelled-tier-gate' 'SKILL must not retain cancelled-tier-gate outcome'
# shellcheck disable=SC2016 # Markdown literal contains backticks intentionally.
absent "$SKILL_MD" 'the tier `AskUserQuestion`' 'SKILL must not retain interactive tier AskUserQuestion gate'
absent "$SKILL_MD" 'argv tier: --simple' 'SKILL must not retain legacy argv-tier --simple reason string'
# shellcheck disable=SC2016 # Markdown literal contains backticks intentionally.
contains "$SKILL_MD" 'unrecognized or disallowed leading public `--` flag is a hard error before Step 0' 'SKILL must document disallowed-public-flag rejection before Step 0'
contains "$SKILL_MD" 'before invoking the Step 0a Bash block' 'SKILL must validate public argv before session-setup'
absent "$APPROVAL_MD" 'Step 0 tier-gate' 'approval-gates.md must not retain retired Step 0 tier-gate contrast'
contains "$SKILL_MD" 'design_classification == SIMPLE' 'SKILL missing SIMPLE branch prose'
assert_degraded_tools_gate_fence
# shellcheck disable=SC2016 # Markdown literal contains backticks intentionally.
contains "$SKILL_MD" 'unless `design_classification == SIMPLE`, where the user-confirmed no-sketch carve-out applies' 'SKILL missing SIMPLE Design Mindset carve-out'
contains "$SKILL_MD" 'NO_SKETCHES_CLASSIFIED_SIMPLE' 'SKILL missing SIMPLE sketch sentinel'
# shellcheck disable=SC2016 # Markdown literal contains backticks intentionally.
contains "$SKILL_MD" 'Skip sketches only when `design_classification == SIMPLE`' 'SKILL missing Anti-pattern #1 SIMPLE carve-out prose'
contains "$SKILL_MD" 'This is a SIMPLE-tier design. Bias the plan toward the **smallest change that achieves the goal**.' 'SKILL missing SIMPLE designer emphasis'
contains "$SKILL_MD" 'This is a HARD-tier design. Bias the plan toward **thoroughness**.' 'SKILL missing HARD designer emphasis'
contains "$RUN_STEP3_SH" 'review-round-count.txt' 'run-step3-review.sh missing review-round counter'
# shellcheck disable=SC2016 # Removed flag must not be forwarded to the inner loop.
_removed_round_cap_flag='--round-'"cap"
absent "$RUN_STEP3_SH" "$_removed_round_cap_flag" 'run-step3-review.sh must not mention removed round-cap flag'
# shellcheck disable=SC2016 # Script literal intentionally checks unexpanded parameter syntax.
absent "$RUN_STEP3_SH" '--convergence-threshold "$CONVERGENCE_THRESHOLD"' 'run-step3-review.sh must NOT forward convergence-threshold to plan-review-loop'
absent "$SKILL_MD" '--convergence-threshold' 'SKILL.md must NOT pass convergence-threshold to run-step3-review.sh'
absent "$SKILL_MD" 'LARCH_DESIGN_CONVERGENCE_THRESHOLD' 'SKILL.md must NOT reference LARCH_DESIGN_CONVERGENCE_THRESHOLD'
# shellcheck disable=SC2016 # Removed env var must not remain in Step 3 launch fence.
_removed_design_cap_var='LARCH_DESIGN_'"ROUND_CAP"
absent "$SKILL_MD" "$_removed_design_cap_var" 'SKILL must not reference removed design round-cap env var'
TR_RUN_STEP3_SH="$REPO_ROOT/skills/design/scripts/test-run-step3-review.sh"
contains "$TR_RUN_STEP3_SH" 'driver argv matches plan-review-loop contract' \
  'test-run-step3-review.sh missing plan-review-loop integration-seam case'
_plan_forward_flags=(--design-tmpdir --plan-file --feature-file --codex-present --cursor-present --round-num --prune-round-num)
for _pf in "${_plan_forward_flags[@]}"; do
  grep -Fq -- "$_pf" "$PLAN_LOOP_SH" \
    || fail "plan-review-loop.sh missing $_pf in argv parser"
  grep -Fq -- "$_pf" "$RUN_STEP3_SH" \
    || fail "run-step3-review.sh missing $_pf forward to plan-review-loop"
  grep -Fq -- "$_pf" "$TR_RUN_STEP3_SH" \
    || fail "test-run-step3-review.sh integration-seam stub missing $_pf (sync with plan-review-loop.sh)"
done
contains "$RUN_STEP3_SH" '.step3-plan-review-result.env' 'run-step3-review.sh must read step3 plan-review result env'
contains "$RUN_STEP3_SH" 'result env is a symlink; ignoring it and using stdout fallback only' 'run-step3-review.sh missing symlink-safe step3 result env warning'
contains "$SKILL_MD" 'invoke-plan-validator.sh' 'SKILL missing renamed validator helper'
contains "$RUN_STEP3_SH" 'read-design-classification.sh' 'run-step3-review.sh missing classification reader'
contains "$RUN_STEP3_SH" '.step3-review-cap.env' 'run-step3-review.sh missing persisted Step 3 cap state file'
contains "$RUN_STEP3_SH" 'STEP3_REVIEW_CAP_REACHED=false' 'run-step3-review.sh missing persisted cap-false state'
contains "$RUN_STEP3_SH" 'STEP3_REVIEW_ROUND_NUM=' 'run-step3-review.sh missing persisted Step 3 round number state'
contains "$SKILL_MD" 'run-step3-review.sh' 'SKILL must invoke run-step3-review.sh'
contains "$SKILL_MD" 'step3 review result env is a symlink; refusing to source' 'SKILL must read allowlisted KVs from .step3-review-result.env'
[[ -x "$RUN_STEP3_SH" ]] || fail 'run-step3-review.sh must be executable'
[[ -f "$RUN_STEP3_MD" ]] || fail "run-step3-review.md missing: $RUN_STEP3_MD"
# shellcheck disable=SC2016 # Markdown literal contains backticks intentionally.
contains "$SKILL_MD" 'including `LOOP_STATUS=panel-failed`' 'SKILL missing panel-failed counter-consumption contract'
# shellcheck disable=SC2016 # Markdown literal contains backticks intentionally.
contains "$SKILL_MD" 'MUST NOT persist when `TALLY_PLAN_REVIEW_STATUS=tally-error`' 'SKILL missing tally-error counter-skip contract'
# shellcheck disable=SC2016 # Markdown literal contains backticks intentionally.
contains "$SKILL_MD" '`LOOP_STATUS=complete` — proceed to Gate B' 'SKILL missing complete branch matrix entry'
# shellcheck disable=SC2016 # Markdown literal contains backticks intentionally.
absent "$SKILL_MD" '`LOOP_STATUS=emit-plan-failed`' 'SKILL should remove emit-plan-failed branch matrix entry'
# shellcheck disable=SC2016 # Script literal intentionally checks unexpanded parameter syntax.
contains "$RUN_STEP3_SH" 'review-round cap (${_round_cap}) reached for ${_tier}' 'run-step3-review.sh missing Step 3 cap breadcrumb emit'
contains "$SKILL_MD" 'skip Gate B, and jump to Step 3b, then the Step 3b completion boundary (FINALIZE + step-3b), then Step 4, then Gate C with existing artifacts' 'SKILL missing boundary-qualified cap short-circuit Gate B bypass'
contains "$SKILL_MD" 'Gate B would otherwise re-surface stale accepted findings from an earlier round' 'SKILL missing stale-finding cap rationale'
contains "$SKILL_MD" 'The Step 3.5 continuation block below is bypassed on this path.' 'SKILL missing explicit Step 3.5 bypass prose'
contains "$SKILL_MD" 'the four primary options are **Approve final design** / **See full plan** / **Discuss further** / **Re-run review panel**' 'SKILL missing Gate C four-option prose'
contains "$SKILL_MD" 'Gate C MUST omit **Re-run review panel** and offer only **Approve final design** / **See full plan** / **Discuss further**' 'SKILL missing Gate C cap-omission prose with See full plan'
contains "$SKILL_MD" 'plan review MUST ALWAYS run the full Step 3 panel' 'SKILL missing full-panel Step 3 contract'
# shellcheck disable=SC2016 # Markdown literals intentionally pin unexpanded shell snippets.
contains "$SKILL_MD" 'After successful re-tally, read `$DESIGN_TMPDIR/plan-review/round-${ROUNDS_COMPLETED:-$ROUND_NUM}/round-start-s`' 'SKILL missing deferred MAV round-start-s read'
# shellcheck disable=SC2016 # Markdown literals intentionally pin unexpanded shell snippets.
contains "$SKILL_MD" 'record-plan-review-round-timing.sh --design-tmpdir "$DESIGN_TMPDIR" --round "${ROUNDS_COMPLETED:-$ROUND_NUM}" --start-s "$round_start_s" --end-s "$end_s" || true' 'SKILL missing deferred MAV timing helper invocation'
# shellcheck disable=SC2016 # Markdown literal intentionally checks backticked status token.
step3_main_agent_line=$(grep -nF 'If `TALLY_PLAN_REVIEW_STATUS` is `main-agent-vote-required`' "$SKILL_MD" | head -1 | cut -d: -f1 || true)
step3_mav_order_ok=$(awk -v s="${step3_main_agent_line:-0}" '
  NR >= s && /re-run `tally-plan-review\.sh`/ && /record-plan-review-round-timing\.sh --design-tmpdir/ {
    print (index($0, "re-run `tally-plan-review.sh`") < index($0, "record-plan-review-round-timing.sh --design-tmpdir")) ? "1" : "0"
    exit
  }
' "$SKILL_MD")
[[ -n "$step3_main_agent_line" && "$step3_mav_order_ok" == "1" ]] \
  || fail 'SKILL deferred MAV timing helper must run after re-tally'

grep -Fq 'sketch_budget=0' "$REPO_ROOT/skills/design/scripts/design-init-runparams.sh" \
  || fail 'design-init-runparams.sh must pin SIMPLE sketch_budget=0'
contains "$SKILL_MD" 'design-postplan-emit.sh' 'SKILL missing postplan driver quick validator skip owner'
absent "$SKILL_MD" 'invoke-plan-validator-if-not-quick.sh' 'SKILL must not reference old validator helper'
absent "$SKILL_MD" 'read-design-review-budget.sh' 'SKILL must not reference old budget reader'
absent "$SKILL_MD" 'NO_SKETCHES_CLASSIFIED_TRIVIAL' 'SKILL must not reference old trivial sentinel'
absent "$SKILL_MD" 'plan-review-quick.md' 'SKILL must not reference deleted quick review reference'
absent "$SKILL_MD" 'design-l3-velocity-notified-2670' 'SKILL must not retain Step 5d velocity comment sentinel'
contains "$DESIGN_INIT_SH" 'contract drift' 'design-init-runparams.sh missing Step 0b contract-drift abort prose'
contains "$DESIGN_INIT_SH" 'aborting before silent tier downgrade' 'design-init-runparams.sh missing silent tier downgrade abort pin'
contains "$DESIGN_INIT_SH" 'bash scripts/test-write-run-params.sh' 'design-init-runparams.sh missing contract-drift repro command'
grep -Fq 'refusing to recreate it with fallback defaults' "$REPO_ROOT/skills/design/scripts/design-init-runparams.sh" \
  || fail 'design-init-runparams.sh missing no-fallback run-params warning'
absent "$SKILL_MD" 'run-params write failed; router-flag recovery' 'SKILL must not retain old HARD fallback recovery reason'

contains "$FLAGS_MD" 'design-postplan-emit.sh' 'flags.md missing postplan driver validator contract'
contains "$FLAGS_MD" 'Validation is unconditional: there is no quick-skip path and no force flag.' 'flags.md missing unconditional validator contract'
contains "$APPROVAL_MD" 'Cap: 5 (both tiers).' 'approval-gates.md missing flat cap'
contains "$APPROVAL_MD" 'review-round cap (<cap>) reached for <tier>; skipping panel and continuing to Step 3b, then the Step 3b completion boundary (FINALIZE + step-3b), then Step 4, then Gate C.' 'approval-gates.md missing canonical boundary-qualified Step 3 cap breadcrumb'
contains "$APPROVAL_MD" 'auto-applying N accepted finding(s)' 'approval-gates.md missing Gate B auto-apply default breadcrumb'
contains "$APPROVAL_MD" 'Apply all / Go through each / Switch to discussion mode prompt below' 'approval-gates.md missing --approve explicit Gate B option wording'
contains "$APPROVAL_MD" 'Gate B prompts explicitly before any finding changes' 'approval-gates.md missing explicit Gate B apply boundary (--approve path)'
contains "$APPROVAL_MD" 'Step 3b → Step 3b completion boundary → Step 4 → Step 4b (Gate C) run in normal sequence' 'approval-gates.md missing zero-findings Step 3b boundary-qualified forward link'
contains "$APPROVAL_MD" 'proceed to Step 3b, then the Step 3b completion boundary (FINALIZE + step-3b); Step 4 and Gate C follow in normal sequence.' 'approval-gates.md missing shared post-apply Step 3b forward link'
contains "$APPROVAL_MD" '(default) — auto-apply.' 'approval-gates.md missing Gate B auto-apply default branch'
contains "$APPROVAL_MD" 'Re-run review panel' 'approval-gates.md missing Gate C rerun option contract'
# shellcheck disable=SC2016 # Markdown literal contains backticks intentionally.
contains "$APPROVAL_MD" 're-fires the same Gate A `AskUserQuestion` minus the `See full plan` option, leaving exactly two options (`Ready for review` / `Discuss more`)' 'approval-gates.md missing Gate A See-full-plan re-prompt contract'
# shellcheck disable=SC2016 # Markdown literal contains backticks intentionally.
contains "$APPROVAL_MD" 'If `$DESIGN_TMPDIR/plan.txt` is missing or empty on re-entry (should not happen — re-entry is post-plan by definition), print `**⚠ plan.txt missing or empty; nothing to show.**` and re-prompt with the two-option shape anyway.' 'approval-gates.md missing Gate A missing-plan recovery contract'
# shellcheck disable=SC2016 # Markdown literal contains backticks intentionally.
contains "$APPROVAL_MD" 'Any Gate C re-prompt after `Other` must preserve those three at-cap options' 'approval-gates.md missing Gate C cap re-prompt omission contract'
# shellcheck disable=SC2016 # Markdown literal contains backticks intentionally.
contains "$APPROVAL_MD" '- **See full plan** — Print the current `$DESIGN_TMPDIR/plan.txt` into chat under a `## Final Design Plan` header' 'approval-gates.md missing Gate C See-full-plan bullet'
# shellcheck disable=SC2016 # Markdown literal contains backticks intentionally.
contains "$APPROVAL_MD" 'If `$DESIGN_TMPDIR/plan.txt` is missing or empty when the user picks the structured `See full plan` option (for example after the warning-only presentation path), print `**⚠ plan.txt missing or empty; nothing to show.**` and still re-fire the same Gate C `AskUserQuestion` minus the `See full plan` option.' 'approval-gates.md missing Gate C structured missing-plan recovery contract'
# shellcheck disable=SC2016 # Markdown literal contains backticks intentionally.
contains "$APPROVAL_MD" 'the `Other` re-prompt preserves the **same option set unchanged**' 'approval-gates.md missing Gate C Other-path unchanged-option-set contract'
# shellcheck disable=SC2016 # Markdown literal contains backticks intentionally.
contains "$APPROVAL_MD" 'when `plan.txt` is missing or empty, print `**⚠ plan.txt missing or empty; nothing to show.**` instead and still re-fire the same prompt' 'approval-gates.md missing Gate C Other missing-plan recovery contract'
contains "$APPROVAL_MD" 'offer this option only when the current review-round count is still below the flattened cap of 5' 'approval-gates.md missing Gate C cap-aware rerun contract'
# shellcheck disable=SC2016 # Markdown literal contains backticks intentionally.
contains "$PLAN_REVIEW_MD" 'Step 3 always runs the full panel via `plan-review-loop.sh`' 'plan-review.md missing full-panel consumer line'
contains "$PLAN_REVIEW_MD" 'injects the SIMPLE-emphasis or HARD-emphasis text immediately after the role line' 'plan-review.md missing tier-emphasis injection contract'
contains "$PLAN_REVIEW_MD" 'vote YES or NO on proposed modifications' 'plan-review.md missing voter YES/NO instruction line'
contains "$PLAN_REVIEW_MD" 'Treat any suggested remedy in the item body as *informational only*' 'plan-review.md missing OOS remedy informational-only pin'
contains "$PLAN_REVIEW_MD" 'Security-tagged findings are held locally and NEVER written to this public OOS issue artifact' 'plan-review.md missing SECURITY.md OOS exclusion pin'
# shellcheck disable=SC2016 # Markdown literal contains backticks intentionally.
contains "$PLAN_REVIEW_MD" 'Security-tagged accepted OOS findings are held locally per SECURITY.md and are NOT included in `oos.md`.' 'plan-review.md missing SECURITY.md oos.md exclusion pin'
contains "$DISCUSSION_MD" 'design-postplan-emit.sh' 'discussion-rounds.md missing postplan validator driver helper'

if grep -Eq 'grep .*review-round-count\.txt|review-round-count\.txt.*grep' "$PLAN_LOOP_SH"; then
  fail 'plan-review-loop.sh must not grep review-round-count.txt'
fi
contains "$PLAN_LOOP_SH" '--round-num is a stateless integer supplied by the caller' 'plan-review-loop.sh missing stateless round comment'

absent "$MAKEFILE" 'test-read-design-review-budget-invoke' 'Makefile must not reference deleted read-design-review-budget harness'

# Gate B auto-apply default + --approve explicit pins are covered above and by current branch-matrix checks.
# Check 15d: design SKILL must not chat-print token/timing summaries.
if grep -nF 'token-report.sh --summary' "$SKILL_MD" | grep -q .; then
  fail "(15d) skills/design/SKILL.md must not invoke token-report.sh --summary"
fi
if grep -nF 'timing-report.sh --summary' "$SKILL_MD" | grep -q .; then
  fail "(15d) skills/design/SKILL.md must not invoke timing-report.sh --summary"
fi

# Check 14: design ACTION dispatcher pins. The focus-area enum must remain in
# SKILL.md because CI and prompt rendering scan the inline reviewer launch
# blocks, while scriptable mechanics route through ACTION records.
focus_anchor_count=$(grep -Fc 'Focus area enum anchor for CI: code-quality / risk-integration / correctness / architecture / security' "$SKILL_MD")
[[ "$focus_anchor_count" == "1" ]] \
  || fail "(14a) SKILL.md must keep exactly 1 focus-area enum anchor comment; found $focus_anchor_count"
grep -Fq 'design-postplan-emit.sh' "$SKILL_MD" \
  || fail "(14b1) SKILL.md missing design-postplan-emit.sh invocation"
grep -Fq 'ACTION=FINALIZE' "$SKILL_MD" \
  || fail "(14b3) SKILL.md missing ACTION=FINALIZE emission"
grep -Fq 'design-driver.sh' "$SKILL_MD" \
  || fail "(14b4) SKILL.md missing design-driver.sh dispatcher invocation"
grep -Fq 'run-step3-review.sh' "$SKILL_MD" \
  || fail "(14c0) SKILL.md missing run-step3-review.sh Step 3 driver invocation"
grep -Fq 'set +e' "$RUN_STEP3_SH" \
  || fail "(14c0b) run-step3-review.sh missing set +e guard around plan-review-loop.sh"
grep -Fq '_plan_review_rc=$?' "$SKILL_MD" \
  || fail "(14c0c) SKILL.md missing _plan_review_rc capture for run-step3-review.sh"
# shellcheck disable=SC2016 # Markdown/bash excerpt literal; $DESIGN_TMPDIR must not expand here.
contains "$SKILL_MD" '-f "$DESIGN_TMPDIR/.step3-review-result.env"' 'SKILL must source .step3-review-result.env when present'
contains "$SKILL_MD" 'WARN) printf' 'SKILL must re-emit WARN lines from step3 review handoff'
contains "$SKILL_MD" 'missing or invalid LOOP_STATUS after run-step3-review.sh; treating plan review as panel-failed' 'SKILL must default missing LOOP_STATUS to panel-failed (not hard abort on driver exit 1)'
contains "$SKILL_MD" 'configuration error (exit 2)' 'SKILL must warn on run-step3-review.sh exit 2'
grep -Fq 'scout-plan-archetypes-wrapper.sh' "$PLAN_REVIEW_LOOP_SH" \
  || fail "(14c1) plan-review-loop.sh missing scout-plan-archetypes-wrapper.sh"
grep -Fq 'dispatch-plan-review-panel.sh' "$PLAN_REVIEW_LOOP_SH" \
  || fail "(14c2) plan-review-loop.sh missing dispatch-plan-review-panel.sh"
grep -Fq 'PANEL_PATHS_FILE' "$PLAN_REVIEW_LOOP_SH" \
  || fail "(14c3) plan-review-loop.sh missing PANEL_PATHS_FILE handling"
[[ -x "$PLAN_REVIEW_LOOP_SH" ]] \
  || fail "(14c4) plan-review-loop.sh must be executable"
PR_LOOP_MD="$REPO_ROOT/skills/design/scripts/plan-review-loop.md"
[[ -f "$PR_LOOP_MD" ]] || fail "(14c5) plan-review-loop.md missing: $PR_LOOP_MD"
grep -Fqe '--input-mode plan' "$PLAN_REVIEW_LOOP_SH" \
  || fail "(14c6) plan-review-loop.sh missing --input-mode plan aggregate invocation"
grep -Fq 'tally-plan-review.sh' "$PLAN_REVIEW_LOOP_SH" \
  || fail "(14c7) plan-review-loop.sh missing tally-plan-review.sh"
grep -Fq 'dispatch-plan-voters.sh' "$PLAN_REVIEW_LOOP_SH" \
  || fail "(14c8) plan-review-loop.sh missing dispatch-plan-voters.sh"
grep -Fq 'aggregate-findings.sh' "$PLAN_REVIEW_LOOP_SH" \
  || fail "(14c9) plan-review-loop.sh missing aggregate-findings.sh"
grep -Fq 'check-mid-run-dirty-tree.sh' "$PLAN_REVIEW_LOOP_SH" \
  || fail "(14c10) plan-review-loop.sh missing check-mid-run-dirty-tree.sh"
grep -Fq 'compose-collector-failure-log.sh' "$PLAN_REVIEW_LOOP_SH" \
  || fail "(14c11) plan-review-loop.sh missing compose-collector-failure-log.sh"
grep -Fq 'launch-claude-review.sh' "$REPO_ROOT/scripts/dispatch-plan-voters.sh" \
  || fail "(14c12) dispatch-plan-voters.sh missing launch-claude-review.sh (Voter 1)"
TR_LOOP_SH="$REPO_ROOT/skills/design/scripts/test-plan-review-loop.sh"
TR_LOOP_MD="$REPO_ROOT/skills/design/scripts/test-plan-review-loop.md"
[[ -x "$TR_LOOP_SH" ]] || fail "(14c13) test-plan-review-loop.sh missing or not executable"
[[ -f "$TR_LOOP_MD" ]] || fail "(14c14) test-plan-review-loop.md missing"

[[ -x "$PARSE_DESIGN_ARGV_SH" ]] || fail 'parse-design-argv.sh must be executable'
contains "$PARSE_DESIGN_ARGV_SH" 'VALIDATION_ERROR=' 'parse-design-argv.sh missing validation-error output'
contains "$PARSE_DESIGN_ARGV_SH" 'POSITIONAL_KIND=' 'parse-design-argv.sh missing positional-kind output'
grep -Fq 'parse-design-argv.sh' "$SKILL_MD" || fail 'SKILL.md missing parse-design-argv.sh Step 0-pre wiring'
if ! grep -Fq 'POSITIONAL_KIND' "$SKILL_MD" || grep -Fq 'remaining tokens after flags' "$SKILL_MD"; then
  fail 'Step 0b must consume POSITIONAL_KIND from 0-pre, not re-parse argv tail'
fi
step0pre_block=$(awk '/^### 0-pre /,/^### 0a /' "$SKILL_MD")
printf '%s\n' "$step0pre_block" | grep -Fq 'set +e' \
  || fail 'Step 0-pre fence missing set +e around parse-design-argv.sh capture'
printf '%s\n' "$step0pre_block" | grep -Fq '_argv_rc=$?' \
  || fail 'Step 0-pre fence missing explicit _argv_rc capture'
printf '%s\n' "$step0pre_block" | grep -Fq 'VALIDATION_ERROR' \
  || fail 'Step 0-pre fence missing VALIDATION_ERROR handling'
printf '%s\n' "$step0pre_block" | grep -Fq '<PUBLIC_ARGV_WORDS>' \
  || fail 'Step 0-pre fence must invoke parse-design-argv.sh via <PUBLIC_ARGV_WORDS> substitution'
if printf '%s\n' "$step0pre_block" | grep -Fq "\$ARGUMENTS"; then
  fail "Step 0-pre fence must not re-parse \$ARGUMENTS"
fi
printf '%s\n' "$step0pre_block" | grep -Fq 'unexpanded template literal' \
  || fail 'Step 0-pre must reject unexpanded CLAUDE_PLUGIN_ROOT template literal'
printf '%s\n' "$step0pre_block" | grep -Fq 'parse-design-argv.sh not executable' \
  || fail 'Step 0-pre must verify parse-design-argv.sh is executable before invoke'
# shellcheck disable=SC2016 # Markdown literal; ${CLAUDE_PLUGIN_ROOT} must stay unexpanded in the forbidden pattern.
if printf '%s\n' "$step0pre_block" | grep -Fq "= '\${CLAUDE_PLUGIN_ROOT}'"; then
  fail 'Step 0-pre must not compare CLAUDE_PLUGIN_ROOT against a bare ${CLAUDE_PLUGIN_ROOT} sentinel (loader expands it; use a de-tokenized literal)'
fi
contains "$PARSE_DESIGN_ARGV_SH" 'assert_safe_kv_value' 'parse-design-argv.sh missing newline guard on emitted values'

DESIGN_DRIVER_SH="$REPO_ROOT/skills/design/scripts/design-driver.sh"
[[ -x "$DESIGN_POSTPLAN_EMIT_SH" ]] || fail "design-postplan-emit.sh must be executable"
contains "$DESIGN_POSTPLAN_EMIT_SH" 'ACTION=EMIT_PLAN' 'design-postplan-emit.sh missing EMIT_PLAN dispatch'
contains "$DESIGN_POSTPLAN_EMIT_SH" 'snapshot-plan-round.sh' 'design-postplan-emit.sh missing snapshot helper call'
contains "$DESIGN_POSTPLAN_EMIT_SH" 'write-original' 'design-postplan-emit.sh missing write-original call'
contains "$DESIGN_POSTPLAN_EMIT_SH" 'invoke-plan-validator.sh' 'design-postplan-emit.sh missing validator helper call'
contains "$DESIGN_POSTPLAN_EMIT_SH" '_postplan_resolve_issue' 'design-postplan-emit.sh missing issue resolver'
contains "$DESIGN_POSTPLAN_EMIT_SH" '_postplan_pause_checkpoint' 'design-postplan-emit.sh missing pause checkpoint'
contains "$DESIGN_POSTPLAN_EMIT_SH" '_postplan_write_result_and_emit' 'design-postplan-emit.sh missing result flush helper'
contains "$DESIGN_POSTPLAN_EMIT_SH" 'set +e' 'design-postplan-emit.sh missing child set +e capture'
contains "$DESIGN_POSTPLAN_EMIT_SH" '--with-plan-size' 'design-postplan-emit.sh missing --with-plan-size flag'
contains "$DESIGN_POSTPLAN_EMIT_SH" 'exit 10' 'design-postplan-emit.sh missing exit 10 defects'
contains "$DESIGN_POSTPLAN_EMIT_SH" 'exit 11' 'design-postplan-emit.sh missing exit 11 pause'
contains "$DESIGN_POSTPLAN_EMIT_SH" 'exit 12' 'design-postplan-emit.sh missing exit 12 hard'
contains "$DESIGN_POSTPLAN_EMIT_SH" 'exit 13' 'design-postplan-emit.sh missing exit 13 partition'
postplan_emit_line=$(grep -nF 'ACTION=EMIT_PLAN' "$DESIGN_POSTPLAN_EMIT_SH" | head -1 | cut -d: -f1 || true)
postplan_val_line=$(grep -nF 'invoke-plan-validator.sh' "$DESIGN_POSTPLAN_EMIT_SH" | head -1 | cut -d: -f1 || true)
[[ -n "$postplan_emit_line" && -n "$postplan_val_line" && "$postplan_emit_line" -le "$postplan_val_line" ]]   || fail "design-postplan-emit.sh must dispatch EMIT at or before validator"
contains "$SKILL_MD" '.design-postplan-emit-result.env' 'SKILL.md missing postplan result env read'
contains "$SKILL_MD" 'design-postplan-emit.sh configuration error (exit 2)' 'SKILL.md missing postplan exit-2 abort prose'
assert_postplan_thin_fence "$SKILL_MD" 'SKILL Step 2b thin-fence' '<!-- step:2b ' '### Step 2b.5'
run_postplan_thin_fence_self_tests
assert_postplan_reference_thin_fence "$APPROVAL_MD" 'approval-gates Gate B postplan fence' '### Shared post-apply pipeline' '### Gate B plan revision and Step 2b.5'
assert_postplan_reference_thin_fence "$DISCUSSION_MD" 'discussion-round2 postplan fence' '**Plan revision authority**' '## Cap'
# shellcheck disable=SC2016 # Markdown literal contains unexpanded shell syntax.
contains "$APPROVAL_MD" 'case "${_postplan_rc:-1}" in' 'approval-gates Gate B postplan fence missing rc case'
contains "$APPROVAL_MD" 'default-abort' 'approval-gates Gate B postplan fence missing default-abort arm'
# shellcheck disable=SC2016 # Markdown literal contains unexpanded shell syntax.
contains "$DISCUSSION_MD" 'case "${_postplan_rc:-1}" in' 'discussion-round2 postplan fence missing rc case'
contains "$DISCUSSION_MD" 'default-abort' 'discussion-round2 postplan fence missing default-abort arm'
# shellcheck disable=SC2016 # Markdown literal contains unexpanded shell syntax.
absent "$APPROVAL_MD" '<<<"${_postplan_out:-}"' 'approval-gates Gate B postplan fence must not merge stdout KVs via heredoc'
# shellcheck disable=SC2016 # Markdown literal contains unexpanded shell syntax.
absent "$DISCUSSION_MD" '<<<"${_postplan_out:-}"' 'discussion-round2 postplan fence must not merge stdout KVs via heredoc'
# shellcheck disable=SC2016 # Markdown literal; $PPID must remain unexpanded.
contains "$SKILL_MD" 'current-design-env-$PPID.sh' 'SKILL.md Step 2b postplan fence missing canonical prelude'
DESIGN_POSTPLAN_STEP2B=$(awk '/^<!-- step:2b /,/^### Step 2b\.5/' "$SKILL_MD")
if printf '%s\n' "$DESIGN_POSTPLAN_STEP2B" | grep -Fq 'ACTION=EMIT_PLAN'; then
  fail "(FINDING_1) Step 2b block must not retain bare ACTION=EMIT_PLAN outside shared validator failure prose"
fi
step1e_block=$(awk '/Optional trailer guard \(Gate A re-entry rewrites\)/,/^<!-- step:2a /' "$SKILL_MD")
printf '%s\n' "$step1e_block" | grep -Fq 'design-postplan-emit.sh' \
  || fail "(14c14i) Gate A optional-trailer guard missing design-postplan-emit.sh"
printf '%s\n' "$step1e_block" | grep -Fq 'Plan command validator failure' \
  || fail "(14c14i) Gate A optional-trailer guard missing shared defects-found routing"
grep -Fq 'VALIDATE_PLAN_COMMANDS' "$DESIGN_DRIVER_SH" \
  || fail "(14b5) design-driver.sh missing VALIDATE_PLAN_COMMANDS"
grep -Fq 'validate-plan.sh' "$DESIGN_DRIVER_SH" \
  || fail "(14b6) design-driver.sh missing validate-plan.sh dispatch arm"
grep -Fq 'ACTION=VALIDATE_PLAN_COMMANDS' "$SKILL_MD" \
  || fail "(14b7) SKILL.md missing ACTION=VALIDATE_PLAN_COMMANDS"
grep -Fq 'Fix-and-retry' "$SKILL_MD" \
  || fail "(14b8) SKILL.md missing Fix-and-retry validator option label"
grep -Fq 'Override' "$SKILL_MD" \
  || fail "(14b9a) SKILL.md missing Override validator option label"
grep -Fq 'Cancel' "$SKILL_MD" \
  || fail "(14b9b) SKILL.md missing Cancel validator option label"
grep -Fq 'auto-fix-plan-commands.sh' "$SKILL_MD" \
  || fail "(FINDING_14) SKILL.md missing validator auto-fix helper invocation"
grep -Fq '.plan-command-autofix-${_autofix_cycle_key:-site}.attempted' "$SKILL_MD" \
  || fail "(FINDING_23) SKILL.md missing durable auto-fix cycle cap sentinel"
grep -Fq 'ORIGINAL_VALIDATE_LOG_FILE' "$SKILL_MD" \
  || fail "(FINDING_11) SKILL.md missing original validator evidence handoff"
grep -Fq 'Missing/unknown `AUTOFIX_STATUS` never continues silently' "$SKILL_MD" \
  || fail "(FINDING_4) SKILL.md missing auto-fix unknown-status fallback"
grep -Fq 'continue the surrounding success path without prompting' "$SKILL_MD" \
  || fail "(FINDING_17) SKILL.md missing auto-fix ok prompt-suppression contract"
grep -Fq 'Always** append a `Warnings` entry noting that defects occurred and auto-fix did not resolve them' "$SKILL_MD" \
  || fail "(FINDING_17) SKILL.md missing auto-fix fallback warning contract"
grep -Fq -- '--repo-root "$PWD"' "$SKILL_MD" \
  || fail "(FINDING_5) SKILL.md missing consumer repo-root forwarding"
step2b_mark=$(grep -nF 'mark "design Step 2b — plan"' "$SKILL_MD" | head -1 | cut -d: -f1 || true)
postplan_line=$(awk -v s="$step2b_mark" 'NR>s && /design-postplan-emit\.sh/ {print NR; exit}' "$SKILL_MD" || true)
step2b5_line=$(awk -v s="$step2b_mark" 'NR>s && /### Step 2b\.5/ {print NR; exit}' "$SKILL_MD" || true)
[[ -n "$step2b_mark" && -n "$postplan_line" && -n "$step2b5_line" && "$step2b5_line" -gt "$postplan_line" ]] \
  || fail "(14b10) design-postplan-emit.sh must precede Step 2b.5 in Step 2b block"

AG_MD="$REPO_ROOT/skills/design/references/approval-gates.md"
DR_MD="$REPO_ROOT/skills/design/references/discussion-rounds.md"
[[ -f "$AG_MD" ]] || fail "(14c14a) approval-gates.md missing: $AG_MD"
[[ -f "$DR_MD" ]] || fail "(14c14b) discussion-rounds.md missing: $DR_MD"
grep -Fq 'design-postplan-emit.sh' "$AG_MD" \
  || fail "(14c14c) approval-gates.md missing design-postplan-emit.sh pin"
grep -Fq 'VALIDATE_STATUS' "$AG_MD" \
  || fail "(14c14d) approval-gates.md must reference VALIDATE_STATUS (validator routing through driver)"
grep -Fq -- '--with-plan-size' "$AG_MD" \
  || fail "(14c14e) approval-gates.md missing --with-plan-size"
grep -Fq '_postplan_rc=10' "$AG_MD" \
  || fail "(14c14e) approval-gates.md missing _postplan_rc=10 handling"
grep -Fq '_postplan_rc=12' "$AG_MD" \
  || fail "(14c14e) approval-gates.md missing _postplan_rc=12 handling"
# shellcheck disable=SC2016 # Markdown literal references SKILL case arms.
grep -Fq 'case` arms as `SKILL.md` Step 2b' "$AG_MD" \
  || fail "(14c14e) approval-gates.md must delegate to SKILL Step 2b case arms"
grep -Fq 'design-postplan-emit.sh' "$DR_MD" \
  || fail "(14c14f) discussion-rounds.md missing design-postplan-emit.sh pin"
grep -Fq -- '--with-plan-size' "$DR_MD" \
  || fail "(14c14g) discussion-rounds.md missing merged --with-plan-size"
if grep -Fq -- '--force-validate' "$DR_MD"; then
  fail "(14c14h) discussion-rounds.md must not mention retired --force-validate"
fi
grep -Fq '_postplan_rc=10' "$DR_MD" \
  || fail "(14c14h) discussion-rounds.md missing _postplan_rc=10 handling"
grep -Fq '_postplan_rc=0' "$DR_MD" \
  || fail "(14c14h) discussion-rounds.md missing _postplan_rc=0 sentinel handling"
printf '%s\n' "$step1e_block" | grep -Fq -- '--with-plan-size' \
  || fail "(14c14i) Gate A optional-trailer guard missing --with-plan-size"
if printf '%s\n' "$step1e_block" | grep -Fq -- '--force-validate'; then
  fail "(14c14i) Gate A optional-trailer guard must not mention retired --force-validate"
fi

# Check 16: dialectic waterfall + per-side assignment contract pins (#2620).
DIALPROTO_MD="$REPO_ROOT/skills/shared/dialectic-protocol.md"
DEBATE_MD="$REPO_ROOT/skills/design/references/dialectic-debate.md"
TIMING_KINDS_SH="$REPO_ROOT/scripts/lib-timing-kinds.sh"
grep -Fq '## Per-side waterfall retry' "$DIALPROTO_MD" \
  || fail "(16) dialectic-protocol.md missing '## Per-side waterfall retry' section header"
grep -Fq 'Debater quorum gate (six tags)' "$DIALPROTO_MD" \
  || fail "(16) dialectic-protocol.md missing six-tag eligibility gate anchor"
grep -Fq '<steelman>' "$DIALPROTO_MD" \
  || fail "(16) dialectic-protocol.md missing <steelman> in six-tag gate text"
grep -Fq '5. **Per-side waterfall retry**' "$DIALEXEC_MD" \
  || fail "(16) dialectic-execution.md missing step 5 Per-side waterfall retry header"
grep -Fq 'waterfall' "$DIALEXEC_MD" \
  || fail "(16) dialectic-execution.md missing waterfall token (step 5 contract)"
grep -Fq '1. **Per-side external tool assignment**' "$DIALEXEC_MD" \
  || fail "(16) dialectic-execution.md missing step 1 per-side external tool assignment header"
grep -Fq 'launch-codex-exec.sh' "$DIALEXEC_MD" \
  || fail "(codex judge) dialectic-execution.md must reference launch-codex-exec.sh for Codex judge"
grep -Fq 'OUTPUT FORMAT' "$DEBATE_MD" \
  || fail "(16) dialectic-debate.md missing OUTPUT FORMAT header"
grep -Fq 'SELF-CHECK BEFORE STOPPING' "$DEBATE_MD" \
  || fail "(16) dialectic-debate.md missing SELF-CHECK BEFORE STOPPING directive"
grep -Fq '2nd-retry' "$SKILL_MD" \
  || fail "(16) design SKILL.md NEVER #2 missing 2nd-retry Claude exception token"
for kind in \
  cursor-debate-thesis-retry1 \
  cursor-debate-antithesis-retry1 \
  codex-debate-thesis-retry1 \
  codex-debate-antithesis-retry1 \
  claude-debate-thesis-retry2 \
  claude-debate-antithesis-retry2
do
  grep -Fq "$kind" "$TIMING_KINDS_SH" \
    || fail "(16) scripts/lib-timing-kinds.sh missing timing kind: $kind"
done

grep -Fq $'2b\tfull plan' "$REPO_ROOT/skills/design/scripts/step-name-registry.tsv" \
  || fail "(15b) step-name-registry.tsv missing 2b\\tfull plan row"
grep -Fq $'2b.5\tplan size' "$REPO_ROOT/skills/design/scripts/step-name-registry.tsv" \
  || fail "(15b) step-name-registry.tsv missing 2b.5\\tplan size row"
grep -Fq $'5\tfinalize' "$REPO_ROOT/skills/design/scripts/step-name-registry.tsv" \
  || fail "(15b) step-name-registry.tsv missing 5\\tfinalize row"
grep -Fq $'6\tcleanup' "$REPO_ROOT/skills/design/scripts/step-name-registry.tsv" \
  || fail "(15b) step-name-registry.tsv missing 6\\tcleanup row"
grep -Fq '> **🔶 /design 5: finalize**' "$SKILL_MD" \
  || fail "(15b) SKILL.md missing /design 5 finalize breadcrumb"
grep -Fq '> **🔶 /design 6: cleanup**' "$SKILL_MD" \
  || fail "(15b) SKILL.md missing /design 6 cleanup breadcrumb"
step5b_line=$(grep -nF '### 5b — File accepted OOS issues' "$SKILL_MD" | head -1 | cut -d: -f1 || true)
step5c_line=$(grep -nF "### 5c — Write \`larch:plan\` to GitHub + publish" "$SKILL_MD" | head -1 | cut -d: -f1 || true)
[[ -n "$step5b_line" && -n "$step5c_line" ]] || fail "(15b) missing Step 5b or 5c sub-step headers"
if (( step5b_line >= step5c_line )); then
  fail "(15b) Step 5b must appear before Step 5c in SKILL.md"
fi
publish_red_line=$(grep -n 'redact-secrets\.sh.*composed-plan\.md' "$REPO_ROOT/skills/design/scripts/design-publish.sh" | head -1 | cut -d: -f1 || true)
publish_val_line=$(grep -n 'invoke-plan-validator\.sh.*composed-plan\.md' "$REPO_ROOT/skills/design/scripts/design-publish.sh" | head -1 | cut -d: -f1 || true)
[[ -n "$publish_red_line" && -n "$publish_val_line" && "$publish_val_line" -lt "$publish_red_line" ]] \
  || fail "(14b11) design-publish.sh validator must appear before redact-secrets on composed-plan.md"
# shellcheck disable=SC2016  # literal backticks + $DESIGN_TMPDIR token must match SKILL.md prose
needle='preserve `$DESIGN_TMPDIR`, skip Step 6 cleanup'
grep -Fq "$needle" "$SKILL_MD" \
  || fail "(14b12) Step 5c validator cancel must preserve tmpdir and skip cleanup"
grep -Fq '5c.5→5c.7→5c.8→6' "$SKILL_MD" \
  || fail "(15b) anti-halt reminder must mention 5c.5→5c.7→5c.8→6 step boundary (intra-Step-5 through rename)"

DESIGN_PUBLISH_SH="$REPO_ROOT/skills/design/scripts/design-publish.sh"
[[ -x "$DESIGN_PUBLISH_SH" ]] || fail "design-publish.sh must be executable"
publish_plan_line=$(grep -nF 'plan-block-write.sh' "$DESIGN_PUBLISH_SH" | head -1 | cut -d: -f1 || true)
publish_upsert_line=$(grep -nF 'upsert-diagrams-comment.sh' "$DESIGN_PUBLISH_SH" | head -1 | cut -d: -f1 || true)
publish_log_line=$(grep -nF 'design-log-publish.sh' "$DESIGN_PUBLISH_SH" | head -1 | cut -d: -f1 || true)
[[ -n "$publish_plan_line" && -n "$publish_upsert_line" && -n "$publish_log_line" && "$publish_plan_line" -lt "$publish_upsert_line" && "$publish_upsert_line" -lt "$publish_log_line" ]] \
  || fail "(15b) design-publish.sh must call plan-block-write.sh before upsert-diagrams-comment.sh before design-log-publish.sh"
grep -Fq 'architecture-diagram.skipped' "$DESIGN_PUBLISH_SH" \
  || fail "(15b) design-publish.sh must handle architecture-diagram.skipped sentinel"
grep -Fq -- '--clear-architecture' "$DESIGN_PUBLISH_SH" \
  || fail "(15b) design-publish.sh must invoke --clear-architecture when skipped sentinel present"
step3b_line=$(grep -nF '<!-- step:3b' "$SKILL_MD" | head -1 | cut -d: -f1 || true)
step4_line=$(grep -nF '<!-- step:4 —' "$SKILL_MD" | head -1 | cut -d: -f1 || true)
[[ -n "$step3b_line" && -n "$step4_line" ]] || fail "(15b) missing Step 3b or Step 4 marker"
step3b_between=$(sed -n "$((step3b_line + 1)),$((step4_line - 1))p" "$SKILL_MD")
grep -Fq 'architecture-diagram.skipped' <<<"$step3b_between" \
  || fail "(15b) Step 3b must document architecture-diagram.skipped sentinel creation"
assert_step3b_finalize_boundary
assert_step2a_entry_simple_guard
assert_simple_branch_has_no_sentinel_fence
assert_no_direct_step3b_step4_routes 'SKILL Step 3b slice' "$SKILL_MD" '<!-- step:3b' '<!-- step:4 —'
assert_no_direct_step3b_step4_routes 'SKILL Step 3/Gate-B-bypass/Gate B slice' "$SKILL_MD" '<!-- step:3 —' '<!-- step:3.5'
assert_no_direct_step3b_step4_routes 'approval-gates.md' "$APPROVAL_MD"
assert_no_direct_step3b_step4_routes 'run-step3-review.sh' "$RUN_STEP3_SH"
assert_no_direct_step3b_step4_routes 'run-step3-review.md' "$RUN_STEP3_MD"
assert_no_direct_step3b_step4_routes 'plan-review.md' "$PLAN_REVIEW_MD"
assert_no_direct_step3b_step4_routes 'flags.md' "$FLAGS_MD"
assert_no_direct_step3b_step4_routes 'configuration-and-permissions.md' "$CONFIG_MD"
contains "$RUN_STEP3_SH" 'skipping panel and continuing to Step 3b, then the Step 3b completion boundary (FINALIZE + step-3b), then Step 4, then Gate C' 'run-step3-review.sh missing boundary-qualified cap breadcrumb'
contains "$FLAGS_MD" 'proceeds to Step 3b, then the Step 3b completion boundary (FINALIZE + step-3b), then Step 4, then Gate C' 'flags.md missing boundary-qualified panel-failed route'
contains "$SKILL_MD" 'repair pre-existing paused SIMPLE runs' 'SKILL missing old SIMPLE Step 2a.5 resume compatibility guard'
contains "$SKILL_MD" '[ ! -f "$DESIGN_TMPDIR/.completed/finalize" ]' 'SKILL missing old Step 4 finalize compatibility guard'
# shellcheck disable=SC2016 # Markdown literal contains backticks intentionally.
contains "$SKILL_MD" 'design-step3-state.sh --gate-b-bypass' 'SKILL missing Gate-B-bypass executable helper prose'
[[ -x "$REPO_ROOT/skills/design/scripts/design-step3-state.sh" ]] \
  || fail 'design-step3-state.sh must be committed executable helper'
contains "$REPO_ROOT/skills/design/scripts/design-step3-state.sh" 'STEP3_STATE=refused-partial-gate-b-bypass' 'design-step3-state.sh missing refused partial Gate-B-bypass state'
# shellcheck disable=SC2016 # Script literal intentionally checks unexpanded parameter syntax.
contains "$SKILL_MD" '${REPO:+--repo "$REPO"}' 'SKILL Step 3.6 rc=11 pause-save must thread REPO'
contains "$REPO_ROOT/skills/design/scripts/test-design-pause-resume.sh" 'gate B bypass' 'pause/resume harness missing Gate-B-bypass regression'
contains "$REPO_ROOT/skills/design/scripts/test-design-pause-resume.sh" 'missing gate B bypass sentinels should resume at 3.5' 'pause/resume harness missing missing-sentinel regression'
contains "$REPO_ROOT/skills/design/scripts/test-design-pause-resume.sh" 'old SIMPLE state with step-2a only should resume at Step 2a.5 compatibility guard' 'pause/resume harness missing old SIMPLE Step 2a compatibility fixture'
contains "$REPO_ROOT/skills/design/scripts/test-design-pause-resume.sh" 'old step-3b without finalize should resume at Step 4 compatibility guard' 'pause/resume harness missing old Step 3b finalize compatibility fixture'
assert_gate_b_bypass_branch_sentinels "$SKILL_MD"
assert_step3b_entry_guard_threads_repo "$SKILL_MD"
# Check 17: Step 5b /larch:issue summary-halt guardrails (#2681).
ORCHESTRATOR_NEVER_MD="$REPO_ROOT/skills/shared/orchestrator-never.md"
[[ -f "$ORCHESTRATOR_NEVER_MD" ]] || fail "(17) orchestrator-never.md missing: $ORCHESTRATOR_NEVER_MD"
grep -Fq '5→5a→5b→5c.1→5c.5→5c.7→5c.8→6' "$SKILL_MD" \
  || fail "(17) anti-halt reminder missing intra-Step-5 sub-step enumeration"
grep -Fq "NEVER treat a sub-skill's terminal output as the parent skill's terminal output" "$ORCHESTRATOR_NEVER_MD" \
  || fail "(17) orchestrator-never.md missing sub-skill vs parent-skill terminal-output NEVER literal"
grep -Fq 'NEVER poll a background task by reading its output file once per turn' "$ORCHESTRATOR_NEVER_MD" \
  || fail "(17) orchestrator-never.md missing per-turn-polling NEVER literal"
step5_between=$(sed -n "$((step5b_line + 1)),$((step5c_line - 1))p" "$SKILL_MD")
# Pin `/larch:issue` to the continuation-banner line (not merely anywhere in the 5b→5c window).
grep -Fq $'> **Continue to Step 5c IMMEDIATELY.** The `/larch:issue` Skill tool' <<<"$step5_between" \
  || fail "(17) Step 5b→5c continuation banner missing or /larch:issue not on the same line as the banner"

# Check FINDING_21 (#2670): plan-size thresholds + --partition documentation pins.
grep -Fq "| \`-p\` / \`--partition\` |" "$SKILL_MD" \
  || fail "(FINDING_21) SKILL.md compact flag table missing -p/--partition row"
grep -Fq '[-p|--partition]' "$SKILL_MD" \
  || fail "(FINDING_21) SKILL.md argument-hint missing [-p|--partition]"
grep -Fq '[--brainstorm]' "$SKILL_MD" \
  || fail "(FINDING_21) SKILL.md argument-hint missing [--brainstorm]"
grep -Fq '[--approve]' "$SKILL_MD" \
  || fail "(3628) SKILL.md argument-hint missing [--approve]"
grep -Fq "\`-p\`, \`--partition\`" "$SKILL_MD" \
  || fail "(FINDING_21) SKILL.md public argv allowlist missing -p/--partition"
# shellcheck disable=SC2016 # Markdown literal; backticks are SKILL.md prose, not command substitution
grep -Fq '`--partition`, `--brainstorm`, `--approve`, `--no-dedup`, and `--run-id`' "$SKILL_MD" \
  || fail "(FINDING_21) SKILL.md public argv allowlist missing reduced flag sequence"
grep -Fq '### Step 2b.5 — Plan-size threshold check' "$SKILL_MD" \
  || fail "(FINDING_21) SKILL.md missing Step 2b.5 header"
step2b_block=$(awk '/^<!-- step:2b /,/^<!-- step:3 /' "$SKILL_MD")
printf '%s\n' "$step2b_block" | grep -Fq -- '--with-plan-size' \
  || fail "(FINDING_21) Step 2b block missing --with-plan-size"
# shellcheck disable=SC2016 # Markdown literal contains unexpanded parameter syntax.
printf '%s\n' "$step2b_block" | grep -Fq ': > "$DESIGN_TMPDIR/.completed/step-2b.5"' \
  || fail "(FINDING_21) Step 2b rc0 must write step-2b.5 sentinel"
grep -Fq 'non-exiting Split returns' "$SKILL_MD" \
  || fail "(FINDING_21) SKILL.md missing non-exiting Split return sentinel prose"
# shellcheck disable=SC2016 # Markdown literal must stay unexpanded.
grep -Fq 'Override / clean proceed writes `: > "$DESIGN_TMPDIR/.completed/step-2b.5"`' "$SKILL_MD" \
  || true
grep -Fq 'Retained callers' "$SKILL_MD" \
  || fail "(FINDING_21) SKILL.md Step 2b.5 must document retained callers"
grep -Fq '## Plan Size — Hard Trigger' "$SKILL_MD" \
  || fail "(FINDING_21) SKILL.md missing hard-trigger plan-size header"
grep -Fq '(no **Continue** option — hard triggers' "$SKILL_MD" \
  || fail "(FINDING_21) SKILL.md hard branch must document no-Continue invariant"
DISCUSSION_MD="$REPO_ROOT/skills/design/references/discussion-rounds.md"
grep -Fq 'Step 1c sprawl heuristic' "$DISCUSSION_MD" \
  || fail "(FINDING_21) discussion-rounds.md missing Step 1c sprawl hook"
grep -Fq 'per Step 1d invocation' "$DISCUSSION_MD" \
  || fail "(FINDING_21) discussion-rounds.md missing Step 1d sprawl-once cap"
grep -Fq 'semantic sprawl heuristic' "$DISCUSSION_MD" \
  || fail "(FINDING_21) discussion-rounds.md missing semantic sprawl heuristic prose"
APPROVAL_MD="$REPO_ROOT/skills/design/references/approval-gates.md"
grep -Fq 'Step 2b.5' "$APPROVAL_MD" \
  || fail "(FINDING_21) approval-gates.md missing Step 2b.5 reference after Gate B EMIT_PLAN"
grep -Fq 'SOFT_ADVISORY=' "$SKILL_MD" \
  || fail "(3175) SKILL.md Step 2b.5 must parse SOFT_ADVISORY"
grep -Fq 'DIFF_ADDED=' "$SKILL_MD" \
  || fail "(3175) SKILL.md Step 2b.5 must parse DIFF_ADDED"
grep -Fq 'DIFF_DELETED=' "$SKILL_MD" \
  || fail "(3175) SKILL.md Step 2b.5 must parse DIFF_DELETED"
grep -Fq 'MECHANICAL_CHURN=' "$SKILL_MD" \
  || fail "(3175) SKILL.md Step 2b.5 must parse MECHANICAL_CHURN"
grep -Fq 'plan-body gate still requires Split/Cancel' "$SKILL_MD" \
  || fail "(3175) SKILL.md must document plan-body hard + SOFT_ADVISORY combined advisory"
grep -Fq 'diff_added' "$SKILL_MD" \
  || fail "(3175) SKILL.md missing diff_added preservation/recompute language"
grep -Fq 'diff_deleted' "$SKILL_MD" \
  || fail "(3175) SKILL.md missing diff_deleted preservation language"
grep -Fq 'mechanical_churn' "$SKILL_MD" \
  || fail "(3175) SKILL.md missing mechanical_churn preservation language"
grep -Fq 'gate-b-dedup-plan.sh' "$APPROVAL_MD" \
  || fail "(3175) approval-gates.md missing mechanical gate-b-dedup-plan.sh post-apply hook"
grep -Fq "gate-b-dedup-plan.sh\" --design-tmpdir \"\$DESIGN_TMPDIR\" --snapshot-trailers" "$SKILL_MD" \
  || fail "(3175) SKILL.md Gate A/B optional-trailer guard missing --snapshot-trailers hook"
grep -Fq 'gate-b-dedup-plan.sh --dedup' "$SKILL_MD" \
  || fail "(3175) SKILL.md Gate A/B optional-trailer guard missing --dedup hook"
grep -Fq -- '--snapshot-trailers' "$APPROVAL_MD" \
  || fail "(3175) approval-gates.md missing --snapshot-trailers hook"
grep -Fq -- '--dedup' "$APPROVAL_MD" \
  || fail "(3175) approval-gates.md missing --dedup hook"
grep -Fq 'diff_added' "$APPROVAL_MD" \
  || fail "(3175) approval-gates.md missing diff_added preservation language"
grep -Fq -- '--snapshot-trailers' "$DISCUSSION_MD" \
  || fail "(3175) discussion-rounds.md missing --snapshot-trailers hook"
grep -Fq -- '--dedup' "$DISCUSSION_MD" \
  || fail "(3175) discussion-rounds.md missing --dedup hook"
grep -Fq 'mechanical_churn' "$DISCUSSION_MD" \
  || fail "(3175) discussion-rounds.md missing mechanical_churn preservation language"
FLAGS_MD="$REPO_ROOT/skills/design/references/flags.md"
grep -Fq 'diff_deleted' "$APPROVAL_MD" \
  || fail "(3175) approval-gates.md missing diff_deleted preservation language"
grep -Fq 'diff_deleted' "$DISCUSSION_MD" \
  || fail "(3175) discussion-rounds.md missing diff_deleted preservation language"
grep -Fq 'diff_deleted' "$FLAGS_MD" \
  || fail "(3175) flags.md missing diff_deleted preservation language"
# shellcheck disable=SC2016 # Markdown literal; backticks are prose, not command substitution
grep -Fq 'before `ACTION=EMIT_PLAN`' "$APPROVAL_MD" \
  || grep -Fq 'before the merged post-plan fence' "$APPROVAL_MD" \
  || fail "(3175) approval-gates.md missing validate-before-postplan-fence guard"
# shellcheck disable=SC2016 # Markdown literal; backticks are prose, not command substitution
grep -Fq 'before `ACTION=EMIT_PLAN`' "$DISCUSSION_MD" \
  || grep -Fq 'before the merged post-plan fence' "$DISCUSSION_MD" \
  || fail "(3175) discussion-rounds.md missing validate-before-postplan-fence guard"
grep -Fq 'lib-plan-optional-trailers' "$REPO_ROOT/skills/design/scripts/revise-plan-with-waterfall.sh" \
  || fail "(3175) revise-plan-with-waterfall.sh must source shared optional-trailer lib"
grep -Fq 'lib-plan-optional-trailers' "$REPO_ROOT/skills/design/scripts/check-plan-size.sh" \
  || fail "(3175) check-plan-size.sh must source shared optional-trailer lib"
[[ -f "$REPO_ROOT/scripts/lib-untrusted-block.sh" ]] \
  || fail "scripts/lib-untrusted-block.sh must ship in plugin tree"
[[ -f "$REPO_ROOT/scripts/lib-scope-anchor-handoff.sh" ]] \
  || fail "scripts/lib-scope-anchor-handoff.sh must ship in plugin tree"
grep -Fq 'lib-untrusted-block' "$REPO_ROOT/skills/design/scripts/plan-review-loop.sh" \
  || grep -Fq 'lib-scope-anchor-handoff' "$REPO_ROOT/skills/design/scripts/plan-review-loop.sh" \
  || fail "plan-review-loop.sh must source scope-anchor handoff library"
grep -Fq 'lib-untrusted-block' "$REPO_ROOT/scripts/launch-claude-subprocess.sh" \
  || fail "launch-claude-subprocess.sh must source lib-untrusted-block.sh"
grep -Fq 'lib-untrusted-block' "$REPO_ROOT/skills/design/scripts/revise-plan-with-waterfall.sh" \
  || fail "revise-plan-with-waterfall.sh must source lib-untrusted-block.sh"
# Check 19 (#2754): --brainstorm / Step 1d.5 / run-params / plan-review feature-context pins.
BRAINSTORM_MD="$REPO_ROOT/skills/design/references/brainstorm.md"
BRAINSTORM_PROMPTS="$REPO_ROOT/skills/design/references/brainstorm-prompts.md"
[[ -f "$BRAINSTORM_MD" ]] || fail "(2754) brainstorm.md missing"
[[ -f "$BRAINSTORM_PROMPTS" ]] || fail "(2754) brainstorm-prompts.md missing"
# shellcheck disable=SC2016 # Markdown table cell literal
grep -Fq '| `--brainstorm` |' "$SKILL_MD" \
  || fail "(2754) SKILL.md compact flag table missing --brainstorm row"
grep -Fq '<!-- step:1d.5 — Brainstorm Panel -->' "$SKILL_MD" \
  || fail "(2754) SKILL.md missing Step 1d.5 anchor"
grep -Fq '> **🔶 /design 1d.5: brainstorm**' "$BRAINSTORM_MD" \
  || fail "(2754) brainstorm.md missing 1d.5 brainstorm breadcrumb"
grep -Fq '⏩ 1d.5: brainstorm — skipped (already complete; .brainstorm-done present)' "$BRAINSTORM_MD" \
  || fail "(2754) brainstorm.md missing sentinel-hit skip breadcrumb"
grep -Fq $'1d.5\tbrainstorm' "$REPO_ROOT/skills/design/scripts/step-name-registry.tsv" \
  || fail "(2754) step-name-registry.tsv missing 1d.5 brainstorm row"
grep -Fq '<BRAINSTORM_FRAMING_PROMPT>' "$BRAINSTORM_PROMPTS" \
  || fail "(2754) brainstorm-prompts.md missing <BRAINSTORM_FRAMING_PROMPT>"
grep -Fq '<BRAINSTORM_SCOPE_PROMPT>' "$BRAINSTORM_PROMPTS" \
  || fail "(2754) brainstorm-prompts.md missing <BRAINSTORM_SCOPE_PROMPT>"
grep -Fq '<BRAINSTORM_PRAGMATIC_PROMPT>' "$BRAINSTORM_PROMPTS" \
  || fail "(2754) brainstorm-prompts.md missing <BRAINSTORM_PRAGMATIC_PROMPT>"
# shellcheck disable=SC2016 # flags.md list marker uses backticks
grep -Fq '`--brainstorm`:' "$FLAGS_MD" \
  || fail "(2754) flags.md missing --brainstorm bullet anchor"
grep -Fq '1c→1d→1d.5→1d.7→2a' "$SKILL_MD" \
  || fail "(2754) SKILL.md anti-halt sequence missing 1d.5→1d.7→2a transition"
grep -Fq 'MANDATORY — READ ENTIRE FILE' "$BRAINSTORM_MD" \
  || fail "(2754) brainstorm.md missing MANDATORY directive"
grep -Fq 'skills/design/references/brainstorm-prompts.md' "$BRAINSTORM_MD" \
  || fail "(2754) brainstorm.md missing brainstorm-prompts.md path literal"
grep -Fq 'ScheduleWakeup' "$BRAINSTORM_MD" \
  || fail "(2754) brainstorm.md missing ScheduleWakeup prohibition anchor"
# Stage 4 (#3119): Family-B fence shape must stay absent from design orchestrator docs.
assert_p3119_family_b_fence_absent "$SKILL_MD" "SKILL.md"
assert_p3119_family_b_fence_absent "$BRAINSTORM_MD" "brainstorm.md"
assert_p3119_family_b_fence_absent "$DIALEXEC_MD" "dialectic-execution.md"
assert_p3119_family_b_fence_absent "$PLAN_REVIEW_MD" "plan-review.md"
assert_p3119_family_b_fence_absent "$DIALPROTO_MD" "dialectic-protocol.md"
# shellcheck disable=SC2016 # SKILL.md bash excerpt; quotes are literal
grep -Fq -- '--brainstorm-requested "$brainstorm_requested"' "$SKILL_MD" \
  || fail "(2754) SKILL.md design-init-runparams invocation missing --brainstorm-requested"
# shellcheck disable=SC2016 # SKILL.md bash excerpt; quotes are literal
grep -Fq -- '--approve-requested "$approve_requested"' "$SKILL_MD" \
  || fail "(3628) SKILL.md design-init-runparams invocation missing --approve-requested"
# shellcheck disable=SC2016 # SKILL.md bash excerpt
grep -Fq -- '[[ "$PARTITION_REQUESTED" == true || "$BRAINSTORM_REQUESTED" == true || "$APPROVE_REQUESTED" == true ]]' "$REPO_ROOT/skills/design/scripts/design-init-runparams.sh" \
  || fail "(2754) design-init-runparams.sh recovery guard missing partition OR brainstorm OR approve"
# shellcheck disable=SC2016 # jq filter literal
grep -Fq -- '.brainstorm_requested = (.brainstorm_requested == true or $merge_b)' "$REPO_ROOT/skills/design/scripts/design-init-runparams.sh" \
  || fail "(2754) design-init-runparams.sh jq merge missing brainstorm_requested arm"
# shellcheck disable=SC2016 # jq filter literal
grep -Fq -- '.approve_requested = (.approve_requested == true or $merge_a)' "$REPO_ROOT/skills/design/scripts/design-init-runparams.sh" \
  || fail "(3628) design-init-runparams.sh jq merge missing approve_requested arm"
grep -Fq '⏩ 1d.5: brainstorm — skipped' "$BRAINSTORM_MD" \
  || fail "(2754) brainstorm.md missing skip breadcrumb literal"
grep -Fq 'plan-review-feature-context.txt' "$REPO_ROOT/skills/design/scripts/plan-review-loop.sh" \
  || fail "(2754) plan-review-loop.sh missing plan-review-feature-context merge path"
for _bk in cursor-brainstorm codex-brainstorm; do
  grep -Fq "$_bk" "$TIMING_KINDS_SH" \
    || fail "(2754) scripts/lib-timing-kinds.sh missing timing kind: $_bk"
done

# Check 20 (#2974): Step 1d.7 outline approval replaces first-time Gate A.
DESIGN_OUTLINE_MD="$REPO_ROOT/skills/design/references/design-outline.md"
[[ -f "$DESIGN_OUTLINE_MD" ]] || fail "(2974) design-outline.md missing"
line_1d5=$(grep -nF '<!-- step:1d.5 — Brainstorm Panel -->' "$SKILL_MD" | head -1 | cut -d: -f1 || true)
line_1d7=$(grep -nF '<!-- step:1d.7 — Design Outline (Outline-Approval Gate) -->' "$SKILL_MD" | head -1 | cut -d: -f1 || true)
line_1e=$(grep -nF '<!-- step:1e — Discussion Mode Gate (Gate A) -->' "$SKILL_MD" | head -1 | cut -d: -f1 || true)
[[ -n "$line_1d5" && -n "$line_1d7" && -n "$line_1e" ]] || fail "(2974) missing Step 1d.5, 1d.7, or 1e anchor"
if (( line_1d5 >= line_1d7 || line_1d7 >= line_1e )); then
  fail "(2974) Step 1d.7 anchor must appear between Step 1d.5 and Step 1e"
fi
grep -Fq $'1d.7\toutline' "$REPO_ROOT/skills/design/scripts/step-name-registry.tsv" \
  || fail "(2974) step-name-registry.tsv missing 1d.7 outline row"
grep -Fq '> **🔶 /design 1d.7: outline**' "$DESIGN_OUTLINE_MD" \
  || fail "(2974) design-outline.md missing outline banner"
grep -Fq '⏩ 1d.7: outline — skipped (already approved; .outline-approved present)' "$DESIGN_OUTLINE_MD" \
  || fail "(2974) design-outline.md missing approved-sentinel skip breadcrumb"
# shellcheck disable=SC2016 # literal env var reference pinned in markdown
grep -Fq '$DESIGN_TMPDIR/.outline-approved' "$DESIGN_OUTLINE_MD" \
  || fail "(2974) design-outline.md missing .outline-approved sentinel reference"
grep -Fq 'proceed to Step 2a' "$DESIGN_OUTLINE_MD" \
  || fail "(2974) design-outline.md missing Step 2a skip handoff"
grep -Fq 'approved outline + existing plan; continue to Step 1e Gate A post-plan path' "$DESIGN_OUTLINE_MD" \
  || fail "(2974) design-outline.md missing stale-sentinel post-plan recovery guard"
grep -Fq 'plan already exists; continue to Step 1e Gate A post-plan path even without .outline-approved' "$DESIGN_OUTLINE_MD" \
  || fail "(2974) design-outline.md missing missing-sentinel post-plan recovery guard"
grep -Fq 'continue directly to **Step 1e Gate A**' "$DESIGN_OUTLINE_MD" \
  || fail "(2974) design-outline.md missing explicit Step 1e successor for existing-plan skips"
# shellcheck disable=SC2016 # Markdown literal includes backticks and emoji intentionally.
grep -Fq 'print `✅ 1d.7: outline approved — proceeding to sketches`' "$DESIGN_OUTLINE_MD" \
  || fail "(2974) design-outline.md missing outline-approve acknowledgment breadcrumb"
grep -Fq 'This sentinel is written **only** on explicit Approve.' "$DESIGN_OUTLINE_MD" \
  || fail "(2974) design-outline.md must pin approve-only sentinel writes"
grep -Fq 'The already-planned ad-hoc Q&A-only branch does **not** invoke this file.' "$DESIGN_OUTLINE_MD" \
  || fail "(2974) design-outline.md must exclude ad-hoc Q&A-only runs from outline gating"
if grep -Fq 'proceed to Step 1e' "$DESIGN_OUTLINE_MD"; then
  fail "(2974) design-outline.md must not hand off outline approval to Step 1e"
fi
grep -Fq '1c→1d→1d.5→1d.7→2a→2a.5→2b→2b.5→3→3.5→3b→4→4b→5→5a→5b→5c.1→5c.5→5c.7→5c.8→6' "$SKILL_MD" \
  || fail "(2974) SKILL.md missing updated anti-halt sequence"
if grep -Fq '1c→1d→1d.5→1e' "$SKILL_MD"; then
  fail "(2974) SKILL.md still contains stale 1d.5→1e anti-halt sequence"
fi
grep -Fq '**Narrow exception — Step 1d.5 and Step 1d.7 only**' "$SKILL_MD" \
  || fail "(2974) SKILL.md missing Step 1d.5 and Step 1d.7 anti-halt exception"
grep -Fq 'Re-entry-only' "$APPROVAL_MD" \
  || fail "(2974) approval-gates.md Gate A must be re-entry-only"
grep -Fq 'design-outline.md' "$APPROVAL_MD" \
  || fail "(2974) approval-gates.md must cross-reference design-outline.md"
if grep -Fq 'first-time entry from Step 1d / Step 1d.5, proceed to Step 2a' "$APPROVAL_MD"; then
  fail "(2974) approval-gates.md still contains stale first-time Gate A proceed language"
fi
grep -Fq 'before entering Step **1d.7**' "$BRAINSTORM_MD" \
  || fail "(2974) brainstorm.md missing Step 1d.7 terminal handoff"
if grep -Fq 'before entering Step **1e**' "$BRAINSTORM_MD"; then
  fail "(2974) brainstorm.md still mentions Step 1e terminal handoff"
fi
grep -Fq 'Step 1d.5 (brainstorm panel, when enabled) or Step 1d.7 (outline) when brainstorm is off' "$DISCUSSION_MD" \
  || fail "(2974) discussion-rounds.md missing Step 1d.7 short-circuit/cap successor"
if grep -Fq 'proceed to Step 1e (Gate A)' "$DISCUSSION_MD"; then
  fail "(2974) discussion-rounds.md still routes Step 1d exits to Step 1e"
fi
grep -Fq 'cancelled-outline' "$REPO_ROOT/skills/design/scripts/render-final-summary.sh" \
  || fail "(2974) render-final-summary.sh missing cancelled-outline enum"
# shellcheck disable=SC2016 # Markdown enum literal in SKILL.md
grep -Fq 'cancelled-decompose` | `cancelled-outline` | `cancelled-plan-size-hard' "$SKILL_MD" \
  || fail "(2974) SKILL.md SUMMARY_OUTCOME enum missing cancelled-outline in documented order"
grep -Fq 'first-time entry handled by Step 1d.7; proceed to Step 2a' "$SKILL_MD" \
  || fail "(2974) SKILL.md missing Step 1e defensive entry guard"
grep -Fq 'outline not yet approved; return to Step 1d.7' "$SKILL_MD" \
  || fail "(2974) SKILL.md Step 1e must return pre-plan missing-outline flows to Step 1d.7"
# shellcheck disable=SC2016 # Markdown literal includes a literal env-var reference.
grep -Fq 'When `$DESIGN_TMPDIR/plan.txt` exists, stay on the post-plan gate path — never route back to Step 2a from Step 1e.' "$SKILL_MD" \
  || fail "(2974) SKILL.md Step 1e must not re-enter sketches once plan.txt exists"
# shellcheck disable=SC2016 # Markdown literal includes inline code formatting.
grep -Fq 'run the Gate A re-entry body even when `.outline-approved` is absent' "$SKILL_MD" \
  || fail "(2974) SKILL.md Step 1e must keep existing-plan paths on Gate A even without outline sentinel"
# shellcheck disable=SC2016 # Markdown literal includes a literal env-var reference.
grep -Fq 'exists, is non-empty, **and** `$DESIGN_TMPDIR/.outline-approved` exists' "$SKILL_MD" \
  || fail "(2974) SKILL.md must require .outline-approved for downstream outline consumption"
grep -Fq 'Step 1d sprawl returns to the pre-plan path that re-enters Step 1d.7 outline approval, not Gate A' "$SKILL_MD" \
  || fail "(2974) SKILL.md Step 2b.5 must route Step 1d sprawl back through Step 1d.7"
echo "PASS: (2974) Step 1d.7 outline approval anchors OK"

# Check 21 (#2930): removed manual flag; always-explicit Gate B is pinned above.
# FINDING_2678 removed: YES↔EXONERATE phrase no longer valid after EXONERATE removal (PR #3647).

# Check: voter YES/NO-only instructions pinned in plan-review.md + renderer.
RENDER_VOTER_SH="$REPO_ROOT/skills/shared/scripts/render-voter-prompt.sh"

voter1_line=$(grep -n '^- \*\*Voter 1\*\*' "$PLAN_REVIEW_MD" | head -1 | cut -d: -f1 || true)
[[ -n "$voter1_line" ]] || fail "plan-review.md missing '- **Voter 1**' prompt anchor"
voter1_text=$(sed -n "${voter1_line}p" "$PLAN_REVIEW_MD")
grep -Fq 'YES or NO on proposed modifications' <<< "$voter1_text" \
  || fail "plan-review.md Voter 1 prompt missing YES/NO-only instruction"

shared_line=$(grep -n '^For Codex, Cursor, and their Claude replacement voters' "$PLAN_REVIEW_MD" | head -1 | cut -d: -f1 || true)
[[ -n "$shared_line" ]] || fail "plan-review.md missing shared-voter-prompt anchor"
shared_text=$(sed -n "${shared_line}p" "$PLAN_REVIEW_MD")
grep -Fq 'Vote YES only if' <<< "$shared_text" \
  || fail "plan-review.md shared Voter 2/3 prompt missing YES/NO-only instruction"

grep -Fq 'Vote NO only when the stated problem is not real or not worth raising' "$RENDER_VOTER_SH" \
  || fail "render-voter-prompt.sh missing voter NO-only guard instruction"

echo "PASS: voter YES/NO-only instructions pinned in plan-review.md + renderer"

# Check 19 (#2672): decomposition panel replaces Split-path stub.
DECOMP_REF="$REPO_ROOT/skills/design/references/decompose-panel.md"
[[ -f "$DECOMP_REF" ]] || fail "(19) references/decompose-panel.md missing"
grep -Fq 'decompose-panel-dispatch.sh' "$DECOMP_REF" \
  || fail "(19) decompose-panel.md must retain decompose-panel-dispatch.sh anchor for structure tests"
grep -Fq 'decompose-panel-dispatch.sh' "$SKILL_MD" \
  || fail "(19) SKILL.md Split-path must reference decompose-panel-dispatch.sh"
! grep -q 'decomposition panel is in development' "$SKILL_MD" \
  || fail "(19) SKILL.md must not retain the pre-panel stub string"
echo "PASS: (19) decomposition panel Split-path anchors OK"

# Check 18 (#2702): literal plan-preview header anchors in Step 3 + Gate C prose.
step3_block=$(awk '/^<!-- step:3 /,/^<!-- step:3.5 /' "$SKILL_MD")
printf '%s\n' "$step3_block" | grep -Fq '## Plan Candidate for Review' \
  || fail "(18) SKILL.md Step 3 block missing ## Plan Candidate for Review anchor"
gate_c_block=$(awk '/^## Gate C/,/^## State invariants/' "$APPROVAL_MD")
printf '%s\n' "$gate_c_block" | grep -Fq '## Final Design Plan' \
  || fail "(18) approval-gates.md Gate C block missing ## Final Design Plan anchor"
# Check 20 (#2800): Step 0b title-eligibility filter anchors (extracted to design-route.sh).
grep -Fq 'title_has_lifecycle_reject_prefix' "$DESIGN_ROUTE_SH" \
  || fail "(20) design-route.sh missing title_has_lifecycle_reject_prefix"
grep -Fq 'title_has_archival_report_prefix' "$DESIGN_ROUTE_SH" \
  || fail "(20) design-route.sh missing title_has_archival_report_prefix"
grep -Fq 'title_starts_with_brainstorm' "$DESIGN_ROUTE_SH" \
  || fail "(20) design-route.sh missing title_starts_with_brainstorm"
grep -Fq 'cancelled-title-filter' "$SKILL_MD" \
  || fail "(20) SKILL.md missing cancelled-title-filter enum"
grep -Fq 'issue title starts with managed lifecycle marker' "$DESIGN_ROUTE_SH" \
  || fail "(20) design-route.sh missing lifecycle-reject banner text"
grep -Fq 'issue title matches archival report-prefix' "$DESIGN_ROUTE_SH" \
  || fail "(20) design-route.sh missing archival-report-reject banner text"
grep -Fq 'detected Brainstorm title prefix — auto-enabling brainstorm mode' "$SKILL_MD" \
  || fail "(20) SKILL.md missing brainstorm info banner text"
title_cancel_line=$(grep -n 'cancel-title-filter' "$SKILL_MD" | head -1 | cut -d: -f1 || true)
clarify_line=$(grep -n '^3\. \*\*Clarify loop\*\*' "$SKILL_MD" | head -1 | cut -d: -f1 || true)
[[ -n "$title_cancel_line" && -n "$clarify_line" ]] \
  || fail "(20) Step 0b cancel-title-filter / clarify anchors missing"
if (( title_cancel_line >= clarify_line )); then
  fail "(20) Step 0b orchestrator must handle cancel-title-filter before clarify branch"
fi
echo "PASS: (20) Step 0b title-eligibility filter anchors OK"

# Check 21 (#2959): pause/resume prelude and completion sentinels.
extract_bash_fence_after_marker() {
  local file="$1" marker="$2"
  awk -v marker="$marker" '
    BEGIN { start=0; in_fence=0 }
    index($0, marker) { start=1; next }
    start && /^[[:space:]]*```bash[[:space:]]*$/ { in_fence=1; next }
    start && in_fence && /^[[:space:]]*```[[:space:]]*$/ { exit }
    start && in_fence { print }
  ' "$file"
}

extract_bash_fence_containing() {
  local file="$1" needle="$2" after_marker="${3:-}"
  awk -v needle="$needle" -v marker="$after_marker" '
    BEGIN { start=(marker == ""); in_fence=0 }
    marker != "" && index($0, marker) { start=1; next }
    start && /^[[:space:]]*```bash[[:space:]]*$/ { in_fence=1; buf=""; next }
    start && in_fence && /^[[:space:]]*```[[:space:]]*$/ {
      if (index(buf, needle) > 0) {
        printf "%s", buf
        exit
      }
      in_fence=0
      next
    }
    start && in_fence { buf = buf $0 "\n" }
  ' "$file"
}

assert_fence_write_before_pause() {
  local fence_file="$1" step_token="$2" label="$3" after_pause="${4:-false}"
  local sentinel source_line pause_line sentinel_line
  sentinel=": > \"\$DESIGN_TMPDIR/.completed/${step_token}\""
  grep -Fq "$sentinel" "$fence_file" \
    || fail "$label missing ${step_token} sentinel write"
  source_line=$(grep -nF 'current-design-env-$PPID.sh' "$fence_file" | head -1 | cut -d: -f1 || true)
  pause_line=$(grep -nF 'design-pause-save.sh' "$fence_file" | head -1 | cut -d: -f1 || true)
  sentinel_line=$(grep -nF "$sentinel" "$fence_file" | head -1 | cut -d: -f1 || true)
  [[ -n "$source_line" && -n "$pause_line" && -n "$sentinel_line" ]] \
    || fail "$label missing source-env, pause-check, or ${step_token} sentinel line"
  if [[ "$after_pause" == true ]]; then
    (( source_line < pause_line && pause_line < sentinel_line )) \
      || fail "$label ${step_token} must be written after pause-check"
  else
    (( source_line < sentinel_line && sentinel_line < pause_line )) \
      || fail "$label ${step_token} must be after source-env and before pause-check"
  fi
}

assert_qa_only_contiguous_prefix() {
  local tmp
  tmp=$(mktemp "${TMPDIR:-/tmp}/qa-only-prefix.XXXXXX")
  extract_bash_fence_after_marker "$SKILL_MD" 'Before the terminal already-planned hygiene' >"$tmp"
  [[ -s "$tmp" ]] || fail '(21) Step 0b Q&A-only prefix fence missing'
  assert_fence_write_before_pause "$tmp" 'step-1c' 'Step 0b Q&A-only prefix'
  assert_fence_write_before_pause "$tmp" 'step-1d' 'Step 0b Q&A-only prefix'
  assert_fence_write_before_pause "$tmp" 'step-1d.5' 'Step 0b Q&A-only prefix'
  rm -f "$tmp"
}

assert_step_sentinel_inside_guard() {
  local fence_file="$1" step_token="$2" guard_pat="$3" label="$4"
  local guard_line closing_line sentinel_line sentinel
  sentinel=": > \"\$DESIGN_TMPDIR/.completed/${step_token}\""
  guard_line=$(grep -nF "$guard_pat" "$fence_file" | head -1 | cut -d: -f1 || true)
  sentinel_line=$(grep -nF "$sentinel" "$fence_file" | head -1 | cut -d: -f1 || true)
  closing_line=$(awk -v start="${guard_line:-0}" 'NR > start && $0 ~ /^[[:space:]]*fi[[:space:]]*$/ { line=NR } END { if (line) print line }' "$fence_file")
  [[ -n "$guard_line" && -n "$sentinel_line" && -n "$closing_line" ]] \
    || fail "$label missing guard or ${step_token} sentinel for guard-scoped check"
  (( guard_line < sentinel_line && sentinel_line < closing_line )) \
    || fail "$label ${step_token} sentinel must stay inside guard block"
}

assert_folded_sentinel_writes() {
  local tmp
  tmp=$(mktemp "${TMPDIR:-/tmp}/folded-sentinel.XXXXXX")

  assert_qa_only_contiguous_prefix

  extract_bash_fence_after_marker "$SKILL_MD" '<!-- step:1d.5' >"$tmp"
  [[ -s "$tmp" ]] || fail '(21) Step 1d.5 prelude fence missing'
  assert_fence_write_before_pause "$tmp" 'step-1c' 'Step 1d.5 prelude'
  assert_fence_write_before_pause "$tmp" 'step-1d' 'Step 1d.5 prelude'

  extract_bash_fence_after_marker "$SKILL_MD" '<!-- step:2a —' >"$tmp"
  [[ -s "$tmp" ]] || fail '(21) Step 2a entry fence missing'
  assert_fence_write_before_pause "$tmp" 'step-1c' 'Step 2a entry'
  assert_fence_write_before_pause "$tmp" 'step-1d' 'Step 2a entry'
  assert_fence_write_before_pause "$tmp" 'step-1d.7' 'Step 2a entry'
  assert_fence_write_before_pause "$tmp" 'step-1e' 'Step 2a entry'
  grep -Fq '_brainstorm_requested' "$tmp" \
    || fail '(21) Step 2a entry missing brainstorm_requested guard for step-1d.5'
  grep -Fq ': > "$DESIGN_TMPDIR/.completed/step-1d.5"' "$tmp" \
    || fail '(21) Step 2a entry missing conditional step-1d.5 write'
  assert_step_sentinel_inside_guard "$tmp" 'step-1d.5' 'if [ "$_brainstorm_requested" != true ]; then' 'Step 2a entry'
  assert_step_sentinel_inside_guard "$tmp" 'step-2a' 'if [ "$_design_classification" = SIMPLE ]; then' 'Step 2a entry'
  assert_step_sentinel_inside_guard "$tmp" 'step-2a.5' 'if [ "$_design_classification" = SIMPLE ]; then' 'Step 2a entry'

  extract_bash_fence_after_marker "$SKILL_MD" '<!-- step:3 —' >"$tmp"
  [[ -s "$tmp" ]] || fail '(21) Step 3 entry fence missing'
  grep -Fq 'design-step3-state.sh" --design-tmpdir "$DESIGN_TMPDIR" --direct-review-entry' "$tmp" \
    || fail '(21) Step 3 entry missing direct-review state helper'
  helper_line=$(grep -nF 'design-step3-state.sh" --design-tmpdir "$DESIGN_TMPDIR" --direct-review-entry' "$tmp" | head -1 | cut -d: -f1 || true)
  pause_line=$(grep -nF '.pause-requested' "$tmp" | head -1 | cut -d: -f1 || true)
  [[ -n "$helper_line" && -n "$pause_line" && "$helper_line" -lt "$pause_line" ]] \
    || fail 'Step 3 entry direct-review helper must run before pause'

  extract_bash_fence_after_marker "$SKILL_MD" '### 2a.5' >"$tmp"
  [[ -s "$tmp" ]] || fail '(21) Step 2a.5 prelude fence missing'
  grep -Fq 'if [ "$_design_classification" = HARD ]; then' "$tmp" \
    || fail '(21) Step 2a.5 prelude must guard folded step-2a write to HARD'
  assert_fence_write_before_pause "$tmp" 'step-2a' 'Step 2a.5 prelude'
  assert_step_sentinel_inside_guard "$tmp" 'step-2a' 'if [ "$_design_classification" = HARD ]; then' 'Step 2a.5 prelude'

  extract_bash_fence_after_marker "$SKILL_MD" 'zero-sketch degraded fence below' >"$tmp"
  [[ -s "$tmp" ]] || fail '(21) zero-sketch degraded fence missing'
  grep -Fq 'if [ "$_design_classification" = HARD ]; then' "$tmp" \
    || fail '(21) zero-sketch degraded fence must guard Step 2 markers to HARD'
  assert_fence_write_before_pause "$tmp" 'step-2a' 'zero-sketch degraded fence'
  assert_fence_write_before_pause "$tmp" 'step-2a.5' 'zero-sketch degraded fence'
  assert_step_sentinel_inside_guard "$tmp" 'step-2a' 'if [ "$_design_classification" = HARD ]; then' 'zero-sketch degraded fence'
  assert_step_sentinel_inside_guard "$tmp" 'step-2a.5' 'if [ "$_design_classification" = HARD ]; then' 'zero-sketch degraded fence'

  extract_bash_fence_after_marker "$SKILL_MD" '<!-- step:2b —' >"$tmp"
  [[ -s "$tmp" ]] || fail '(21) Step 2b prelude fence missing'
  grep -Fq 'if [ "$_design_classification" = HARD ]; then' "$tmp" \
    || fail '(21) Step 2b prelude must guard Step 2 repair writes to HARD'
  assert_fence_write_before_pause "$tmp" 'step-2a' 'Step 2b prelude'
  assert_fence_write_before_pause "$tmp" 'step-2a.5' 'Step 2b prelude'
  assert_step_sentinel_inside_guard "$tmp" 'step-2a' 'if [ "$_design_classification" = HARD ]; then' 'Step 2b prelude'
  assert_step_sentinel_inside_guard "$tmp" 'step-2a.5' 'if [ "$_design_classification" = HARD ]; then' 'Step 2b prelude'

  extract_bash_fence_after_marker "$SKILL_MD" '<!-- step:3.5' >"$tmp"
  [[ -s "$tmp" ]] || fail '(21) Step 3.5 prelude fence missing'
  assert_fence_write_before_pause "$tmp" 'step-3' 'Step 3.5 prelude'

  extract_bash_fence_after_marker "$SKILL_MD" '<!-- step:3b' >"$tmp"
  [[ -s "$tmp" ]] || fail '(21) Step 3b entry fence missing'
  assert_fence_write_before_pause "$tmp" 'step-3.5' 'Step 3b entry'

  extract_bash_fence_after_marker "$SKILL_MD" '<!-- step:5 —' >"$tmp"
  [[ -s "$tmp" ]] || fail '(21) Step 5 prelude fence missing'
  assert_fence_write_before_pause "$tmp" 'step-4b' 'Step 5 prelude'

  extract_bash_fence_containing "$SKILL_MD" ': > "$DESIGN_TMPDIR/.completed/step-5d"' '<!-- step:6' >"$tmp"
  [[ -s "$tmp" ]] || fail '(21) Step 6 prelude fence missing step-5d write'
  ! grep -Fq 'cleanup-tmpdir.sh' "$tmp" \
    || fail '(21) Step 6 prelude must not run cleanup-tmpdir.sh'
  assert_fence_write_before_pause "$tmp" 'step-5d' 'Step 6 prelude'

  extract_bash_fence_containing "$SKILL_MD" 'cleanup-tmpdir.sh' '<!-- step:6' >"$tmp"
  [[ -s "$tmp" ]] || fail '(21) Step 6 cleanup fence missing'
  assert_fence_write_before_pause "$tmp" 'step-6' 'Step 6 cleanup fence' true

  extract_bash_fence_containing "$SKILL_MD" 'design-publish.sh' '### 5c —' >"$tmp"
  [[ -s "$tmp" ]] || fail '(21) Step 5c design-publish fence missing'
  grep -Fq '[[ "${PLAN_WRITE_OK:-}" == true ]]' "$tmp" \
    || fail '(21) Step 5c design-publish fence missing PLAN_WRITE_OK=true gate'
  assert_step_sentinel_inside_guard "$tmp" 'step-5c' 'if [[ "${PLAN_WRITE_OK:-}" == true ]]; then' 'Step 5c design-publish fence'
  parse_line=$(grep -nF 'done <<<"${_publish_out:-}"' "$tmp" | head -1 | cut -d: -f1 || true)
  sentinel_line=$(grep -nF ': > "$DESIGN_TMPDIR/.completed/step-5c"' "$tmp" | head -1 | cut -d: -f1 || true)
  pause_line=$(grep -nF 'design-pause-save.sh' "$tmp" | head -1 | cut -d: -f1 || true)
  [[ -n "$parse_line" && -n "$sentinel_line" && -n "$pause_line" ]] \
    || fail '(21) Step 5c design-publish fence missing parse/pause/sentinel line'
  (( pause_line < parse_line && parse_line < sentinel_line )) \
    || fail '(21) Step 5c sentinel must be after parse and inside publish fence'

  rm -f "$tmp"
}

assert_deleted_prelude_guards() {
  local start_line end_line region
  start_line=$(grep -nF '<!-- step:1c' "$SKILL_MD" | head -1 | cut -d: -f1 || true)
  end_line=$(grep -nF '<!-- step:1d' "$SKILL_MD" | head -1 | cut -d: -f1 || true)
  [[ -n "$start_line" && -n "$end_line" ]] || fail '(21) Step 1c region anchors missing'
  region=$(sed -n "${start_line},$((end_line - 1))p" "$SKILL_MD")
  grep -Fq 'design Step 1c — questions' <<<"$region" \
    && fail '(21) Step 1c must not retain standalone timing-only prelude fence'

  start_line=$(grep -nF '<!-- step:1d —' "$SKILL_MD" | head -1 | cut -d: -f1 || true)
  end_line=$(grep -nF '<!-- step:1d.5' "$SKILL_MD" | head -1 | cut -d: -f1 || true)
  [[ -n "$start_line" && -n "$end_line" ]] || fail '(21) Step 1d region anchors missing'
  region=$(sed -n "${start_line},$((end_line - 1))p" "$SKILL_MD")
  grep -Fq 'design Step 1d — discussion r1' <<<"$region" \
    && fail '(21) Step 1d must not retain standalone timing-only prelude fence'

  start_line=$(grep -nF '<!-- step:1d.7' "$SKILL_MD" | head -1 | cut -d: -f1 || true)
  end_line=$(grep -nF '<!-- step:1e' "$SKILL_MD" | head -1 | cut -d: -f1 || true)
  [[ -n "$start_line" && -n "$end_line" ]] || fail '(21) Step 1d.7 region anchors missing'
  region=$(sed -n "${start_line},$((end_line - 1))p" "$SKILL_MD")
  grep -Fq 'design Step 1d.7 — outline' <<<"$region" \
    && fail '(21) Step 1d.7 must not retain standalone timing-only prelude fence'

  start_line=$(grep -nF '<!-- step:1e' "$SKILL_MD" | head -1 | cut -d: -f1 || true)
  end_line=$(grep -nF '<!-- step:2a —' "$SKILL_MD" | head -1 | cut -d: -f1 || true)
  [[ -n "$start_line" && -n "$end_line" ]] || fail '(21) Step 1e region anchors missing'
  region=$(sed -n "${start_line},$((end_line - 1))p" "$SKILL_MD")
  grep -Fq 'design Step 1e — gate A' <<<"$region" \
    && fail '(21) Step 1e must not retain standalone timing-only prelude fence'

  grep -Fq 'design Step 1d.5 — brainstorm' "$SKILL_MD" \
    || fail '(21) Step 1d.5 prelude timing mark must remain'
  grep -Fq 'design folded discussion block' "$SKILL_MD" \
    || fail '(21) Step 0c folded discussion block timing mark missing'
  grep -Fq 'When Step 1d.5 finishes or is skipped by its entry guard' "$SKILL_MD" \
    || fail '(21) Step 1d.5 boundary-local step-1d.5 write prose missing'
  grep -Fq ': > "$DESIGN_TMPDIR/.completed/step-1d.5"' "$SKILL_MD" \
    || fail '(21) Step 1d.5 boundary-local step-1d.5 write missing'
}

assert_step3b_diagram_branches() {
  local tmp rm_line skipped_line
  tmp=$(mktemp "${TMPDIR:-/tmp}/step3b-diagram.XXXXXX")

  extract_bash_fence_after_marker "$SKILL_MD" 'branch-local skip fence below' >"$tmp"
  [[ -s "$tmp" ]] || fail '(21) Step 3b skip-path fence missing'
  grep -Fq 'architecture-diagram.skipped' "$tmp" \
    || fail '(21) Step 3b skip-path fence missing architecture-diagram.skipped write'
  grep -Fq 'rm -f "$DESIGN_TMPDIR/architecture-diagram.md"' "$tmp" \
    || fail '(21) Step 3b skip-path fence must rm diagram files before .skipped write'
  rm_line=$(grep -nF 'rm -f "$DESIGN_TMPDIR/architecture-diagram.md"' "$tmp" | head -1 | cut -d: -f1)
  skipped_line=$(grep -nF ': > "$DESIGN_TMPDIR/architecture-diagram.skipped"' "$tmp" | head -1 | cut -d: -f1)
  (( rm_line < skipped_line )) \
    || fail '(21) Step 3b skip-path fence must rm before architecture-diagram.skipped write'

  extract_bash_fence_after_marker "$SKILL_MD" 'architectural entry cleanup fence below' >"$tmp"
  [[ -s "$tmp" ]] || fail '(21) Step 3b architectural entry fence missing'
  grep -Fq 'architecture-diagram.skipped' "$tmp" \
    || fail '(21) Step 3b architectural entry must rm architecture-diagram.skipped'

  extract_bash_fence_containing "$SKILL_MD" 'ACTION=FINALIZE' '<!-- step:3b' >"$tmp"
  [[ -s "$tmp" ]] || fail '(21) Step 3b FINALIZE boundary fence missing'
  ! grep -Fq 'architecture-diagram.skipped' "$tmp" \
    || fail '(21) Step 3b FINALIZE boundary must not write architecture-diagram.skipped'

  rm -f "$tmp"
}

assert_backward_reentry_guards() {
  local tmp
  tmp=$(mktemp "${TMPDIR:-/tmp}/backward-reentry.XXXXXX")

  extract_bash_fence_after_marker "$SKILL_MD" 'Gate B(c) / Gate C(b) re-entry only' >"$tmp"
  [[ -s "$tmp" ]] || fail '(21) Gate B/C Step 1e re-entry fence missing'
  for step in step-1e step-2a step-2a.5 step-2b step-2b.5 step-3 step-3.5 step-3b step-4 step-4b; do
    grep -Fq "$step" "$tmp" \
      || fail "(21) Gate B/C re-entry fence missing stale clear for ${step}"
  done

  extract_bash_fence_after_marker "$SKILL_MD" '<!-- step:3 —' >"$tmp"
  grep -Fq 'design-step3-state.sh" --design-tmpdir "$DESIGN_TMPDIR" --direct-review-entry' "$tmp" \
    || fail '(21) Step 3 entry must delegate direct-review restore to executable helper'
  grep -Fq 'design-step3-state.sh --direct-review-entry' "$SKILL_MD" \
    || fail '(21) Step 3 direct-review table/prose missing helper contract'

  rm -f "$tmp"
}

assert_publish_fence_guards() {
  local tmp
  tmp=$(mktemp "${TMPDIR:-/tmp}/publish-fence.XXXXXX")

  extract_bash_fence_containing "$SKILL_MD" 'design-publish.sh' '### 5c —' >"$tmp"
  [[ -s "$tmp" ]] || fail '(21) design-publish fence missing'
  grep -nF 'current-design-env-$PPID.sh' "$tmp" >/dev/null \
    || fail '(21) design-publish fence missing source-env'
  grep -nF 'design-pause-save.sh' "$tmp" >/dev/null \
    || fail '(21) design-publish fence missing pause-check'
  local source_line pause_line
  source_line=$(grep -nF 'current-design-env-$PPID.sh' "$tmp" | head -1 | cut -d: -f1)
  pause_line=$(grep -nF 'design-pause-save.sh' "$tmp" | head -1 | cut -d: -f1)
  (( source_line < pause_line )) \
    || fail '(21) design-publish fence pause-check must follow source-env'
  ! grep -Fq ': > "$DESIGN_TMPDIR/.completed/step-5b"' "$tmp" \
    || fail '(21) design-publish fence must not write step-5b'
  grep -Fq '[[ "${PLAN_WRITE_OK:-}" == true ]]' "$tmp" \
    || fail '(21) design-publish fence missing PLAN_WRITE_OK=true step-5c guard'
  grep -Fq ': > "$DESIGN_TMPDIR/.completed/step-5c"' "$tmp" \
    || fail '(21) design-publish fence must write step-5c after PLAN_WRITE_OK parse'

  extract_bash_fence_after_marker "$SKILL_MD" 'Mechanical Gate C plan emit' >"$tmp"
  [[ -s "$tmp" ]] || fail '(21) Gate C preview fence missing'
  ! grep -Fq ': > "$DESIGN_TMPDIR/.completed/step-4"' "$tmp" \
    || fail '(21) Gate C preview fence must not write step-4'

  rm -f "$tmp"
}

assert_bash_fences_have_pause_check() {
  local missing
  missing=$(awk '
    /<!-- step:1c/ { start=1; in_fence=0 }
    start && /^[[:space:]]*```bash[[:space:]]*$/ { in_fence=1; saw_source=0; saw_pause=0; next }
    start && in_fence && /^[[:space:]]*```[[:space:]]*$/ {
      if (saw_source && !saw_pause) print source_line
      in_fence=0
      next
    }
    start && in_fence && /current-design-env-\$PPID\.sh/ {
      saw_source=1
      source_line=NR
      next
    }
    start && in_fence && saw_source && /design-pause-save\.sh/ { saw_pause=1 }
  ' "$SKILL_MD")
  [[ -z "$missing" ]] || fail "(21) current-design-env source lines missing pause-check after lines: $missing"
}

assert_step_completion_sentinels() {
  local step start_pat end_pat start_line end_line section
  for step in 0c 1d.5 2b 2b.5 3b 4 5b; do
    case "$step" in
      0c) start_pat='### 0c —'; end_pat='<!-- step:1c' ;;
      1d.5) start_pat='<!-- step:1d.5'; end_pat='<!-- step:1e' ;;
      2b) start_pat='<!-- step:2b —'; end_pat='### Step 2b.5' ;;
      2b.5) start_pat='### Step 2b.5'; end_pat='<!-- step:3' ;;
      3b) start_pat='<!-- step:3b'; end_pat='<!-- step:4 —' ;;
      4) start_pat='<!-- step:4 —'; end_pat='<!-- step:4b' ;;
      5b) start_pat='### 5b'; end_pat='### 5c' ;;
    esac
    start_line=$(grep -nF "$start_pat" "$SKILL_MD" | head -1 | cut -d: -f1 || true)
    [[ -n "$start_line" ]] || fail "(21) SKILL.md missing start anchor for step $step"
    end_line=$(grep -nF "$end_pat" "$SKILL_MD" | head -1 | cut -d: -f1 || true)
    [[ -n "$end_line" ]] || fail "(21) SKILL.md missing end anchor for step $step"
    section=$(sed -n "${start_line},$((end_line - 1))p" "$SKILL_MD")
    printf '%s\n' "$section" | grep -Fq ".completed/step-$step" \
      || fail "(21) SKILL.md missing step-local .completed sentinel for step $step"
  done
  assert_gate_b_bypass_branch_sentinels "$SKILL_MD"
}

assert_bash_fences_have_pause_check
assert_step_completion_sentinels
assert_folded_sentinel_writes
assert_deleted_prelude_guards
assert_step3b_diagram_branches
assert_backward_reentry_guards
assert_publish_fence_guards
echo "PASS: (21) Phase 7 folded-sentinel contract OK"
grep -Fq 'design-route.sh' "$SKILL_MD" \
  || fail "(21) SKILL.md missing design-route.sh invocation"
grep -Fq 'design-pause-load.sh' "$DESIGN_ROUTE_SH" \
  || fail "(21) design-route.sh missing design-pause-load.sh invocation"
grep -Fq 'write-design-current-env.sh' "$SKILL_MD" \
  || fail "(21) SKILL.md missing resume env refresh via write-design-current-env.sh"
grep -Fq 'write-design-current-env.sh' "$DESIGN_INIT_SH" \
  || fail "(21) design-init-runparams.sh must refresh env before rename (single refresh)"
echo "PASS: (21) /design pause/resume structure anchors OK"

# Checks 24-26 (#2935): /design same-session re-entry guard pins.
grep -Fq 'title_has_lifecycle_reject_prefix' "$DESIGN_ROUTE_SH" \
  || fail "(24) design-route.sh missing title_has_lifecycle_reject_prefix"
grep -Fq 'design_reentry_marker_hit' "$DESIGN_ROUTE_SH" \
  || fail "(24) design-route.sh missing design_reentry_marker_hit"
step0b_reentry_order=$(awk '
  /^### 0b / { in0b=1; next }
  /^### Final summary block$/ && in0b { in0b=0 }
  in0b && /cancel-title-filter/ && !title { title=NR }
  in0b && /cancel-reentry-guard/ && !guard { guard=NR }
  in0b && /^3\. \*\*Clarify loop\*\*/ && !clarify { clarify=NR }
  END {
    if (!title || !guard || !clarify) exit 2
    if (!(title < guard && guard < clarify)) exit 1
  }
' "$SKILL_MD" || echo "$?")
case "${step0b_reentry_order:-0}" in
  0) ;;
  1|2) fail "(24) SKILL.md missing cancel-title-filter / cancel-reentry-guard orchestrator branches OR clarify ordering regression" ;;
  *) fail "(24) unexpected Step 0b re-entry guard ordering check exit: ${step0b_reentry_order:-?}" ;;
esac

publish_marker_line=$(grep -nF 'design_reentry_marker_write' "$DESIGN_PUBLISH_SH" | head -1 | cut -d: -f1 || true)
publish_rename_line=$(grep -n 'tracking-issue-write.sh' "$DESIGN_PUBLISH_SH" | grep 'state designed' | head -1 | cut -d: -f1 || true)
[[ -n "$publish_marker_line" && -n "$publish_log_line" && "$publish_log_line" -lt "$publish_marker_line" ]] \
  || fail "(25) design-publish.sh design_reentry_marker_write must run only after design-log-publish.sh"
[[ -n "$publish_marker_line" && -n "$publish_rename_line" && "$publish_rename_line" -lt "$publish_marker_line" ]] \
  || fail "(25) design-publish.sh design_reentry_marker_write must follow tracking-issue-write.sh rename --state designed"
# shellcheck disable=SC2016 # Script literal intentionally checks unexpanded parameter syntax.
grep -Fq '${REPO:+--repo' "$DESIGN_PUBLISH_SH" \
  || fail "(15b) design-publish.sh must forward REPO via \${REPO:+--repo}"
grep -Fq 'design-publish.sh' "$SKILL_MD" \
  || fail "(15b) SKILL.md Step 5c must invoke design-publish.sh"
grep -Fq '.design-publish-result.env' "$SKILL_MD" \
  || fail "(15b) SKILL.md Step 5c must read .design-publish-result.env file-first"
grep -Fq 'design-publish.sh configuration error (exit 2)' "$SKILL_MD" \
  || fail "(15b) SKILL.md Step 5c missing design-publish.sh exit 2 abort prose"
grep -Fq '.completed/step-5c' "$SKILL_MD" \
  || fail "(15b) SKILL.md Step 5c must write .completed/step-5c sentinel"
# shellcheck disable=SC2016 # Markdown literal contains $DESIGN_TMPDIR and backticks intentionally.
grep -Fq 'has already written `step-5c` under the `PLAN_WRITE_OK=true` gate' "$SKILL_MD" \
  || fail "(15b) SKILL.md Step 5c must gate step-5c sentinel on PLAN_WRITE_OK=true"
grep -Fq 'result-env write failed (exit 3)' "$SKILL_MD" \
  || fail "(15b) SKILL.md Step 5c missing design-publish.sh exit 3 result-env WARN prose"
grep -Fq '_publish_rc` is 0, 1, or 3' "$SKILL_MD" \
  || fail "(15b) SKILL.md Step 5c missing exit 3 parse-and-continue contract"
grep -Fq '_publish_rc`=3' "$SKILL_MD" \
  || fail "(15b) SKILL.md Step 5c missing _publish_rc=3 contract"
# shellcheck disable=SC2016 # Script literal intentionally checks unexpanded parameter syntax.
grep -Fq 'if ! "$PLUGIN_ROOT/scripts/plan-block-write.sh"' "$DESIGN_PUBLISH_SH" \
  || fail "(15b) design-publish.sh must use if ! around plan-block-write.sh"
grep -Fq 'export ISSUE_NUMBER' "$DESIGN_PUBLISH_SH" \
  || fail "(15b) design-publish.sh must export ISSUE_NUMBER before render-final-summary.sh"
grep -Fq 'export SESSION_ID' "$DESIGN_PUBLISH_SH" \
  || fail "(15b) design-publish.sh must export SESSION_ID before render-final-summary.sh"
grep -Fq 'render-final-summary.sh' "$DESIGN_PUBLISH_SH" \
  || fail "(15b) design-publish.sh must invoke render-final-summary.sh"
# shellcheck disable=SC2016 # Script literal intentionally checks unexpanded parameter syntax.
grep -Fq 'phase_driver_write_result_env "$RESULT_ENV"' "$DESIGN_PUBLISH_SH" \
  || fail "(15b) design-publish.sh must write result env via phase_driver_write_result_env"
# shellcheck disable=SC2016 # Script literal intentionally checks unexpanded parameter syntax.
grep -Fq '_publish_out=$("$PLUGIN_ROOT/scripts/design-log-publish.sh"' "$DESIGN_PUBLISH_SH" \
  || fail "(15b) design-publish.sh must subshell-capture design-log-publish.sh stdout"
# shellcheck disable=SC2016 # Script literal intentionally checks unexpanded parameter syntax.
grep -Fq '_upsert_out=$("$PLUGIN_ROOT/scripts/upsert-diagrams-comment.sh"' "$DESIGN_PUBLISH_SH" \
  || fail "(15b) design-publish.sh must subshell-capture upsert-diagrams-comment.sh stdout"
grep -Fq '.completed/step-5b' "$DESIGN_PUBLISH_SH" \
  || fail "(15b) design-publish.sh must require .completed/step-5b precondition"
grep -Fq 'exit 1 is the normal plan-block-write failure path' "$SKILL_MD" \
  || fail "(15b) SKILL.md Step 5c missing exit 1 parse-then-branch contract"
grep -Fq '_publish_rc` ∈ {0, 1, 3}' "$SKILL_MD" \
  || fail "(15b) SKILL.md Step 5c missing driver exit-code contract for rc 0, 1, or 3"
# shellcheck disable=SC2016
grep -Fq 'do not abort solely because `_publish_rc`=1' "$SKILL_MD" \
  || fail "(15b) SKILL.md Step 5c must not abort solely on driver exit 1"
# shellcheck disable=SC2016
grep -Fq '"${_publish_rc:-0}" -ne 3' "$SKILL_MD" \
  || fail "(15b) SKILL.md Step 5c unexpected-rc guard must exclude exit 3"

grep -Fq '**⚠ /design: refusing spurious re-entry — guard=session-cache' "$DESIGN_ROUTE_SH" \
  || fail "(26) design-route.sh missing literal session-cache banner"
grep -Fq 'delete %s to override.**' "$DESIGN_ROUTE_SH" \
  || fail "(26) design-route.sh must preserve delete-path override hint in the session-cache banner literal"
# shellcheck disable=SC2016
grep -Fq '"$ISSUE" "$CLAUDE_PID" "$MARKER_AGE" "$MARKER_TTL" "$MARKER_REMAINING" "$DESIGN_REENTRY_MARKER_PATH"' "$DESIGN_ROUTE_SH" \
  || fail "(26) design-route.sh session-cache banner must pass DESIGN_REENTRY_MARKER_PATH to delete-path placeholder"
echo "PASS: (24-26) Step 0b/5c re-entry guard anchors OK"

# Check FINDING_2667 (#2667): Gate B severity precedence prose in approval-gates.md.
contains "$APPROVAL_MD" 'important → High' '(FINDING_2667) approval-gates.md missing important → High mapping'
contains "$APPROVAL_MD" 'latent → Medium' '(FINDING_2667) approval-gates.md missing latent → Medium mapping'
contains "$APPROVAL_MD" 'nit → Low' '(FINDING_2667) approval-gates.md missing nit → Low mapping'
# shellcheck disable=SC2016 # Markdown literal contains backticks intentionally.
contains "$APPROVAL_MD" 'When **any** accepted finding lacks that structured `- **Severity**:` line' \
  '(FINDING_2667) approval-gates.md missing all-or-nothing Concern-text fallback when structured Severity absent'
echo "PASS: FINDING_2667 — Gate B severity precedence prose OK"

# Check FINDING_2667_TEMPLATE (#2667): Accepted FINDING_N template field labels in plan-review.md.
finding_template_start=$(grep -n '^### Accepted FINDING_N template' "$PLAN_REVIEW_MD" | head -1 | cut -d: -f1 || true)
finding_template_end=$(grep -n '^### Accepted OOS format' "$PLAN_REVIEW_MD" | head -1 | cut -d: -f1 || true)
[[ -n "$finding_template_start" && -n "$finding_template_end" && "$finding_template_end" -gt "$finding_template_start" ]] \
  || fail "(FINDING_2667_TEMPLATE) could not locate FINDING_N template block in plan-review.md"
finding_template_block=$(sed -n "${finding_template_start},${finding_template_end}p" "$PLAN_REVIEW_MD")
for _label in \
  '- **Reviewer(s)**:' \
  '- **Severity**:' \
  '- **Focus area**:' \
  '- **Location**:' \
  '- **Concern**:' \
  '- **Proposed resolution**:'; do
  grep -Fq -- "$_label" <<< "$finding_template_block" \
    || fail "(FINDING_2667_TEMPLATE) plan-review.md FINDING_N template missing label: $_label"
done
echo "PASS: FINDING_2667_TEMPLATE — FINDING_N template six-field label set OK"

contains "$DESIGN_POSTPLAN_EMIT_SH" 'snapshot-plan-round.sh' 'design-postplan-emit.sh missing snapshot-plan-round'
contains "$DESIGN_POSTPLAN_EMIT_SH" 'write-original --design-tmpdir' 'design-postplan-emit.sh missing write-original invocation'
contains "$SKILL_MD" 'plan-review-round-cursor.txt' 'SKILL.md missing plan-review-round-cursor reference'
# shellcheck disable=SC2016 # Script literal intentionally checks unexpanded parameter syntax.
contains "$RUN_STEP3_SH" '--round-num "$ROUND_NUM"' 'run-step3-review.sh missing --round-num ROUND_NUM to plan-review-loop'
contains "$RUN_STEP3_SH" '--prune-round-num "$STEP3_REVIEW_ROUND_NUM"' 'run-step3-review.sh missing --prune-round-num STEP3_REVIEW_ROUND_NUM to plan-review-loop'
contains "$SKILL_MD" 'restores the explicit per-round prompt (Apply all / Go through each / Switch to discussion mode)' 'SKILL.md missing --approve explicit Gate B settle path'
contains "$SKILL_MD" 'auto-applies** every accepted in-scope finding with no' 'SKILL.md missing Gate B auto-apply default routing pin'
# shellcheck disable=SC2016 # backticks and $ tokens are literal markdown pins
contains "$APPROVAL_MD" 'refresh the active Step 3 result state (including `.step3-plan-review-result.env`) before continuing to Gate B as complete-equivalent' 'approval-gates.md missing MainAgent re-tally Step 3 state refresh pin'
# shellcheck disable=SC2016 # backticks and $ tokens are literal markdown pins
contains "$SKILL_MD" 'APPROVE_REQUESTED=' 'SKILL.md missing Gate B approve_requested read in Step 3.5 fence'
contains "$APPROVAL_MD" 'approve_requested=false' 'approval-gates.md missing Gate B approve_requested default branch'
# shellcheck disable=SC2016 # backticks are literal markdown pins
contains "$APPROVAL_MD" 'restores the pre-#3512 auto-apply behavior' 'approval-gates.md missing Gate B pre-#3512 auto-apply restoration note'
# shellcheck disable=SC2016 # backticks and $ tokens are literal markdown pins
contains "$SKILL_MD" 'so both `.step3-plan-review-result.env` and `.step3-review-result.env` are refreshed through `larch_scope_anchor_retally_handoff_value` before entering Gate B' 'SKILL.md missing MainAgent re-tally state refresh pin'
# shellcheck disable=SC2016 # $ tokens are literal markdown pins
contains "$SKILL_MD" '--findings-classification-out "$DESIGN_TMPDIR/plan-review/round-${ROUNDS_COMPLETED:-$ROUND_NUM}/findings-classification.tsv"' 'SKILL.md missing MainAgent re-tally findings-classification-out pin'
# shellcheck disable=SC2016 # backticks are literal markdown pins
contains "$APPROVAL_MD" 'Apply-pipeline prompts under auto-apply' 'approval-gates.md missing auto-apply size-brake (Component C) coverage'
# shellcheck disable=SC2016 # backticks are literal markdown pins
for _bypass_line in \
  "$(grep -F 'Gate-B-bypass short-circuits (' "$SKILL_MD")" \
  "$(grep -F 'Gate-B-bypass short-circuits (' "$APPROVAL_MD")" \
  "$(grep -F 'When `LOOP_STATUS` is `tally-error`' "$APPROVAL_MD")" \
  "$(grep -F 'Step 3 bypasses such as `LOOP_STATUS=cap-reached`' "$APPROVAL_MD")" \
  "$(grep -F 'If `LOOP_STATUS` is `tally-error`' "$SKILL_MD")"
do
  [[ "$_bypass_line" != *'main-agent-vote-required'* ]] || fail 'bypass prose must not include main-agent-vote-required'
  [[ "$_bypass_line" != *'zero-findings-degraded-panel'* ]] || fail 'bypass prose must not include zero-findings-degraded-panel'
done
contains "$MAKEFILE" 'test-snapshot-plan-round' 'Makefile missing test-snapshot-plan-round'

echo "PASS: test-design-structure.sh — structural invariants hold (including security OOS exclusions)"
exit 0
