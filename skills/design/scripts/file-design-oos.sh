#!/usr/bin/env bash
# file-design-oos.sh — Stage design accepted-OOS for /larch:issue and annotate Filed URLs.
# Phase: prepare (cap + deps) | annotate (parse /issue stdout, sentinel, accepted md).
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)"
# shellcheck source=scripts/lib-quiet.sh
source "$SCRIPT_DIR/../../../scripts/lib-quiet.sh"
larch_quiet_init
# shellcheck source=scripts/lib-design-tmpdir.sh
source "$SCRIPT_DIR/../../../scripts/lib-design-tmpdir.sh"

PLUGIN_ROOT="$(cd "$SCRIPT_DIR/../../.." && pwd -P)"
CAP_SH="$PLUGIN_ROOT/skills/implement/scripts/oos-issue-cap.sh"
DEPS_SH="$PLUGIN_ROOT/skills/implement/scripts/oos-file-conflict-deps.sh"
COUNT_AWK="$PLUGIN_ROOT/skills/implement/scripts/oos-non-security-block-count.awk"
APPEND_FAIL_SH="$PLUGIN_ROOT/scripts/append-tool-failure.sh"

usage() {
  while IFS= read -r line; do larch_err "$line"; done <<'USAGE'
usage: file-design-oos.sh prepare --design-tmpdir DIR [--issue-number N] [--clear-cross-session-cache]
       file-design-oos.sh annotate --design-tmpdir DIR --issue-stdout-file FILE [--issue-number N]
USAGE
}

extract_unfiled_blocks() {
  python3 - "$1" <<'PY'
import re
import sys

path = sys.argv[1]
text = open(path, encoding="utf-8").read()
rx = re.compile(r"^###\s+OOS_(\d+):[^\n]*\n", re.M)
indices = [m.start() for m in rx.finditer(text)]
if not indices:
    sys.exit(0)
for i, start in enumerate(indices):
    end = indices[i + 1] if i + 1 < len(indices) else len(text)
    block = text[start:end]
    if re.search(r"(?m)^\s*-\s*\*\*Filed[ \t]*URL\*\*[ \t]*:", block):
        continue
    sys.stdout.write(block.rstrip("\n") + "\n\n")
PY
}

fdesign_issue_number() {
  printf '%s' "${FDESIGN_ISSUE_NUMBER:-${ISSUE_NUMBER:-}}"
}

fdesign_normalized_issue_number() {
  local raw
  raw=$(fdesign_issue_number)
  if [[ -z "$raw" ]]; then
    return 1
  fi
  if [[ ! "$raw" =~ ^[0-9]+$ ]]; then
    return 1
  fi
  printf '%s' "$raw"
}

fdesign_cross_session_cache_path() {
  local n
  if ! n=$(fdesign_normalized_issue_number); then
    return 0
  fi
  printf '%s' "${HOME}/.cache/larch/design-oos-filed/${n}.md"
}

fdesign_warn_append() {
  local logf="$1" site="$2" tool="$3" msgf="$4"
  [[ -f "$msgf" ]] || printf 'file-design-oos: (no detail)\n' >"$msgf"
  touch "$logf" 2>/dev/null || true
  set +e
  bash "$APPEND_FAIL_SH" \
    --log "$logf" \
    --site "$site" \
    --tool "$tool" \
    --exit-code 1 \
    --category "Warnings" \
    --output-file "$msgf" \
    --redact || true
  set -e
  rm -f "$msgf" 2>/dev/null || true
}

recover_oos_accepted_from_sentinel_urls() {
  local acc="$1" sent="$2" rc
  set +e
  python3 - "$acc" "$sent" >"${acc}.crosssess.tmp" <<'PY'
import re
import sys

acc_path, urls_path = sys.argv[1:3]
with open(urls_path, encoding="utf-8") as fh:
    lines = [ln.rstrip("\n") for ln in fh]

maps = []
plain_urls = []
for ln in lines:
    if ln.startswith("OOS_FILE_MAP\t"):
        parts = ln.split("\t", 2)
        if len(parts) >= 3 and parts[1].strip() and parts[2].strip():
            maps.append((parts[1].strip(), parts[2].strip()))
    else:
        u = ln.strip()
        if u.startswith("http"):
            plain_urls.append(u)

with open(acc_path, encoding="utf-8") as fh:
    text = fh.read()

blk_re = re.compile(
    r"(^###\s+OOS_(\d+):[^\n]*\n)([\s\S]*?)(?=^###\s+OOS_|\Z)",
    re.M,
)
filed_rx = re.compile(r"(?m)^\s*-\s*\*\*Filed[ \t]*URL\*\*[ \t]*:")


def apply_url_to_oos_block(body, osnum, url):
    blk = re.compile(
        rf"(^###\s+OOS_{re.escape(osnum)}:[^\n]*\n)([\s\S]*?)(?=^###\s+OOS_|\Z)",
        re.M,
    )
    m = blk.search(body)
    if not m:
        print(
            "recover_oos_accepted_from_sentinel_urls: OOS_FILE_MAP references missing "
            f"### OOS_{osnum}: block",
            file=sys.stderr,
        )
        sys.exit(2)
    block = m.group(0)
    if filed_rx.search(block):
        return body
    new_block = block.rstrip("\n") + f"\n- **Filed URL**: {url}\n"
    return body[: m.start()] + new_block + body[m.end() :]

if maps:
    for osnum, url in maps:
        text = apply_url_to_oos_block(text, osnum, url)
    sys.stdout.write(text)
    sys.exit(0)

# Without OOS_FILE_MAP lines, pairing plain http(s) URLs to unfiled blocks is only
# safe when there is exactly one URL and exactly one unfiled block (document order).
if plain_urls:
    unfiled_blocks = [
        c.group(0)
        for c in blk_re.finditer(text)
        if not filed_rx.search(c.group(0))
    ]
    if len(plain_urls) > 1 or len(unfiled_blocks) > 1:
        print(
            "recover_oos_accepted_from_sentinel_urls: OOS_FILE_MAP lines are required "
            "when the sentinel lists multiple GitHub URLs or the accepted md has "
            "multiple unfiled OOS blocks (annotate emits OOS_FILE_MAP for each filing).",
            file=sys.stderr,
        )
        sys.exit(2)

urls = plain_urls
ui = 0
while ui < len(urls):
    m = None
    for cand in blk_re.finditer(text):
        block = cand.group(0)
        if filed_rx.search(block):
            continue
        m = cand
        break
    if m is None:
        break
    block = m.group(0)
    new_block = block.rstrip("\n") + f"\n- **Filed URL**: {urls[ui]}\n"
    text = text[: m.start()] + new_block + text[m.end() :]
    ui += 1

if ui != len(urls):
    print(
        "recover_oos_accepted_from_sentinel_urls: unconsumed sentinel URLs "
        "after pairing with unfiled OOS blocks",
        file=sys.stderr,
    )
    sys.exit(2)
sys.stdout.write(text)
PY
  rc=$?
  set -e
  return "$rc"
}

sync_cross_session_oos_cache() {
  local d="$1" sent="$2"
  local warnf="$d/oos-cache-sync.stderr.log"
  local issue_n cache_dir tmpc
  if ! issue_n=$(fdesign_normalized_issue_number); then
    return 0
  fi
  cache_dir="${HOME}/.cache/larch/design-oos-filed"
  : >"$warnf"
  if ! mkdir -p "$cache_dir" 2>>"$warnf"; then
    fdesign_warn_append "$d/execution-issues.md" "design file-design-oos cache" "file-design-oos.sh mkdir" "$warnf"
    return 0
  fi
  if ! tmpc=$(mktemp "${cache_dir}/.oos-cache.XXXXXX" 2>>"$warnf"); then
    fdesign_warn_append "$d/execution-issues.md" "design file-design-oos cache" "file-design-oos.sh mktemp" "$warnf"
    return 0
  fi
  if cp "$sent" "$tmpc" 2>>"$warnf" && mv "$tmpc" "${cache_dir}/${issue_n}.md" 2>>"$warnf"; then
    rm -f "$warnf"
    return 0
  fi
  rm -f "$tmpc" 2>/dev/null || true
  fdesign_warn_append "$d/execution-issues.md" "design file-design-oos cache" "file-design-oos.sh cache mv" "$warnf"
}

cmd_prepare() {
  local d="$DESIGN_TMPDIR"
  local acc="$d/oos-accepted-design.md"
  local sent="$d/oos-issues-created.md"
  local comb="$d/oos-combined.md"
  local deps_out="$d/oos-intra-batch-deps.tsv"
  local order="$d/oos-design-filing-order.txt"
  local cache_p warn_copy

  cache_p=$(fdesign_cross_session_cache_path || true)

  if [[ "${FILEDESIGN_CLEAR_CROSS_SESSION_CACHE:-false}" == true ]] && [[ -n "$cache_p" ]]; then
    rm -f "$cache_p" 2>/dev/null || true
  fi

  if [[ -f "$sent" && -s "$sent" ]]; then
    emit_kv FILE_DESIGN_OOS_STATUS skip-sentinel
    exit 0
  fi

  if [[ -n "$cache_p" && -f "$cache_p" && -s "$cache_p" ]]; then
    warn_copy="$d/oos-cross-session-cache-copy.stderr.log"
    : >"$warn_copy"
    if cp "$cache_p" "${sent}.crosssess.tmp" 2>>"$warn_copy" && mv "${sent}.crosssess.tmp" "$sent" 2>>"$warn_copy"; then
      if recover_oos_accepted_from_sentinel_urls "$acc" "$sent"; then
        mv "${acc}.crosssess.tmp" "$acc"
        [[ ! -s "$warn_copy" ]] && rm -f "$warn_copy"
        emit_kv FILE_DESIGN_OOS_STATUS skip-sentinel
        exit 0
      fi
      rm -f "${acc}.crosssess.tmp"
      printf '%s\n' 'recover_oos_accepted_from_sentinel_urls failed' >"$d/oos-recover-fail.log"
      fdesign_warn_append "$d/execution-issues.md" "design file-design-oos cross-session" "file-design-oos.sh recover" "$d/oos-recover-fail.log"
      rm -f "$sent"
    else
      fdesign_warn_append "$d/execution-issues.md" "design file-design-oos cross-session" "file-design-oos.sh cache->sentinel" "$warn_copy"
    fi
  fi

  if [[ ! -f "$acc" ]] || [[ ! -s "$acc" ]]; then
    emit_kv FILE_DESIGN_OOS_STATUS skip-no-items
    exit 0
  fi

  rm -f "$comb" "$comb.capped.tmp" "$deps_out" "$order" "${comb}.tmp" 2>/dev/null || true
  extract_unfiled_blocks "$acc" >"${comb}.tmp" || true
  if [[ ! -s "${comb}.tmp" ]]; then
    rm -f "${comb}.tmp"
    emit_kv FILE_DESIGN_OOS_STATUS skip-no-items
    exit 0
  fi
  mv "${comb}.tmp" "$comb"

  local n
  n=$(awk '/^###[[:space:]]+OOS_/ {c++} END{print c+0}' "$comb")
  if [[ "${n:-0}" -eq 0 ]]; then
    rm -f "$comb"
    emit_kv FILE_DESIGN_OOS_STATUS skip-no-items
    exit 0
  fi

  local nonsec
  nonsec=$(awk -f "$COUNT_AWK" "$comb" 2>/dev/null | tr -d '[:space:]' || printf '0')
  if [[ "${nonsec:-0}" -eq 0 ]]; then
    rm -f "$comb"
    emit_kv FILE_DESIGN_OOS_STATUS skip-all-security
    exit 0
  fi

  grep -E '^###[[:space:]]+OOS_' "$comb" | sed -E 's/^###[[:space:]]+OOS_([0-9]+):.*/\1/' >"$order"

  if ! bash "$CAP_SH" --input-file "$comb" --output "$comb.capped.tmp"; then
    larch_err "file-design-oos: oos-issue-cap.sh failed"
    rm -f "$comb.capped.tmp"
    exit 2
  fi
  mv "$comb.capped.tmp" "$comb"

  local deps_rc=0 deps_avail=false
  set +e
  bash "$DEPS_SH" --input-file "$comb" --output "$deps_out" 2>"$d/oos-file-conflict-deps.stderr.log"
  deps_rc=$?
  set -e
  if [[ "$deps_rc" -eq 0 ]] && [[ -s "$deps_out" ]]; then
    deps_avail=true
  else
    rm -f "$deps_out"
    larch_err "file-design-oos: oos-file-conflict-deps.sh exit $deps_rc — graceful-degrade (no caller TSV)"
  fi

  if [[ "$deps_avail" == true ]]; then
    emit_kv FILE_DESIGN_OOS_DEPS_AVAILABLE true
  else
    emit_kv FILE_DESIGN_OOS_DEPS_AVAILABLE false
  fi
  emit_kv FILE_DESIGN_OOS_STATUS ready
  emit_kv FILE_DESIGN_OOS_COMBINED "$comb"
  emit_kv FILE_DESIGN_OOS_DEPS_TSV "$deps_out"
  emit_kv FILE_DESIGN_OOS_ORDER "$order"
  exit 0
}

cmd_annotate() {
  local d="$DESIGN_TMPDIR"
  local acc="$d/oos-accepted-design.md"
  local sent="$d/oos-issues-created.md"
  local order="$d/oos-design-filing-order.txt"
  local stdout_file="$ISSUE_STDOUT_FILE"

  if [[ ! -f "$stdout_file" ]]; then
    larch_err "file-design-oos: --issue-stdout-file missing or not a file"
    exit 2
  fi
  if [[ ! -f "$order" ]]; then
    larch_err "file-design-oos: missing $order (run prepare first)"
    exit 2
  fi
  if [[ ! -f "$acc" ]]; then
    larch_err "file-design-oos: missing $acc"
    exit 2
  fi

  local issues_failed=0
  issues_failed=$(grep -E '^ISSUES_FAILED=' "$stdout_file" 2>/dev/null | tail -n 1 | cut -d= -f2- | tr -d '\r' || printf '0')
  if ! [[ "${issues_failed:-0}" =~ ^[0-9]+$ ]]; then
    issues_failed=0
  fi

  python3 - "$acc" "$order" "$stdout_file" "${acc}.annotated.tmp" "${sent}.tmp" <<'PY'
import re
import sys

acc_path, order_path, stdout_path, acc_out, sent_out = sys.argv[1:6]
order = [ln.strip() for ln in open(order_path, encoding="utf-8") if ln.strip()]
text = open(acc_path, encoding="utf-8").read()
lines = [ln.strip() for ln in open(stdout_path, encoding="utf-8")]

url_by_i = {}
dup_by_i = {}
failed = set()
for ln in lines:
    m = re.match(r"^ISSUE_(\d+)_(URL|DUPLICATE_OF_URL)=(.*)$", ln)
    if m:
        i, kind, val = m.group(1), m.group(2), m.group(3).strip()
        if not val:
            continue
        if kind == "URL":
            url_by_i[i] = val
        else:
            dup_by_i[i] = val
    m2 = re.match(r"^ISSUE_(\d+)_FAILED=true$", ln)
    if m2:
        failed.add(m2.group(1))

filed_in_block = re.compile(r"(?m)^\s*-\s*\*\*Filed[ \t]*URL\*\*[ \t]*:")

for idx, osnum in enumerate(order, start=1):
    sk = str(idx)
    if sk in failed:
        continue
    url = url_by_i.get(sk) or dup_by_i.get(sk)
    if not url:
        continue
    blk = re.compile(
        rf"(^###\s+OOS_{re.escape(osnum)}:[^\n]*\n)([\s\S]*?)(?=^###\s+OOS_|\Z)",
        re.M,
    )
    m = blk.search(text)
    if not m:
        continue
    block = m.group(0)
    if filed_in_block.search(block):
        continue
    new_block = block.rstrip("\n") + f"\n- **Filed URL**: {url}\n"
    text = text[: m.start()] + new_block + text[m.end() :]

gh_url = re.compile(r"https://[^[:space:]]+/issues/[0-9]+")
map_lines = []
url_tokens = set()
for idx, osnum in enumerate(order, start=1):
    sk = str(idx)
    if sk in failed:
        continue
    url = url_by_i.get(sk) or dup_by_i.get(sk)
    if not url:
        continue
    map_lines.append(f"OOS_FILE_MAP\t{osnum}\t{url}\n")
    m = gh_url.search(url)
    if m:
        url_tokens.add(m.group(0))

with open(acc_out, "w", encoding="utf-8") as fh:
    fh.write(text)
with open(sent_out, "w", encoding="utf-8") as fh:
    for ml in map_lines:
        fh.write(ml)
    for u in sorted(url_tokens):
        fh.write(u + "\n")
PY

  mv "${sent}.tmp" "$sent"
  mv "${acc}.annotated.tmp" "$acc"

  if [[ "${issues_failed:-0}" -gt 0 ]]; then
    exit 1
  fi
  sync_cross_session_oos_cache "$d" "$sent"
  exit 0
}

PHASE=""
DESIGN_TMPDIR=""
ISSUE_STDOUT_FILE=""
FDESIGN_ISSUE_NUMBER=""
FILEDESIGN_CLEAR_CROSS_SESSION_CACHE=false

while [[ $# -gt 0 ]]; do
  case "$1" in
    prepare | annotate) PHASE="$1"; shift ;;
    --design-tmpdir)
      DESIGN_TMPDIR="${2:?}"
      shift 2
      ;;
    --issue-stdout-file)
      ISSUE_STDOUT_FILE="${2:?}"
      shift 2
      ;;
    --issue-number)
      FDESIGN_ISSUE_NUMBER="${2:?}"
      shift 2
      ;;
    --clear-cross-session-cache)
      FILEDESIGN_CLEAR_CROSS_SESSION_CACHE=true
      shift
      ;;
    -h | --help)
      usage
      exit 0
      ;;
    *)
      larch_err "file-design-oos.sh: unknown argument: $1"
      usage
      exit 2
      ;;
  esac
done

if [[ "$PHASE" == annotate ]] && [[ "${FILEDESIGN_CLEAR_CROSS_SESSION_CACHE:-false}" == true ]]; then
  larch_err "file-design-oos: --clear-cross-session-cache is only valid for prepare"
  usage
  exit 2
fi

if [[ -z "$PHASE" || -z "$DESIGN_TMPDIR" ]]; then
  usage
  exit 2
fi
larch_design_tmpdir_validate "$DESIGN_TMPDIR" || exit $?
case "$PHASE" in
  prepare) cmd_prepare ;;
  annotate)
    if [[ -z "$ISSUE_STDOUT_FILE" ]]; then
      usage
      exit 2
    fi
    cmd_annotate
    ;;
  *)
    usage
    exit 2
    ;;
esac
