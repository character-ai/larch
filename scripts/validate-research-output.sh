#!/usr/bin/env bash
# validate-research-output.sh — Substantive-content validator for /research outputs.
#
# Reads a single file, applies either a fixed set of substantive-content checks
# or structured reviewer record checks, and exits 0 if valid or non-zero with a
# one-line diagnostic on stdout. The intended consumer is
# `scripts/collect-agent-results.sh --substantive-validation` and/or
# `--structured-reviewer-validation`, which translates most non-zero exits into
# a `STATUS=NOT_SUBSTANTIVE` entry; validation-mode exit 5
# maps to `STATUS=CURSOR_EMPTY_RESPONSE`.
# Phase 3 of umbrella issue #413 (closes #416, #447, #473).
#
# Substantive = ALL of:
#   1. Body word count >= --min-words (default 200), excluding fenced-code-block
#      interiors. The opening and closing fence lines are also excluded.
#   2. (when --require-citations is on, the default) at least one provenance
#      marker, where a marker is any of:
#        - file or file:line: regex match for an extension in the recognized
#          set, split into two tiers per #473:
#            LONG tier (relaxed rule, current behavior unchanged):
#              {cc, cfg, cjs, cpp, cs, css, csv, dart, go, gradle, groovy,
#               hpp, htm, html, java, js, json, jsx, kt, lua, md, mjs, mk,
#               mm, php, pl, proto, py, rb, rs, sass, scala, scss, sh, sql,
#               swift, toml, ts, tsv, tsx, vue, xml, yaml, yml}
#            SHORT tier (strict rule, #473): {c, env, h, lock, m, r, txt}.
#              Short-tier extensions overlap with English words / short
#              identifiers (e.g., the verified `spin.lock` repro from
#              issue #473), so the path-stem MUST contain at least one
#              path-likeness signal: `/`, `_`, `-` somewhere in the stem,
#              OR a trailing `:line-ref` (`:[0-9]+(-[0-9]+)?`).
#          Forward-compat behavioral change (#473): bare short-extension
#          citations like `Cargo.lock`, `main.c`, `app.env`, `foo.h`,
#          `notes.txt` standing alone in prose (no `/`, `_`, `-` in the
#          basename, no `:line-ref`) are NO LONGER markers. Operators
#          citing short-extension files in research outputs MUST add a
#          line ref (e.g., `Cargo.lock:7`) or path segment (e.g.,
#          `kernel/spin.lock`, `parser_state.h`, `kernel-mod.h`). Long
#          extensions (`.go`, `.py`, `.md`, `.json`, etc.) are unaffected
#          and continue to match under the relaxed rule.
#          Both tiers permit leading dot for hidden files with a basename
#          (e.g., `.pre-commit-config.yaml`); both require a trailing-token
#          boundary so the extension cannot bleed into adjacent path-token
#          characters (rejects fake citations like `file.mdjunk:42`,
#          `file.md:garbage`, `file.md/child`). Bare hidden-file forms
#          without a basename (e.g. `.env:7`, `.gitignore:5`) are NOT
#          matched and rely on probes 2-4 / contract. Boundary class
#          excludes alnum, `_`, `-`, `:`, `/`; `.` IS a valid boundary so
#          sentence-ending periods (`See foo.sh.`) match. Compound
#          extensions: `bundle.js.map` still matches (inner `.js` is long-
#          tier); `Cargo.lock.bak` no longer matches (inner `.lock` is
#          short-tier and `Cargo` lacks any path-likeness signal).
#          Edit-in-sync: this tiered list is duplicated in
#          `validate-research-output.md` intentionally so `--help`
#          (sed-extracted from this header) stays self-contained; both
#          must be updated together.
#        - extensionless filename: Makefile / Dockerfile / GNUmakefile,
#        - a fenced code block (``` ... ```) with at least one non-blank
#          content line,
#        - a URL (https?://...).
#
# Validation-mode preset (--validation-mode): for short reviewer-style outputs
# that are structurally different from research-phase prose (they contain a
# no-findings sentinel on the happy path, or short numbered findings with
# file:line citations). The preset:
#   - accepts a file whose entire trimmed content equals the canonical JSON
#     sentinel `{"no_issues_found": true}` or legacy `NO_ISSUES_FOUND`
#     (case-sensitive) as substantive — exit 0 with no further checks,
#   - maps a file whose entire trimmed content equals `CURSOR_EMPTY_RESPONSE`
#     to exit 5 with a diagnostic so the collector can surface
#     STATUS=CURSOR_EMPTY_RESPONSE,
#   - lowers the default --min-words floor to 30 (a single concise finding
#     comfortably exceeds this, but a junk one-liner does not),
#   - keeps the citation requirement unchanged (validation findings must
#     still cite file:line per the reviewer-template archetype).
# The preset is a defaults override: explicit `--min-words N` and
# `--no-require-citations` flags still take precedence.
#
# Structured-reviewer mode (--structured-reviewer-mode): validates reviewer
# records emitted as JSONL or TSV. This mode is independent of --validation-mode
# and bypasses the prose word-count/citation gates when at least one valid
# structured record is found. `--write-structured <path>` writes normalized valid
# records to the given path; the canonical JSON no-findings sentinel and legacy
# NO_ISSUES_FOUND write an empty file and exit 0.
# JSONL detection prefers `jq`: each candidate line must parse as a JSON object
# with schema_version=1 and the required schema fields. Severity aliases
# Important/Nit/Latent are normalized case-insensitively. If `jq` is unavailable,
# JSONL detection falls back to the degraded strict prefix match
# `{"schema_version":1,` with no leading spaces and no spaces around the colon
# or comma. TSV detection requires the exact header:
# `schema_version	scope	severity	focus_area	location	what	scenario_or_breakage	suggested_fix`.
# TSV rows must have at least 8 tab-separated fields; extra tabs are repaired by
# folding fields 8..N into `suggested_fix` with spaces. Literal newlines cannot
# be recovered after line-oriented output and are therefore not reconstructed.
#
# Known limitations (defense-in-depth, not authentication):
#   - Tilde-fence variants (~~~ ... ~~~) are NOT recognized; only triple-
#     backtick fences are.
#   - Length-mismatched fences (e.g. open with ```` close with ```) are
#     simplified to "any line beginning with optional whitespace + 3+
#     backticks toggles the fence state". Pathological inputs may exhibit
#     surprising body-word-count behavior.
#   - Adversarial padding: 200 words of repeated nonsense plus one fake
#     `path/file.md:42` will pass both gates. The validator is a deterministic
#     sanity gate, not a quality oracle.
#
# Usage:
#   validate-research-output.sh [--min-words N] [--require-citations|--no-require-citations] [--validation-mode] [--structured-reviewer-mode] [--write-structured <path>] <file>
#
# Exit codes:
#   0 — substantive (no stdout output)
#   1 — usage error (missing/unknown flag, multiple file arguments)
#   2 — body too thin (word count below --min-words after stripping fenced code)
#   3 — no provenance marker found (only when --require-citations is on)
#   4 — file missing or not readable
#   5 — validation mode: CURSOR_EMPTY_RESPONSE marker; structured mode:
#       structured records not found after repair
#
# Diagnostic format:
#   Exit 2: `body too thin: <count>/<min> words after stripping fenced code`
#   Exit 3: `no provenance marker found`
#   Exit 4: `file missing or not readable: <path>`
#   Exit 5: validation mode emits `STATUS=CURSOR_EMPTY_RESPONSE` plus
#           `FAILURE_REASON=...`; structured mode emits
#           `structured records not found after repair`
#
# Portability: uses `awk` (POSIX) and `grep -E` (BSD + GNU). No `\d`, no
# lookarounds, no `\w` — all character classes are explicit `[...]`.

# No -e: exit codes are meaningful return values that distinguish failure
# modes for the test harness and the collector consumer. Bare `grep -Eq`
# returning 1 (no match) must NOT abort the script.
set -uo pipefail

SCRIPT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
# shellcheck source=scripts/file-line-regex-lib.sh
# shellcheck disable=SC1091
. "$SCRIPT_DIR/file-line-regex-lib.sh"
# shellcheck source=scripts/lib-quiet.sh
source "$SCRIPT_DIR/lib-quiet.sh"
# Print help before quiet init so --help output reaches the terminal.
for _arg in "$@"; do
  if [[ "$_arg" == "--help" ]]; then
    sed -n '/^# /,/^[^#]/p' "$0" | head -n 120
    exit 0
  fi
done
unset _arg
larch_quiet_init

MIN_WORDS=""
REQUIRE_CITATIONS=true
VALIDATION_MODE=false
STRUCTURED_REVIEWER_MODE=false
WRITE_STRUCTURED=""
INPUT=""

while [[ $# -gt 0 ]]; do
    case "$1" in
        --min-words)
            MIN_WORDS="${2:?--min-words requires a value}"; shift 2 ;;
        --require-citations)
            REQUIRE_CITATIONS=true; shift ;;
        --no-require-citations)
            REQUIRE_CITATIONS=false; shift ;;
        --validation-mode)
            VALIDATION_MODE=true; shift ;;
        --structured-reviewer-mode)
            STRUCTURED_REVIEWER_MODE=true; shift ;;
        --write-structured)
            WRITE_STRUCTURED="${2:?--write-structured requires a value}"; shift 2 ;;
        --help)
            sed -n '/^# /,/^[^#]/p' "$0" | head -n 120
            exit 0 ;;
        -*)
            larch_err "validate-research-output.sh: unknown option: $1"
            exit 1 ;;
        *)
            if [[ -n "$INPUT" ]]; then
                larch_err "validate-research-output.sh: only one file argument allowed"
                exit 1
            fi
            INPUT="$1"; shift ;;
    esac
done

# Apply --validation-mode defaults: lower min-words floor to 30 (a single
# concise finding suffices) when not explicitly overridden. Citation
# requirement is unchanged by the preset — explicit --no-require-citations
# still wins.
if [[ -z "$MIN_WORDS" ]]; then
    if [[ "$VALIDATION_MODE" == "true" ]]; then
        MIN_WORDS=30
    else
        MIN_WORDS=200
    fi
fi

if [[ -z "$INPUT" ]]; then
    larch_err "validate-research-output.sh: file argument is required"
    exit 1
fi

if [[ ! -r "$INPUT" ]]; then
    emit "file missing or not readable: $INPUT"
    exit 4
fi

write_structured_output() {
    local target="$1"
    local source="$2"
    local tmp
    [[ -n "$target" ]] || return 0
    tmp=$(mktemp "${target}.tmp.XXXXXX") || return 1
    if [[ -n "$source" ]]; then
        cat "$source" > "$tmp" || { rm -f "$tmp"; return 1; }
    else
        : > "$tmp" || { rm -f "$tmp"; return 1; }
    fi
    mv "$tmp" "$target"
}

trimmed_nonblank_content() {
    awk 'NF { gsub(/^[[:space:]]+|[[:space:]]+$/, ""); print }' "$1"
}

validate_structured_jsonl_with_jq() {
    local input="$1"
    local output="$2"
    local tmp_line
    : > "$output"
    while IFS= read -r line || [[ -n "$line" ]]; do
        case "$line" in
            ''|[[:space:]]*) continue ;;
        esac
        if printf '%s\n' "$line" | grep -Eq '^[[:space:]]*```'; then
            continue
        fi
        tmp_line=$(printf '%s' "$line" | jq -c '
            if type == "object" then
              .severity = (if (.severity | type) == "string" then (.severity | ascii_downcase) else .severity end)
            else
              .
            end
            | select(
                type == "object"
                and .schema_version == 1
                and (.scope == "in_scope" or .scope == "out_of_scope")
                and (.severity == "important" or .severity == "nit" or .severity == "latent")
                and (.focus_area == "code-quality" or .focus_area == "risk-integration" or .focus_area == "correctness" or .focus_area == "architecture" or .focus_area == "security")
                and (.location | type == "string")
                and (.what | type == "string")
                and (.scenario_or_breakage | type == "string")
                and (.suggested_fix | type == "string")
              )
        ' 2>/dev/null)
        if [[ -n "$tmp_line" ]]; then
            printf '%s\n' "$tmp_line" >> "$output"
        fi
    done < "$input"
    [[ -s "$output" ]]
}

validate_structured_jsonl_prefix_fallback() {
    local input="$1"
    local output="$2"
    : > "$output"
    while IFS= read -r line || [[ -n "$line" ]]; do
        case "$line" in
            '{"schema_version":1,'*) printf '%s\n' "$line" >> "$output" ;;
        esac
    done < "$input"
    [[ -s "$output" ]]
}

validate_structured_tsv() {
    local input="$1"
    local output="$2"
    local header
    header=$'schema_version\tscope\tseverity\tfocus_area\tlocation\twhat\tscenario_or_breakage\tsuggested_fix'
    awk -F '\t' -v OFS='\t' -v header="$header" '
        function clean(s) {
            gsub(/\r/, " ", s)
            gsub(/\n/, " ", s)
            gsub(/[[:space:]]+/, " ", s)
            sub(/^ /, "", s)
            sub(/ $/, "", s)
            return s
        }
        /^[[:space:]]*```/ { next }
        !seen {
            if ($0 == header) {
                print header
                seen = 1
            }
            next
        }
        seen && NF == 0 { next }
        seen {
            if (NF < 8) next
            schema = clean($1)
            scope = clean($2)
            severity = tolower(clean($3))
            focus = clean($4)
            location = clean($5)
            what = clean($6)
            scenario = clean($7)
            fix = clean($8)
            if (NF > 8) {
                for (i = 9; i <= NF; i++) {
                    fix = fix " " clean($i)
                }
            }
            if (schema != "1") next
            if (scope != "in_scope" && scope != "out_of_scope") next
            if (severity != "important" && severity != "nit" && severity != "latent") next
            if (focus != "code-quality" && focus != "risk-integration" && focus != "correctness" && focus != "architecture" && focus != "security") next
            print schema, scope, severity, focus, location, what, scenario, fix
            records++
        }
        END { exit(records > 0 ? 0 : 1) }
    ' "$input" > "$output"
}

if [[ "$STRUCTURED_REVIEWER_MODE" == "true" ]]; then
    TRIMMED=$(trimmed_nonblank_content "$INPUT")
    if [[ "$TRIMMED" == "NO_ISSUES_FOUND" ]]; then
        write_structured_output "$WRITE_STRUCTURED" ""
        exit 0
    fi
    if command -v jq >/dev/null 2>&1 \
       && jq -e 'type == "object" and .no_issues_found == true' <<<"$TRIMMED" >/dev/null 2>&1; then
        write_structured_output "$WRITE_STRUCTURED" ""
        exit 0
    fi

    STRUCTURED_TMP=$(mktemp "${TMPDIR:-/tmp}/structured-reviewer.XXXXXX") || exit 1
    trap 'rm -f "$STRUCTURED_TMP"' EXIT

    if command -v jq >/dev/null 2>&1; then
        if validate_structured_jsonl_with_jq "$INPUT" "$STRUCTURED_TMP"; then
            write_structured_output "$WRITE_STRUCTURED" "$STRUCTURED_TMP"
            exit 0
        fi
    elif validate_structured_jsonl_prefix_fallback "$INPUT" "$STRUCTURED_TMP"; then
        write_structured_output "$WRITE_STRUCTURED" "$STRUCTURED_TMP"
        exit 0
    fi

    if validate_structured_tsv "$INPUT" "$STRUCTURED_TMP"; then
        write_structured_output "$WRITE_STRUCTURED" "$STRUCTURED_TMP"
        exit 0
    fi

    write_structured_output "$WRITE_STRUCTURED" ""
    emit "structured records not found after repair"
    exit 5
fi

# --- 0. Validation-mode short-circuits: accept no-findings sentinels as
# substantive without applying word-count or citation checks, and distinguish
# Cursor's empty .result response marker from generic thin content. Sentinels
# must be the entire trimmed file content (whitespace-only lines removed top +
# bottom; tabs and trailing whitespace stripped) — partial matches inside
# larger prose do NOT trigger the short-circuit.
if [[ "$VALIDATION_MODE" == "true" ]]; then
    TRIMMED=$(trimmed_nonblank_content "$INPUT")
    if [[ "$TRIMMED" == "CURSOR_EMPTY_RESPONSE" ]]; then
        emit "STATUS=CURSOR_EMPTY_RESPONSE"
        emit "FAILURE_REASON=Cursor returned a JSON envelope with empty .result field — likely transient backend issue. Fallback engaged."
        exit 5
    fi
    if [[ "$TRIMMED" == "NO_ISSUES_FOUND" ]]; then
        exit 0
    fi
    if command -v jq >/dev/null 2>&1 \
       && jq -e 'type == "object" and .no_issues_found == true' <<<"$TRIMMED" >/dev/null 2>&1; then
        exit 0
    fi
    # Inline-TSV short-circuit: when cursor runs in --mode plan it cannot write
    # the TSV sidecar and inlines TSV records in its text response instead. Accept
    # a response containing valid inline TSV (even inside a code fence) as
    # substantive without applying the word-count or citation gates.
    _tsv_tmp=$(mktemp "${TMPDIR:-/tmp}/validate-tsv-tmp.XXXXXX") || exit 1
    if validate_structured_tsv "$INPUT" "$_tsv_tmp" 2>/dev/null; then
        rm -f "$_tsv_tmp"
        exit 0
    fi
    rm -f "$_tsv_tmp"
fi

# --- 1. Body word count, excluding fenced-code-block interiors ---
# awk state machine: every line beginning with optional whitespace + 3+
# backticks toggles `in_fence`; lines inside the fence (and the fence lines
# themselves) are skipped via `next`. NF is summed across body lines.
WORD_COUNT=$(awk '
    /^[[:space:]]*```/ { in_fence = !in_fence; next }
    in_fence { next }
    { words += NF }
    END { print words + 0 }
' "$INPUT")

if [[ "$WORD_COUNT" -lt "$MIN_WORDS" ]]; then
    emit "body too thin: $WORD_COUNT/$MIN_WORDS words after stripping fenced code"
    exit 2
fi

# --- 2. Provenance markers (when --require-citations) ---
if [[ "$REQUIRE_CITATIONS" == "true" ]]; then
    # Probe 1: file path with a known extension (#416 origin, #447 broadened
    # extension set + trailing-boundary rule, #473 split into LONG and SHORT
    # tiers to fix generic-English false positives like `the spin.lock
    # primitive`). Longest-first ordering preserved inside prefix-conflict
    # families (e.g., `cc|cfg|cjs|cpp|css|csv|cs`, `html|htm|hpp`,
    # `json|jsx|js`, `mjs|mk|mm|md`, `tsx|tsv|ts`) so BSD/macOS grep -E
    # does not need to backtrack through alternation. Boundary
    # `(^|[^A-Za-z0-9])` and trailing `($|[^A-Za-z0-9_:/-])` are unchanged
    # from #447 — see header for the boundary semantics; `.` IS still a
    # valid trailing boundary so sentence-ending periods (`See foo.sh.`)
    # and long-tier compound extensions (`bundle.js.map`) still match.
    #
    # SHORT-tier strict rule (#473): the short extension set
    # {c, env, h, lock, m, r, txt} overlaps with English words / short
    # identifiers, so the path-stem must carry a path-likeness signal:
    #   - `/`, `_`, or `-` somewhere in the stem, OR
    #   - a trailing `:[0-9]+(-[0-9]+)?` line reference.
    # The first stem character `[A-Za-z_]` may be `_`, but the strict-mode
    # `[/_-]` requires a signal AFTER the start char, so a bare-underscore
    # start does not by itself satisfy the rule.
    # Tier-split regex now sourced from scripts/file-line-regex-lib.sh
    # (`__filelinelib_long_re`, `__filelinelib_short_path_re`,
    # `__filelinelib_short_line_re`, `__filelinelib_any_re`).
    if grep -Eq "$__filelinelib_any_re" "$INPUT"; then
        exit 0
    fi

    # Probe 2: extensionless capitalized filenames (Makefile, Dockerfile,
    # GNUmakefile) — common /research provenance citations not covered by
    # probe 1. Pattern sourced from `__filelinelib_extensionless_re`.
    if grep -Eq "$__filelinelib_extensionless_re" "$INPUT"; then
        exit 0
    fi

    # Probe 3: fenced code block with >= 1 non-blank content line. A fence-
    # only block (``` ... ``` with empty interior) does NOT count.
    HAS_CODE_FENCE=$(awk '
        /^[[:space:]]*```/ { in_fence = !in_fence; next }
        in_fence && NF > 0 { content++ }
        END { print (content > 0) ? 1 : 0 }
    ' "$INPUT")
    if [[ "$HAS_CODE_FENCE" == "1" ]]; then
        exit 0
    fi

    # Probe 4: URL.
    if grep -Eq 'https?://' "$INPUT"; then
        exit 0
    fi

    emit "no provenance marker found"
    exit 3
fi

exit 0
