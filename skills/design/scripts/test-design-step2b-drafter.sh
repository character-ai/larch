#!/usr/bin/env bash
# test-design-step2b-drafter.sh — stale-sidecar cleanup and Codex drafter token ingestion.
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/../../.." && pwd -P)"
WRAPPER="$REPO_ROOT/skills/design/scripts/design-step2b-drafter.sh"
TMP_ROOT="$(mktemp -d "${TMPDIR:-/tmp}/step2b-drafter-test.XXXXXX")"
trap 'rm -rf "$TMP_ROOT"' EXIT

fail() { printf 'FAIL: %s\n' "$1" >&2; exit 1; }
pass() { printf 'PASS: %s\n' "$1"; }

make_fake_plugin() {
    local root="$1"
    mkdir -p "$root/scripts" "$root/skills/design/scripts" "$root/skills/design/references"
    ln -s "$REPO_ROOT/python" "$root/python"
    cat > "$root/skills/design/references/readability-style.md" <<'STYLE'
- Test readability style.
STYLE
    cat > "$root/skills/design/scripts/emit-design-plan-preview.sh" <<'PREVIEW'
#!/usr/bin/env bash
set -euo pipefail
exit 0
PREVIEW
    chmod +x "$root/skills/design/scripts/emit-design-plan-preview.sh"
}

write_session_env() {
    local env_file="$1" design_tmpdir="$2" plugin_root="$3"
    cat > "$env_file" <<EOF_ENV
export DESIGN_TMPDIR='$design_tmpdir'
export SESSION_TMPDIR='$design_tmpdir'
export SESSION_ID='test-session'
export ISSUE_NUMBER='1'
export ISSUE_TITLE='Test issue'
export REPO='example/repo'
export CODEX_PRESENT='true'
export CURSOR_PRESENT='false'
export LARCH_DESIGN_DRAFTER='codex'
export CLAUDE_PLUGIN_ROOT='$plugin_root'
export LARCH_TOKEN_SESSION_ID='step2b-drafter-test'
export IMPLEMENT_TMPDIR=''
unset LARCH_TOKEN_LEDGER
EOF_ENV
}

# Stale sidecar is removed before a no-sidecar launch and must not be ingested.
plugin1="$TMP_ROOT/plugin1"
design1="$TMP_ROOT/design1"
mkdir -p "$design1"
make_fake_plugin "$plugin1"
cat > "$plugin1/scripts/launch-codex-drafter.sh" <<'STUB'
#!/usr/bin/env bash
set -euo pipefail
out=""
while [[ $# -gt 0 ]]; do
  case "$1" in
    --output-file) out="$2"; shift 2 ;;
    *) shift ;;
  esac
done
printf 'STATUS=ERROR\nPLAN_WRITTEN=false\nDRAFTER_LAUNCHED=true\nREASON=no-sidecar\n' > "$out"
printf 'STATUS=ERROR\nOUTPUT_FILE=%s\nTOKEN_RECORD=%s.token-record\n' "$out" "$out"
exit 1
STUB
chmod +x "$plugin1/scripts/launch-codex-drafter.sh"
printf 'TOOL=codex\nINPUT=1\nOUTPUT=1\nTOTAL=2\nRAW=codex_plan_draft\n' > "$design1/step2b-drafter-status.txt.token-record"
write_session_env "$design1/session.env" "$design1" "$plugin1"
env -u IMPLEMENT_TMPDIR -u LARCH_TOKEN_LEDGER CLAUDE_PLUGIN_ROOT="$plugin1" "$WRAPPER" --session-env-path "$design1/session.env" --claude-pid $$ >/dev/null 2>"$design1/stderr.log" || true
[[ ! -e "$design1/token-report.ndjson" ]] || fail 'stale sidecar was appended to token-report.ndjson'
if compgen -G "$design1/larch-tokens-*.jsonl" >/dev/null; then
    fail 'stale sidecar reached active ledger'
fi
pass 'stale Codex drafter sidecar cleanup'

# Fresh sidecar is appended once to both token-report.ndjson and active ledger.
plugin2="$TMP_ROOT/plugin2"
design2="$TMP_ROOT/design2"
impl2="$TMP_ROOT/implement2"
stale_ledger2="$TMP_ROOT/stale-ledger2.jsonl"
mkdir -p "$design2" "$impl2"
make_fake_plugin "$plugin2"
cat > "$plugin2/scripts/launch-codex-drafter.sh" <<'STUB'
#!/usr/bin/env bash
set -euo pipefail
out=""; design=""
while [[ $# -gt 0 ]]; do
  case "$1" in
    --output-file) out="$2"; shift 2 ;;
    --design-tmpdir) design="$2"; shift 2 ;;
    *) shift ;;
  esac
done
cat > "$design/plan.txt" <<'PLAN'
## Plan

diff_lines: 1
PLAN
printf 'STATUS=OK\nPLAN_WRITTEN=true\nPLAN_LINES=3\nDIFF_LINES=1\nSUMMARY_WRITTEN=false\nDRAFTER_LAUNCHED=true\n' > "$out"
printf 'STATUS=clean\nMODE=absolute\nREASON=test\n' > "$out.dirty-tree"
printf 'TOOL=codex\nINPUT=10\nOUTPUT=2\nCACHE_READ=30\nTOTAL=42\nRAW=codex_plan_draft\nMODEL=gpt-5.5\n' > "$out.token-record"
printf 'STATUS=OK\nOUTPUT_FILE=%s\nTOKEN_RECORD=%s.token-record\n' "$out" "$out"
STUB
chmod +x "$plugin2/scripts/launch-codex-drafter.sh"
write_session_env "$design2/session.env" "$design2" "$plugin2"
{
    printf "export IMPLEMENT_TMPDIR='%s'\n" "$impl2"
    printf "export LARCH_TOKEN_LEDGER='%s'\n" "$stale_ledger2"
    printf "export LARCH_TOKEN_SESSION_ID='stale-parent-session'\n"
} >> "$design2/session.env"
env -u IMPLEMENT_TMPDIR -u LARCH_TOKEN_LEDGER CLAUDE_PLUGIN_ROOT="$plugin2" "$WRAPPER" --session-env-path "$design2/session.env" --claude-pid $$ >/dev/null 2>"$design2/stderr.log"
[[ -f "$design2/token-report.ndjson" ]] || fail 'missing token-report.ndjson'
[[ "$(grep -c 'codex_plan_draft' "$design2/token-report.ndjson")" = 1 ]] || fail 'expected one codex_plan_draft NDJSON row'
ledger_count=$(grep -h -c 'codex_plan_draft' "$design2"/larch-tokens-*.jsonl 2>/dev/null || true)
[[ "$ledger_count" = 1 ]] || fail 'expected one active ledger codex_plan_draft row'
if compgen -G "$impl2/larch-tokens-*.jsonl" >/dev/null; then
    fail 'design drafter wrote active ledger under IMPLEMENT_TMPDIR'
fi
[[ ! -e "$stale_ledger2" ]] || fail 'design drafter wrote active ledger to stale LARCH_TOKEN_LEDGER'
grep -Fq '"model":"gpt-5.5"' "$design2/token-report.ndjson" || fail 'missing model in NDJSON row'
grep -h -Fq '"model":"gpt-5.5"' "$design2"/larch-tokens-*.jsonl || fail 'missing model in active ledger row'
if grep -h -Fq 'stale-parent-session' "$design2"/larch-tokens-*.jsonl; then
    fail 'design drafter used stale LARCH_TOKEN_SESSION_ID'
fi
pass 'fresh Codex drafter sidecar exactly-once ingestion'

printf 'PASS: test-design-step2b-drafter.sh\n'
