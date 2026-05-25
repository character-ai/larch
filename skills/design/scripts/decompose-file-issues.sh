#!/usr/bin/env bash
# decompose-file-issues.sh — partition batch filing + annotate + close-original for /design decomposition.
# Topology composition: prepare annotate close-original
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)"
PLUGIN_ROOT="${CLAUDE_PLUGIN_ROOT:-$(cd "$SCRIPT_DIR/../../.." && pwd -P)}"
LARCH_QUIET_DISABLE=1
export LARCH_QUIET_DISABLE
# shellcheck source=scripts/lib-quiet.sh
source "$PLUGIN_ROOT/scripts/lib-quiet.sh"
larch_quiet_init

APPEND_FAIL_SH="$PLUGIN_ROOT/scripts/append-tool-failure.sh"

usage() {
    larch_err "usage: decompose-file-issues.sh prepare --design-tmpdir DIR --partition-file PATH [--issue-number N]"
    larch_err "       decompose-file-issues.sh annotate --design-tmpdir DIR --issue-stdout-file FILE [--issue-number N]"
    larch_err "       decompose-file-issues.sh close-original --design-tmpdir DIR --original-issue N --repo OWNER/REPO"
}

DESIGN_TMPDIR=""
ISSUE_NUMBER=""

cmd_prepare() {
    local partition_file=""
    while [[ $# -gt 0 ]]; do
        case "$1" in
            --design-tmpdir) DESIGN_TMPDIR="${2:?}"; shift 2 ;;
            --partition-file) partition_file="${2:?}"; shift 2 ;;
            --issue-number) ISSUE_NUMBER="${2:?}"; shift 2 ;;
            *) larch_err "prepare: unknown option: $1"; usage; exit 2 ;;
        esac
    done
    [[ -n "$DESIGN_TMPDIR" ]] || { larch_err "prepare: --design-tmpdir required"; exit 2; }
    [[ -n "$partition_file" ]] || { larch_err "prepare: --partition-file required"; exit 2; }
    [[ -f "$partition_file" ]] || { larch_err "prepare: partition file not found"; exit 2; }
    DESIGN_TMPDIR=$(cd "$DESIGN_TMPDIR" && pwd -P)
    local dec="$DESIGN_TMPDIR/decompose"
    mkdir -p "$dec"
    rm -f "$dec/partition-input.txt" "$dec/partition-deps.tsv"
    local _plog="$dec/prepare-python.log"
    set +e
    python3 - "$partition_file" "$dec/partition-input.txt" "$dec/partition-deps.tsv" "$DESIGN_TMPDIR/feature-description.txt" "${ISSUE_NUMBER:-}" >"$_plog" 2>&1 <<'PY'
import pathlib
import re
import sys
from collections import defaultdict, deque

partition_path = pathlib.Path(sys.argv[1])
out_input = pathlib.Path(sys.argv[2])
out_deps = pathlib.Path(sys.argv[3])
feat_path = pathlib.Path(sys.argv[4])
issue_num = (sys.argv[5] or "").strip()

text = partition_path.read_text(encoding="utf-8")
if "## Pieces" not in text:
    print("DECOMPOSE_PARTITION_STATUS=invalid-partition-file", flush=True)
    sys.exit(2)

piece_rx = re.compile(r"(?m)^###\s+Piece\s+(\d+)\s*:\s*([^\n]+)$")
pieces = []


def neutralize_markdown_h3_line_starts(text: str) -> str:
    """Avoid embedded lines matching ^### so generic /larch:issue batch parsers do not split items."""
    return re.sub(r"(?m)^###", "\u200b###", text)


for m in piece_rx.finditer(text):
    idx = int(m.group(1))
    title = m.group(2).strip()
    start = m.end()
    nxt = piece_rx.search(text, start)
    end = nxt.start() if nxt else len(text)
    body = text[start:end].strip()
    pieces.append((idx, title, body))

if not pieces:
    print("DECOMPOSE_PARTITION_STATUS=no-pieces", flush=True)
    sys.exit(2)

pieces.sort(key=lambda t: t[0])
n = len(pieces)
index_by_num = {p[0]: i for i, p in enumerate(pieces)}

edges = []
dep_lines = []
for i, (pnum, title, body) in enumerate(pieces):
    dep = "none"
    for ln in body.splitlines():
        s = ln.strip()
        if s.lower().startswith("- dependencies:"):
            dep = s.split(":", 1)[1].strip()
            break
    dep_lines.append(dep)
    m = re.search(r"blocked-by\s+Piece\s+(\d+)", dep, re.I)
    if m:
        blocker = int(m.group(1))
        if blocker not in index_by_num:
            print("DECOMPOSE_PARTITION_STATUS=bad-dependency-ref", flush=True)
            sys.exit(2)
        bi = index_by_num[blocker]
        edges.append((bi, i))

adj = defaultdict(list)
indeg = [0] * n
for a, b in edges:
    adj[a].append(b)
    indeg[b] += 1
q = deque([i for i in range(n) if indeg[i] == 0])
seen = 0
while q:
    u = q.popleft()
    seen += 1
    for v in adj[u]:
        indeg[v] -= 1
        if indeg[v] == 0:
            q.append(v)
if seen != n:
    w_parts = []
    for a, b in edges:
        w_parts.append(f"Piece {pieces[a][0]}→Piece {pieces[b][0]}")
    witness = "; ".join(w_parts) if w_parts else "(edges unavailable)"
    print(f"DECOMPOSE_PARTITION_CYCLE_WITNESS={witness}", flush=True)
    print("DECOMPOSE_PARTITION_STATUS=cycle-detected", flush=True)
    sys.exit(0)

feat = feat_path.read_text(encoding="utf-8") if feat_path.is_file() else ""
feat = neutralize_markdown_h3_line_starts(feat)
orig = f"#{issue_num}" if issue_num.isdigit() else "(original issue — set ISSUE_NUMBER in session)"

lines = []
for i, (pnum, title, body) in enumerate(pieces):
    scope = ""
    for ln in body.splitlines():
        if ln.strip().lower().startswith("- scope:"):
            scope = ln.split(":", 1)[1].strip()
            break
    lines.append(f"### {title}\n")
    lines.append(
        neutralize_markdown_h3_line_starts(
            f"Partition piece {pnum} of {n} split from {orig}.\n\n"
            f"**Scope**: {scope or '(see parent partition file)'}\n\n"
            f"**Dependencies (from panel)**: {dep_lines[i]}\n\n"
            "```\n"
            "<!-- larch:plan:start -->\n"
            "## Plan\n\n"
            "(needs /design — operator runs `/design` on this issue after partition lands.)\n\n"
            "<!-- larch:plan:end -->\n"
            "```\n\n"
            f"**Original feature context (excerpt)**:\n\n{feat[:4000]}\n"
        )
    )

out_input.write_text("\n".join(lines) + "\n", encoding="utf-8")

with out_deps.open("w", encoding="utf-8") as fh:
    for a, b in edges:
        fh.write(f"{a + 1}\t{b + 1}\n")

print("DECOMPOSE_PARTITION_STATUS=ok", flush=True)
PY
    local _prc=$?
    set -e
    local _st=""
    _st=$(grep -E '^DECOMPOSE_PARTITION_STATUS=' "$_plog" | tail -1 || true)
    if [[ -n "$_st" ]]; then
        emit_kv DECOMPOSE_PARTITION_STATUS "${_st#DECOMPOSE_PARTITION_STATUS=}"
    fi
    local _pv=""
    _pv=$(grep -E '^DECOMPOSE_PARTITION_CYCLE_WITNESS=' "$_plog" | tail -1 || true)
    if [[ -n "$_pv" ]]; then
        emit_kv DECOMPOSE_PARTITION_CYCLE_WITNESS "${_pv#DECOMPOSE_PARTITION_CYCLE_WITNESS=}"
    fi
    if [[ "$_prc" != 0 ]] || [[ -n "$_st" && "${_st#DECOMPOSE_PARTITION_STATUS=}" != "ok" ]]; then
        rm -f "$dec/partition-input.txt" "$dec/partition-deps.tsv"
    fi
    if [[ "$_prc" != 0 ]]; then
        exit "$_prc"
    fi
}

cmd_annotate() {
    local stdout_file=""
    while [[ $# -gt 0 ]]; do
        case "$1" in
            --design-tmpdir) DESIGN_TMPDIR="${2:?}"; shift 2 ;;
            --issue-stdout-file) stdout_file="${2:?}"; shift 2 ;;
            --issue-number) ISSUE_NUMBER="${2:?}"; shift 2 ;;
            *) larch_err "annotate: unknown option: $1"; usage; exit 2 ;;
        esac
    done
    [[ -n "$DESIGN_TMPDIR" ]] || { larch_err "annotate: --design-tmpdir required"; exit 2; }
    [[ -n "$stdout_file" ]] || { larch_err "annotate: --issue-stdout-file required"; exit 2; }
    [[ -f "$stdout_file" ]] || { larch_err "annotate: stdout capture missing"; exit 2; }
    DESIGN_TMPDIR=$(cd "$DESIGN_TMPDIR" && pwd -P)
    local sent="$DESIGN_TMPDIR/.decompose-issues-filed"
    local dec="$DESIGN_TMPDIR/decompose"
    mkdir -p "$dec"
    local filed="$dec/partition-filed.md"

    python3 - "$stdout_file" "$sent" "$filed" <<'PY'
import pathlib
import re
import sys

stdout_path = pathlib.Path(sys.argv[1])
sent_path = pathlib.Path(sys.argv[2])
filed_path = pathlib.Path(sys.argv[3])
text = stdout_path.read_text(encoding="utf-8")

def kv(pat, s):
    m = re.search(pat, s, re.M)
    return m.group(1) if m else ""

created = kv(r"(?m)^ISSUES_CREATED=([0-9]+)\s*$", text) or "0"
failed = kv(r"(?m)^ISSUES_FAILED=([0-9]+)\s*$", text) or "0"
failed_n = int(failed)
urls = {}
for m in re.finditer(r"(?m)^ISSUE_([0-9]+)_URL=(.+)\s*$", text):
    urls[int(m.group(1))] = m.group(2).strip()

if sent_path.is_file():
    prev = sent_path.read_text(encoding="utf-8")
    if prev.strip() and filed_path.is_file() and failed_n == 0:
        # Idempotent no-op when sentinel already records the same URLs
        ok = True
        for i, u in sorted(urls.items()):
            if f"PARTITION_FILE_MAP\t{i}\t{u}" not in prev:
                ok = False
                break
        if ok and int(created) == len(urls):
            sys.exit(0)

lines = ["# Partition filing record", ""]
lines.append(f"- **ISSUES_CREATED**: {created}")
lines.append(f"- **ISSUES_FAILED**: {failed}")
lines.append("")
for i in sorted(urls):
    lines.append(f"## Piece {i}")
    lines.append(f"- **Filed URL**: {urls[i]}")
    lines.append("")
filed_path.write_text("\n".join(lines) + "\n", encoding="utf-8")

if failed_n == 0:
    with sent_path.open("w", encoding="utf-8") as fh:
        for i in sorted(urls):
            fh.write(f"PARTITION_FILE_MAP\t{i}\t{urls[i]}\n")
elif sent_path.is_file():
    sent_path.unlink()
PY
}

cmd_close_original() {
    local original=""
    local repo=""
    while [[ $# -gt 0 ]]; do
        case "$1" in
            --design-tmpdir) DESIGN_TMPDIR="${2:?}"; shift 2 ;;
            --original-issue) original="${2:?}"; shift 2 ;;
            --repo) repo="${2:?}"; shift 2 ;;
            *) larch_err "close-original: unknown option: $1"; usage; exit 2 ;;
        esac
    done
    [[ -n "$DESIGN_TMPDIR" ]] || { larch_err "close-original: --design-tmpdir required"; exit 2; }
    [[ -n "$original" ]] || { larch_err "close-original: --original-issue required"; exit 2; }
    [[ -n "$repo" ]] || { larch_err "close-original: --repo required"; exit 2; }
    DESIGN_TMPDIR=$(cd "$DESIGN_TMPDIR" && pwd -P)
    local dec="$DESIGN_TMPDIR/decompose"
    local filed="$dec/partition-filed.md"
    [[ -f "$filed" ]] || { larch_err "close-original: missing partition-filed.md (run annotate first)"; exit 2; }

    local body="$dec/close-comment-draft.md"
    local comment_sent="$dec/.decompose-close-comment-posted"
    {
        printf 'This issue is **obviated by a partition** into follow-up work.\n\n'
        printf '## New pieces\n\n'
        grep -E '^\#\# Piece |^\-\s\*\*Filed URL\*\*' "$filed" || true
        printf '\n## Blocked-by chain\n\n'
        printf 'See intra-batch dependency edges filed via /larch:issue (partition-deps.tsv).\n'
    } >"$body"

    local redact_sh="${DECOMPOSE_REDACT_SH:-$PLUGIN_ROOT/scripts/redact-secrets.sh}"
    local redacted="$dec/close-comment.redacted.md"
    if ! "$redact_sh" <"$body" >"$redacted"; then
        if [[ -x "$APPEND_FAIL_SH" ]]; then
            set +e
            bash "$APPEND_FAIL_SH" \
                --log "$DESIGN_TMPDIR/execution-issues.md" \
                --site "design decompose close-original" \
                --tool "redact-secrets.sh" \
                --exit-code 1 \
                --category "External Reviewer Issues" \
                --output-file "$body" \
                --redact || true
            set -e
        fi
        emit_kv CLOSE_ORIGINAL_STATUS failed
        exit 1
    fi

    if [[ ! -f "$comment_sent" ]]; then
        set +e
        gh issue comment "$original" --repo "$repo" --body-file "$redacted"
        _c_rc=$?
        set -e
        if [[ "$_c_rc" != 0 ]]; then
            if [[ -x "$APPEND_FAIL_SH" ]]; then
                set +e
                bash "$APPEND_FAIL_SH" \
                    --log "$DESIGN_TMPDIR/execution-issues.md" \
                    --site "design decompose close-original" \
                    --tool "gh issue comment" \
                    --exit-code "$_c_rc" \
                    --category "External Reviewer Issues" \
                    --output-file "$redacted" \
                    --redact || true
                set -e
            fi
            emit_kv CLOSE_ORIGINAL_STATUS failed
            exit 1
        fi
        : >"$comment_sent"
    fi

    set +e
    gh issue close "$original" --repo "$repo"
    _cl_rc=$?
    set -e
    if [[ "$_cl_rc" != 0 ]]; then
        if [[ -x "$APPEND_FAIL_SH" ]]; then
            set +e
            bash "$APPEND_FAIL_SH" \
                --log "$DESIGN_TMPDIR/execution-issues.md" \
                --site "design decompose close-original" \
                --tool "gh issue close" \
                --exit-code "$_cl_rc" \
                --category "External Reviewer Issues" \
                --output-file "$redacted" \
                --redact || true
            set -e
        fi
        emit_kv CLOSE_ORIGINAL_STATUS failed
        exit 1
    fi

    rm -f "$comment_sent"
    : >"$DESIGN_TMPDIR/.decompose-original-closed"
    emit_kv CLOSE_ORIGINAL_STATUS ok
    exit 0
}

[[ $# -ge 1 ]] || { usage; exit 2; }
_sub="$1"
shift
case "$_sub" in
    prepare) cmd_prepare "$@" ;;
    annotate) cmd_annotate "$@" ;;
    close-original) cmd_close_original "$@" ;;
    *) usage; exit 2 ;;
esac
