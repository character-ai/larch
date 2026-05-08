#!/usr/bin/env bash
# assemble-anchor.sh — assemble the anchor comment body from local fragments.
#
# Walks SECTION_MARKERS (sourced from anchor-section-markers.sh), reads each
# fragment file under --sections-dir, emits `<!-- section:<slug> -->\n<content>\n<!-- section-end:<slug> -->`
# marker pairs (empty content when a fragment file is absent), prepends the
# first-line HTML anchor marker, and writes the assembled body to --output.
#
# Seed-only visible-placeholder behavior: when every fragment is absent,
# zero-byte, or whitespace-only (lenient predicate), the assembled body
# carries one extra italic-markdown line between the first-line HTML marker
# and the first <!-- section:... --> open marker so the comment renders
# non-empty in GitHub's UI. Populated runs (any fragment with at least one
# non-whitespace byte) suppress the placeholder; populated content is emitted
# byte-for-byte for every section EXCEPT run-statistics, which is normalized
# (trailing blank lines stripped, any pre-existing trailing `| larch plugin
# version | ... |` rows dropped) and a fresh canonical version row is
# appended. See scripts/assemble-anchor.md "Seed-only visible placeholder"
# and "Run Statistics version-row injection".
#
# Consumers:
#   - skills/implement/SKILL.md Step 0.5 (Branch 2/3 adoption seed body, Branch 4
#     first-remote-write seed body), Steps 1/2/5/7a/8/9a.1/11 (progressive upserts —
#     Step 2 covers Q/A anchor refresh after each opportunistic question or
#     mid-coding ambiguity resolution).
#   - skills/implement/references/rebase-rebump-subprocedure.md Step 6 (Phase 5 —
#     post-rebase anchor version-bump-reasoning refresh).
#
# Output contract (KEY=value on stdout):
#   Success:  ASSEMBLED=true
#             OUTPUT=<path>
#   Failure:  FAILED=true
#             ERROR=<single-line message>
#
# Exit codes:
#   0 — success
#   1 — invocation / usage error (missing flag, empty value, missing helper)
#   2 — I/O failure (unreadable sections dir, unwritable output path, etc.)
#
# The helper does NOT invoke the redaction pipeline — that responsibility
# lives with scripts/tracking-issue-write.sh at publish time. Compose-time
# sanitization is the SKILL's responsibility, and this helper also enforces
# the diagrams slug with a fail-closed Mermaid sanitizer as defense in depth.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
MARKERS_HELPER="$SCRIPT_DIR/anchor-section-markers.sh"
PLUGIN_VERSION_HELPER="$SCRIPT_DIR/read-plugin-version.sh"
MERMAID_SANITIZER="$SCRIPT_DIR/sanitize-mermaid-fragment.sh"
APPEND_ISSUE="$SCRIPT_DIR/append-execution-issue.sh"

if [ ! -f "$MARKERS_HELPER" ]; then
    echo "FAILED=true"
    echo "ERROR=missing helper: $MARKERS_HELPER"
    exit 1
fi

# shellcheck source=scripts/anchor-section-markers.sh
# shellcheck disable=SC1091
source "$MARKERS_HELPER"

PLUGIN_VERSION="unknown"
if [ -x "$PLUGIN_VERSION_HELPER" ]; then
    version_stdout="$("$PLUGIN_VERSION_HELPER" 2>/dev/null || true)"
    if version_line="$(printf '%s\n' "$version_stdout" | grep -m 1 '^LARCH_PLUGIN_VERSION=' 2>/dev/null)"; then
        PLUGIN_VERSION="${version_line#LARCH_PLUGIN_VERSION=}"
        [ -n "$PLUGIN_VERSION" ] || PLUGIN_VERSION="unknown"
    fi
fi

fail_usage() {
    echo "FAILED=true"
    echo "ERROR=usage: $1"
    exit 1
}

fail_io() {
    echo "FAILED=true"
    echo "ERROR=$1"
    exit 2
}

emit_run_statistics() {
    fragment="$1"

    normalized=""
    if [ -f "$fragment" ] && grep -q '[^[:space:]]' "$fragment" 2>/dev/null; then
        # Emit populated run-statistics content with trailing blank lines
        # AND trailing pre-existing `| larch plugin version | ... |` rows
        # stripped, then append the freshly-captured plugin version as the
        # canonical final table row. Stripping pre-existing version rows
        # prevents duplicates when the run-statistics fragment was hydrated
        # from a prior anchor body that already carried an injected row
        # (closes #348-Phase5-resume duplicate-row regression).
        normalized=$(awk '
            { lines[NR] = $0 }
            END {
                last = NR
                while (last > 0 && (lines[last] ~ /^[[:space:]]*$/ || lines[last] ~ /^[[:space:]]*\|[[:space:]]*larch plugin version[[:space:]]*\|/)) {
                    last--
                }
                for (i = 1; i <= last; i++) {
                    print lines[i]
                }
            }
        ' "$fragment") || fail_io "failed to read fragment: $fragment"
    fi

    if [ -n "$normalized" ]; then
        printf '%s\n' "$normalized"
    else
        # Seed case OR populated fragment whose interior normalized down to
        # nothing (e.g. a fragment that contained only a stale version row
        # that the strip loop above removed). Either way the output needs a
        # complete table scaffold so the appended version row renders as a
        # well-formed table.
        printf '## Run Statistics\n\n'
        printf '| Metric | Value |\n'
        printf '|---|---|\n'
    fi

    printf '| larch plugin version | %s |\n' "$PLUGIN_VERSION"
}

SECTIONS_DIR=""
ISSUE=""
OUTPUT=""
WARNINGS_LOG=""

while [ $# -gt 0 ]; do
    case "$1" in
        --sections-dir)
            [ $# -ge 2 ] || fail_usage "--sections-dir requires a value"
            SECTIONS_DIR="$2"; shift 2 ;;
        --issue)
            [ $# -ge 2 ] || fail_usage "--issue requires a value"
            ISSUE="$2"; shift 2 ;;
        --output)
            [ $# -ge 2 ] || fail_usage "--output requires a value"
            OUTPUT="$2"; shift 2 ;;
        --warnings-log)
            [ $# -ge 2 ] || fail_usage "--warnings-log requires a value"
            WARNINGS_LOG="$2"; shift 2 ;;
        *)
            fail_usage "unknown flag: $1" ;;
    esac
done

[ -n "$SECTIONS_DIR" ] || fail_usage "--sections-dir is required"
[ -n "$ISSUE" ]        || fail_usage "--issue is required"
[ -n "$OUTPUT" ]       || fail_usage "--output is required"

# Validate --issue is a non-negative integer (matches tracking-issue-write.sh convention).
case "$ISSUE" in
    ''|*[!0-9]*) fail_usage "invalid value for --issue: '$ISSUE' (expected non-negative integer)" ;;
esac

# Ensure output parent directory exists.
OUTPUT_DIR="$(dirname "$OUTPUT")"
mkdir -p "$OUTPUT_DIR" 2>/dev/null || fail_io "cannot create output directory: $OUTPUT_DIR"

# Missing sections directory is tolerated — walk emits all empty marker pairs.
# Unreadable sections directory is an I/O failure (distinguish missing vs permission denied).
# A non-directory entry (regular file, symlink to file, fifo, etc.) is fail-closed:
# silently walking it would treat each `<slug>.md` path lookup as "file not present" and
# emit an all-empty skeleton, which could overwrite populated remote anchor content on
# a subsequent upsert — a documentation-correctness regression.
if [ -e "$SECTIONS_DIR" ]; then
    if [ ! -d "$SECTIONS_DIR" ]; then
        fail_io "sections-dir exists but is not a directory: $SECTIONS_DIR"
    fi
    if [ ! -r "$SECTIONS_DIR" ]; then
        fail_io "sections directory not readable: $SECTIONS_DIR"
    fi
fi

placeholder_for_heading() {
    case "$1" in
        architecture) printf '%s\n' 'Architecture diagram not available.' ;;
        code-flow) printf '%s\n' 'Code flow diagram not available.' ;;
        *) printf '%s\n' 'Mermaid diagram not available.' ;;
    esac
}

heading_from_history() {
    history="$1"
    if printf '%s\n' "$history" | tail -n 5 | grep -Eiq '^##[[:space:]]+Code Flow Diagram[[:space:]]*$'; then
        printf '%s\n' 'code-flow'
    elif printf '%s\n' "$history" | tail -n 5 | grep -Eiq '^##[[:space:]]+Architecture Diagram[[:space:]]*$'; then
        printf '%s\n' 'architecture'
    else
        printf '%s\n' 'unknown'
    fi
}

drop_list_contains() {
    needle="$1"
    list="$2"
    case " $list " in
        *" $needle "*) return 0 ;;
        *) return 1 ;;
    esac
}

replace_mermaid_fences() {
    src="$1"
    dst="$2"
    drop_fences="$3"
    drop_all="$4"

    # Accept up to 3 leading spaces of indentation per GFM/CommonMark
    # fenced-code-block grammar; without this an indented mermaid fence
    # would slip past replace_mermaid_fences's defense-in-depth scan
    # (round-2 follow-up SECURITY).
    # shellcheck disable=SC2016 # literal backtick regex; no shell expansion intended.
    fence_re='^[[:space:]]{0,3}(`{3,})([^`]*)$'
    in_outer=false
    outer_len=0
    outer_mermaid=false
    dropping=false
    fence_count=0
    history=""

    while IFS= read -r line || [ -n "$line" ]; do
        if [[ "$line" =~ $fence_re ]]; then
            opener="${BASH_REMATCH[1]}"
            rest="${BASH_REMATCH[2]}"
            len=${#opener}
            if [ "$in_outer" = false ]; then
                if [[ "$rest" =~ ^[[:space:]]*mermaid[[:space:]]*$ ]]; then
                    fence_count=$((fence_count + 1))
                    in_outer=true
                    outer_len=$len
                    outer_mermaid=true
                    if [ "$drop_all" = true ] || drop_list_contains "$fence_count" "$drop_fences"; then
                        dropping=true
                        placeholder_for_heading "$(heading_from_history "$history")" >> "$dst"
                    else
                        dropping=false
                        printf '%s\n' "$line" >> "$dst"
                    fi
                    continue
                else
                    in_outer=true
                    outer_len=$len
                    outer_mermaid=false
                    printf '%s\n' "$line" >> "$dst"
                    continue
                fi
            else
                if [ "$len" -ge "$outer_len" ] && [[ "$rest" =~ ^[[:space:]]*$ ]]; then
                    if [ "$outer_mermaid" = true ] && [ "$dropping" = true ]; then
                        in_outer=false
                        outer_len=0
                        outer_mermaid=false
                        dropping=false
                        continue
                    fi
                    printf '%s\n' "$line" >> "$dst"
                    in_outer=false
                    outer_len=0
                    outer_mermaid=false
                    dropping=false
                    continue
                fi
            fi
        fi

        if [ "$in_outer" = true ] && [ "$outer_mermaid" = true ] && [ "$dropping" = true ]; then
            continue
        fi
        printf '%s\n' "$line" >> "$dst"
        if [ "$in_outer" = false ] && [ -n "$(printf '%s' "$line" | tr -d '[:space:]')" ]; then
            history="${history}${line}"$'\n'
            history="$(printf '%s\n' "$history" | tail -n 5)"$'\n'
        fi
    done < "$src"
}

emit_diagrams_fragment() {
    fragment="$1"
    sanitized="$TMP_OUTPUT.diagrams"
    : > "$sanitized" || fail_io "cannot create sanitized diagrams temp file"

    if [ ! -x "$MERMAID_SANITIZER" ]; then
        replace_mermaid_fences "$fragment" "$sanitized" "" true || fail_io "failed to sanitize diagrams fragment"
        if [ -n "$WARNINGS_LOG" ] && [ -x "$APPEND_ISSUE" ]; then
            "$APPEND_ISSUE" --log "$WARNINGS_LOG" --category "Tool Failures" \
                --entry "- **assemble-anchor: sanitizer exit 2 — diagrams slug fail-closed**" >/dev/null 2>&1 || true
        fi
        cat "$sanitized" || fail_io "failed to read sanitized diagrams fragment"
        return 0
    fi

    sanitizer_args=(--input "$fragment" --from-md)
    [ -n "$WARNINGS_LOG" ] && sanitizer_args+=(--warnings-log "$WARNINGS_LOG" --warnings-step "assemble-anchor")
    set +e
    sanitizer_out="$("$MERMAID_SANITIZER" "${sanitizer_args[@]}" 2>/dev/null)"
    sanitizer_rc=$?
    set -e

    if [ "$sanitizer_rc" -eq 0 ]; then
        cat "$fragment" || fail_io "failed to read fragment: $fragment"
        return 0
    fi

    if [ "$sanitizer_rc" -eq 1 ]; then
        drop_fences="$(printf '%s\n' "$sanitizer_out" | awk -F'[ =]' '/^REASON_TOKEN=/{print $4}' | sort -n -u | tr '\n' ' ' | sed 's/[[:space:]]*$//')"
        replace_mermaid_fences "$fragment" "$sanitized" "$drop_fences" false || fail_io "failed to sanitize diagrams fragment"
        cat "$sanitized" || fail_io "failed to read sanitized diagrams fragment"
        return 0
    fi

    replace_mermaid_fences "$fragment" "$sanitized" "" true || fail_io "failed to sanitize diagrams fragment"
    if [ -n "$WARNINGS_LOG" ] && [ -x "$APPEND_ISSUE" ]; then
        "$APPEND_ISSUE" --log "$WARNINGS_LOG" --category "Tool Failures" \
            --entry "- **assemble-anchor: sanitizer exit 2 — diagrams slug fail-closed**" >/dev/null 2>&1 || true
    fi
    cat "$sanitized" || fail_io "failed to read sanitized diagrams fragment"
}

# Pre-pass: verify every existing fragment file is readable BEFORE entering
# the assembly brace-group (whose redirection `> "$TMP_OUTPUT"` would swallow
# any FAILED=true / ERROR= output emitted from inside the loop into the tmp
# file instead of the parent's stdout). Any unreadable fragment fails closed
# now, with the envelope reaching the parent shell's stdout intact.
for slug in "${SECTION_MARKERS[@]}"; do
    fragment="$SECTIONS_DIR/$slug.md"
    if [ -f "$fragment" ] && [ ! -r "$fragment" ]; then
        fail_io "failed to read fragment: $fragment"
    fi
done

# Seed-only visible-placeholder pre-pass: detect whether every fragment is
# absent, zero-byte, or whitespace-only (lenient predicate per dialectic
# DECISION_1 and Round 2 user confirmation in /design — see the
# "Seed-only visible placeholder" subsection of scripts/assemble-anchor.md).
# An anchor body composed entirely of HTML comment markers renders invisible
# in GitHub's UI; emit one visible markdown line in that case so the seed
# anchor is not blank between Step 0.5 plant and the first progressive
# upsert. Populated runs (any fragment with at least one non-whitespace
# byte) are byte-for-byte unchanged for every section EXCEPT run-statistics,
# which is normalized via emit_run_statistics (see above).
ALL_EMPTY=true
for slug in "${SECTION_MARKERS[@]}"; do
    fragment="$SECTIONS_DIR/$slug.md"
    if [ -f "$fragment" ] && grep -q '[^[:space:]]' "$fragment" 2>/dev/null; then
        ALL_EMPTY=false
        break
    fi
done

# Assemble body in a tmp file first, then atomic-rename into place.
TMP_OUTPUT="$(mktemp "${OUTPUT}.XXXXXX")" || fail_io "cannot create temp file next to $OUTPUT"
# Clean up tmp on any exit path (success atomic-renames; failure removes stale tmp).
trap 'rm -f "$TMP_OUTPUT"' EXIT

{
    printf '<!-- larch:implement-anchor v1 issue=%s -->\n' "$ISSUE"
    if "$ALL_EMPTY"; then
        printf '%s\n' '_/implement run in progress — sections below populate as the run proceeds._'
    fi
    for slug in "${SECTION_MARKERS[@]}"; do
        fragment="$SECTIONS_DIR/$slug.md"
        printf '<!-- section:%s -->\n' "$slug"
        if [ "$slug" = "run-statistics" ]; then
            emit_run_statistics "$fragment"
        elif [ "$slug" = "diagrams" ] && [ -f "$fragment" ]; then
            emit_diagrams_fragment "$fragment"
        elif [ -f "$fragment" ]; then
            # Fragment content emitted verbatim; caller owns compose-time sanitization.
            # cat preserves trailing-newline semantics as authored by the caller.
            # Fail closed on read error so a permission-denied fragment cannot
            # silently produce an empty section interior (which would clobber
            # populated remote content on upsert).
            cat "$fragment" || fail_io "failed to read fragment: $fragment"
            # Ensure exactly one newline between fragment content and the close
            # marker. If the fragment already ends with a newline, do not add
            # another — command substitution in bash strips trailing newlines,
            # so we cannot use `$(tail -c 1 ...)` to detect it. Instead, use
            # `od -An -to1 | tr -d ' '` which preserves byte identity of the
            # last byte even when it is a newline. Newline = octal 012.
            if [ -s "$fragment" ]; then
                last_oct="$(tail -c 1 "$fragment" 2>/dev/null | od -An -to1 | tr -d ' ')"
                if [ "$last_oct" != "012" ]; then
                    printf '\n'
                fi
            fi
        fi
        printf '<!-- section-end:%s -->\n' "$slug"
    done
} > "$TMP_OUTPUT" || fail_io "failed to write assembled body to $TMP_OUTPUT"

mv -f "$TMP_OUTPUT" "$OUTPUT" || fail_io "failed to move assembled body into $OUTPUT"
# mv succeeded; clear the trap's rm target so the file stays.
trap - EXIT

echo "ASSEMBLED=true"
echo "OUTPUT=$OUTPUT"
exit 0
