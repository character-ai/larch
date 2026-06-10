#!/usr/bin/env bash
# compose-review-findings.sh — compose review-findings-full JSONL records.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)"
REDACT_TMP="$SCRIPT_DIR/redact-tmpdir-paths.sh"
REDACT_SECRETS="$SCRIPT_DIR/redact-secrets.sh"
# shellcheck source=scripts/lib-quiet.sh
source "$SCRIPT_DIR/lib-quiet.sh"
larch_quiet_init
# shellcheck source=scripts/lib-vote-tally.sh
source "$SCRIPT_DIR/lib-vote-tally.sh"

DESIGN_DIR=""
IMPLEMENT_TMPDIR=""
ISSUE=""
OUTPUT=""

usage() {
    while IFS= read -r line; do larch_err "$line"; done <<'USAGE'
Usage: compose-review-findings.sh \
  --design-artifacts-dir DIR \
  --implement-tmpdir DIR \
  --issue N \
  --output PATH
USAGE
}

fail() {
    emit_kv FAILED true
    emit_kv ERROR "$1"
    exit 2
}

while [ $# -gt 0 ]; do
    case "$1" in
        --design-artifacts-dir) DESIGN_DIR="${2:?--design-artifacts-dir requires a value}"; shift 2 ;;
        --implement-tmpdir) IMPLEMENT_TMPDIR="${2:?--implement-tmpdir requires a value}"; shift 2 ;;
        --issue) ISSUE="${2:?--issue requires a value}"; shift 2 ;;
        --output) OUTPUT="${2:?--output requires a value}"; shift 2 ;;
        --archive-dir|--archive-threshold)
            # Backward-compatible no-op while callers migrate away from archive mode.
            shift 2 ;;
        *) usage; fail "unknown flag: $1" ;;
    esac
done

[ -n "$ISSUE" ] || { usage; fail "--issue is required"; }
[ -n "$OUTPUT" ] || { usage; fail "--output is required"; }
case "$ISSUE" in *[!0-9]*|"") fail "invalid value for --issue: '$ISSUE' (expected non-negative integer)" ;; esac
[ -x "$REDACT_TMP" ] || fail "redaction helper not executable: $REDACT_TMP"
[ -x "$REDACT_SECRETS" ] || fail "redaction helper not executable: $REDACT_SECRETS"

redact_field() {
    printf '%s' "$1" | "$REDACT_TMP" | "$REDACT_SECRETS"
}

# Extract the category from a finding body. Bodies typically open with a
# '## <category>: …' line or '## **<category>** — …'. Rejected findings may instead
# lead with a triple-hash inner line '### FINDING_<id>: <category>: …' (no synthetic
# '## ' prefix). If absent, returns the empty string.
# For out_of_scope and plan-review accepted (strict=1), '## …' lines must match a canonical
# focus-area tag or scanning continues; non-canonical '##' tokens are skipped (so a synthetic
# prose title line prepended by flush_pending does not steal category from a later canonical
# '## <tag>: …' line). For other outcomes (strict=0), the first non-empty '## …' label wins.
# Triple-hash '### FINDING_<id>: …' lines only populate category for canonical focus-area tags
# or true '<tag>: <location>' shapes (two colons) per the strict/loose branches inside awk.
extract_category() {
    local body="$1" strict="${2:-0}"
    LC_ALL=C awk -v strict="$strict" '
        function is_canonical(c) {
            return (c == "code-quality" || c == "risk-integration" ||
                c == "correctness" || c == "architecture" || c == "security")
        }
        /^###[[:space:]]+FINDING_[0-9A-Za-z_]+:/ {
            if (!sub(/^###[[:space:]]+FINDING_[0-9A-Za-z_]+:[[:space:]]*/, "")) {
                next
            }
            sub(/^[[:space:]]+/, "", $0)
            rest = $0
            n1 = index(rest, ":")
            if (n1 == 0) {
                candidate = rest
                gsub(/^[[:space:]]+|[[:space:]]+$/, "", candidate)
                if (candidate == "" || !is_canonical(candidate)) {
                    next
                }
                print candidate
                exit
            }
            seg1 = substr(rest, 1, n1 - 1)
            after1 = substr(rest, n1 + 1)
            gsub(/^[[:space:]]+|[[:space:]]+$/, "", seg1)
            n2 = index(after1, ":")
            if (n2 > 0) {
                candidate = seg1
            } else if (is_canonical(seg1)) {
                candidate = seg1
            } else {
                next
            }
            gsub(/^[[:space:]]+|[[:space:]]+$/, "", candidate)
            if (candidate == "") {
                next
            }
            if (strict == 1) {
                if (is_canonical(candidate)) {
                    print candidate
                }
            } else if (candidate != "") {
                print candidate
            }
            exit
        }
        /^## / {
            sub(/^## /, "")
            if (substr($0, 1, 2) == "**") {
                sub(/^\*\*/, "")
                n = index($0, "**")
                if (n > 0) {
                    candidate = substr($0, 1, n - 1)
                } else {
                    candidate = $0
                }
            } else {
                n = index($0, ":")
                if (n > 0) {
                    candidate = substr($0, 1, n - 1)
                } else {
                    candidate = $0
                }
            }
            gsub(/^[[:space:]]+|[[:space:]]+$/, "", candidate)
            if (strict == 1) {
                if (is_canonical(candidate)) {
                    print candidate
                    exit
                }
                # Non-canonical in strict mode: skip and continue scanning
                next
            }
            if (candidate != "") {
                print candidate
            }
            exit
        }
    ' <<<"$body"
}


extract_body_severity() {
    LC_ALL=C awk '
        /^[[:space:]-]*\*\*Severity\*\*:[[:space:]]*/ {
            sub(/^[[:space:]-]*\*\*Severity\*\*:[[:space:]]*/, "")
            gsub(/[[:space:]]+$/, "")
            print
            exit
        }
    ' <<<"$1"
}

extract_focus_area() {
    LC_ALL=C awk '
        /^[[:space:]-]*\*\*Focus area\*\*:[[:space:]]*/ {
            sub(/^[[:space:]-]*\*\*Focus area\*\*:[[:space:]]*/, "")
            gsub(/[[:space:]]+$/, "")
            print
            exit
        }
    ' <<<"$1"
}

extract_reviewer_from_body() {
    LC_ALL=C awk -F: '
        /^[[:space:]-]*\*\*Reviewer\(s\)\*\*:/ ||
        /^[[:space:]-]*\*\*Reviewers?\*\*:/ ||
        /^[[:space:]-]*Reviewer\(s\):/ ||
        /^[[:space:]-]*Reviewers?:/ {
            sub(/^[[:space:]-]*/, "", $1)
            $1=""
            sub(/^:[[:space:]]*/, "", $0)
            gsub(/\*/, "", $0)
            gsub(/^[[:space:]]+|[[:space:]]+$/, "", $0)
            print
            exit
        }
    ' <<<"$1"
}

TMP_OUT="$(mktemp "${TMPDIR:-/tmp}/review-findings-full.XXXXXX")" || fail "cannot create temp output"
DESIGN_REVIEWER_MAP="$(mktemp "${TMPDIR:-/tmp}/review-findings-design-map.XXXXXX")" || fail "cannot create temp map"
trap 'rm -f "$TMP_OUT" "$DESIGN_REVIEWER_MAP"' EXIT
FINDINGS_TOTAL=0

build_design_reviewer_map() {
    : >"$DESIGN_REVIEWER_MAP"
    [ -n "$DESIGN_DIR" ] || return 0
    command -v python3 >/dev/null 2>&1 || return 0
    python3 - "$DESIGN_DIR" "$DESIGN_REVIEWER_MAP" <<'PY' || : >"$DESIGN_REVIEWER_MAP"
import json
import os
import re
import sys
from pathlib import Path

design_dir = Path(sys.argv[1])
out_path = Path(sys.argv[2])

def human_label(slot: str) -> str:
    pairs = [
        ("dyn-cursor-plan-", "Cursor-dyn-", True),
        ("dyn-codex-plan-", "Codex-dyn-", True),
        ("cursor-plan-", "Cursor-", False),
        ("codex-plan-", "Codex-", False),
        ("claude-plan-", "Claude-", False),
    ]
    for prefix, name, dynamic in pairs:
        if slot.startswith(prefix):
            rest = slot[len(prefix):]
            if dynamic:
                return name + rest
            return name + re.sub(r"[_ ]+", " ", rest).title().replace(" ", "")
    return slot

def add(mapping, key, value):
    key = (key or "").strip()
    value = (value or "").strip()
    if key and value and key not in mapping:
        mapping[key] = value

def manifest_paths():
    rounds_root = design_dir / "plan-review"
    round_paths = []
    if rounds_root.is_dir():
        for child in rounds_root.iterdir():
            m = re.match(r"round-([0-9]+)$", child.name)
            if m and child.is_dir():
                round_paths.append((int(m.group(1)), child / "plan-review-slots.ndjson"))
    for _, path in sorted(round_paths):
        yield path
    yield design_dir / "plan-review-slots.ndjson"

mapping = {}
for path in manifest_paths():
    try:
        lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
    except OSError:
        continue
    for line in lines:
        if not line.strip():
            continue
        try:
            row = json.loads(line)
        except Exception:
            continue
        if not isinstance(row, dict):
            continue
        output = str(row.get("output") or "")
        basename = os.path.basename(output)
        slot = str(row.get("slot") or "")
        if not basename:
            continue
        add(mapping, slot, basename)
        add(mapping, human_label(slot), basename)

label_maps = [design_dir / "plan-review-prune-label-map.tsv"]
rounds_root = design_dir / "plan-review"
if rounds_root.is_dir():
    for child in sorted(rounds_root.iterdir(), key=lambda p: p.name):
        if child.is_dir():
            label_maps.append(child / "plan-review-prune-label-map.tsv")
for path in label_maps:
    try:
        lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
    except OSError:
        continue
    for line in lines:
        parts = line.split("\t")
        if len(parts) < 2:
            continue
        slot, label = parts[0].strip(), parts[1].strip()
        if slot in mapping:
            add(mapping, label, mapping[slot])

with out_path.open("w", encoding="utf-8") as fh:
    for key in sorted(mapping):
        fh.write(f"{key}\t{mapping[key]}\n")
PY
}

normalize_design_reviewer_slots() {
    local reviewer="$1"
    [ -s "$DESIGN_REVIEWER_MAP" ] || { printf '%s' "$reviewer"; return 0; }
    python3 - "$DESIGN_REVIEWER_MAP" "$reviewer" <<'PY' 2>/dev/null || printf '%s' "$reviewer"
import sys
mapping = {}
with open(sys.argv[1], encoding="utf-8", errors="replace") as fh:
    for line in fh:
        key, sep, value = line.rstrip("\n").partition("\t")
        if sep and key and value:
            mapping[key] = value
parts = [p.strip() for p in sys.argv[2].split(",")]
out = [mapping.get(p, p) for p in parts if p]
print(",".join(out) if out else sys.argv[2], end="")
PY
}

build_design_reviewer_map

emit_record() {
    local id="$1" phase="$2" outcome="$3" reviewer="$4" body="$5" round_num="$6"
    local reviewer_redacted body_redacted body_severity focus_area category strict_cat=0 reviewer_slots_json
    if [[ "$phase" == "plan-review" ]]; then
        reviewer="$(normalize_design_reviewer_slots "$reviewer")"
    fi
    reviewer_redacted="$(redact_field "$reviewer")" || fail "redaction failed for reviewer in $id"
    body_redacted="$(redact_field "$body")" || fail "redaction failed for prose_body in $id"
    body_severity="$(extract_body_severity "$body_redacted")"
    focus_area="$(extract_focus_area "$body_redacted")"
    [[ "$outcome" == "out_of_scope" ]] && strict_cat=1
    [[ "$phase" == "plan-review" && "$outcome" == "accepted" ]] && strict_cat=1
    category="$(extract_category "$body_redacted" "$strict_cat")"
    body_redacted="${body_redacted:0:2000}"
    reviewer_slots_json=$(jq -nc --arg r "$reviewer_redacted" '($r | split(",") | map(sub("^[[:space:]]+";"") | sub("[[:space:]]+$";"")) | map(select(length > 0))) | if length == 0 then ["panel"] else . end')
    # JSONL: one compact JSON object per line. jq handles string escaping.
    jq -nc \
        --arg id "$id" \
        --arg issue_number "$ISSUE" \
        --arg phase "$phase" \
        --arg outcome "$outcome" \
        --arg round_num "$round_num" \
        --arg category "$category" \
        --arg prose_body "$body_redacted" \
        --arg body_severity "$body_severity" \
        --arg focus_area "$focus_area" \
        --arg schema_version "2" \
        --argjson reviewer_slots "$reviewer_slots_json" \
        '{id: $id, issue_number: $issue_number, phase: $phase, outcome: $outcome, schema_version: $schema_version, reviewer_slots: $reviewer_slots, round_num: $round_num, category: $category, body_severity: $body_severity, focus_area: $focus_area, prose_body: $prose_body}' \
        >> "$TMP_OUT" || fail "failed to write JSONL record for $id"
    FINDINGS_TOTAL=$((FINDINGS_TOTAL + 1))
}

parse_artifact() {
    local file="$1" kind="$2" round_num="${3:-}"
    [ -f "$file" ] && [ -s "$file" ] || return 0

    local pending_id="" pending_reviewer="" pending_title="" pending_body="" counter=0 id_prefix phase outcome
    case "$kind" in
        plan-review-accepted) phase="plan-review"; outcome="accepted"; id_prefix="" ;;
        plan-review-rejected) phase="plan-review"; outcome="rejected"; id_prefix="REJ_P" ;;
        code-review-accepted) phase="code-review"; outcome="accepted"; id_prefix="" ;;
        code-review-rejected) phase="code-review"; outcome="rejected"; id_prefix="REJ_C" ;;
        code-review-oos) phase="code-review"; outcome="out_of_scope"; id_prefix="OOS_C" ;;
        *) fail "internal: unknown kind: $kind" ;;
    esac

    synthetic_id() {
        local prefix="$1" num="$2" round="$3"
        if [ -n "$round" ]; then
            printf '%sR%s_%s' "$prefix" "$round" "$num"
        else
            printf '%s%s' "$prefix" "$num"
        fi
    }

    flush_pending() {
        [ -n "$pending_id" ] || return 0
        local reviewer="$pending_reviewer"
        local body="$pending_body"
        if [ -n "$pending_title" ]; then
            body="## $pending_title"$'\n\n'"$body"
        fi
        if [ -z "$reviewer" ]; then
            reviewer="$(extract_reviewer_from_body "$pending_body")"
        fi
        if [[ "$kind" == "code-review-oos" ]]; then
            local _sec_tmp
            _sec_tmp="$(mktemp)"
            printf '%s\n' "$body" > "$_sec_tmp"
            local _sec_match=false
            if is_security_block "$_sec_tmp" 2>/dev/null; then _sec_match=true; fi
            rm -f "$_sec_tmp"
            if [[ "$_sec_match" == "true" ]]; then
                pending_id=""; pending_reviewer=""; pending_title=""; pending_body=""
                return 0
            fi
        fi
        emit_record "$pending_id" "$phase" "$outcome" "${reviewer:-panel}" "$body" "$round_num"
        pending_id=""; pending_reviewer=""; pending_title=""; pending_body=""
    }

    while IFS= read -r line || [ -n "$line" ]; do
        case "$kind" in
            plan-review-accepted)
                if [[ "$line" =~ ^###[[:space:]]+(FINDING_[0-9A-Za-z_]+):[[:space:]]*(.*)$ ]]; then
                    flush_pending
                    pending_id="${BASH_REMATCH[1]}"
                    pending_title="${BASH_REMATCH[2]}"
                    continue
                fi
                ;;
            code-review-accepted)
                if [[ "$line" =~ ^###[[:space:]]+(FINDING_[0-9A-Za-z_]+):[[:space:]]*(.*)$ ]]; then
                    flush_pending
                    pending_id="${BASH_REMATCH[1]}"
                    pending_title="${BASH_REMATCH[2]}"
                    continue
                fi
                ;;
            plan-review-rejected)
                if [[ "$line" =~ ^###[[:space:]]+\[Plan[[:space:]]+Review\][[:space:]]+(.+)$ ]]; then
                    flush_pending
                    counter=$((counter + 1))
                    pending_id="$(synthetic_id "$id_prefix" "$counter" "$round_num")"
                    pending_reviewer="${BASH_REMATCH[1]}"
                    continue
                fi
                ;;
            code-review-rejected)
                if [[ "$line" =~ ^###[[:space:]]+\[(rejected|Code[[:space:]]+Review)\][[:space:]]+(.+)$ ]]; then
                    flush_pending
                    counter=$((counter + 1))
                    pending_id="$(synthetic_id "$id_prefix" "$counter" "$round_num")"
                    if [ "${BASH_REMATCH[1]}" = "Code Review" ]; then
                        pending_reviewer="${BASH_REMATCH[2]}"
                    fi
                    continue
                fi
                # Inner headings inside a rejected block belong to that block's body.
                if [[ -n "$pending_id" && "$line" =~ ^###[[:space:]] ]]; then
                    pending_body="${pending_body}${pending_body:+$'\n'}$line"
                    continue
                fi
                ;;
            code-review-oos)
                if [[ "$line" =~ ^###[[:space:]]+OOS_[0-9A-Za-z_]+:[[:space:]]*(.*)$ ]]; then
                    flush_pending
                    counter=$((counter + 1))
                    pending_id="$(synthetic_id "$id_prefix" "$counter" "$round_num")"
                    pending_title="${BASH_REMATCH[1]}"
                    continue
                fi
                if [[ "$line" =~ ^###[[:space:]]+FINDING_[0-9A-Za-z_]+:[[:space:]]*\[OUT_OF_SCOPE\][[:space:]]*(.*)$ ]]; then
                    flush_pending
                    counter=$((counter + 1))
                    pending_id="$(synthetic_id "$id_prefix" "$counter" "$round_num")"
                    pending_title="${BASH_REMATCH[1]}"
                    continue
                fi
                # Inner headings inside an OOS block belong to that block's body.
                if [[ -n "$pending_id" && "$line" =~ ^###[[:space:]] ]]; then
                    pending_body="${pending_body}${pending_body:+$'\n'}$line"
                    continue
                fi
                ;;
        esac
        if [[ "$line" =~ ^###[[:space:]] ]]; then
            flush_pending
            continue
        fi
        if [ -n "$pending_id" ]; then
            pending_body="${pending_body}${pending_body:+$'\n'}$line"
        fi
    done < "$file"
    flush_pending
}

filter_design_gate_b_skipped() {
    local accepted_file="$1" rejected_file="$2" out_file="$3"
    command -v python3 >/dev/null 2>&1 || return 1
    python3 - "$accepted_file" "$rejected_file" "$out_file" <<'PY'
import re
import sys
from pathlib import Path

accepted_path, rejected_path, out_path = map(Path, sys.argv[1:4])
reason = "rejected by user during one-by-one review"

def read(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return ""

def blocks(text: str, prefix: str):
    pattern = rf"(?ms)^### {prefix}_[0-9A-Za-z_]+:.*?(?=^### |\Z)"
    return [m.group(0).strip() for m in re.finditer(pattern, text)]

def normalize(block: str) -> str:
    lines = [line.rstrip() for line in block.strip().splitlines() if reason not in line]
    return "\n".join(lines).strip()

skipped = {normalize(block) for block in blocks(read(rejected_path), "FINDING") if reason in block}
accepted = [block for block in blocks(read(accepted_path), "FINDING") if normalize(block) not in skipped]
body = "\n\n".join(accepted)
if body:
    body += "\n\n"
out_path.write_text(body, encoding="utf-8")
PY
}

if [ -n "$DESIGN_DIR" ]; then
    _design_accepted="$DESIGN_DIR/accepted-plan-findings-all.md"
    _design_filtered=""
    [ -s "$_design_accepted" ] || _design_accepted="$DESIGN_DIR/accepted-plan-findings.md"
    if [ -s "$_design_accepted" ] && [ -s "$DESIGN_DIR/rejected-findings.md" ] \
        && grep -Fq 'rejected by user during one-by-one review' "$DESIGN_DIR/rejected-findings.md" 2>/dev/null; then
        _design_filtered="$(mktemp "${TMPDIR:-/tmp}/review-findings-design-accepted.XXXXXX")" || fail "cannot create design accepted filter temp"
        if filter_design_gate_b_skipped "$_design_accepted" "$DESIGN_DIR/rejected-findings.md" "$_design_filtered" 2>/dev/null; then
            _design_accepted="$_design_filtered"
        fi
    fi
    parse_artifact "$_design_accepted" plan-review-accepted ""
    [ -z "$_design_filtered" ] || rm -f "$_design_filtered"
fi
[ -n "$DESIGN_DIR" ] && parse_artifact "$DESIGN_DIR/rejected-findings.md" plan-review-rejected ""
if [ -n "$IMPLEMENT_TMPDIR" ]; then
    shopt -s nullglob
    round_dirs=( "$IMPLEMENT_TMPDIR"/round-* )
    shopt -u nullglob
    round_rejected_found=false
    for round_dir in "${round_dirs[@]+"${round_dirs[@]}"}"; do
        [ -d "$round_dir" ] || continue
        round_num="$(basename "$round_dir" | sed 's/^round-//')"
        parse_artifact "$round_dir/accepted-findings.md" code-review-accepted "$round_num"
        parse_artifact "$round_dir/oos.md" code-review-oos "$round_num"
        if [ -s "$round_dir/rejected-findings-full.md" ]; then
            round_rejected_found=true
            parse_artifact "$round_dir/rejected-findings-full.md" code-review-rejected "$round_num"
        elif [ -s "$round_dir/rejected-findings.md" ]; then
            round_rejected_found=true
            parse_artifact "$round_dir/rejected-findings.md" code-review-rejected "$round_num"
        fi
    done
    if [ "$round_rejected_found" = false ]; then
        if [ -s "$IMPLEMENT_TMPDIR/rejected-findings-full.md" ]; then
            parse_artifact "$IMPLEMENT_TMPDIR/rejected-findings-full.md" code-review-rejected ""
        else
            parse_artifact "$IMPLEMENT_TMPDIR/rejected-findings.md" code-review-rejected ""
        fi
    fi
fi

mkdir -p "$(dirname "$OUTPUT")" || fail "cannot create output directory"
mv -f "$TMP_OUT" "$OUTPUT" || fail "failed to write output: $OUTPUT"
trap - EXIT

emit_kv COMPOSED true
emit_kv OUTPUT "$OUTPUT"
emit_kv FINDINGS_TOTAL "$FINDINGS_TOTAL"
emit_kv MODE jsonl
