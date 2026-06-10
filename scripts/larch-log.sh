#!/usr/bin/env bash
# larch-log.sh — router for committed larch-logs artifacts.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)"
# Resolve repo root from caller's CWD so git operations target the consumer
# repo, not the plugin install cache. Remains empty outside a git worktree.
REPO_ROOT="$(git -C "$PWD" rev-parse --show-toplevel 2>/dev/null)" || true

# shellcheck source=scripts/lib-larch-log.sh
# shellcheck disable=SC1091
source "$SCRIPT_DIR/lib-larch-log.sh"
# shellcheck source=scripts/lib-redact.sh
# shellcheck disable=SC1091
source "$SCRIPT_DIR/lib-redact.sh"

usage() {
    cat <<'USAGE' >&2
Usage:
  larch-log.sh init --log-root D --skill S --run-id R [--parent-skill P] [--issue N]
  larch-log.sh write --log-root D --skill S --run-id R --batch B --input-file F
  larch-log.sh write-round --log-root D --skill S --run-id R --round N --source-dir DIR
  larch-log.sh append --log-root D --skill S --run-id R --batch B --record-file F
  larch-log.sh exists --log-root D --skill S --run-id R --batch B
  larch-log.sh commit --log-root D --skill S --run-id R
  larch-log.sh manifest --log-root D --skill S --run-id R --field K=V...
USAGE
}

json_escape() {
    if command -v jq >/dev/null 2>&1; then
        jq -Rn --arg v "$1" '$v'
    else
        printf '"%s"' "$(printf '%s' "$1" | sed 's/\\/\\\\/g; s/"/\\"/g')"
    fi
}

now_utc() {
    date -u '+%Y-%m-%dT%H:%M:%SZ'
}

plugin_version() {
    "$SCRIPT_DIR/read-plugin-version.sh" 2>/dev/null | awk -F= '/^LARCH_PLUGIN_VERSION=/{print $2; exit}'
}

require_common() {
    [ -n "${SKILL:-}" ] || { usage; larch_log_fail 1 "--skill is required"; }
    [ -n "${RUN_ID:-}" ] || { usage; larch_log_fail 1 "--run-id is required"; }
    larch_log_validate_slug skill "$SKILL"
    larch_log_validate_slug run-id "$RUN_ID"
}

require_log_root() {
    if [ -n "${LOG_ROOT:-}" ]; then
        [[ "$LOG_ROOT" == /* ]] || larch_log_fail 1 "--log-root must be an absolute path: $LOG_ROOT"
        export LARCH_LOG_ROOT="$LOG_ROOT"
        return 0
    fi
    if [ -n "${LARCH_LOG_ROOT:-}" ]; then
        [[ "$LARCH_LOG_ROOT" == /* ]] || larch_log_fail 1 "LARCH_LOG_ROOT must be an absolute path: $LARCH_LOG_ROOT"
        return 0
    fi
    larch_log_fail 1 "--log-root is required (or export LARCH_LOG_ROOT for test isolation)"
}

round_artifact_included() {
    local name="$1"
    case "$name" in
        # Excluded raw per-specialist reviewer outputs and their sidecars.
        # Exact-form deny; phase/retry variants are denied in the next branch.
        cursor-specialist-*-output.txt|cursor-specialist-*-output.txt.meta|cursor-specialist-*-output.txt.json|cursor-specialist-*-output.txt.cap-hit|codex-specialist-*-output.txt|codex-specialist-*-output.txt.meta|codex-specialist-*-output.txt.json|codex-specialist-*-output.txt.cap-hit)
            return 1
            ;;
        # Phase, retry, and NS-retry specialist outputs are raw transcripts or
        # sidecars; default committed logs use round-meta reviewer_signals instead.
        cursor-specialist-*-output-phase*.txt|cursor-specialist-*-output-phase*.txt.*|cursor-specialist-*-output-retry.txt|cursor-specialist-*-output-retry.txt.*|codex-specialist-*-output-phase*.txt|codex-specialist-*-output-phase*.txt.*|codex-specialist-*-output-retry.txt|codex-specialist-*-output-retry.txt.*)
            return 1
            ;;
        # `*.failure-diag` is DENIED in the per-output write-round path on
        # purpose (#3713 F14): the canonical durable implement carrier is the
        # `vendor-failure-diagnostics` batch (sole durable path), so committing
        # the per-output carrier here too would double-commit. The raw
        # `*.sidecar.history` / `*.events.history` archives are never committed.
        *.dirty-tree|*.untracked-baseline|*.done|*.diag|*.sidecar|*.events.jsonl|*.sidecar.history|*.events.history|*.failure-diag|*-output.txt.prompt|*-output-*.txt.prompt|coder-output.log|coder-codex.log)
            return 1
            ;;
        # Excluded vote prompts (the ballot is byte-identical across voters
        # and is already captured by voting-tally.md plus the per-voter outputs).
        *-vote-prompt.txt)
            return 1
            ;;
        # Dynamic Codex retry transcripts are deliberately excluded from
        # durable logs; retry bookkeeping remains private session state.
        # Keep this deny before the broad *-output* allow below.
        dyn-*-codex-output-retry*.txt|dyn-*-codex-output-retry*.txt.meta|dyn-*-codex-output-retry*.txt.json|dyn-*-codex-output-retry*.txt.cap-hit)
            return 1
            ;;
        # Excluded zero-byte placeholders (observed empty in every committed run).
        skipped-findings.security.md|submodule-paths.txt|submodule-scrub.log|submodule-revert.log|coder-commit.log)
            return 1
            ;;
        # Dynamic reviewer prompt files: each re-embeds the full diff, plan,
        # and feature description; only the archetype section differs and is
        # already captured by the committed reviewer-dyn-*.md definition (~2 KB).
        dyn-*-prompt.md)
            return 1
            ;;
        # Raw scout manifests: byte-identical to the cooked .json in nearly all
        # committed runs; the cooked .json is canonical.
        scout-round*-manifest.json.raw)
            return 1
            ;;
        # Proposal-stage finding aggregates: projections of review-findings-full.jsonl.
        # Drop at staging time — the jsonl is the canonical store; jq reconstructs any
        # view on demand (see scripts/render-findings-view.sh).
        findings.md|accepted-findings.md|rejected-findings-full.md|oos.md)
            return 1
            ;;
        dyn-*-codex-output.txt|dyn-*-codex-output-phase*.txt|dyn-*-codex-output.txt.meta|dyn-*-codex-output-phase*.txt.meta|dyn-*-codex-output.txt.json|dyn-*-codex-output-phase*.txt.json|dyn-*-codex-output.txt.cap-hit|dyn-*-codex-output-phase*.txt.cap-hit)
            [[ "${LARCH_FLUSH_DEBUG:-}" == "1" ]]
            return $?
            ;;
        prune-decision.env|prune-nit.env|findings-classification.tsv|scout-archetype-yield.tsv|rejected-findings.md|oos-accepted-review.md|review-round-summary.md|voting-tally.md|aggregator-validate.stderr|aggregator-dispatch.stderr|review-dirty-tree-summary.env|panel-manifest.ndjson|code-voter-slots.ndjson|coder-prompt.md|coder-tool.txt|coder-cursor.log)
            return 0
            ;;
        cursor-ci-stall-*.json)
            return 0
            ;;
        # Archetype definition files are pooled in larch-logs/shared/archetypes/
        # and referenced by hash via archetype_ref in panel-manifest.ndjson;
        # they are not committed individually per round.
        reviewer-dyn-*.md)
            return 1
            ;;
        *-vote-output*.txt|*-vote-output*.txt.*|*-ns-retry*.txt|*-ns-retry*.txt.*|*-output-first-pass.txt|*-output.txt|*-output-*.txt|*-output.txt.meta|*-output-*.txt.meta|*-output.txt.json|*-output-*.txt.json|*-output.txt.cap-hit|*-output-*.txt.cap-hit)
            [[ "${LARCH_FLUSH_DEBUG:-}" == "1" ]]
            return $?
            ;;
        dirty-checkpoint-*.env|voter*-diag.txt|*-parse-rate-diag.txt|skipped-findings*.md|scout-round*-status.env|scout-round*-manifest.json)
            return 0
            ;;
        *)
            return 1
            ;;
    esac
}

# Returns 0 when the file should be consolidated into round-meta.json rather
# than committed as an individual artifact.
is_round_sidecar_file() {
    case "$1" in
        review-tally.env|collector-results.env|collect-agent-results.log|review-summary.json|coder.env|coder-codex.wrapper.log|coder-cursor.wrapper.log) return 0 ;;
        *) return 1 ;;
    esac
}

stage_round_artifact() {
    local input="$1"
    local output="$2"
    local name trim_tmp
    name="$(basename "$input")"
    trim_tmp="$(mktemp "${TMPDIR:-/tmp}/larch-log-round-trim.XXXXXX")" || larch_log_fail 2 "cannot create round trim temp"
    (
        trap 'rm -f "$trim_tmp"' EXIT
        case "$name" in
            *.meta)
                larch_redact_strip_meta_cmd_json "$input" "$trim_tmp" || larch_log_fail 2 "cannot trim meta sidecar: $input"
                ;;
            *-output.txt.json|*-output-*.txt.json)
                larch_redact_strip_json_result "$input" "$trim_tmp" || larch_log_fail 2 "cannot trim json sidecar: $input"
                ;;
            *-vote-output.txt|*-vote-output-*.txt)
                # Cap at 2 KB; per-finding vote lines are near the top, rationale prose below.
                # Covers *-vote-output-first-pass.txt via the *-vote-output-*.txt pattern.
                _orig_bytes=$(wc -c < "$input" | tr -d ' ')
                if [ "$_orig_bytes" -gt 2048 ]; then
                    head -c 2048 "$input" > "$trim_tmp" || larch_log_fail 2 "cannot cap vote output: $input"
                    printf '\n[TRUNCATED: original %s bytes]\n' "$_orig_bytes" >> "$trim_tmp"
                else
                    cp "$input" "$trim_tmp" || larch_log_fail 2 "cannot stage round artifact: $input"
                fi
                ;;
            *)
                cp "$input" "$trim_tmp" || larch_log_fail 2 "cannot stage round artifact: $input"
                ;;
        esac
        larch_log_redact_file "$trim_tmp" "$output"
    )
}

larch_log_breadcrumb_source_dir() {
    local root session_root
    if [ -n "${LARCH_BREADCRUMB_SOURCE_DIR:-}" ]; then
        printf '%s\n' "$LARCH_BREADCRUMB_SOURCE_DIR"
        return 0
    fi
    root="$(larch_log_root)"
    case "$root" in
        */larch-logs)
            # Returns session breadcrumbs/; quiet logs at session-root are staged via dirname in larch_log_publish_breadcrumbs_shared.
            session_root="${root%/larch-logs}"
            printf '%s/breadcrumbs\n' "$session_root"
            ;;
        *)
            return 1
            ;;
    esac
}

larch_log_copy_run_tree_without_breadcrumbs() {
    local src_path="$1" repo_path="$2" item base
    mkdir -p "$repo_path" || larch_log_fail 3 "cannot create repo log directory"
    for item in "$src_path"/*; do
        [ -e "$item" ] || continue
        base="$(basename "$item")"
        [ "$base" != "breadcrumbs" ] || continue
        cp -rp "$item" "$repo_path/" || larch_log_fail 3 "cannot copy logs from temp to repo"
    done
}

larch_log_publish_breadcrumbs() {
    local source_dir="$1" repo_path="$2"
    larch_log_publish_breadcrumbs_shared "$source_dir" "$repo_path/breadcrumbs" larch_log_publish_breadcrumbs_error
}

larch_log_publish_breadcrumbs_error() {
    larch_log_fail 3 "$1"
}

current_branch_is_default() {
    local current_branch default_branch
    current_branch="$(git -C "$REPO_ROOT" rev-parse --abbrev-ref HEAD 2>/dev/null || true)"
    [ -n "$current_branch" ] || return 1
    [ "$current_branch" != "HEAD" ] || return 1
    [ "$current_branch" != "main" ] || return 0
    [ "$current_branch" != "master" ] || return 0

    default_branch="$(
        git -C "$REPO_ROOT" symbolic-ref refs/remotes/origin/HEAD 2>/dev/null \
            | sed 's|^refs/remotes/origin/||'
    )" || default_branch=""
    [ -n "$default_branch" ] || return 1
    [ "$current_branch" = "$default_branch" ]
}

write_manifest_file() {
    local path="$1"
    local parent_skill="$2"
    local issue="$3"
    local ts version parent_json issue_json model_json effort_json operator_repo_root operator_cwd_json operator_repo_root_json tmp
    ts="$(now_utc)"
    version="$(plugin_version)"
    [ -n "$version" ] || version="unknown"
    operator_repo_root="$(git -C "$PWD" rev-parse --show-toplevel 2>/dev/null)" || true
    operator_cwd_json='"<OPERATOR_CWD>"'
    if [ -n "$operator_repo_root" ]; then
        operator_repo_root_json='"<REPO_ROOT>"'
    else
        operator_repo_root_json="null"
    fi
    if [ -n "$parent_skill" ]; then
        parent_json="$(json_escape "$parent_skill")"
    else
        parent_json="null"
    fi
    if [ -n "$issue" ]; then
        issue_json="$issue"
    else
        issue_json="null"
    fi
    model_json="$(json_escape "${CLAUDE_CODE_MODEL:-${CLAUDE_MODEL:-unknown}}")"
    effort_json="$(json_escape "${CLAUDE_CODE_EFFORT_LEVEL:-${CLAUDE_EFFORT:-unknown}}")"
    mkdir -p "$(dirname "$path")" || larch_log_fail 2 "cannot create manifest directory"
    tmp="$(mktemp "$(dirname "$path")/.tmp.manifest.XXXXXX")" || larch_log_fail 2 "cannot create manifest temp"
    cat > "$tmp" <<EOF
{
  "schema_version": 2,
  "skill": "$SKILL",
  "run_id": "$RUN_ID",
  "operator_cwd": $operator_cwd_json,
  "operator_repo_root": $operator_repo_root_json,
  "parent_skill": $parent_json,
  "issue_number": $issue_json,
  "larch_version": "$version",
  "model_roster": {"main": $model_json},
  "effort": $effort_json,
  "started_at": "$ts",
  "updated_at": "$ts",
  "attempt": 1,
  "superseded_by": null,
  "stalled_at_step": null,
  "steps_ran": {},
  "flags": {}
}
EOF
    mv -f "$tmp" "$path" || {
        rm -f "$tmp"
        larch_log_fail 2 "cannot publish manifest"
    }
}

cmd="${1:-}"
[ -n "$cmd" ] || { usage; exit 1; }
shift

case "$cmd" in
    init)
        LOG_ROOT=""; SKILL=""; RUN_ID=""; PARENT_SKILL=""; ISSUE=""
        while [ $# -gt 0 ]; do
            case "$1" in
                --log-root) LOG_ROOT="${2:?--log-root requires a value}"; shift 2 ;;
                --skill) SKILL="${2:?--skill requires a value}"; shift 2 ;;
                --run-id) RUN_ID="${2:?--run-id requires a value}"; shift 2 ;;
                --parent-skill) PARENT_SKILL="${2:?--parent-skill requires a value}"; shift 2 ;;
                --issue) ISSUE="${2:?--issue requires a value}"; shift 2 ;;
                *) usage; larch_log_fail 1 "unknown option for init: $1" ;;
            esac
        done
        require_log_root
        require_common
        [ -z "$PARENT_SKILL" ] || larch_log_validate_slug parent-skill "$PARENT_SKILL"
        case "$ISSUE" in ""|*[!0-9]*) [ -z "$ISSUE" ] || larch_log_fail 1 "invalid issue: $ISSUE" ;; esac
        path="$(larch_log_run_dir "$SKILL" "$RUN_ID")/manifest.json"
        if [ -f "$path" ]; then
            larch_log_emit_success "$path" false true
            exit 0
        fi
        write_manifest_file "$path" "$PARENT_SKILL" "$ISSUE"
        larch_log_emit_success "$path" true false
        ;;

    write)
        LOG_ROOT=""; SKILL=""; RUN_ID=""; BATCH=""; INPUT_FILE=""
        while [ $# -gt 0 ]; do
            case "$1" in
                --log-root) LOG_ROOT="${2:?--log-root requires a value}"; shift 2 ;;
                --skill) SKILL="${2:?--skill requires a value}"; shift 2 ;;
                --run-id) RUN_ID="${2:?--run-id requires a value}"; shift 2 ;;
                --batch) BATCH="${2:?--batch requires a value}"; shift 2 ;;
                --input-file) INPUT_FILE="${2:?--input-file requires a value}"; shift 2 ;;
                --commit) shift ;;
                *) usage; larch_log_fail 1 "unknown option for write: $1" ;;
            esac
        done
        require_log_root
        require_common
        [ -n "$BATCH" ] || larch_log_fail 1 "--batch is required"
        [ -f "$INPUT_FILE" ] || larch_log_fail 1 "input file not found: $INPUT_FILE"
        mode="$(larch_log_batch_mode "$BATCH")" || larch_log_fail 1 "unknown batch: $BATCH"
        [ "$mode" = "replace" ] || larch_log_fail 1 "batch $BATCH is append-only; use append"
        path="$(larch_log_batch_path "$SKILL" "$RUN_ID" "$BATCH")"
        tmp="$(mktemp "${TMPDIR:-/tmp}/larch-log-write.XXXXXX")" || larch_log_fail 2 "cannot create temp payload"
        _cap_tmp=""
        trap 'rm -f "${tmp:-}" "${_cap_tmp:-}"' EXIT
        larch_log_redact_file "$INPUT_FILE" "$tmp"
        # Trim large batches at staging time (cap + byte-count marker).
        case "$BATCH" in
            codex-impl-transcript)
                _orig_bytes=$(wc -c < "$tmp" | tr -d ' ')
                if [ "$_orig_bytes" -gt 8192 ]; then
                    _cap_tmp="$(mktemp "${TMPDIR:-/tmp}/larch-log-write-cap.XXXXXX")"
                    head -c 8192 "$tmp" > "$_cap_tmp"
                    printf '\n[TRUNCATED: original %s bytes]\n' "$_orig_bytes" >> "$_cap_tmp"
                    mv -f "$_cap_tmp" "$tmp" && _cap_tmp=""
                fi
                ;;
        esac
        larch_log_validate_batch_payload "$BATCH" "$tmp"
        if [ -f "$path" ] && cmp -s "$tmp" "$path"; then
            larch_log_emit_success "$path" false true
            exit 0
        fi
        larch_log_atomic_replace "$tmp" "$path"
        larch_log_emit_success "$path" true false
        ;;

    write-round)
        LOG_ROOT=""; SKILL=""; RUN_ID=""; ROUND_NUM=""; SOURCE_DIR=""
        round_dir=""; prev_round_dir=""; written=false; round_tmp=""; src=""; name=""; dest=""
        dynamic_dir=""; seen_round_artifacts=""; sidecar_paths=""; archetype_paths=""
        while [ $# -gt 0 ]; do
            case "$1" in
                --log-root) LOG_ROOT="${2:?--log-root requires a value}"; shift 2 ;;
                --skill) SKILL="${2:?--skill requires a value}"; shift 2 ;;
                --run-id) RUN_ID="${2:?--run-id requires a value}"; shift 2 ;;
                --round) ROUND_NUM="${2:?--round requires a value}"; shift 2 ;;
                --source-dir) SOURCE_DIR="${2:?--source-dir requires a value}"; shift 2 ;;
                *) usage; larch_log_fail 1 "unknown option for write-round: $1" ;;
            esac
        done
        require_log_root
        require_common
        case "$ROUND_NUM" in ''|*[!0-9]*) larch_log_fail 1 "--round must be a positive integer" ;; esac
        [ "$ROUND_NUM" -gt 0 ] || larch_log_fail 1 "--round must be a positive integer"
        [ -d "$SOURCE_DIR" ] || larch_log_fail 1 "source directory not found: $SOURCE_DIR"
        [ ! -L "$SOURCE_DIR" ] || larch_log_fail 1 "source directory must not be a symlink: $SOURCE_DIR"
        dynamic_dir="$SOURCE_DIR/dynamic-archetypes"
        [ ! -L "$dynamic_dir" ] || larch_log_fail 2 "dynamic-archetypes must not be a symlink: $dynamic_dir"

        round_dir="$(larch_log_run_dir "$SKILL" "$RUN_ID")/round-$ROUND_NUM"
        prev_round_dir="$(larch_log_run_dir "$SKILL" "$RUN_ID")/round-$((ROUND_NUM - 1))"
        mkdir -p "$round_dir" || larch_log_fail 2 "cannot create round log directory: $round_dir"
        written=false
        round_tmp="$(mktemp "${TMPDIR:-/tmp}/larch-log-round.XXXXXX")" || larch_log_fail 2 "cannot create round artifact temp"
        seen_round_artifacts="$(mktemp "${TMPDIR:-/tmp}/larch-log-round-seen.XXXXXX")" || larch_log_fail 2 "cannot create round basename temp"
        sidecar_paths="$(mktemp "${TMPDIR:-/tmp}/larch-log-round-sidecars.XXXXXX")" || larch_log_fail 2 "cannot create sidecar paths temp"
        archetype_paths="$(mktemp "${TMPDIR:-/tmp}/larch-log-round-archetypes.XXXXXX")" || larch_log_fail 2 "cannot create archetype paths temp"
        trap 'rm -f "${round_tmp:-}" "${seen_round_artifacts:-}" "${sidecar_paths:-}" "${archetype_paths:-}"' EXIT

        while IFS= read -r src || [ -n "$src" ]; do
            name="$(basename "$src")"

            # Sidecar files: collect for round-meta.json composition; not staged individually.
            if is_round_sidecar_file "$name"; then
                [ -f "$src" ] || continue
                [ ! -L "$src" ] || continue
                printf '%s\t%s\n' "$name" "$src" >> "$sidecar_paths"
                continue
            fi

            # Archetype definition files: collect for pool; not staged individually.
            case "$name" in
                reviewer-dyn-*.md)
                    [ -f "$src" ] || continue
                    [ ! -L "$src" ] || continue
                    printf '%s\n' "$src" >> "$archetype_paths"
                    continue
                    ;;
            esac

            round_artifact_included "$name" || continue
            [ -f "$src" ] || continue
            [ ! -L "$src" ] || continue

            # Skip aggregator output when byte-identical to findings.md (the staged
            # aggregate); avoids committing a third copy of the same content.
            case "$name" in
                aggregator-output.txt)
                    _agg_findings="${src%/*}/findings.md"
                    [ -f "$_agg_findings" ] && cmp -s "$src" "$_agg_findings" && continue
                    ;;
                # Scout manifest cross-round dedup: skip when identical to the
                # same-named file from the previous committed round.
                scout-round*-manifest.json)
                    _prev_m="$prev_round_dir/$name"
                    if [ -f "$_prev_m" ] && cmp -s "$src" "$_prev_m"; then
                        continue
                    fi
                    ;;
            esac

            prev_src="$(awk -F '\t' -v target="$name" '$1 == target { print $2; exit }' "$seen_round_artifacts")"
            if [ -n "$prev_src" ]; then
                larch_log_fail 2 "duplicate round artifact basename '$name' from $src and $prev_src"
            fi
            printf '%s\t%s\n' "$name" "$src" >> "$seen_round_artifacts"
            : > "$round_tmp"
            stage_round_artifact "$src" "$round_tmp"
            dest="$round_dir/$name"
            if [ -f "$dest" ] && cmp -s "$round_tmp" "$dest"; then
                continue
            fi
            larch_log_atomic_replace "$round_tmp" "$dest"
            written=true
        done < <({
            find "$SOURCE_DIR" -maxdepth 1 -type f -print
            if [ -d "$dynamic_dir" ]; then
                find "$dynamic_dir" -maxdepth 1 -type f -print
            fi
        } | LC_ALL=C sort)

        # Compose round-meta.json: reviewer_signals when reviewer outputs exist;
        # sidecar-driven sections when sidecar_paths is non-empty.
        _has_reviewer_outputs=false
        _larch_log_has_reviewer_outputs() {
            local _scan_dir="$1"
            find "$_scan_dir" -maxdepth 1 -type f \
                \( -name '*-output.txt' -o -name 'dyn-*-output.txt' \) \
                ! -name '*-vote-output*' ! -name '*-ns-retry*' ! -name '*-first-pass.txt' \
                -print -quit 2>/dev/null | grep -q .
        }
        if _larch_log_has_reviewer_outputs "$SOURCE_DIR"; then
            _has_reviewer_outputs=true
        elif [ -d "$dynamic_dir" ] && _larch_log_has_reviewer_outputs "$dynamic_dir"; then
            _has_reviewer_outputs=true
        fi
        if [ -s "$sidecar_paths" ] || [ "$_has_reviewer_outputs" = true ]; then
            : > "$round_tmp"
            if ! python3 - "$SOURCE_DIR" > "$round_tmp" <<'PYEOF'
import json, os, sys

src = sys.argv[1]
out = {}

def read_kv(path):
    d = {}
    with open(path) as f:
        for line in f:
            line = line.strip()
            if '=' in line and not line.startswith('#'):
                k, _, v = line.partition('=')
                d[k.strip()] = v.strip()
    return d

def read_raw(path):
    with open(path) as f:
        return f.read()

def read_json(path):
    with open(path) as f:
        try:
            return json.load(f)
        except Exception:
            return f.read()

for key, fname, kind in [
    ('tally',       'review-tally.env',          'kv'),
    ('collector',   'collector-results.env',      'raw'),
    ('summary',     'review-summary.json',        'json'),
    ('coder',       'coder.env',                  'kv'),
]:
    path = os.path.join(src, fname)
    if not os.path.isfile(path):
        continue
    if kind == 'kv':
        out[key] = read_kv(path)
    elif kind == 'raw':
        out[key] = read_raw(path)
    else:
        out[key] = read_json(path)

wl = {}
for tool, fname in [('cursor', 'coder-cursor.wrapper.log'), ('codex', 'coder-codex.wrapper.log')]:
    path = os.path.join(src, fname)
    if os.path.isfile(path):
        wl[tool] = read_raw(path)
if wl:
    out['wrapper_logs'] = wl


def first_substantive(path):
    try:
        with open(path, encoding="utf-8", errors="replace") as f:
            for line in f:
                stripped = line.strip()
                if stripped:
                    return stripped
    except OSError:
        pass
    return ""

def result_kind(line):
    low = (line or "").lower()
    if not line:
        return "UNKNOWN"
    if line.startswith('{'):
        try:
            data = json.loads(line)
            if data.get("no_issues_found") is True:
                return "NO_ISSUES_FOUND"
            if data.get("findings"):
                return "HAS_FINDINGS"
        except Exception:
            return "PARSE_FAILURE"
    if "no_issues_found" in low or low.startswith("no issues found"):
        return "NO_ISSUES_FOUND"
    if "not substantive" in low:
        return "NOT_SUBSTANTIVE"
    if "timeout" in low:
        return "TIMEOUT"
    if "finding" in low or "schema_version" in low:
        return "HAS_FINDINGS"
    return "UNKNOWN"

def trailing_content(path):
    first = True
    try:
        with open(path, encoding="utf-8", errors="replace") as f:
            for line in f:
                stripped = line.strip()
                if not stripped:
                    continue
                if first:
                    first = False
                    if result_kind(stripped) != "NO_ISSUES_FOUND":
                        return False
                    continue
                return True
    except OSError:
        return False
    return False

manifest = {}
for mf in ("panel-manifest.ndjson", "code-voter-slots.ndjson"):
    path = os.path.join(src, mf)
    if not os.path.isfile(path):
        continue
    try:
        with open(path, encoding="utf-8", errors="replace") as f:
            for row in f:
                try:
                    data = json.loads(row)
                except Exception:
                    continue
                base = os.path.basename(str(data.get("output") or ""))
                if base:
                    manifest[base] = data
    except OSError:
        pass
ALLOWED_NS_RETRY = frozenset({
    "NO_ISSUES_FOUND_TOO_THIN",
    "OUTPUT_EMPTY",
    "JSON_PARSE_FAIL",
    "UNKNOWN",
})

def normalize_ns_retry_reason(raw):
    token = (raw or "").strip()
    return token if token in ALLOWED_NS_RETRY else "UNKNOWN"

def iter_scan_dirs(root):
    yield root
    dyn = os.path.join(root, "dynamic-archetypes")
    if os.path.isdir(dyn) and not os.path.islink(dyn):
        yield dyn

signals = []
for scan_dir in iter_scan_dirs(src):
    try:
        names = sorted(os.listdir(scan_dir))
    except OSError:
        continue
    for name in names:
        if not (name.endswith(".txt") and "output" in name):
            continue
        if "vote-output" in name or "ns-retry" in name or name.endswith("-first-pass.txt"):
            continue
        path = os.path.join(scan_dir, name)
        try:
            if os.path.islink(path) or not os.path.isfile(path):
                continue
        except OSError:
            continue
        meta = manifest.get(name, {})
        first = first_substantive(path)
        ns_reason = ""
        stem = os.path.splitext(name)[0]
        for spath in (
            os.path.join(scan_dir, stem + "-ns-retry.txt.meta"),
            os.path.join(scan_dir, name + ".ns-retry.meta"),
            os.path.join(scan_dir, name + "-ns-retry.meta"),
            os.path.join(scan_dir, stem + "-ns-retry.json"),
            os.path.join(scan_dir, name + ".ns-retry.json"),
        ):
            try:
                if os.path.islink(spath) or not os.path.isfile(spath):
                    continue
            except OSError:
                continue
            try:
                raw = read_raw(spath).strip()
                for line in raw.splitlines():
                    if line.startswith("NS_RETRY_REASON="):
                        ns_reason = normalize_ns_retry_reason(line.partition("=")[2].strip())
                        break
                if not ns_reason:
                    try:
                        obj = json.loads(raw)
                        ns_reason = normalize_ns_retry_reason(
                            str(obj.get("reason") or obj.get("ns_retry_reason") or "")
                        )
                    except Exception:
                        ns_reason = ""
            except Exception:
                ns_reason = ""
            if ns_reason:
                break
        first_pass = os.path.join(scan_dir, name[:-4] + "-first-pass.txt") if name.endswith(".txt") else ""
        signals.append({
            "output_basename": name,
            "slot_label": str(meta.get("slot") or os.path.splitext(name)[0]),
            "result_kind": result_kind(first),
            "ns_retry_reason": ns_reason,
            "first_pass_trailing_content": trailing_content(first_pass),
        })
if signals:
    out["reviewer_signals"] = signals

if out:
    sys.stdout.write(json.dumps(out, ensure_ascii=False) + '\n')
PYEOF
            then
                larch_log_fail 2 "reviewer_signals composition failed for round $ROUND_NUM"
            fi
            if [ -s "$round_tmp" ]; then
                _rm_raw="$(mktemp "${TMPDIR:-/tmp}/larch-log-round-meta-red.XXXXXX")" || larch_log_fail 2 "cannot create round-meta redact temp"
                larch_log_redact_file "$round_tmp" "$_rm_raw"
                dest="$round_dir/round-meta.json"
                if [ -f "$dest" ] && cmp -s "$_rm_raw" "$dest"; then
                    rm -f "$_rm_raw"
                else
                    mv -f "$_rm_raw" "$dest" || { rm -f "$_rm_raw"; larch_log_fail 2 "cannot write round-meta.json"; }
                    written=true
                fi
            fi
        fi

        # Pool reviewer-dyn-*.md archetypes into larch-logs/shared/archetypes/
        # using content-addressed hashing (idempotent: existing hash → no write).
        # Updates panel-manifest.ndjson with archetype_ref for dynamic slots.
        if [ -s "$archetype_paths" ]; then
            _pool_dir="$(larch_log_root)/shared/archetypes"
            mkdir -p "$_pool_dir" || true
            _refs_tmp="$(mktemp "${TMPDIR:-/tmp}/larch-log-archetype-refs.XXXXXX")" || true
            if [ -n "$_refs_tmp" ]; then
                while IFS= read -r _arch_src || [ -n "$_arch_src" ]; do
                    [ -f "$_arch_src" ] || continue
                    _arch_sha="$(larch_log_sha256 "$_arch_src" | cut -c1-12 2>/dev/null || true)"
                    [ -n "$_arch_sha" ] || continue
                    _pool_path="$_pool_dir/$_arch_sha.md"
                    if [ ! -f "$_pool_path" ]; then
                        cp "$_arch_src" "$_pool_path" || continue
                    fi
                    _arch_name="$(basename "$_arch_src")"
                    printf '%s\t%s\n' "$_arch_name" "$_arch_sha" >> "$_refs_tmp"
                done < "$archetype_paths"

                # Update panel-manifest.ndjson with archetype_ref for dynamic slots.
                _pm="$round_dir/panel-manifest.ndjson"
                if [ -f "$_pm" ] && [ -s "$_refs_tmp" ]; then
                    _pm_new="$(mktemp "${TMPDIR:-/tmp}/larch-log-pm.XXXXXX")" || true
                    if [ -n "$_pm_new" ]; then
                        python3 - "$_pm" "$_refs_tmp" > "$_pm_new" <<'PYEOF' || true
import json, sys

pm_path, refs_path = sys.argv[1], sys.argv[2]
refs = {}
with open(refs_path) as f:
    for line in f:
        line = line.strip()
        if '\t' in line:
            fname, sha12 = line.split('\t', 1)
            if fname.startswith('reviewer-dyn-') and fname.endswith('.md'):
                slot = 'dyn-' + fname[len('reviewer-dyn-'):-len('.md')]
                refs[slot] = sha12
lines = []
with open(pm_path) as f:
    for line in f:
        stripped = line.rstrip('\n')
        if not stripped.strip():
            lines.append(line)
            continue
        try:
            obj = json.loads(stripped)
            slot = obj.get('slot', '')
            if slot in refs and 'archetype_ref' not in obj:
                obj['archetype_ref'] = refs[slot]
            lines.append(json.dumps(obj, ensure_ascii=False) + '\n')
        except (json.JSONDecodeError, ValueError):
            lines.append(line)
sys.stdout.write(''.join(lines))
PYEOF
                        if [ -s "$_pm_new" ] && ! cmp -s "$_pm_new" "$_pm"; then
                            mv -f "$_pm_new" "$_pm"
                            written=true
                        else
                            rm -f "$_pm_new"
                        fi
                    fi
                fi
                rm -f "$_refs_tmp"
            fi
        fi

        if [ "$written" = true ]; then
            larch_log_emit_success "$round_dir" true false
        else
            larch_log_emit_success "$round_dir" false true
        fi
        ;;

    append)
        LOG_ROOT=""; SKILL=""; RUN_ID=""; BATCH=""; RECORD_FILE=""
        while [ $# -gt 0 ]; do
            case "$1" in
                --log-root) LOG_ROOT="${2:?--log-root requires a value}"; shift 2 ;;
                --skill) SKILL="${2:?--skill requires a value}"; shift 2 ;;
                --run-id) RUN_ID="${2:?--run-id requires a value}"; shift 2 ;;
                --batch) BATCH="${2:?--batch requires a value}"; shift 2 ;;
                --record-file) RECORD_FILE="${2:?--record-file requires a value}"; shift 2 ;;
                *) usage; larch_log_fail 1 "unknown option for append: $1" ;;
            esac
        done
        require_log_root
        require_common
        [ -n "$BATCH" ] || larch_log_fail 1 "--batch is required"
        [ -f "$RECORD_FILE" ] || larch_log_fail 1 "record file not found: $RECORD_FILE"
        mode="$(larch_log_batch_mode "$BATCH")" || larch_log_fail 1 "unknown batch: $BATCH"
        [ "$mode" = "append" ] || larch_log_fail 1 "batch $BATCH is replace-only; use write"
        path="$(larch_log_batch_path "$SKILL" "$RUN_ID" "$BATCH")"
        dir="$(dirname "$path")"
        mkdir -p "$dir" || larch_log_fail 2 "cannot create log directory: $dir"
        redacted="$(mktemp "${TMPDIR:-/tmp}/larch-log-record.XXXXXX")" || larch_log_fail 2 "cannot create record temp"
        staged="$(mktemp "$dir/.tmp.$(basename "$path").XXXXXX")" || larch_log_fail 2 "cannot create append temp"
        trap 'rm -f "${redacted:-}" "${staged:-}"' EXIT
        larch_log_redact_file "$RECORD_FILE" "$redacted"
        larch_log_validate_batch_payload "$BATCH" "$redacted"
        [ -f "$path" ] && cat "$path" > "$staged"
        cat "$redacted" >> "$staged"
        tail_char="$(tail -c 1 "$staged" 2>/dev/null || true)"
        [ "$tail_char" = "" ] || printf '\n' >> "$staged"
        mv -f "$staged" "$path" || larch_log_fail 2 "cannot append log record"
        larch_log_emit_success "$path" true false
        ;;

    exists)
        LOG_ROOT=""; SKILL=""; RUN_ID=""; BATCH=""
        while [ $# -gt 0 ]; do
            case "$1" in
                --log-root) LOG_ROOT="${2:?--log-root requires a value}"; shift 2 ;;
                --skill) SKILL="${2:?--skill requires a value}"; shift 2 ;;
                --run-id) RUN_ID="${2:?--run-id requires a value}"; shift 2 ;;
                --batch) BATCH="${2:?--batch requires a value}"; shift 2 ;;
                *) usage; larch_log_fail 1 "unknown option for exists: $1" ;;
            esac
        done
        require_log_root
        require_common
        path="$(larch_log_batch_path "$SKILL" "$RUN_ID" "$BATCH")"
        if [ -f "$path" ]; then
            larch_log_emit_success "$path" false true
        else
            larch_log_emit_success "$path" false false
        fi
        ;;

    manifest)
        LOG_ROOT=""; SKILL=""; RUN_ID=""; FIELDS=()
        while [ $# -gt 0 ]; do
            case "$1" in
                --log-root) LOG_ROOT="${2:?--log-root requires a value}"; shift 2 ;;
                --skill) SKILL="${2:?--skill requires a value}"; shift 2 ;;
                --run-id) RUN_ID="${2:?--run-id requires a value}"; shift 2 ;;
                --field) FIELDS+=("${2:?--field requires a value}"); shift 2 ;;
                *) usage; larch_log_fail 1 "unknown option for manifest: $1" ;;
            esac
        done
        require_log_root
        require_common
        path="$(larch_log_run_dir "$SKILL" "$RUN_ID")/manifest.json"
        [ -f "$path" ] || larch_log_fail 1 "manifest not found: $path"
        command -v jq >/dev/null 2>&1 || larch_log_fail 2 "jq is required for manifest updates"
        # shellcheck disable=SC2016 # jq variables are expanded by jq, not the shell.
        filter='.updated_at = $updated'
        args=(--arg updated "$(now_utc)")
        for field in "${FIELDS[@]}"; do
            case "$field" in
                *=*) key="${field%%=*}"; value="${field#*=}" ;;
                *) larch_log_fail 1 "invalid --field: $field" ;;
            esac
            case "$key" in
                schema_version|skill|run_id|started_at|operator_cwd|operator_repo_root) larch_log_fail 1 "manifest field is immutable: $key" ;;
                steps_ran)
                    larch_log_fail 1 "manifest field steps_ran cannot be set as a flat key; use steps_ran.<step>=true|false" ;;
                steps_ran.*)
                    step_key="${key#steps_ran.}"
                    [ -n "$step_key" ] || larch_log_fail 1 "invalid --field: $field"
                    case "$step_key" in *[!A-Za-z0-9_]*) larch_log_fail 1 "invalid steps_ran step: $step_key" ;; esac
                    case "$value" in true|false) ;;
                    *) larch_log_fail 1 "steps_ran field requires true/false: $field" ;;
                    esac
                    sn="s${#args[@]}"
                    args+=(--arg "$sn" "$step_key")
                    var="v${#args[@]}"
                    args+=(--argjson "$var" "$value")
                    filter="$filter | (.steps_ran //= {}) | .steps_ran[\$$sn] = \$$var"
                    ;;
                steps_ran*)
                    larch_log_fail 1 "invalid steps_ran manifest key '$key'; use steps_ran.<step>=true|false only" ;;
                *[!A-Za-z0-9_]*|"") larch_log_fail 1 "invalid manifest field: $key" ;;
                *)
                    var="v${#args[@]}"
                    # Use --argjson for JSON-native scalar types so numeric fields
                    # like pr_number are stored as numbers rather than strings.
                    if printf '%s' "$value" | grep -Eq '^(null|true|false|-?[0-9]+)$'; then
                        args+=(--argjson "$var" "$value")
                    else
                        args+=(--arg "$var" "$value")
                    fi
                    filter="$filter | .$key = \$$var"
                    ;;
            esac
        done
        tmp="$(mktemp "$(dirname "$path")/.tmp.manifest.XXXXXX")" || larch_log_fail 2 "cannot create manifest temp"
        jq "${args[@]}" "$filter" "$path" > "$tmp" || {
            rm -f "$tmp"
            larch_log_fail 2 "manifest update failed"
        }
        if cmp -s "$tmp" "$path"; then
            rm -f "$tmp"
            larch_log_emit_success "$path" false true
        else
            mv -f "$tmp" "$path" || larch_log_fail 2 "cannot publish manifest"
            larch_log_emit_success "$path" true false
        fi
        ;;

    commit)
        LOG_ROOT=""; SKILL=""; RUN_ID=""
        while [ $# -gt 0 ]; do
            case "$1" in
                --log-root) LOG_ROOT="${2:?--log-root requires a value}"; shift 2 ;;
                --skill) SKILL="${2:?--skill requires a value}"; shift 2 ;;
                --run-id) RUN_ID="${2:?--run-id requires a value}"; shift 2 ;;
                *) usage; larch_log_fail 1 "unknown option for commit: $1" ;;
            esac
        done
        if [ -n "${IMPLEMENT_TMPDIR:-}" ] && [ -e "$IMPLEMENT_TMPDIR/post-merge-sentinel" ]; then
            printf 'larch-log.sh: refusing commit after post-merge sentinel exists: %s\n' "$IMPLEMENT_TMPDIR/post-merge-sentinel" >&2
            exit 1
        fi
        [ -n "$REPO_ROOT" ] || larch_log_fail 1 "commit requires a git worktree (PWD is not inside a git repo)"
        if current_branch_is_default; then
            printf 'larch-log.sh: refusing commit on default branch/main after post-merge cleanup guard\n' >&2
            exit 1
        fi
        require_log_root
        require_common
        src_path="$(larch_log_run_dir "$SKILL" "$RUN_ID")"
        repo_path="$(larch_log_repo_run_dir "$SKILL" "$RUN_ID")"
        breadcrumbs_source="$(larch_log_breadcrumb_source_dir || true)"
        [ -d "$src_path" ] || larch_log_fail 1 "log directory not found: $src_path"
        if [ -f "$src_path/manifest.json" ]; then
            mf_commit_tmp="$(mktemp "$(dirname "$src_path/manifest.json")/.tmp.manifest-commit.XXXXXX")" || larch_log_fail 2 "cannot create manifest commit temp"
            jq --arg ts "$(now_utc)" '.updated_at = $ts' "$src_path/manifest.json" > "$mf_commit_tmp" || {
                rm -f "$mf_commit_tmp"
                larch_log_fail 2 "manifest updated_at refresh failed"
            }
            mv -f "$mf_commit_tmp" "$src_path/manifest.json" || {
                rm -f "$mf_commit_tmp"
                larch_log_fail 2 "cannot publish manifest updated_at"
            }
        fi
        if [ "$src_path" != "$repo_path" ]; then
            larch_log_copy_run_tree_without_breadcrumbs "$src_path" "$repo_path"
        fi
        # Copy shared archetype pool from the log root into the repo if present.
        # The pool lives at <LARCH_LOG_ROOT>/shared/archetypes/ (written by
        # write-round) and is committed alongside the per-run tree so archetypes
        # are content-addressed once across all runs.
        _commit_shared_src="$(larch_log_root)/shared"
        _commit_shared_repo="$REPO_ROOT/larch-logs/shared"
        if [ -d "$_commit_shared_src" ]; then
            mkdir -p "$_commit_shared_repo" || larch_log_fail 3 "cannot create shared archetype pool directory in repo"
            for _commit_shared_item in "$_commit_shared_src"/*; do
                [ -e "$_commit_shared_item" ] || continue
                cp -rp "$_commit_shared_item" "$_commit_shared_repo/" || larch_log_fail 3 "cannot copy shared archetypes to repo"
            done
        fi
        larch_log_publish_breadcrumbs "$breadcrumbs_source" "$repo_path"
        # Pre-flush secret gate: scrub secret-shaped values (Cursor keys et al.)
        # from the staged run tree before commit. Fail-closed — refuse to commit
        # if the tree cannot be made clean (missing gate, scrub failure, or a
        # secret that survived scrubbing). On a real redaction, surface the count
        # on both the stdout contract (SECRET_SCRUB_VIOLATIONS) and stderr so
        # callers can warn the operator to rotate the exposed credential.
        scrub_gate="$SCRIPT_DIR/scrub-log-secrets.sh"
        [ -x "$scrub_gate" ] || larch_log_fail 3 "secret scrub gate missing: $scrub_gate"
        set +e
        scrub_out="$("$scrub_gate" "$repo_path")"
        scrub_rc=$?
        set -e
        [ "$scrub_rc" -eq 0 ] || larch_log_fail 3 "secret scrub gate failed (rc=$scrub_rc) for $repo_path; refusing to commit"
        scrub_n="$(printf '%s\n' "$scrub_out" | sed -n 's/^LARCH_SECRET_SCRUB_VIOLATIONS=//p' | tail -1)"
        case "${scrub_n:-}" in ''|*[!0-9]*) scrub_n=0 ;; esac
        if [ "$scrub_n" -gt 0 ]; then
            printf 'SECRET_SCRUB_VIOLATIONS=%s\n' "$scrub_n"
            printf 'larch-log.sh: WARNING — scrub-log-secrets.sh redacted %s secret-shaped value(s) from %s run %s logs before flush; ROTATE the affected credential(s)\n' "$scrub_n" "$SKILL" "$RUN_ID" >&2
        fi
        # Scope all git operations to the per-run directory, and conditionally
        # to the shared archetype pool when it exists. Building the pathspec
        # explicitly hardens add/status/diff against prefix math mistakes and
        # untracked-file omissions.
        rel="larch-logs/$SKILL/$RUN_ID"
        _shared_rel=""
        if [ -d "$REPO_ROOT/larch-logs/shared" ]; then
            _shared_rel="larch-logs/shared"
        fi
        # Check status first: git diff alone misses untracked files.
        if ! git -C "$REPO_ROOT" status --porcelain -- "$rel" ${_shared_rel:+"$_shared_rel"} | grep -q .; then
            larch_log_emit_success "$repo_path" false true
            exit 0
        fi
        git -C "$REPO_ROOT" add -- "$rel" ${_shared_rel:+"$_shared_rel"} || larch_log_fail 3 "git add failed"
        if git -C "$REPO_ROOT" diff --cached --quiet -- "$rel" ${_shared_rel:+"$_shared_rel"}; then
            larch_log_emit_success "$repo_path" false true
            exit 0
        fi
        git -C "$REPO_ROOT" commit -m "chore(larch-logs): flush $SKILL run $RUN_ID" -- "$rel" ${_shared_rel:+"$_shared_rel"} >/dev/null || {
            git -C "$REPO_ROOT" reset HEAD -- "$rel" ${_shared_rel:+"$_shared_rel"} 2>/dev/null || true
            larch_log_fail 3 "git commit failed"
        }
        commit_sha="$(git -C "$REPO_ROOT" rev-parse HEAD)"
        larch_log_emit_success "$repo_path" true false "$commit_sha"
        ;;

    *)
        usage
        larch_log_fail 1 "unknown command: $cmd"
        ;;
esac
