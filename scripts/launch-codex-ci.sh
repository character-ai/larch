#!/usr/bin/env bash
# launch-codex-ci.sh — Launch Codex for /implement CI-fix subwork.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PLUGIN_ROOT="${CLAUDE_PLUGIN_ROOT:-$(cd "$SCRIPT_DIR/.." && pwd -P)}"

ROLE=""
OUTPUT=""
RUN_ID=""
REPO=""
TIMEOUT="1800"
TIMING_TASK_KIND="codex-ci-fix"

usage() {
    echo "Usage: launch-codex-ci.sh --role fix|resolve-conflict|bump-classify|changelog-draft --output PATH --run-id ID --repo OWNER/REPO [--timeout SECONDS]" >&2
}

die() {
    echo "launch-codex-ci.sh: $1" >&2
    usage
    exit 2
}

while [ $# -gt 0 ]; do
    case "$1" in
        --role) [ $# -ge 2 ] || die "--role requires a value"; ROLE=$2; shift 2 ;;
        --output) [ $# -ge 2 ] || die "--output requires a value"; OUTPUT=$2; shift 2 ;;
        --run-id) [ $# -ge 2 ] || die "--run-id requires a value"; RUN_ID=$2; shift 2 ;;
        --repo) [ $# -ge 2 ] || die "--repo requires a value"; REPO=$2; shift 2 ;;
        --timeout) [ $# -ge 2 ] || die "--timeout requires a value"; TIMEOUT=$2; shift 2 ;;
        --timing-task-kind) [ $# -ge 2 ] || die "--timing-task-kind requires a value"; TIMING_TASK_KIND=$2; shift 2 ;;
        --help) usage; exit 0 ;;
        *) die "unknown flag: $1" ;;
    esac
done

case "$ROLE" in fix|resolve-conflict|bump-classify|changelog-draft) ;; *) die "--role must be fix, resolve-conflict, bump-classify, or changelog-draft" ;; esac
[ -n "$OUTPUT" ] || die "--output is required"
[ -n "$RUN_ID" ] || die "--run-id is required"
[ -n "$REPO" ] || die "--repo is required"
case "$TIMEOUT" in ''|*[!0-9]*|0) die "--timeout must be a positive integer" ;; esac
case "$OUTPUT" in /*) ;; *) die "--output must be an absolute path" ;; esac
case "$OUTPUT" in *[!A-Za-z0-9._/-]*) die "--output contains unsupported characters" ;; esac

PROMPT="You are fixing larch /implement CI subwork.

Role: $ROLE
Repository: $REPO
Failed run id: $RUN_ID
Working directory: $PWD

Inspect the repository and CI logs as needed. Make only the minimal changes required for this role. Do not rewrite history. Do not edit submodules. Leave a concise summary in the final answer."
PROMPT_FILE="${OUTPUT}.prompt"
printf '%s' "$PROMPT" > "$PROMPT_FILE"

MODEL_ARGS_TMP=$(mktemp)
CODEX_HOME_DIR=$(mktemp -d /tmp/larch-codex-ci-home-XXXXXX)
trap 'rm -f "$MODEL_ARGS_TMP"; rm -rf "$CODEX_HOME_DIR"' EXIT
"$SCRIPT_DIR/agent-model-args.sh" --tool codex --with-effort > "$MODEL_ARGS_TMP"
MODEL_ARGS=()
while IFS= read -r arg; do
    MODEL_ARGS+=("$arg")
done < "$MODEL_ARGS_TMP"
if [ -f ~/.codex/auth.json ]; then
    ln -sf "$(cd ~/.codex && pwd)/auth.json" "$CODEX_HOME_DIR/auth.json"
fi
PROJECT_KEY=${PWD//\\/\\\\}
PROJECT_KEY=${PROJECT_KEY//\"/\\\"}
TRUST_CONFIG_ARG="projects.\"$PROJECT_KEY\".trust_level=\"trusted\""

TIMING_START_S=$(date +%s)
LAUNCHER_EXIT=0
CODEX_HOME="$CODEX_HOME_DIR" "$SCRIPT_DIR/run-external-agent.sh" \
    --tool codex \
    --output "$OUTPUT" \
    --timeout "$TIMEOUT" \
    -- \
    codex exec --full-auto -C "$PWD" \
    ${MODEL_ARGS[@]+"${MODEL_ARGS[@]}"} \
    -c "$TRUST_CONFIG_ARG" \
    --output-last-message "$OUTPUT" \
    -- \
    "$PROMPT" || LAUNCHER_EXIT=$?

END_S=$(date +%s)
"$PLUGIN_ROOT/scripts/timing-ledger.sh" record-vendor-task \
    --vendor codex \
    --task-kind "$TIMING_TASK_KIND" \
    --start-s "$TIMING_START_S" \
    --end-s "$END_S" \
    --output "$OUTPUT" \
    --exit-code "$LAUNCHER_EXIT" \
    --status "$([ "$LAUNCHER_EXIT" -eq 0 ] && echo complete || echo signal)" >/dev/null 2>&1 || true

TOKENS=$(awk '/^tokens used$/ { getline n; gsub(",","",n); last=n } END { print last }' "${OUTPUT}.diag" "$OUTPUT" 2>/dev/null || true)
if [[ "$TOKENS" =~ ^[0-9]+$ ]]; then
    printf 'TOOL=codex\nTOTAL=%s\nRAW=codex_ci_fix\n' "$TOKENS" > "${OUTPUT}.token-record"
fi

printf 'LAUNCHER_EXIT=%s\nOUTPUT=%s\nTOKEN_RECORD=%s\n' "$LAUNCHER_EXIT" "$OUTPUT" "${OUTPUT}.token-record"
exit 0
