#!/usr/bin/env bash
# step2-implement.sh — Dispatcher for /implement Step 2 (coder selection).
#
# This is the SINGLE entrypoint /implement Step 2 invokes. It is the only place
# that branches on the chosen --coder value. The orchestrator only falls back
# to Claude main-agent Edit/Write when BOTH STATUS=claude_fallback AND
# ORCHESTRATOR_EDIT_AUTHORITY=allowed are present in this script's stdout (the
# pair invariant: AUTH=allowed iff STATUS=claude_fallback). claude_fallback is
# emitted when --coder=claude, when --coder=cursor with --cursor-healthy
# unset/false, or when --coder=gemini with --gemini-healthy unset/false
# (Cursor/Gemini fall back to Claude instead of failing closed); every
# external-implementer outcome (complete / needs_qa / bailed) emits AUTH=forbidden
# instead. See SKILL.md NEVER #10 and the Step 2 entry preconditions matrix.
#
# Coder flag (preferred):
#   --coder claude   → STATUS=claude_fallback (main-agent path)
#   --coder codex    → spawn Codex implementer (default when --coder is omitted)
#   --coder cursor   → spawn Cursor implementer when --cursor-healthy true;
#                      otherwise emits STATUS=claude_fallback so the orchestrator
#                      runs the main-agent code-edit path.
#   --coder gemini   → spawn Gemini implementer when --gemini-healthy true;
#                      otherwise emits STATUS=claude_fallback so the orchestrator
#                      runs the main-agent code-edit path.
#
# Cursor health flag:
#   --cursor-healthy true   → permit --coder cursor to launch Cursor
#   --cursor-healthy false  → --coder cursor falls back to claude_fallback
#   --cursor-healthy ""     → treated as false (falls back to claude_fallback)
#
# Gemini health flag:
#   --gemini-healthy true   → permit --coder gemini to launch Gemini
#   --gemini-healthy false  → --coder gemini falls back to claude_fallback
#   --gemini-healthy ""     → treated as false (falls back to claude_fallback)
#
# Legacy flag (deprecated, accepted for one release):
#   --codex-available true   → maps to --coder codex (stderr deprecation warning)
#   --codex-available false  → maps to --coder claude (stderr deprecation warning)
# Passing both --coder and --codex-available exits 2.
#
# See:
#   - skills/implement/SKILL.md Step 2 (caller)
#   - skills/implement/references/codex-manifest-schema.md (manifest contract)
#   - agents/codex-implementer.md (Codex prompt)
#   - scripts/launch-codex-implement.sh (leaf launcher)
#
# Stdout contract (KEY=VALUE lines, parsed by SKILL.md Step 2):
#   STATUS=<complete|needs_qa|bailed|claude_fallback>
#   MANIFEST=<path>          # set when STATUS=complete or needs_qa, or when
#                            # STATUS=bailed came from a Codex-authored manifest
#                            # (status=bailed in the manifest itself).
#                            # Dispatcher mechanical bails (emit_bailed path)
#                            # do NOT emit MANIFEST=, and on commit-failed
#                            # the manifest files are deleted from $TMPDIR_ARG
#                            # before bail. See step2-implement.md for the
#                            # full per-bucket breakdown.
#   QA_PENDING=<path>        # set when STATUS=needs_qa
#   REASON=<token>           # set when STATUS=bailed
#   TOOL=<codex|cursor|gemini> # set on external implementer paths
#   TRANSCRIPT=<path>        # set when launcher actually ran
#   SIDECAR_LOG=<path>       # set when launcher actually ran
#   ORCHESTRATOR_EDIT_AUTHORITY=<allowed|forbidden>
#                            # ALWAYS emitted on every exit-0 path. `allowed`
#                            # only when STATUS=claude_fallback (the only
#                            # outcome that authorizes main-agent Edit/Write
#                            # at SKILL.md Step 2.4). `forbidden` on every
#                            # external-implementer outcome (complete /
#                            # needs_qa / bailed). See SKILL.md NEVER #10
#                            # and the Step 2 entry preconditions matrix.
#
# Exit code is always 0 unless caller / invocation validation fails (exit 2):
# missing or invalid flag, missing required path, bad enum value,
# or — on the Codex / Cursor / Gemini path — cwd is not inside a git working tree.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

TMPDIR_ARG=""
PLAN_FILE=""
FEATURE_FILE=""
AUTO_MODE=""
CODER=""
CODEX_AVAILABLE=""
CURSOR_HEALTHY_ARG=""
GEMINI_HEALTHY_ARG=""
ANSWERS_FILE=""

while [[ $# -gt 0 ]]; do
    case "$1" in
        --tmpdir)            TMPDIR_ARG="${2:?--tmpdir requires a value}"; shift 2 ;;
        --plan-file)         PLAN_FILE="${2:?--plan-file requires a value}"; shift 2 ;;
        --feature-file)      FEATURE_FILE="${2:?--feature-file requires a value}"; shift 2 ;;
        --auto-mode)         AUTO_MODE="${2:?--auto-mode requires a value}"; shift 2 ;;
        --coder)             CODER="${2:?--coder requires a value}"; shift 2 ;;
        --codex-available)   CODEX_AVAILABLE="${2:?--codex-available requires a value}"; shift 2 ;;
        --cursor-healthy)    CURSOR_HEALTHY_ARG="${2-}"; shift 2 ;;
        --gemini-healthy)    GEMINI_HEALTHY_ARG="${2-}"; shift 2 ;;
        --answers)           ANSWERS_FILE="${2:?--answers requires a value}"; shift 2 ;;
        *) echo "step2-implement.sh: unknown flag: $1" >&2; exit 2 ;;
    esac
done

# Coder selection: --coder is the canonical flag; --codex-available is accepted
# for one release as a deprecated alias. Mutual-exclusion is mandatory because
# the legacy flag sets the same internal state and silent precedence would
# mask operator misconfiguration.
if [[ -n "$CODER" && -n "$CODEX_AVAILABLE" ]]; then
    echo "step2-implement.sh: --coder and --codex-available are mutually exclusive" >&2
    exit 2
fi

if [[ -n "$CODEX_AVAILABLE" ]]; then
    case "$CODEX_AVAILABLE" in
        true)
            echo "step2-implement.sh: WARNING: --codex-available is deprecated; pass --coder codex instead" >&2
            CODER="codex"
            ;;
        false)
            echo "step2-implement.sh: WARNING: --codex-available is deprecated; pass --coder claude instead" >&2
            CODER="claude"
            ;;
        *)
            echo "step2-implement.sh: --codex-available must be 'true' or 'false', got: $CODEX_AVAILABLE" >&2
            exit 2
            ;;
    esac
fi

# Default coder is codex (Codex spawn path) when --coder is omitted.
if [[ -z "$CODER" ]]; then
    CODER="codex"
fi

# shellcheck source=scripts/external-tool-registry.sh
source "$SCRIPT_DIR/../../../scripts/external-tool-registry.sh" || { echo "step2-implement.sh: failed to source external-tool-registry.sh" >&2; exit 2; }
[[ "${LARCH_EXTERNAL_TOOL_REGISTRY_LOADED:-}" == "1" ]] || { echo "step2-implement.sh: external-tool-registry.sh sourced but sentinel missing" >&2; exit 2; }

if ! larch_is_implementer_coder "$CODER"; then
    echo "step2-implement.sh: --coder must be one of $(larch_implementer_coders_braced), got: $CODER" >&2
    exit 2
fi

for var in TMPDIR_ARG PLAN_FILE FEATURE_FILE AUTO_MODE; do
    if [[ -z "${!var}" ]]; then
        flag_lc=$(printf '%s' "$var" | tr '[:upper:]' '[:lower:]' | tr '_' '-')
        echo "step2-implement.sh: --$flag_lc is required" >&2
        exit 2
    fi
done

[[ -d "$TMPDIR_ARG" ]] || { echo "step2-implement.sh: --tmpdir not a directory: $TMPDIR_ARG" >&2; exit 2; }
TMPDIR_ARG=$(cd "$TMPDIR_ARG" && pwd -P)
export IMPLEMENT_TMPDIR="$TMPDIR_ARG"
if [[ -s "$TMPDIR_ARG/session-id" ]]; then
    file_id=$(tr -d '\r\n' < "$TMPDIR_ARG/session-id" 2>/dev/null || true)
    if [[ -n "$file_id" ]]; then
        export LARCH_TOKEN_SESSION_ID="$file_id"
    fi
fi
if [[ -s "$TMPDIR_ARG/claude-source.env" ]]; then
    export LARCH_CLAUDE_SOURCE_FILE="$TMPDIR_ARG/claude-source.env"
fi
[[ -f "$PLAN_FILE" ]]  || { echo "step2-implement.sh: --plan-file not found: $PLAN_FILE" >&2; exit 2; }
[[ -f "$FEATURE_FILE" ]] || { echo "step2-implement.sh: --feature-file not found: $FEATURE_FILE" >&2; exit 2; }
case "$AUTO_MODE" in
    true|false) ;;
    *) echo "step2-implement.sh: --auto-mode must be 'true' or 'false', got: $AUTO_MODE" >&2; exit 2 ;;
esac

if [[ -n "$GEMINI_HEALTHY_ARG" ]]; then
    case "$GEMINI_HEALTHY_ARG" in
        true|false) ;;
        *) echo "step2-implement.sh: --gemini-healthy must be 'true', 'false', or empty, got: $GEMINI_HEALTHY_ARG" >&2; exit 2 ;;
    esac
fi

# Branch 1: coder=claude → emit claude_fallback and return.
# Run BEFORE the PLUGIN_ROOT / REPO_ROOT resolution so the fallback path stays
# git-free (claude_fallback may be invoked outside a git working tree, and it
# needs no plugin assets).
if [[ "$CODER" == "claude" ]]; then
    printf 'STATUS=claude_fallback\n'
    printf 'ORCHESTRATOR_EDIT_AUTHORITY=allowed\n'
    exit 0
fi

# Run after the `claude` early-return so claude path is not affected by
# --cursor-healthy noise. Empty is normalized to false.
if [[ -n "$CURSOR_HEALTHY_ARG" ]]; then
    case "$CURSOR_HEALTHY_ARG" in
        true|false) ;;
        *) echo "step2-implement.sh: --cursor-healthy must be 'true', 'false', or empty, got: $CURSOR_HEALTHY_ARG" >&2; exit 2 ;;
    esac
fi
[[ -z "$CURSOR_HEALTHY_ARG" ]] && CURSOR_HEALTHY_ARG="false"

# Cursor health gate (fall back to claude). Runs before REPO_ROOT resolution
# so that --coder=cursor with --cursor-healthy=false falls back cleanly even
# from outside a git work-tree, mirroring the --coder=claude early-return
# above. The gate runs only on the cursor path; codex/claude are unaffected
# by the value of --cursor-healthy.
if [[ "$CODER" == "cursor" && "$CURSOR_HEALTHY_ARG" != "true" ]]; then
    printf 'STATUS=claude_fallback\n'
    printf 'ORCHESTRATOR_EDIT_AUTHORITY=allowed\n'
    exit 0
fi

[[ -z "$GEMINI_HEALTHY_ARG" ]] && GEMINI_HEALTHY_ARG="false"

# Gemini health gate (fall back to claude). Same ordering as Cursor: the
# fallback path returns before REPO_ROOT lookup and writes no baseline files.
if [[ "$CODER" == "gemini" && "$GEMINI_HEALTHY_ARG" != "true" ]]; then
    printf 'STATUS=claude_fallback\n'
    printf 'ORCHESTRATOR_EDIT_AUTHORITY=allowed\n'
    exit 0
fi

REQUIRES_HEAD_UNCHANGED=false

# ---------------------------------------------------------------------------
# External implementer path. Set up paths inside $TMPDIR_ARG.
# ---------------------------------------------------------------------------

# PLUGIN_ROOT: the plugin tree this script ships in (cache dir when the plugin
# is installed, source repo root when developing on larch itself). Used for
# resolving sibling plugin assets — agent prompt, launcher, redactor.
PLUGIN_ROOT="$(cd "$SCRIPT_DIR/../../.." && pwd)"
# REPO_ROOT: the consumer git repo this run is operating on. Derived from cwd's
# git toplevel because PLUGIN_ROOT (cache snapshot) has no .git when running
# from an installed plugin. All `git -C "$REPO_ROOT"` calls and the
# `.claude-plugin/plugin.json` reference target this root.
REPO_ROOT="$(git rev-parse --show-toplevel 2>/dev/null || true)"
if [[ -z "$REPO_ROOT" ]]; then
    echo "step2-implement.sh: must be invoked from within a git working tree (git rev-parse --show-toplevel failed)" >&2
    exit 2
fi

case "$CODER" in
    codex)
        TOOL_TAG="codex"
        AGENT_PROMPT="$PLUGIN_ROOT/agents/codex-implementer.md"
        LAUNCHER="$PLUGIN_ROOT/scripts/launch-codex-implement.sh"
        RUNTIME_FAILURE_TOKEN="codex-runtime-failure"
        BAILED_NO_REASON_TOKEN="codex-bailed-no-reason"
        ;;
    cursor)
        TOOL_TAG="cursor"
        AGENT_PROMPT="$PLUGIN_ROOT/agents/cursor-implementer.md"
        LAUNCHER="$PLUGIN_ROOT/scripts/launch-cursor-implement.sh"
        RUNTIME_FAILURE_TOKEN="cursor-runtime-failure"
        BAILED_NO_REASON_TOKEN="cursor-bailed-no-reason"
        REQUIRES_HEAD_UNCHANGED=true
        ;;
    gemini)
        TOOL_TAG="gemini"
        AGENT_PROMPT="$PLUGIN_ROOT/agents/gemini-implementer.md"
        LAUNCHER="$PLUGIN_ROOT/scripts/launch-gemini-implement.sh"
        RUNTIME_FAILURE_TOKEN="gemini-runtime-failure"
        BAILED_NO_REASON_TOKEN="gemini-bailed-no-reason"
        REQUIRES_HEAD_UNCHANGED=true
        ;;
    *)
        echo "step2-implement.sh: internal error — CODER=$CODER not handled in tool-case" >&2
        exit 2
        ;;
esac

BASELINE_FILE="$TMPDIR_ARG/step2-baseline.txt"
RESUME_COUNT_FILE="$TMPDIR_ARG/${TOOL_TAG}-resume-count.txt"
SPAWN_BRANCH_FILE="$TMPDIR_ARG/step2-spawn-branch.txt"
PLUGIN_JSON_BASELINE_FILE="$TMPDIR_ARG/step2-plugin-json-baseline.txt"
SPAWN_CODER_FILE="$TMPDIR_ARG/step2-spawn-coder.txt"
MANIFEST_PATH="$TMPDIR_ARG/manifest.json"
MANIFEST_RAW_PATH="$TMPDIR_ARG/manifest-raw.json"
QA_PENDING_PATH="$TMPDIR_ARG/qa-pending.json"
TRANSCRIPT_PATH="$TMPDIR_ARG/${TOOL_TAG}-impl-transcript.txt"
SIDECAR_LOG="$TMPDIR_ARG/${TOOL_TAG}-impl.log"

[[ -f "$AGENT_PROMPT" ]] || { echo "step2-implement.sh: agent prompt missing: $AGENT_PROMPT" >&2; exit 2; }
[[ -x "$LAUNCHER" ]]     || { echo "step2-implement.sh: launcher not executable: $LAUNCHER" >&2; exit 2; }

# Helper: emit a STATUS=bailed envelope and exit 0.
emit_bailed() {
    local reason="$1"
    printf 'STATUS=bailed\n'
    printf 'REASON=%s\n' "$reason"
    printf 'TOOL=%s\n' "$TOOL_TAG"
    if [[ -s "$TRANSCRIPT_PATH" ]]; then printf 'TRANSCRIPT=%s\n' "$TRANSCRIPT_PATH"; fi
    if [[ -s "$SIDECAR_LOG" ]];     then printf 'SIDECAR_LOG=%s\n' "$SIDECAR_LOG"; fi
    # External-implementer bail: orchestrator MUST NOT run main-agent Edit/Write.
    # See SKILL.md NEVER #10 and Step 2 entry preconditions matrix.
    printf 'ORCHESTRATOR_EDIT_AUTHORITY=forbidden\n'
    exit 0
}

# Step 0.5: cross-coder tmpdir-reuse guard. The shared baseline files written
# below (step2-baseline.txt, step2-spawn-branch.txt, step2-plugin-json-baseline.txt)
# and the per-tool ${TOOL_TAG}-resume-count.txt file would desynchronize if a
# tmpdir from a prior --coder=codex run were reused for --coder=cursor/gemini (or vice
# versa). Record the resolved coder on first invocation; bail clearly on any
# subsequent invocation whose --coder differs. Atomic write avoids torn reads.
# Only the external-implementer path writes/reads this sentinel — the claude
# fallback early-returned above without touching the tmpdir, so a prior claude
# run leaves no sentinel and a subsequent codex/cursor/gemini run is the first writer.
if [[ -f "$SPAWN_CODER_FILE" ]]; then
    RECORDED_CODER=$(tr -d '[:space:]' < "$SPAWN_CODER_FILE")
    if [[ "$RECORDED_CODER" != "$CODER" ]]; then
        emit_bailed "coder-mismatch-tmpdir-reuse"
    fi
else
    printf '%s\n' "$CODER" > "$SPAWN_CODER_FILE.tmp"
    mv "$SPAWN_CODER_FILE.tmp" "$SPAWN_CODER_FILE"
fi

# Step 1: write spawn-time baseline + branch + plugin.json SHA on FIRST invocation.
# Subsequent invocations (resume cycles) reuse the existing files.
if [[ ! -f "$BASELINE_FILE" ]]; then
    git -C "$REPO_ROOT" rev-parse HEAD > "$BASELINE_FILE.tmp"
    mv "$BASELINE_FILE.tmp" "$BASELINE_FILE"
fi
BASELINE_SHA=$(cat "$BASELINE_FILE")

if [[ ! -f "$SPAWN_BRANCH_FILE" ]]; then
    git -C "$REPO_ROOT" rev-parse --abbrev-ref HEAD > "$SPAWN_BRANCH_FILE.tmp"
    mv "$SPAWN_BRANCH_FILE.tmp" "$SPAWN_BRANCH_FILE"
fi
SPAWN_BRANCH=$(cat "$SPAWN_BRANCH_FILE")

if [[ ! -f "$PLUGIN_JSON_BASELINE_FILE" ]]; then
    if [[ -f "$REPO_ROOT/.claude-plugin/plugin.json" ]]; then
        git -C "$REPO_ROOT" hash-object "$REPO_ROOT/.claude-plugin/plugin.json" > "$PLUGIN_JSON_BASELINE_FILE.tmp"
    else
        printf '\n' > "$PLUGIN_JSON_BASELINE_FILE.tmp"
    fi
    mv "$PLUGIN_JSON_BASELINE_FILE.tmp" "$PLUGIN_JSON_BASELINE_FILE"
fi
PLUGIN_JSON_BASELINE=$(cat "$PLUGIN_JSON_BASELINE_FILE")

# Step 2: resume counter (incremented on each --answers invocation).
RESUME_COUNT=0
if [[ -f "$RESUME_COUNT_FILE" ]]; then
    raw_count=$(cat "$RESUME_COUNT_FILE")
    if [[ "$raw_count" =~ ^[0-9]+$ ]]; then
        RESUME_COUNT=$raw_count
    else
        emit_bailed "manifest-schema-invalid"
    fi
fi
if [[ -n "$ANSWERS_FILE" ]]; then
    [[ -f "$ANSWERS_FILE" ]] || { echo "step2-implement.sh: --answers given but path does not exist: $ANSWERS_FILE" >&2; exit 2; }
    RESUME_COUNT=$((RESUME_COUNT + 1))
    printf '%s\n' "$RESUME_COUNT" > "$RESUME_COUNT_FILE.tmp"
    mv "$RESUME_COUNT_FILE.tmp" "$RESUME_COUNT_FILE"
fi
if (( RESUME_COUNT > 5 )); then
    emit_bailed "qa-loop-exceeded"
fi

# Step 3: clean stale implementer outputs from prior invocations BEFORE launching.
rm -f "$MANIFEST_PATH" "$MANIFEST_RAW_PATH" "$QA_PENDING_PATH" "$TRANSCRIPT_PATH" "$SIDECAR_LOG"

# Step 4: launch external implementer. Up to 1 retry on transient failure (timeout / non-zero
# exit before manifest written) — but only when post-failure state is clean.
LAUNCHER_TIMEOUT=1800

run_launcher() {
    local launcher_args=(
        --transcript-path "$TRANSCRIPT_PATH"
        --sidecar-log "$SIDECAR_LOG"
        --manifest-path "$MANIFEST_PATH"
        --qa-pending-path "$QA_PENDING_PATH"
        --plan-file "$PLAN_FILE"
        --feature-file "$FEATURE_FILE"
        --agent-prompt "$AGENT_PROMPT"
        --timeout "$LAUNCHER_TIMEOUT"
    )
    if [[ -n "$ANSWERS_FILE" ]]; then
        launcher_args+=(--answers-file "$ANSWERS_FILE")
    fi
    "$LAUNCHER" "${launcher_args[@]}"
}

LAUNCHER_TMP=$(mktemp "$TMPDIR_ARG/${TOOL_TAG}-launcher-output.XXXXXX")
trap 'rm -f "$LAUNCHER_TMP"' EXIT

if run_launcher >"$LAUNCHER_TMP" 2>&1; then
    WRAPPER_EXIT=0
else
    WRAPPER_EXIT=$?
fi
LAUNCHER_OUT=$(head -c 65536 "$LAUNCHER_TMP")
if [[ "$WRAPPER_EXIT" == "2" ]]; then
    emit_bailed "wrapper-validation-failure"
fi

# Parse launcher KV lines.
LAUNCHER_EXIT=$(printf '%s\n' "$LAUNCHER_OUT" | awk -F= '$1=="LAUNCHER_EXIT"{print $2; exit}')
MANIFEST_WRITTEN=$(printf '%s\n' "$LAUNCHER_OUT" | awk -F= '$1=="MANIFEST_WRITTEN"{print $2; exit}')

# Default to 'false' / 99 when missing (e.g., launcher itself crashed before emitting).
LAUNCHER_EXIT=${LAUNCHER_EXIT:-99}
MANIFEST_WRITTEN=${MANIFEST_WRITTEN:-false}

# Retry once on transient failure: launcher exit non-zero AND no manifest, AND clean state.
if [[ "$WRAPPER_EXIT" != "0" || "$MANIFEST_WRITTEN" != "true" || "$LAUNCHER_EXIT" != "0" ]]; then
    if [[ "$MANIFEST_WRITTEN" != "true" ]]; then
        # Check post-failure state is clean enough to retry.
        DIRTY=$(git -C "$REPO_ROOT" status --porcelain)
        INDEX_LOCK_EXISTS=false
        [[ -e "$REPO_ROOT/.git/index.lock" ]] && INDEX_LOCK_EXISTS=true
        CURRENT_HEAD=$(git -C "$REPO_ROOT" rev-parse HEAD)
        if [[ -n "$DIRTY" || "$INDEX_LOCK_EXISTS" == "true" || "$CURRENT_HEAD" != "$BASELINE_SHA" ]]; then
            emit_bailed "dirty-state-after-timeout"
        fi
        # Clean state — single retry.
        if run_launcher >"$LAUNCHER_TMP" 2>&1; then
            WRAPPER_EXIT_RETRY=0
        else
            WRAPPER_EXIT_RETRY=$?
        fi
        LAUNCHER_OUT=$(head -c 65536 "$LAUNCHER_TMP")
        if [[ "$WRAPPER_EXIT_RETRY" == "2" ]]; then
            emit_bailed "wrapper-validation-failure"
        fi
        WRAPPER_EXIT="$WRAPPER_EXIT_RETRY"
        LAUNCHER_EXIT=$(printf '%s\n' "$LAUNCHER_OUT" | awk -F= '$1=="LAUNCHER_EXIT"{print $2; exit}')
        MANIFEST_WRITTEN=$(printf '%s\n' "$LAUNCHER_OUT" | awk -F= '$1=="MANIFEST_WRITTEN"{print $2; exit}')
        LAUNCHER_EXIT=${LAUNCHER_EXIT:-99}
        MANIFEST_WRITTEN=${MANIFEST_WRITTEN:-false}
    fi
fi

if [[ "$WRAPPER_EXIT" != "0" ]]; then
    emit_bailed "$RUNTIME_FAILURE_TOKEN"
fi

if [[ "$MANIFEST_WRITTEN" != "true" ]]; then
    emit_bailed "$RUNTIME_FAILURE_TOKEN"
fi

# Treat a non-zero launcher exit as failure even when a manifest was written —
# the manifest may be a stale .tmp leftover, half-written, or otherwise
# unreliable when the wrapper itself reports failure.
if [[ "$LAUNCHER_EXIT" != "0" ]]; then
    emit_bailed "$RUNTIME_FAILURE_TOKEN"
fi

# Step 5: validate manifest schema with jq.
[[ -s "$MANIFEST_PATH" ]] || emit_bailed "manifest-missing"
cp "$MANIFEST_PATH" "$MANIFEST_RAW_PATH"

# Pull status field; verify schema_version and status enum.
STATUS=$(jq -r 'if type=="object" then .status // "" else "" end' "$MANIFEST_RAW_PATH" 2>/dev/null || true)
SCHEMA_VERSION=$(jq -r 'if type=="object" then .schema_version // "" else "" end' "$MANIFEST_RAW_PATH" 2>/dev/null || true)

if [[ "$SCHEMA_VERSION" != "1" ]]; then
    emit_bailed "manifest-schema-invalid"
fi
case "$STATUS" in
    complete|needs_qa|bailed) ;;
    *) emit_bailed "manifest-schema-invalid" ;;
esac

# Per-status structural validation.
case "$STATUS" in
    complete)
        # Required: files_touched (array, non-empty), commit_message (string, non-empty),
        # summary_bullets (array length 1..5), tests_added_or_modified (array), todos_left (array),
        # oos_observations (array).
        jq -e '
            (.files_touched | type == "array" and length > 0) and
            (.files_touched | all(. | type == "object" and (.path | type == "string"))) and
            (.commit_message | type == "string" and length > 0) and
            (.summary_bullets | type == "array" and length >= 1 and length <= 5) and
            (.tests_added_or_modified | type == "array") and
            (.todos_left | type == "array") and
            (.oos_observations | type == "array")
        ' "$MANIFEST_RAW_PATH" >/dev/null 2>&1 || emit_bailed "manifest-schema-invalid"
        ;;
    needs_qa)
        jq -e '
            (.needs_qa | type == "object") and
            (.needs_qa.questions | type == "array" and length > 0)
        ' "$MANIFEST_RAW_PATH" >/dev/null 2>&1 || emit_bailed "manifest-schema-invalid"
        # qa-pending.json must exist, be non-empty, and contain a non-empty
        # questions array — Step 2.3 of /implement reads it directly via
        # AskUserQuestion. A missing companion file would strand the orchestrator.
        if [[ ! -s "$QA_PENDING_PATH" ]]; then
            emit_bailed "qa-pending-missing"
        fi
        jq -e '(.questions | type == "array" and length > 0)' "$QA_PENDING_PATH" >/dev/null 2>&1 \
            || emit_bailed "qa-pending-missing"
        ;;
    bailed)
        jq -e '(.bail_reason | type == "string" and length > 0)' "$MANIFEST_RAW_PATH" >/dev/null 2>&1 \
            || emit_bailed "manifest-schema-invalid"
        ;;
esac

# Step 6: post-implementer mechanical validation (only meaningful for complete/needs_qa;
# bailed is passed through verbatim).
if [[ "$STATUS" != "bailed" ]]; then
    # 6a: branch unchanged.
    CURRENT_BRANCH=$(git -C "$REPO_ROOT" rev-parse --abbrev-ref HEAD)
    if [[ "$CURRENT_BRANCH" != "$SPAWN_BRANCH" ]]; then
        emit_bailed "branch-changed"
    fi

    # 6b: .claude-plugin/plugin.json unchanged.
    if [[ -f "$REPO_ROOT/.claude-plugin/plugin.json" ]]; then
        CURRENT_PLUGIN_JSON=$(git -C "$REPO_ROOT" hash-object "$REPO_ROOT/.claude-plugin/plugin.json")
    else
        CURRENT_PLUGIN_JSON=$'\n'
    fi
    if [[ "$CURRENT_PLUGIN_JSON" != "$PLUGIN_JSON_BASELINE" ]]; then
        emit_bailed "protected-path-modified"
    fi

    # 6c: submodules clean.
    SUBMODULE_STATUS=$(git -C "$REPO_ROOT" submodule status --recursive 2>/dev/null || true)
    if [[ -n "$SUBMODULE_STATUS" ]]; then
        # any leading char other than space indicates dirty/uninitialized/conflict
        if printf '%s\n' "$SUBMODULE_STATUS" | grep -qE '^[+\-U]'; then
            emit_bailed "submodule-dirty"
        fi
    fi

    # Unsandboxed-tool safety rail: Cursor/Gemini can write to `.git/`. Before
    # the dispatcher commits on their behalf or allows a needs_qa resume cycle,
    # assert HEAD has not moved.
    if [[ "$REQUIRES_HEAD_UNCHANGED" == "true" ]]; then
        CURRENT_HEAD=$(git -C "$REPO_ROOT" rev-parse HEAD)
        if [[ "$CURRENT_HEAD" != "$BASELINE_SHA" ]]; then
            emit_bailed "${TOOL_TAG}-modified-history"
        fi
    fi
fi

# Step 7: complete-only path-normalization check on manifest paths.
# Diff cross-check, commit-subject equality, working-tree-clean, and
# commits-since-baseline are gone — the dispatcher commits on the external implementer's behalf
# below (Step 7b), so there is no committed diff to compare against the
# manifest, and `commit_message` is consumed with no diff/subject second-guessing
# (modulo the commit-time secrets-family redaction applied in Step 7b).
if [[ "$STATUS" == "complete" ]]; then
    # 7a: path normalization on every files_touched[].path and tests_added_or_modified.
    # Reject: contains '..', starts with '/', equals .claude-plugin/plugin.json,
    # under a submodule (per submodule status), escapes repo root after symlink resolve.
    SUBMODULE_PATHS=$(git -C "$REPO_ROOT" submodule status --recursive 2>/dev/null \
        | awk '{print $2}' || true)

    paths_invalid=false
    while IFS= read -r p; do
        [[ -z "$p" ]] && continue
        # absolute path or contains ..
        # NUL detection is implicit — bash strings cannot hold a NUL, so the
        # `read -r` above terminates the field at any NUL in upstream JSON.
        # A literal `*$'\0'*` glob expands to `**` (because `$'\0'` is empty
        # in bash) and matches every non-empty path, so the check must not
        # be expressed that way.
        if [[ "$p" == /* ]] || [[ "$p" == *..* ]]; then
            paths_invalid=true; break
        fi
        # protected file
        if [[ "$p" == ".claude-plugin/plugin.json" ]]; then
            paths_invalid=true; break
        fi
        # under submodule (or the submodule gitlink pointer itself)
        if [[ -n "$SUBMODULE_PATHS" ]]; then
            while IFS= read -r sm; do
                [[ -z "$sm" ]] && continue
                if [[ "$p" == "$sm" || "$p" == "$sm"/* ]]; then
                    paths_invalid=true; break 2
                fi
            done <<< "$SUBMODULE_PATHS"
        fi
    done < <(jq -r '.files_touched[].path, .tests_added_or_modified[]' "$MANIFEST_RAW_PATH" 2>/dev/null)

    # NUL guard at the jq layer. Bash variables cannot represent NUL, so
    # `read -r` over `jq -r` output silently truncates a path like
    # `safe<NUL>../evil` to `safe`, bypassing the `..` check above. Run a
    # separate jq predicate that returns true if any manifest path
    # contains a NUL byte (\u0000), and reject the manifest before any
    # path enters bash control flow. One extra traversal; manifests are
    # small.
    if [[ "$paths_invalid" != "true" ]] && \
       jq -e '[.files_touched[].path, .tests_added_or_modified[]] | any(test("\u0000"))' \
            "$MANIFEST_RAW_PATH" >/dev/null 2>&1; then
        paths_invalid=true
    fi

    if [[ "$paths_invalid" == "true" ]]; then
        emit_bailed "protected-path-modified"
    fi

    # 7b: dispatcher commits on the external implementer's behalf, using manifest.commit_message.
    # Codex stays inside `workspace-write` sandbox semantics (which forbids
    # .git/ writes); Cursor and Gemini run unsandboxed re .git/ but their
    # prompts forbid commits and their HEAD is asserted unchanged before
    # we commit. The dispatcher runs outside that sandbox in the Claude
    # shell. The commit message is piped through scripts/redact-secrets.sh
    # BEFORE git commit so any secret accidentally embedded in commit_message
    # by the implementer never lands in git history (the same redactor runs over the
    # canonical manifest in Step 8 — applying it here closes the prior
    # split-brain where git history was unredacted while the on-disk manifest
    # was redacted).
    #
    # `git add -A` stages every working-tree change (tracked + untracked).
    # That is intentional under the new trust model (per SECURITY.md): the
    # working tree IS the source of truth, manifest.files_touched is
    # advisory, and operator / `/review` / pre-commit hooks are the
    # downstream backstops.
    COMMIT_MSG_FILE="$TMPDIR_ARG/${TOOL_TAG}-commit-message.txt"
    REDACT_FOR_COMMIT="$PLUGIN_ROOT/scripts/redact-secrets.sh"
    if [[ -x "$REDACT_FOR_COMMIT" ]]; then
        jq -r '.commit_message' "$MANIFEST_RAW_PATH" | "$REDACT_FOR_COMMIT" > "$COMMIT_MSG_FILE.tmp"
    else
        # The earlier redactor-not-executable check (top of Step 8 below)
        # would also fail closed, but we have not reached it yet — guard
        # here so an unexecutable redactor does not silently let raw
        # commit_message reach git history.
        emit_bailed "redactor-not-executable"
    fi
    mv "$COMMIT_MSG_FILE.tmp" "$COMMIT_MSG_FILE"

    COMMIT_STDERR_FILE="$TMPDIR_ARG/${TOOL_TAG}-commit-stderr.txt"
    git -C "$REPO_ROOT" add -A
    if ! git -C "$REPO_ROOT" commit -F "$COMMIT_MSG_FILE" >/dev/null 2>"$COMMIT_STDERR_FILE"; then
        # Common causes: empty working tree (Codex declared complete with no
        # actual edits), pre-commit hook rejection, or a transient git error.
        # stderr is captured to $COMMIT_STDERR_FILE for operator diagnosis.
        # We bail BEFORE Step 8's manifest sanitization runs, so the on-disk
        # manifest copies would otherwise carry Codex's raw text fields —
        # remove them so no un-redacted artifact persists. The transcript,
        # sidecar log, and captured stderr file remain for operator
        # inspection.
        rm -f "$MANIFEST_PATH" "$MANIFEST_RAW_PATH"
        emit_bailed "commit-failed"
    fi
    rm -f "$COMMIT_STDERR_FILE"
fi

# Step 8: sanitization. Apply scripts/redact-secrets.sh to text fields, then
# write the canonical manifest.json (replacing the raw copy).
REDACT="$PLUGIN_ROOT/scripts/redact-secrets.sh"
# Fail closed if the redactor file exists but is not executable — a sparse
# checkout or broken perms must NOT silently emit raw manifest text into
# downstream public surfaces (CHANGELOG, PR body, GitHub issues).
if [[ -e "$REDACT" && ! -x "$REDACT" ]]; then
    emit_bailed "redactor-not-executable"
fi
if [[ -x "$REDACT" ]]; then
    # Build a sanitized version of the manifest by piping each text field through
    # redact-secrets.sh. We use jq to extract, redact in shell, then re-inject.
    sanitize_string() {
        if [[ -z "$1" ]]; then printf '%s' ""; else printf '%s' "$1" | "$REDACT"; fi
    }

    # Extract fields, sanitize, and write a sanitized manifest.
    TMP_SAN="$TMPDIR_ARG/manifest-sanitized.json"
    # commit_message
    CM=$(jq -r '.commit_message // ""' "$MANIFEST_RAW_PATH")
    CM_SAN=$(sanitize_string "$CM")
    # bail_reason (kept verbatim - dispatcher tokens are non-sensitive)
    BR=$(jq -r '.bail_reason // ""' "$MANIFEST_RAW_PATH")

    # summary_bullets, todos_left: arrays of strings.
    # oos_observations: array of {title, description, phase}.
    # Rebuild via jq with the sanitized commit_message, then post-process arrays in shell.
    jq --arg cm "$CM_SAN" --arg br "$BR" \
        '.commit_message = $cm | .bail_reason = $br' "$MANIFEST_RAW_PATH" > "$TMP_SAN.0"

    # summary_bullets
    if jq -e '.summary_bullets | type == "array"' "$TMP_SAN.0" >/dev/null 2>&1; then
        SAN_BULLETS_FILE="$TMPDIR_ARG/manifest-bullets.json"
        : > "$SAN_BULLETS_FILE"
        printf '[' > "$SAN_BULLETS_FILE"
        first=true
        while IFS= read -r b; do
            sb=$(sanitize_string "$b")
            if [[ "$first" == "true" ]]; then first=false; else printf ',' >> "$SAN_BULLETS_FILE"; fi
            jq -Rn --arg s "$sb" '$s' >> "$SAN_BULLETS_FILE"
        done < <(jq -r '.summary_bullets[]?' "$TMP_SAN.0")
        printf ']' >> "$SAN_BULLETS_FILE"
        jq --slurpfile sb "$SAN_BULLETS_FILE" '.summary_bullets = $sb[0]' "$TMP_SAN.0" > "$TMP_SAN.1"
        mv "$TMP_SAN.1" "$TMP_SAN.0"
    fi

    # todos_left
    if jq -e '.todos_left | type == "array"' "$TMP_SAN.0" >/dev/null 2>&1; then
        SAN_TODOS_FILE="$TMPDIR_ARG/manifest-todos.json"
        : > "$SAN_TODOS_FILE"
        printf '[' > "$SAN_TODOS_FILE"
        first=true
        while IFS= read -r t; do
            st=$(sanitize_string "$t")
            if [[ "$first" == "true" ]]; then first=false; else printf ',' >> "$SAN_TODOS_FILE"; fi
            jq -Rn --arg s "$st" '$s' >> "$SAN_TODOS_FILE"
        done < <(jq -r '.todos_left[]?' "$TMP_SAN.0")
        printf ']' >> "$SAN_TODOS_FILE"
        jq --slurpfile td "$SAN_TODOS_FILE" '.todos_left = $td[0]' "$TMP_SAN.0" > "$TMP_SAN.1"
        mv "$TMP_SAN.1" "$TMP_SAN.0"
    fi

    # oos_observations: title and description only.
    if jq -e '.oos_observations | type == "array"' "$TMP_SAN.0" >/dev/null 2>&1; then
        SAN_OOS_FILE="$TMPDIR_ARG/manifest-oos.json"
        : > "$SAN_OOS_FILE"
        printf '[' > "$SAN_OOS_FILE"
        first=true
        OOS_LEN=$(jq '.oos_observations | length' "$TMP_SAN.0")
        i=0
        while (( i < OOS_LEN )); do
            ti=$(jq -r ".oos_observations[$i].title // \"\"" "$TMP_SAN.0")
            de=$(jq -r ".oos_observations[$i].description // \"\"" "$TMP_SAN.0")
            ph=$(jq -r ".oos_observations[$i].phase // \"implement\"" "$TMP_SAN.0")
            ti_san=$(sanitize_string "$ti")
            de_san=$(sanitize_string "$de")
            if [[ "$first" == "true" ]]; then first=false; else printf ',' >> "$SAN_OOS_FILE"; fi
            jq -Rn --arg t "$ti_san" --arg d "$de_san" --arg p "$ph" \
                '{title: $t, description: $d, phase: $p}' >> "$SAN_OOS_FILE"
            i=$((i + 1))
        done
        printf ']' >> "$SAN_OOS_FILE"
        jq --slurpfile oo "$SAN_OOS_FILE" '.oos_observations = $oo[0]' "$TMP_SAN.0" > "$TMP_SAN.1"
        mv "$TMP_SAN.1" "$TMP_SAN.0"
    fi

    mv "$TMP_SAN.0" "$MANIFEST_PATH"
fi

# Step 9: emit final KV envelope. ORCHESTRATOR_EDIT_AUTHORITY is the gate the
# orchestrator uses to decide whether main-agent Edit/Write is permitted at
# Step 2.4 — `allowed` ONLY when STATUS=claude_fallback (emitted upstream),
# `forbidden` on every external-implementer outcome here. See SKILL.md NEVER
# #10 and the Step 2 entry preconditions matrix.
case "$STATUS" in
    complete)
        printf 'STATUS=complete\n'
        printf 'TOOL=%s\n' "$TOOL_TAG"
        printf 'MANIFEST=%s\n' "$MANIFEST_PATH"
        printf 'TRANSCRIPT=%s\n' "$TRANSCRIPT_PATH"
        printf 'SIDECAR_LOG=%s\n' "$SIDECAR_LOG"
        printf 'ORCHESTRATOR_EDIT_AUTHORITY=forbidden\n'
        ;;
    needs_qa)
        printf 'STATUS=needs_qa\n'
        printf 'TOOL=%s\n' "$TOOL_TAG"
        printf 'MANIFEST=%s\n' "$MANIFEST_PATH"
        printf 'QA_PENDING=%s\n' "$QA_PENDING_PATH"
        printf 'TRANSCRIPT=%s\n' "$TRANSCRIPT_PATH"
        printf 'SIDECAR_LOG=%s\n' "$SIDECAR_LOG"
        printf 'ORCHESTRATOR_EDIT_AUTHORITY=forbidden\n'
        ;;
    bailed)
        BR=$(jq -r --arg fallback "$BAILED_NO_REASON_TOKEN" '.bail_reason // $fallback' "$MANIFEST_RAW_PATH")
        # Sanitize bail_reason for KV-grammar safety: collapse all
        # whitespace (including newlines) to single spaces, strip ASCII
        # control characters, and cap length so a Codex-authored token
        # cannot break the orchestrator's KV parser by emitting extra
        # `KEY=value` lines or control sequences.
        BR=$(printf '%s' "$BR" | tr -d '\000-\010\013\014\016-\037' | tr '\t\n\r' '   ' | sed -e 's/  */ /g' -e 's/^ //' -e 's/ $//' | cut -c1-200)
        [[ -z "$BR" ]] && BR="$BAILED_NO_REASON_TOKEN"
        printf 'STATUS=bailed\n'
        printf 'REASON=%s\n' "$BR"
        printf 'TOOL=%s\n' "$TOOL_TAG"
        printf 'MANIFEST=%s\n' "$MANIFEST_PATH"
        printf 'TRANSCRIPT=%s\n' "$TRANSCRIPT_PATH"
        printf 'SIDECAR_LOG=%s\n' "$SIDECAR_LOG"
        printf 'ORCHESTRATOR_EDIT_AUTHORITY=forbidden\n'
        ;;
esac
exit 0
