#!/usr/bin/env bash
# file-design-oos.sh — Stage design accepted-OOS for /larch:issue and annotate Filed URLs.
# Phase: prepare (cap + deps) | annotate (parse /issue stdout, sentinel, accepted md).
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)"
# shellcheck source=scripts/lib-quiet.sh
source "$SCRIPT_DIR/../../../scripts/lib-quiet.sh"
larch_quiet_init

PLUGIN_ROOT="$(cd "$SCRIPT_DIR/../../.." && pwd -P)"
CAP_SH="$PLUGIN_ROOT/skills/implement/scripts/oos-issue-cap.sh"
DEPS_SH="$PLUGIN_ROOT/skills/implement/scripts/oos-file-conflict-deps.sh"
COUNT_AWK="$PLUGIN_ROOT/skills/implement/scripts/oos-non-security-block-count.awk"

usage() {
  while IFS= read -r line; do larch_err "$line"; done <<'USAGE'
usage: file-design-oos.sh prepare --design-tmpdir DIR
       file-design-oos.sh annotate --design-tmpdir DIR --issue-stdout-file FILE
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
    if re.search(r"(?m)^\s*-\s*\*\*Filed URL\*\*\s*:", block):
        continue
    sys.stdout.write(block.rstrip("\n") + "\n\n")
PY
}

cmd_prepare() {
  local d="$DESIGN_TMPDIR"
  local acc="$d/oos-accepted-design.md"
  local sent="$d/oos-issues-created.md"
  local comb="$d/oos-combined.md"
  local deps_out="$d/oos-intra-batch-deps.tsv"
  local order="$d/oos-design-filing-order.txt"

  if [[ -f "$sent" && -s "$sent" ]]; then
    emit_kv FILE_DESIGN_OOS_STATUS skip-sentinel
    exit 0
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

  python3 - "$acc" "$order" "$stdout_file" >"${acc}.annotated.tmp" <<'PY'
import re
import sys

acc_path, order_path, stdout_path = sys.argv[1:4]
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
    if re.search(r"(?m)^\s*-\s*\*\*Filed URL\*\*\s*:", block):
        continue
    new_block = block.rstrip("\n") + f"\n- **Filed URL**: {url}\n"
    text = text[: m.start()] + new_block + text[m.end() :]

sys.stdout.write(text)
PY

  local urls_tmp="${sent}.urls.tmp"
  : >"$urls_tmp"
  while IFS= read -r ln; do
    case "$ln" in
      ISSUE_*_DUPLICATE_OF_URL=*)
        val="${ln#*=}"
        val="${val//$'\r'/}"
        if [[ -n "$val" ]]; then
          printf '%s\n' "$val"
        fi
        ;;
      ISSUE_*_URL=*)
        val="${ln#*=}"
        val="${val//$'\r'/}"
        if [[ -n "$val" ]]; then
          printf '%s\n' "$val"
        fi
        ;;
    esac
  done <"$stdout_file" | grep -Eho 'https://[^[:space:]]+/issues/[0-9]+' >>"$urls_tmp" || true
  if [[ -s "$urls_tmp" ]]; then
    sort -u "$urls_tmp" >"${sent}.tmp"
    rm -f "$urls_tmp"
    mv "${sent}.tmp" "$sent"
  else
    rm -f "$urls_tmp"
    : >"${sent}.tmp"
    mv "${sent}.tmp" "$sent"
  fi

  mv "${acc}.annotated.tmp" "$acc"

  if [[ "${issues_failed:-0}" -gt 0 ]]; then
    exit 1
  fi
  exit 0
}

PHASE=""
DESIGN_TMPDIR=""
ISSUE_STDOUT_FILE=""

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

if [[ -z "$PHASE" || -z "$DESIGN_TMPDIR" ]]; then
  usage
  exit 2
fi
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
