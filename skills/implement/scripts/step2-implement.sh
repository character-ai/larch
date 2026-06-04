#!/usr/bin/env bash
# step2-implement.sh — Dispatcher for /implement Step 2 (coder selection).
#
# This is the SINGLE entrypoint /implement Step 2 invokes. It is the only place
# that branches on the chosen --coder value. The orchestrator only falls back
# to Claude main-agent Edit/Write when BOTH STATUS=claude_fallback AND
# ORCHESTRATOR_EDIT_AUTHORITY=allowed are present in this script's stdout (the
# pair invariant: AUTH=allowed iff STATUS=claude_fallback). claude_fallback is
# emitted when --coder=claude or when --coder=cursor with --cursor-present
# unset/false (Cursor falls back to Claude instead of failing closed); every
# external-implementer outcome (complete / needs_qa / bailed) emits AUTH=forbidden
# instead. See SKILL.md NEVER #10 and the Step 2 entry preconditions matrix.
#
# Coder flag (preferred):
#   --coder claude   → STATUS=claude_fallback (main-agent path)
#   --coder cursor   → spawn Cursor implementer; when --cursor-present is
#                      unset/false, falls back to claude_fallback
#   --coder codex    → spawn Codex implementer
#
# Cursor presence flag:
#   --cursor-present true   → permit --coder cursor to launch Cursor
#   --cursor-present false  → --coder cursor falls back to claude_fallback
#   --cursor-present ""     → treated as false (falls back to claude_fallback)
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
#   TOOL=<codex|cursor>      # set on external implementer paths
#   TRANSCRIPT=<path>        # set when launcher actually ran
#   SIDECAR_LOG=<path>       # set when launcher actually ran
#   WARN_CODEX_NONZERO_EXIT=true
#                            # OPTIONAL, advisory. Emitted only on the Codex
#                            # STATUS=complete path when the implementer exited
#                            # non-zero AFTER atomically writing a complete
#                            # manifest (e.g. a self-verification step failed
#                            # once the work was done) and the dispatcher
#                            # salvaged that manifest instead of discarding it.
#                            # Trailing advisory KV, like the PHANTOM_* probe
#                            # tail; SKILL.md Step 2 does not branch on it. See
#                            # issue #3383.
#   ORCHESTRATOR_EDIT_AUTHORITY=<allowed|forbidden>
#                            # ALWAYS emitted on every exit-0 path. `allowed`
#                            # only when STATUS=claude_fallback (the only
#                            # outcome that authorizes main-agent Edit/Write
#                            # at SKILL.md Step 2.4). `forbidden` on every
#                            # external-implementer outcome (complete /
#                            # needs_qa / bailed). See SKILL.md NEVER #10
#                            # and the Step 2 entry preconditions matrix.
#   RECOVERY_FROM=manifest-schema-invalid
#   RECOVERY_PRIOR_TOOL=<codex|cursor>
#   RECOVERY_PATHS_FILE=<nul-delimited-pathspec-file>
#                            # Optional all-or-none triplet on malformed-
#                            # manifest recovery, emitted with
#                            # STATUS=claude_fallback and AUTH=allowed.
#
# Exit code is always 0 unless caller / invocation validation fails (exit 2):
# missing or invalid flag, missing required path, bad enum value,
# or — on the Codex / Cursor path — cwd is not inside a git working tree.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PLUGIN_ROOT="${CLAUDE_PLUGIN_ROOT:-$(cd "$SCRIPT_DIR/../../.." && pwd -P)}"
# shellcheck source=scripts/lib-quiet.sh
source "$PLUGIN_ROOT/scripts/lib-quiet.sh"
# shellcheck source=scripts/lib-failed-agent-stderr-tail.sh
source "$PLUGIN_ROOT/scripts/lib-failed-agent-stderr-tail.sh"
larch_quiet_init

TMPDIR_ARG=""
PLAN_FILE=""
FEATURE_FILE=""
CODER=""
CODEX_AVAILABLE=""
CURSOR_PRESENT_ARG=""
ANSWERS_FILE=""
WORKFLOW_PATH=""

while [[ $# -gt 0 ]]; do
    case "$1" in
        --tmpdir)            TMPDIR_ARG="${2:?--tmpdir requires a value}"; shift 2 ;;
        --plan-file)         PLAN_FILE="${2:?--plan-file requires a value}"; shift 2 ;;
        --feature-file)      FEATURE_FILE="${2:?--feature-file requires a value}"; shift 2 ;;
        --coder)             CODER="${2:?--coder requires a value}"; shift 2 ;;
        --codex-available)   CODEX_AVAILABLE="${2:?--codex-available requires a value}"; shift 2 ;;
        --cursor-present)    CURSOR_PRESENT_ARG="${2-}"; shift 2 ;;
        --answers)           ANSWERS_FILE="${2:?--answers requires a value}"; shift 2 ;;
        --workflow)          WORKFLOW_PATH="${2:?--workflow requires a value}"; shift 2 ;;
        *) larch_err "step2-implement.sh: unknown flag: $1"; exit 2 ;;
    esac
done

# Coder selection: --coder is the canonical flag; --codex-available is accepted
# for one release as a deprecated alias. Mutual-exclusion is mandatory because
# the legacy flag sets the same internal state and silent precedence would
# mask operator misconfiguration.
if [[ -n "$CODER" && -n "$CODEX_AVAILABLE" ]]; then
    larch_err "step2-implement.sh: --coder and --codex-available are mutually exclusive"
    exit 2
fi

if [[ -n "$CODEX_AVAILABLE" ]]; then
    case "$CODEX_AVAILABLE" in
        true)
            larch_err "step2-implement.sh: WARNING: --codex-available is deprecated; pass --coder codex instead"
            CODER="codex"
            ;;
        false)
            larch_err "step2-implement.sh: WARNING: --codex-available is deprecated; pass --coder claude instead"
            CODER="claude"
            ;;
        *)
            larch_err "step2-implement.sh: --codex-available must be 'true' or 'false', got: $CODEX_AVAILABLE"
            exit 2
            ;;
    esac
fi

if [[ -z "$CODER" ]]; then
    larch_err "step2-implement.sh: --coder is required"
    exit 2
fi

# shellcheck source=scripts/external-tool-registry.sh
source "$SCRIPT_DIR/../../../scripts/external-tool-registry.sh" || { larch_err "step2-implement.sh: failed to source external-tool-registry.sh"; exit 2; }
[[ "${LARCH_EXTERNAL_TOOL_REGISTRY_LOADED:-}" == "1" ]] || { larch_err "step2-implement.sh: external-tool-registry.sh sourced but sentinel missing"; exit 2; }

if ! larch_is_implementer_coder "$CODER"; then
    larch_err "step2-implement.sh: --coder must be one of $(larch_implementer_coders_braced), got: $CODER"
    exit 2
fi

for var in TMPDIR_ARG PLAN_FILE FEATURE_FILE; do
    if [[ -z "${!var}" ]]; then
        flag_lc=$(printf '%s' "$var" | tr '[:upper:]' '[:lower:]' | tr '_' '-')
        larch_err "step2-implement.sh: --$flag_lc is required"
        exit 2
    fi
done

[[ -d "$TMPDIR_ARG" ]] || { larch_err "step2-implement.sh: --tmpdir not a directory: $TMPDIR_ARG"; exit 2; }
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
[[ -f "$PLAN_FILE" ]]  || { larch_err "step2-implement.sh: --plan-file not found: $PLAN_FILE"; exit 2; }
[[ -f "$FEATURE_FILE" ]] || { larch_err "step2-implement.sh: --feature-file not found: $FEATURE_FILE"; exit 2; }

WORKFLOW_PATH="${WORKFLOW_PATH:-SIMPLE}"
case "$WORKFLOW_PATH" in
    SIMPLE|HARD) ;;
    *) larch_err "step2-implement.sh: --workflow must be 'SIMPLE' or 'HARD', got: '$WORKFLOW_PATH'"; exit 2 ;;
esac

# Branch 1: coder=claude → emit claude_fallback and return.
# Run BEFORE the PLUGIN_ROOT / REPO_ROOT resolution so the fallback path stays
# git-free (claude_fallback may be invoked outside a git working tree, and it
# needs no plugin assets).
if [[ "$CODER" == "claude" ]]; then
    emit_kv STATUS claude_fallback
    emit_kv ORCHESTRATOR_EDIT_AUTHORITY allowed
    exit 0
fi

# Run after the `claude` early-return so claude path is not affected by
# --cursor-present noise. Empty is normalized to false.
if [[ -n "$CURSOR_PRESENT_ARG" ]]; then
    case "$CURSOR_PRESENT_ARG" in
        true|false) ;;
        *) larch_err "step2-implement.sh: --cursor-present must be 'true', 'false', or empty, got: $CURSOR_PRESENT_ARG"; exit 2 ;;
    esac
fi
[[ -z "$CURSOR_PRESENT_ARG" ]] && CURSOR_PRESENT_ARG="false"

# Cursor presence gate (fall back to claude). Runs before REPO_ROOT resolution
# so that --coder=cursor with --cursor-present=false falls back cleanly even
# from outside a git work-tree, mirroring the --coder=claude early-return
# above. The gate runs only on the cursor path; codex/claude are unaffected
# by the value of --cursor-present.
if [[ "$CODER" == "cursor" && "$CURSOR_PRESENT_ARG" != "true" ]]; then
    emit_kv STATUS claude_fallback
    emit_kv ORCHESTRATOR_EDIT_AUTHORITY allowed
    exit 0
fi

"$PLUGIN_ROOT/scripts/timing-ledger.sh" mark "Step 2 — implementation" || true

REQUIRES_HEAD_UNCHANGED=false
# Set true at the Step 4 LAUNCHER_EXIT gate when a complete, well-formed
# manifest is salvaged despite a non-zero implementer exit (issue #3383). The
# token is the coder-specific KV key emitted in the Step 9 complete envelope;
# it stays empty for coders that do not salvage (Cursor).
WARN_NONZERO_EXIT_SALVAGE=false
NONZERO_EXIT_WARN_TOKEN=""

# ---------------------------------------------------------------------------
# External implementer path. Set up paths inside $TMPDIR_ARG.
# ---------------------------------------------------------------------------

# PLUGIN_ROOT: the plugin tree this script ships in (cache dir when the plugin
# is installed, source repo root when developing on larch itself). Used for
# resolving sibling plugin assets — agent prompt, launcher, redactor.
# REPO_ROOT: the consumer git repo this run is operating on. Derived from cwd's
# git toplevel because PLUGIN_ROOT (cache snapshot) has no .git when running
# from an installed plugin. All `git -C "$REPO_ROOT"` calls and the
# `.claude-plugin/plugin.json` reference target this root.
REPO_ROOT="$(git rev-parse --show-toplevel 2>/dev/null || true)"
if [[ -z "$REPO_ROOT" ]]; then
    larch_err "step2-implement.sh: must be invoked from within a git working tree (git rev-parse --show-toplevel failed)"
    exit 2
fi

case "$CODER" in
    codex)
        TOOL_TAG="codex"
        AGENT_PROMPT="$PLUGIN_ROOT/agents/codex-implementer.md"
        LAUNCHER="$PLUGIN_ROOT/scripts/launch-codex-implement.sh"
        RUNTIME_FAILURE_TOKEN="codex-runtime-failure"
        BAILED_NO_REASON_TOKEN="codex-bailed-no-reason"
        NONZERO_EXIT_WARN_TOKEN="WARN_CODEX_NONZERO_EXIT"
        ;;
    cursor)
        TOOL_TAG="cursor"
        AGENT_PROMPT="$PLUGIN_ROOT/agents/cursor-implementer.md"
        LAUNCHER="$PLUGIN_ROOT/scripts/launch-cursor-implement.sh"
        RUNTIME_FAILURE_TOKEN="cursor-runtime-failure"
        BAILED_NO_REASON_TOKEN="cursor-bailed-no-reason"
        REQUIRES_HEAD_UNCHANGED=true
        ;;
    *)
        larch_err "step2-implement.sh: internal error — CODER=$CODER not handled in tool-case"
        exit 2
        ;;
esac

BASELINE_FILE="$TMPDIR_ARG/step2-baseline.txt"
PRELAUNCH_PORCELAIN_FILE="$TMPDIR_ARG/step2-prelaunch-porcelain.nul"
POSTLAUNCH_PORCELAIN_FILE="$TMPDIR_ARG/step2-postlaunch-porcelain.nul"
PRELAUNCH_CONTENT_DIGESTS_FILE="$TMPDIR_ARG/step2-prelaunch-content-digests.txt"
PRELAUNCH_INDEX_FLAG_FILE="$TMPDIR_ARG/step2-prelaunch-index.env"
RECOVERY_PATHS_FILE="$TMPDIR_ARG/step2-recovery-paths.nul"
RESUME_COUNT_FILE="$TMPDIR_ARG/${TOOL_TAG}-resume-count.txt"
SPAWN_BRANCH_FILE="$TMPDIR_ARG/step2-spawn-branch.txt"
PLUGIN_JSON_BASELINE_FILE="$TMPDIR_ARG/step2-plugin-json-baseline.txt"
SPAWN_CODER_FILE="$TMPDIR_ARG/step2-spawn-coder.txt"
MANIFEST_PATH="$TMPDIR_ARG/manifest.json"
MANIFEST_RAW_PATH="$TMPDIR_ARG/manifest-raw.json"
QA_PENDING_PATH="$TMPDIR_ARG/qa-pending.json"
TRANSCRIPT_PATH="$TMPDIR_ARG/${TOOL_TAG}-impl-transcript.txt"
if [[ "$CODER" == "codex" ]]; then
    STEP2_OUT_DIR="$TMPDIR_ARG/codex-step2-out"
    mkdir -p "$STEP2_OUT_DIR"
    MANIFEST_PATH="$STEP2_OUT_DIR/manifest.json"
    QA_PENDING_PATH="$STEP2_OUT_DIR/qa-pending.json"
    TRANSCRIPT_PATH="$STEP2_OUT_DIR/${TOOL_TAG}-impl-transcript.txt"
fi
SIDECAR_LOG="$TMPDIR_ARG/${TOOL_TAG}-impl.log"

[[ -f "$AGENT_PROMPT" ]] || { larch_err "step2-implement.sh: agent prompt missing: $AGENT_PROMPT"; exit 2; }
[[ -x "$LAUNCHER" ]]     || { larch_err "step2-implement.sh: launcher not executable: $LAUNCHER"; exit 2; }

# Helper: emit a STATUS=bailed envelope and exit 0.
emit_bailed() {
    local reason="$1"
    emit_kv STATUS bailed
    emit_kv REASON "$reason"
    emit_kv TOOL "$TOOL_TAG"
    if [[ -s "$TRANSCRIPT_PATH" ]]; then emit_kv TRANSCRIPT "$TRANSCRIPT_PATH"; fi
    if [[ -s "$SIDECAR_LOG" ]];     then emit_kv SIDECAR_LOG "$SIDECAR_LOG"; fi
    # External-implementer bail: orchestrator MUST NOT run main-agent Edit/Write.
    # See SKILL.md NEVER #10 and Step 2 entry preconditions matrix.
    emit_kv ORCHESTRATOR_EDIT_AUTHORITY forbidden
    emit_failed_agent_stderr_tail_larch_err "$TRANSCRIPT_PATH" || true
    exit 0
}

submodule_roots() {
    git -C "$REPO_ROOT" submodule status --recursive 2>/dev/null | awk '{print $2}' || true
}

path_is_under_any_submodule() {
    local candidate="$1" sm
    while IFS= read -r sm || [[ -n "$sm" ]]; do
        [[ -n "$sm" ]] || continue
        if [[ "$candidate" == "$sm" || "$candidate" == "$sm"/* ]]; then
            return 0
        fi
    done < <(submodule_roots)
    return 1
}

run_post_implementer_safety_gates() {
    # Branch unchanged.
    CURRENT_BRANCH=$(git -C "$REPO_ROOT" rev-parse --abbrev-ref HEAD)
    if [[ "$CURRENT_BRANCH" != "$SPAWN_BRANCH" ]]; then
        emit_bailed "branch-changed"
    fi

    # .claude-plugin/plugin.json unchanged.
    if [[ -f "$REPO_ROOT/.claude-plugin/plugin.json" ]]; then
        CURRENT_PLUGIN_JSON=$(git -C "$REPO_ROOT" hash-object "$REPO_ROOT/.claude-plugin/plugin.json")
    else
        CURRENT_PLUGIN_JSON=""
    fi
    if [[ "$CURRENT_PLUGIN_JSON" != "$PLUGIN_JSON_BASELINE" ]]; then
        emit_bailed "protected-path-modified"
    fi

    # Submodules clean: leading-status check plus dirty files reported under
    # submodule roots when ignore-submodules=none is used.
    SUBMODULE_STATUS=$(git -C "$REPO_ROOT" submodule status --recursive 2>/dev/null || true)
    if [[ -n "$SUBMODULE_STATUS" ]]; then
        if printf '%s\n' "$SUBMODULE_STATUS" | grep -qE '^[+\-U]'; then
            emit_bailed "submodule-dirty"
        fi
    fi
    if [[ -n "$SUBMODULE_STATUS" ]]; then
        python3 - "$REPO_ROOT" <<'PY' || emit_bailed "submodule-dirty"
import subprocess
import sys

repo = sys.argv[1]
roots = []
try:
    out = subprocess.check_output(["git", "-C", repo, "submodule", "status", "--recursive"], stderr=subprocess.DEVNULL, text=True)
except subprocess.CalledProcessError:
    out = ""
for line in out.splitlines():
    parts = line.split()
    if len(parts) >= 2:
        roots.append(parts[1].rstrip("/"))
if not roots:
    sys.exit(0)
try:
    raw = subprocess.check_output(["git", "-C", repo, "status", "--porcelain=v1", "-z", "--ignore-submodules=none"], stderr=subprocess.DEVNULL)
except subprocess.CalledProcessError:
    sys.exit(1)
items = raw.split(b"\0")
i = 0
while i < len(items):
    rec = items[i]
    i += 1
    if not rec:
        continue
    status = rec[:2].decode("ascii", "replace")
    path = rec[3:].decode("utf-8", "surrogateescape")
    if "R" in status or "C" in status:
        if i < len(items):
            i += 1
    for root in roots:
        if path == root or path.startswith(root + "/"):
            sys.exit(1)
sys.exit(0)
PY
    fi

    # Unsandboxed-tool safety rail: Cursor can write to `.git/`.
    if [[ "$REQUIRES_HEAD_UNCHANGED" == "true" ]]; then
        CURRENT_HEAD=$(git -C "$REPO_ROOT" rev-parse HEAD)
        if [[ "$CURRENT_HEAD" != "$BASELINE_SHA" ]]; then
            emit_bailed "${TOOL_TAG}-modified-history"
        fi
    fi
}

write_prelaunch_recovery_baseline() {
    if [[ -n "$ANSWERS_FILE" || -f "$PRELAUNCH_PORCELAIN_FILE" ]]; then
        return 0
    fi
    git -C "$REPO_ROOT" status --porcelain=v1 -z --untracked-files=all > "$PRELAUNCH_PORCELAIN_FILE"
    if git -C "$REPO_ROOT" diff --cached --quiet --no-ext-diff; then
        printf 'PRELAUNCH_INDEX_NONEMPTY=false\n' > "$PRELAUNCH_INDEX_FLAG_FILE.tmp"
    else
        printf 'PRELAUNCH_INDEX_NONEMPTY=true\n' > "$PRELAUNCH_INDEX_FLAG_FILE.tmp"
    fi
    mv "$PRELAUNCH_INDEX_FLAG_FILE.tmp" "$PRELAUNCH_INDEX_FLAG_FILE"
    python3 - "$REPO_ROOT" "$PRELAUNCH_PORCELAIN_FILE" > "$PRELAUNCH_CONTENT_DIGESTS_FILE.tmp" <<'PY'
import hashlib
import os
import sys

repo, porcelain = sys.argv[1], sys.argv[2]
raw = open(porcelain, "rb").read()
items = raw.split(b"\0")
seen = []
i = 0
while i < len(items):
    rec = items[i]
    i += 1
    if not rec:
        continue
    status = rec[:2].decode("ascii", "replace")
    path = rec[3:].decode("utf-8", "surrogateescape")
    if "R" in status or "C" in status:
        if i < len(items):
            i += 1
    if path not in seen:
        seen.append(path)
for path in seen:
    full = os.path.join(repo, path)
    try:
        with open(full, "rb") as fh:
            digest = hashlib.sha256(fh.read()).hexdigest()
        print(f"{digest}\t{path}")
    except OSError:
        print(f"missing\t{path}")
PY
    mv "$PRELAUNCH_CONTENT_DIGESTS_FILE.tmp" "$PRELAUNCH_CONTENT_DIGESTS_FILE"
}

compute_recovery_paths() {
    git -C "$REPO_ROOT" status --porcelain=v1 -z --untracked-files=all > "$POSTLAUNCH_PORCELAIN_FILE"
    "$SCRIPT_DIR/compute-step2-recovery-paths.sh" \
        --repo-root "$REPO_ROOT" \
        --tmpdir "$TMPDIR_ARG" \
        --prelaunch-porcelain "$PRELAUNCH_PORCELAIN_FILE" \
        --postlaunch-porcelain "$POSTLAUNCH_PORCELAIN_FILE" \
        --prelaunch-digests "$PRELAUNCH_CONTENT_DIGESTS_FILE" \
        --out-file "$RECOVERY_PATHS_FILE"
}

manifest_has_legacy_fingerprint() {
    jq -e '
      type == "object" and
      ((has("schema_version") | not)) and
      ((keys_unsorted - ["status", "summary", "checks"]) | length == 0)
    ' "$MANIFEST_RAW_PATH" >/dev/null 2>&1
}

# A complete, well-formed manifest already on disk can be trusted even when the
# implementer process exited non-zero AFTER writing it — e.g. a self-verification
# step failed once the implementation work was already finished and atomically
# committed to manifest.json (issue #3383). Step 3 removes stale manifests before
# launch and the implementer writes manifest.json atomically (.tmp -> mv), so a
# non-empty manifest.json that parses as schema_version "1" / status "complete"
# reflects finished work, not a half-written or stale leftover. This predicate
# only decides salvage-vs-hard-bail at the Step 4 non-zero-exit gate; the full
# Step 5 structural validation (files_touched, commit_message, …) still runs
# afterward and can still bail/recover. Reads $MANIFEST_PATH directly (the
# canonical post-launch path), not the launcher's MANIFEST_WRITTEN KV.
manifest_on_disk_is_salvageable_complete() {
    [[ -s "$MANIFEST_PATH" ]] || return 1
    jq -e '
      type == "object"
      and ((.schema_version | tostring) == "1")
      and (.status == "complete")
    ' "$MANIFEST_PATH" >/dev/null 2>&1
}

# Recovery preserves the pair invariant: STATUS=claude_fallback is the only
# AUTH=allowed envelope, and RECOVERY_FROM/RECOVERY_PRIOR_TOOL/RECOVERY_PATHS_FILE
# are an all-or-none triplet. It is commit-only recovery for a malformed
# manifest that otherwise appears to represent completed implementer work; it
# never authorizes re-implementation from the plan.
emit_manifest_invalid_or_recover() {
    local parse_ok=false prelaunch_index_nonempty=false
    if jq -e 'type == "object"' "$MANIFEST_RAW_PATH" >/dev/null 2>&1; then
        parse_ok=true
    fi
    if [[ "$parse_ok" != "true" ]]; then
        emit_bailed "manifest-schema-invalid"
    fi

    case "$STATUS" in
        complete) ;;
        "")
            if ! manifest_has_legacy_fingerprint; then
                emit_bailed "manifest-schema-invalid"
            fi
            ;;
        needs_qa|bailed|*) emit_bailed "manifest-schema-invalid" ;;
    esac

    if [[ -f "$PRELAUNCH_INDEX_FLAG_FILE" ]]; then
        prelaunch_index_nonempty=$(awk -F= '$1=="PRELAUNCH_INDEX_NONEMPTY"{print $2; exit}' "$PRELAUNCH_INDEX_FLAG_FILE")
    fi
    if [[ "$prelaunch_index_nonempty" == "true" ]]; then
        emit_bailed "manifest-schema-invalid"
    fi

    if ! compute_recovery_paths; then
        emit_bailed "manifest-schema-invalid"
    fi

    while IFS= read -r -d '' recovery_path; do
        [[ -n "$recovery_path" ]] || continue
        if [[ "$recovery_path" == ".claude-plugin/plugin.json" ]]; then
            emit_bailed "protected-path-modified"
        fi
        if path_is_under_any_submodule "$recovery_path"; then
            emit_bailed "submodule-dirty"
        fi
    done < "$RECOVERY_PATHS_FILE"

    run_post_implementer_safety_gates

    if [[ -f "$MANIFEST_RAW_PATH" ]]; then
        mv "$MANIFEST_RAW_PATH" "$TMPDIR_ARG/manifest-raw.invalid.json"
    fi
    jq -n \
        --arg recovery_from "manifest-schema-invalid" \
        --arg prior_tool "$TOOL_TAG" \
        --arg recovery_paths_file "$(basename "$RECOVERY_PATHS_FILE")" \
        '{schema_version: 1, recovery_from: $recovery_from, prior_tool: $prior_tool, recovery_paths_file: $recovery_paths_file}' \
        > "$TMPDIR_ARG/recovery-metadata.json.tmp"
    mv "$TMPDIR_ARG/recovery-metadata.json.tmp" "$TMPDIR_ARG/recovery-metadata.json"

    emit_kv STATUS claude_fallback
    emit_kv TOOL "$TOOL_TAG"
    if [[ -s "$TRANSCRIPT_PATH" ]]; then emit_kv TRANSCRIPT "$TRANSCRIPT_PATH"; fi
    if [[ -s "$SIDECAR_LOG" ]];     then emit_kv SIDECAR_LOG "$SIDECAR_LOG"; fi
    emit_kv ORCHESTRATOR_EDIT_AUTHORITY allowed
    emit_kv RECOVERY_FROM manifest-schema-invalid
    emit_kv RECOVERY_PRIOR_TOOL "$TOOL_TAG"
    emit_kv RECOVERY_PATHS_FILE "$RECOVERY_PATHS_FILE"
    exit 0
}

# Step 0 tracking/issue tmpdir phase: cross-coder tmpdir-reuse guard. The shared baseline files written
# below (step2-baseline.txt, step2-spawn-branch.txt, step2-plugin-json-baseline.txt)
# and the per-tool ${TOOL_TAG}-resume-count.txt file would desynchronize if a
# tmpdir from a prior --coder=codex run were reused for --coder=cursor (or vice
# versa). Record the resolved coder on first invocation; bail clearly on any
# subsequent invocation whose --coder differs. Atomic write avoids torn reads.
# Only the external-implementer path writes/reads this sentinel — the claude
# fallback early-returned above without touching the tmpdir, so a prior claude
# run leaves no sentinel and a subsequent codex/cursor run is the first writer.
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
    # Match scripts/git-current-branch.sh / ship-pr bump guard: symbolic-ref is
    # empty on detached HEAD; rev-parse --abbrev-ref mis-reports "HEAD".
    {
        git -C "$REPO_ROOT" symbolic-ref -q --short HEAD 2>/dev/null || true
    } > "$SPAWN_BRANCH_FILE.tmp"
    mv "$SPAWN_BRANCH_FILE.tmp" "$SPAWN_BRANCH_FILE"
fi
SPAWN_BRANCH=$(tr -d '\r\n' < "$SPAWN_BRANCH_FILE" || true)

# Bail if spawned on a protected branch during an issue-anchored implement run.
# Issue identity may live in parent-issue.md (Step 0.5) while session-env does
# not always persist ISSUE_NUMBER; treat either durable parent-issue ISSUE_NUMBER
# or the presence of session-env as sufficient signal that this is an /implement
# tmpdir (fail-closed on main/master). Fork mode skips via FORKED_TARGET.
SESSION_ENV_FILE="$TMPDIR_ARG/session-env.sh"
PARENT_ISSUE_FILE="$TMPDIR_ARG/parent-issue.md"
_issue_from_parent=""
if [[ -f "$PARENT_ISSUE_FILE" ]]; then
    _issue_from_parent=$(awk 'BEGIN{FS="="} /^ISSUE_NUMBER=/ { print $2; exit }' "$PARENT_ISSUE_FILE" 2>/dev/null || true)
    _issue_from_parent=${_issue_from_parent//$'\r'/}
fi
_forked_target="false"
if [[ -f "$SESSION_ENV_FILE" ]]; then
    _forked_target=$("$PLUGIN_ROOT/scripts/read-session-env-key.sh" --file "$SESSION_ENV_FILE" --key FORKED_TARGET --default "false" 2>/dev/null || printf '%s\n' "false")
fi
_issue_anchored=false
if [[ -n "$_issue_from_parent" ]]; then
    _issue_anchored=true
elif [[ -f "$SESSION_ENV_FILE" ]]; then
    _issue_anchored=true
fi
# Legacy spawn files may still contain "HEAD" from older rev-parse --abbrev-ref captures.
if [[ "$_forked_target" != "true" && "$_issue_anchored" == "true" ]]; then
    if [[ -z "$SPAWN_BRANCH" || "$SPAWN_BRANCH" == "HEAD" ]]; then
        emit_bailed "detached-head-prohibited"
    fi
fi
if [[ "$SPAWN_BRANCH" == "main" || "$SPAWN_BRANCH" == "master" ]]; then
    if [[ "$_forked_target" != "true" && "$_issue_anchored" == "true" ]]; then
        emit_bailed "main-branch-prohibited"
    fi
fi

if [[ ! -f "$PLUGIN_JSON_BASELINE_FILE" ]]; then
    if [[ -f "$REPO_ROOT/.claude-plugin/plugin.json" ]]; then
        git -C "$REPO_ROOT" hash-object "$REPO_ROOT/.claude-plugin/plugin.json" > "$PLUGIN_JSON_BASELINE_FILE.tmp"
    else
        # Empty file is the canonical absent-sentinel — matches the "" produced by
        # the post-implementer absent branch in Step 6b, and round-trips cleanly
        # through `$(cat …)` below (no trailing-newline stripping mismatch). #1475.
        : > "$PLUGIN_JSON_BASELINE_FILE.tmp"
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
        # This is a corrupt dispatcher state file, not manifest validation; do
        # not route it through malformed-manifest recovery.
        emit_bailed "manifest-schema-invalid"
    fi
fi
if [[ -n "$ANSWERS_FILE" ]]; then
    [[ -f "$ANSWERS_FILE" ]] || { larch_err "step2-implement.sh: --answers given but path does not exist: $ANSWERS_FILE"; exit 2; }
    RESUME_COUNT=$((RESUME_COUNT + 1))
    printf '%s\n' "$RESUME_COUNT" > "$RESUME_COUNT_FILE.tmp"
    mv "$RESUME_COUNT_FILE.tmp" "$RESUME_COUNT_FILE"
fi
if (( RESUME_COUNT > 5 )); then
    emit_bailed "qa-loop-exceeded"
fi

# Step 3: clean stale implementer outputs from prior invocations BEFORE launching.
rm -f "$MANIFEST_PATH" "$MANIFEST_RAW_PATH" "$QA_PENDING_PATH" "$TRANSCRIPT_PATH" "$SIDECAR_LOG"

# Recovery baseline: capture the pre-launch working tree once, before either
# external implementer attempt. The malformed-manifest recovery path uses this
# NUL-delimited porcelain snapshot and companion content digests to distinguish
# implementer edits from pre-existing dirty files.
write_prelaunch_recovery_baseline

# Step 4: launch external implementer. Up to 1 retry on transient failure (timeout / non-zero
# exit before manifest written) — but only when post-failure state is clean.
if [[ "$WORKFLOW_PATH" == "HARD" ]]; then
    LAUNCHER_TIMEOUT=7200
else
    LAUNCHER_TIMEOUT=3600
fi

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
    if [[ -n "${LARCH_TOKEN_BUDGET_CAP_IMPLEMENT:-}" ]]; then
        launcher_args+=(--token-budget-cap "$LARCH_TOKEN_BUDGET_CAP_IMPLEMENT")
    fi
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
LAUNCHER_STATUS=$(printf '%s\n' "$LAUNCHER_OUT" | awk -F= '$1=="STATUS"{print $2; exit}')

# Default to 'false' / 99 when missing (e.g., launcher itself crashed before emitting).
LAUNCHER_EXIT=${LAUNCHER_EXIT:-99}
MANIFEST_WRITTEN=${MANIFEST_WRITTEN:-false}

# Budget-cap short-circuit: launcher emits STATUS=cap_hit when the per-step
# token budget is exhausted; surface a clean bail instead of retrying.
if [[ "$LAUNCHER_STATUS" == "cap_hit" ]]; then
    emit_bailed "cap_hit"
fi

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
        LAUNCHER_STATUS=$(printf '%s\n' "$LAUNCHER_OUT" | awk -F= '$1=="STATUS"{print $2; exit}')
        LAUNCHER_EXIT=${LAUNCHER_EXIT:-99}
        MANIFEST_WRITTEN=${MANIFEST_WRITTEN:-false}
        if [[ "$LAUNCHER_STATUS" == "cap_hit" ]]; then
            emit_bailed "cap_hit"
        fi
    fi
fi

if [[ "$WRAPPER_EXIT" != "0" ]]; then
    emit_bailed "$RUNTIME_FAILURE_TOKEN"
fi

if [[ "$MANIFEST_WRITTEN" != "true" ]]; then
    emit_bailed "$RUNTIME_FAILURE_TOKEN"
fi

# A non-zero launcher exit normally fails the run. The one carve-out (issue
# #3383): the Codex implementer atomically wrote a complete, well-formed
# manifest and only THEN exited non-zero — a self-verification step failing
# after the implementation work was already finished. Hard-bailing there
# discarded a finished manifest and stranded the branch with every edit
# uncommitted. Salvage it instead: fall through to the Step 5 validation and
# Step 7b dispatcher commit, annotating the run with WARN_CODEX_NONZERO_EXIT.
# The earlier WRAPPER_EXIT!=0 (launcher script itself crashed) and
# MANIFEST_WRITTEN!=true gates remain hard bails above — only a trustworthy
# on-disk complete manifest is salvageable, and Step 5/6/7 still validate it
# in full. Salvage is intentionally Codex-only: Cursor runs unsandboxed and has
# no offline complete-path harness in test-step2-dispatch.sh, so it keeps the
# conservative hard-bail (classified launcher-parity asymmetry; see
# step2-implement.md and .claude/rules/external-tool-launcher-parity.md).
if [[ "$LAUNCHER_EXIT" != "0" ]]; then
    if [[ "$CODER" == "codex" ]] && manifest_on_disk_is_salvageable_complete; then
        WARN_NONZERO_EXIT_SALVAGE=true
        if [[ -x "$PLUGIN_ROOT/scripts/append-execution-issue.sh" && -d "$TMPDIR_ARG" ]]; then
            "$PLUGIN_ROOT/scripts/append-execution-issue.sh" \
                --log "$TMPDIR_ARG/execution-issues.md" \
                --category Warnings \
                --entry "Step 4 — $TOOL_TAG exited non-zero (LAUNCHER_EXIT=$LAUNCHER_EXIT) after atomically writing a complete manifest; not discarding it — continuing to validation/commit ($NONZERO_EXIT_WARN_TOKEN=true). A self-verification step likely failed after the implementation work completed." >/dev/null 2>&1 || true
        fi
    else
        emit_bailed "$RUNTIME_FAILURE_TOKEN"
    fi
fi

# Step 5: validate manifest schema with jq.
[[ -s "$MANIFEST_PATH" ]] || emit_bailed "manifest-missing"
cp "$MANIFEST_PATH" "$MANIFEST_RAW_PATH"

# Pull status field; verify schema_version and status enum.
STATUS=$(jq -r 'if type=="object" then .status // "" else "" end' "$MANIFEST_RAW_PATH" 2>/dev/null || true)
SCHEMA_VERSION=$(jq -r 'if type=="object" then .schema_version // "" else "" end' "$MANIFEST_RAW_PATH" 2>/dev/null || true)

if [[ -n "$SCHEMA_VERSION" && "$SCHEMA_VERSION" != "1" ]]; then
    emit_bailed "manifest-schema-invalid"
fi
if [[ "$SCHEMA_VERSION" != "1" ]]; then
    emit_manifest_invalid_or_recover
fi
case "$STATUS" in
    complete|needs_qa|bailed) ;;
    *) emit_manifest_invalid_or_recover ;;
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
        ' "$MANIFEST_RAW_PATH" >/dev/null 2>&1 || emit_manifest_invalid_or_recover
        ;;
    needs_qa)
        if ! jq -e '
            (.needs_qa | type == "object") and
            (.needs_qa.questions | type == "array" and length > 0)
        ' "$MANIFEST_RAW_PATH" >/dev/null 2>&1; then
            # Attempt repair: normalize qa-pending.json from non-standard items[]
            # format when manifest.needs_qa.questions is absent/malformed.
            _did_repair=false
            if [[ -s "$QA_PENDING_PATH" ]] \
               && jq -e '(.items | type == "array" and length > 0)' "$QA_PENDING_PATH" >/dev/null 2>&1; then
                _REPAIRED_QA="$TMPDIR_ARG/qa-pending-repaired.json"
                if jq '{questions: [.items | to_entries[] | {
                        id: "q\(.key + 1)",
                        text: ([
                            if (.value.area // "") != "" then "Area: \(.value.area)" else empty end,
                            if (.value.risk // "") != "" then "Risk: \(.value.risk)" else empty end,
                            if (.value.suggested_check // "") != "" then "Suggested check: \(.value.suggested_check)" else empty end
                        ] | join(". "))
                    }]}' "$QA_PENDING_PATH" > "$_REPAIRED_QA" 2>/dev/null \
                   && jq -e '(.questions | type == "array" and length > 0)' "$_REPAIRED_QA" >/dev/null 2>&1; then
                    cp "$_REPAIRED_QA" "$QA_PENDING_PATH"
                    _did_repair=true
                fi
            fi
            if [[ "$_did_repair" != "true" ]]; then
                emit_bailed "manifest-schema-invalid"
            fi
        fi
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
            || emit_manifest_invalid_or_recover
        ;;
esac

# Step 6: post-implementer mechanical validation (only meaningful for complete/needs_qa;
# bailed is passed through verbatim).
if [[ "$STATUS" != "bailed" ]]; then
    run_post_implementer_safety_gates
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

    # 7a.1: warn when the implementer left working-tree changes not declared
    # in the manifest. This is diagnostic only; the dispatcher still commits
    # the working tree below and leaves review/pre-commit as downstream gates.
    # Note: this check compares declared manifest paths against working-tree
    # paths; it does NOT cross-reference the plan's "Files to modify" section.
    # May include pre-existing dirty paths if the tree was not clean at launch.
    APPEND_TOOL="$PLUGIN_ROOT/scripts/append-execution-issue.sh"
    if [[ -x "$APPEND_TOOL" && -d "$TMPDIR_ARG" ]]; then
        {
            WT_PATHS_FILE=$(mktemp "$TMPDIR_ARG/oos-working-tree.XXXXXX")
            MANIFEST_PATHS_FILE=$(mktemp "$TMPDIR_ARG/oos-manifest.XXXXXX")
            OOS_PATHS_FILE=$(mktemp "$TMPDIR_ARG/oos-paths.XXXXXX")

            # Use --name-only and ls-files to avoid porcelain format parsing;
            # both handle paths with spaces correctly.
            {
                git -C "$REPO_ROOT" diff --name-only HEAD 2>/dev/null
                git -C "$REPO_ROOT" ls-files --others --exclude-standard 2>/dev/null
            } | sort -u > "$WT_PATHS_FILE"

            MANIFEST_PATHS=$(jq -r '[.files_touched[].path, .tests_added_or_modified[]] | .[]' \
                "$MANIFEST_RAW_PATH" 2>/dev/null) || MANIFEST_PATHS=""
            if [[ -n "$MANIFEST_PATHS" ]]; then
                printf '%s\n' "$MANIFEST_PATHS" | sort -u > "$MANIFEST_PATHS_FILE"
            else
                : > "$MANIFEST_PATHS_FILE"
            fi
            comm -23 "$WT_PATHS_FILE" "$MANIFEST_PATHS_FILE" > "$OOS_PATHS_FILE"

            OOS_COUNT=$(wc -l < "$OOS_PATHS_FILE" | tr -d '[:space:]')
            if [[ "${OOS_COUNT:-0}" != "0" ]]; then
                OOS_LIST=$(sed -n '1,5s/^/- /p' "$OOS_PATHS_FILE")
                OOS_ENTRY=$(printf 'Step 7a.1 — %s working-tree path(s) not declared in manifest files_touched/tests_added_or_modified (may include pre-existing dirty files). First 5:\n%s' "$OOS_COUNT" "$OOS_LIST")
                "$APPEND_TOOL" \
                    --log "$TMPDIR_ARG/execution-issues.md" \
                    --category Warnings \
                    --entry "$OOS_ENTRY" >/dev/null 2>&1 || true
            fi
            rm -f "$WT_PATHS_FILE" "$MANIFEST_PATHS_FILE" "$OOS_PATHS_FILE"
        } || true
    fi

    # 7b: dispatcher commits on the external implementer's behalf, using manifest.commit_message.
    # Codex stays inside `workspace-write` sandbox semantics (which forbids
    # .git/ writes); Cursor runs unsandboxed re .git/ but its
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
    "$PLUGIN_ROOT/scripts/larch-log-flush.sh" || true
fi

# Step 8: sanitization. Apply scripts/redact-secrets.sh to text fields, then
# write the canonical manifest.json (replacing the raw copy).
REDACT="$PLUGIN_ROOT/scripts/redact-secrets.sh"
# Fail closed if the redactor file exists but is not executable — a sparse
# checkout or broken perms must NOT silently emit raw manifest text into
# downstream public surfaces (release notes, PR body, GitHub issues).
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

    # oos_observations: public-boundary fields plus structured focus_area.
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
            fa=$(jq -r ".oos_observations[$i][\"focus-area\"] // .oos_observations[$i].focus_area // \"\"" "$TMP_SAN.0")
            ti_san=$(sanitize_string "$ti")
            de_san=$(sanitize_string "$de")
            fa_san=$(sanitize_string "$fa")
            if [[ "$first" == "true" ]]; then first=false; else printf ',' >> "$SAN_OOS_FILE"; fi
            jq -Rn --arg t "$ti_san" --arg d "$de_san" --arg p "$ph" --arg fa "$fa_san" \
                '{title: $t, description: $d, phase: $p} + (if $fa == "" then {} else {"focus-area": $fa} end)' >> "$SAN_OOS_FILE"
            i=$((i + 1))
        done
        printf ']' >> "$SAN_OOS_FILE"
        jq --slurpfile oo "$SAN_OOS_FILE" '.oos_observations = $oo[0]' "$TMP_SAN.0" > "$TMP_SAN.1"
        mv "$TMP_SAN.1" "$TMP_SAN.0"
    fi

    mv "$TMP_SAN.0" "$MANIFEST_PATH"
fi

# Step 8b: materialize external-implementer manifest OOS before any
# downstream OOS_PENDING trigger can inspect only file-based accepted-OOS
# artifacts. Fail closed when the manifest contains observations; fail open
# with a Tool Failures breadcrumb when there is no OOS to lose.
if [[ "$STATUS" == "complete" ]]; then
    MATERIALIZE_OOS="$PLUGIN_ROOT/skills/implement/scripts/materialize-manifest-oos.sh"
    MAT_OOS_COUNT=""
    MAT_OOS_COUNT_RC=0
    MAT_OOS_COUNT=$(jq 'if has("oos_observations") and (.oos_observations | type != "array") then error("oos_observations must be an array") elif (.oos_observations | type == "array") then (.oos_observations | length) else 0 end' "$MANIFEST_PATH" 2>/dev/null) || MAT_OOS_COUNT_RC=$?
    MAT_OOS_LOG="$TMPDIR_ARG/materialize-manifest-oos.log"
    if [[ -x "$MATERIALIZE_OOS" ]]; then
        MAT_RC=0
        bash "$MATERIALIZE_OOS" --manifest-path "$MANIFEST_PATH" --implement-tmpdir "$TMPDIR_ARG" >"$MAT_OOS_LOG" 2>&1 || MAT_RC=$?
        if [[ "$MAT_RC" -ne 0 ]]; then
            APPEND_TOOL="$PLUGIN_ROOT/scripts/append-tool-failure.sh"
            if [[ -x "$APPEND_TOOL" ]]; then
                "$APPEND_TOOL" \
                    --log "$TMPDIR_ARG/execution-issues.md" \
                    --site "step2-materialize-manifest-oos" \
                    --tool "materialize-manifest-oos.sh" \
                    --exit-code "$MAT_RC" \
                    --category "Tool Failures" \
                    --output-file "$MAT_OOS_LOG" \
                    --redact >/dev/null 2>&1 || true
            fi
            if [[ "$MAT_OOS_COUNT_RC" -ne 0 || "${MAT_OOS_COUNT:-0}" -gt 0 ]]; then
                emit_bailed "manifest-oos-materialization-failed"
            fi
        fi
    else
        printf 'materialize helper missing or not executable: %s\n' "$MATERIALIZE_OOS" >"$MAT_OOS_LOG"
        APPEND_TOOL="$PLUGIN_ROOT/scripts/append-tool-failure.sh"
        if [[ -x "$APPEND_TOOL" ]]; then
            "$APPEND_TOOL" \
                --log "$TMPDIR_ARG/execution-issues.md" \
                --site "step2-materialize-manifest-oos" \
                --tool "materialize-manifest-oos.sh" \
                --exit-code "127" \
                --category "Tool Failures" \
                --output-file "$MAT_OOS_LOG" \
                --redact >/dev/null 2>&1 || true
        fi
        if [[ "$MAT_OOS_COUNT_RC" -ne 0 || "${MAT_OOS_COUNT:-0}" -gt 0 ]]; then
            emit_bailed "manifest-oos-materialization-failed"
        fi
    fi
fi

# Step 9: emit final KV envelope. ORCHESTRATOR_EDIT_AUTHORITY is the gate the
# orchestrator uses to decide whether main-agent Edit/Write is permitted at
# Step 2.4 — `allowed` ONLY when STATUS=claude_fallback (emitted upstream),
# `forbidden` on every external-implementer outcome here. See SKILL.md NEVER
# #10 and the Step 2 entry preconditions matrix.
case "$STATUS" in
    complete)
        emit_kv STATUS complete
        emit_kv TOOL "$TOOL_TAG"
        emit_kv MANIFEST "$MANIFEST_PATH"
        emit_kv TRANSCRIPT "$TRANSCRIPT_PATH"
        emit_kv SIDECAR_LOG "$SIDECAR_LOG"
        # Advisory salvage marker (issue #3383): the implementer exited non-zero
        # after writing this complete manifest and the dispatcher salvaged it.
        if [[ "$WARN_NONZERO_EXIT_SALVAGE" == "true" && -n "$NONZERO_EXIT_WARN_TOKEN" ]]; then
            emit_kv "$NONZERO_EXIT_WARN_TOKEN" true
        fi
        emit_kv ORCHESTRATOR_EDIT_AUTHORITY forbidden
        ;;
    needs_qa)
        emit_kv STATUS needs_qa
        emit_kv TOOL "$TOOL_TAG"
        emit_kv MANIFEST "$MANIFEST_PATH"
        emit_kv QA_PENDING "$QA_PENDING_PATH"
        emit_kv TRANSCRIPT "$TRANSCRIPT_PATH"
        emit_kv SIDECAR_LOG "$SIDECAR_LOG"
        emit_kv ORCHESTRATOR_EDIT_AUTHORITY forbidden
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
        emit_kv STATUS bailed
        emit_kv REASON "$BR"
        emit_kv TOOL "$TOOL_TAG"
        emit_kv MANIFEST "$MANIFEST_PATH"
        emit_kv TRANSCRIPT "$TRANSCRIPT_PATH"
        emit_kv SIDECAR_LOG "$SIDECAR_LOG"
        emit_kv ORCHESTRATOR_EDIT_AUTHORITY forbidden
        if [[ ! -s "${TRANSCRIPT_PATH}.stderr-tail" ]]; then
            if [[ -s "${TRANSCRIPT_PATH}.diag" ]]; then
                write_failed_agent_stderr_tail "${TRANSCRIPT_PATH}.diag" "$TRANSCRIPT_PATH" || true
            elif [[ -s "$SIDECAR_LOG" ]]; then
                write_failed_agent_stderr_tail "$SIDECAR_LOG" "$TRANSCRIPT_PATH" || true
            fi
        fi
        emit_failed_agent_stderr_tail_larch_err "$TRANSCRIPT_PATH" || true
        ;;
esac
exit 0
