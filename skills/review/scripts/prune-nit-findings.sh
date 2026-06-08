#!/usr/bin/env bash
# prune-nit-findings.sh — Move in-scope nit-severity findings to the OOS track.
#
# Invoked by review-core.sh (code path) and plan-review-loop.sh (plan path) after
# findings are collected and before the voting round so judges never spend a vote
# on an in-scope nit finding.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../../.." && pwd -P)"
PLUGIN_ROOT="${CLAUDE_PLUGIN_ROOT:-$REPO_ROOT}"
if [[ ! -f "$PLUGIN_ROOT/scripts/lib-quiet.sh" ]]; then
    PLUGIN_ROOT="$REPO_ROOT"
fi
# shellcheck source=scripts/lib-quiet.sh
source "$PLUGIN_ROOT/scripts/lib-quiet.sh"
larch_quiet_init

usage() {
    larch_err "Usage: prune-nit-findings.sh --findings-file PATH --oos-file PATH [--input-mode code|plan]"
}

FINDINGS_FILE=""
OOS_FILE=""
INPUT_MODE="code"

while [[ $# -gt 0 ]]; do
    case "$1" in
        --findings-file) FINDINGS_FILE="${2:?--findings-file requires a value}"; shift 2 ;;
        --oos-file) OOS_FILE="${2:?--oos-file requires a value}"; shift 2 ;;
        --input-mode) INPUT_MODE="${2:?--input-mode requires a value}"; shift 2 ;;
        --help) usage; exit 0 ;;
        *) larch_err "prune-nit-findings.sh: unknown option: $1"; usage; exit 2 ;;
    esac
done

[[ -n "$FINDINGS_FILE" ]] || { larch_err "prune-nit-findings.sh: --findings-file is required"; exit 2; }
[[ -n "$OOS_FILE" ]] || { larch_err "prune-nit-findings.sh: --oos-file is required"; exit 2; }
[[ "$INPUT_MODE" == "code" || "$INPUT_MODE" == "plan" ]] || {
    larch_err "prune-nit-findings.sh: --input-mode must be code or plan"
    exit 2
}
[[ -f "$FINDINGS_FILE" ]] || { larch_err "prune-nit-findings.sh: --findings-file not found: $FINDINGS_FILE"; exit 2; }

if [[ "${LARCH_PRUNE_NITS_DISABLED:-}" == "1" ]]; then
    emit_kv PRUNED_COUNT 0
    emit_kv INSCOPE_REMAINING 0
    emit_kv STATUS disabled
    exit 0
fi

_prune_py="$FINDINGS_FILE.prune-nit-inline.py"
cat > "$_prune_py" <<'PY'
import re, sys, os, tempfile, shutil

findings_file, oos_file, input_mode = sys.argv[1:4]

# Reuse the exact severity pattern from aggregate-findings.sh:321
SEVERITY_PAT = re.compile(r'(?m)^-\s*\*\*Severity\*\*:\s*(important|latent|nit)\s*$', re.IGNORECASE)
FINDING_BLOCK_PAT = re.compile(r'(?ms)^### FINDING_[0-9]+:.*?(?=^### |\Z)')
OOS_BLOCK_PAT = re.compile(r'(?ms)^### OOS_[0-9]+:.*?(?=^### |\Z)')


def fail_open():
    print('PRUNED_COUNT=0')
    print('INSCOPE_REMAINING=0')
    print('STATUS=skipped')
    sys.exit(0)


try:
    text = open(findings_file, 'r', encoding='utf-8', errors='replace').read()
except Exception:
    fail_open()

oos_text = ''
if os.path.exists(oos_file):
    try:
        oos_text = open(oos_file, 'r', encoding='utf-8', errors='replace').read()
    except Exception:
        fail_open()

# Split into FINDING_N blocks
blocks = [m.group(0).strip() for m in FINDING_BLOCK_PAT.finditer(text)]

inscope = []
pruned = []
for block in blocks:
    m = SEVERITY_PAT.search(block)
    if m and m.group(1).lower() == 'nit':
        pruned.append(block)
    else:
        inscope.append(block)

if not pruned:
    print('PRUNED_COUNT=0')
    print('INSCOPE_REMAINING=%d' % len(inscope))
    print('STATUS=ok')
    sys.exit(0)

# Renumber remaining in-scope FINDING_N ids in first-seen order (match aggregate-findings.sh id-rewriting)
new_inscope = []
for i, block in enumerate(inscope, 1):
    new_inscope.append(re.sub(r'^### FINDING_[0-9]+:', '### FINDING_%d:' % i, block, count=1, flags=re.M))

new_findings_content = '\n\n'.join(new_inscope) + ('\n\n' if new_inscope else '')

# Prepare OOS additions depending on input-mode
if input_mode == 'plan':
    # findings-oos.md uses OOS_N format; convert moved FINDING_N blocks to OOS_N
    existing_oos = [m.group(0).strip() for m in OOS_BLOCK_PAT.finditer(oos_text)]
    next_num = len(existing_oos) + 1
    oos_additions = []
    for j, block in enumerate(pruned, next_num):
        new_block = re.sub(r'^### FINDING_[0-9]+:', '### OOS_%d:' % j, block, count=1, flags=re.M)
        oos_additions.append(new_block)
else:
    # code review path: oos.md uses FINDING_N: [OUT_OF_SCOPE] ... format
    oos_additions = []
    for block in pruned:
        lines = block.split('\n')
        heading = lines[0]
        m2 = re.match(r'^(### FINDING_[0-9]+:)\s*(.*)', heading)
        if m2:
            title = m2.group(2).strip()
            if not title.startswith('[OUT_OF_SCOPE]'):
                title = '[OUT_OF_SCOPE] ' + title if title else '[OUT_OF_SCOPE]'
            lines[0] = m2.group(1) + ' ' + title
        oos_additions.append('\n'.join(lines))

try:
    # Write findings-file atomically (write to temp, then rename)
    dirn = os.path.dirname(os.path.abspath(findings_file))
    fd, tmp_path = tempfile.mkstemp(dir=dirn)
    try:
        with os.fdopen(fd, 'w', encoding='utf-8') as f:
            f.write(new_findings_content)
        shutil.move(tmp_path, findings_file)
    except Exception:
        try:
            os.unlink(tmp_path)
        except OSError:
            pass
        raise

    # Append OOS additions to oos-file
    if oos_additions:
        separator = '\n\n'
        with open(oos_file, 'a', encoding='utf-8') as f:
            f.write(separator + '\n\n'.join(oos_additions) + '\n\n')
except Exception:
    fail_open()

print('PRUNED_COUNT=%d' % len(pruned))
print('INSCOPE_REMAINING=%d' % len(inscope))
print('STATUS=ok')
PY

_prune_out=""
set +e
_prune_out=$(python3 "$_prune_py" "$FINDINGS_FILE" "$OOS_FILE" "$INPUT_MODE")
_prune_rc=$?
set -e
rm -f "$_prune_py"
if [[ "$_prune_rc" -ne 0 ]]; then
    emit_kv PRUNED_COUNT 0
    emit_kv INSCOPE_REMAINING 0
    emit_kv STATUS skipped
    exit 0
fi

pruned_count=""
inscope_remaining=""
status=""
while IFS= read -r _line || [[ -n "$_line" ]]; do
    [[ -z "$_line" ]] && continue
    _k="${_line%%=*}"
    _v="${_line#*=}"
    case "$_k" in
        PRUNED_COUNT) pruned_count="$_v" ;;
        INSCOPE_REMAINING) inscope_remaining="$_v" ;;
        STATUS) status="$_v" ;;
    esac
done <<< "$_prune_out"

pruned_count="${pruned_count:-0}"
inscope_remaining="${inscope_remaining:-0}"
status="${status:-skipped}"

if [[ "$status" == "ok" && "${pruned_count}" != "0" ]]; then
    larch_err "→ prune-nit-findings: pruned ${pruned_count} nit finding(s) to OOS track (${inscope_remaining} in-scope remaining)"
fi

emit_kv PRUNED_COUNT "$pruned_count"
emit_kv INSCOPE_REMAINING "$inscope_remaining"
emit_kv STATUS "$status"
