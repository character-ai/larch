#!/usr/bin/env bash
# Regression harness for oos-serialize.sh.

set -euo pipefail

DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)
TMP=$(mktemp -d "${TMPDIR:-/tmp}/test-oos-serialize.XXXXXX")
trap 'rm -rf "$TMP"' EXIT

cat > "$TMP/findings.md" <<'EOF'
### FINDING_1: [OUT_OF_SCOPE] Public cleanup
- **Concern**: Cleanup.
### FINDING_2: [OUT_OF_SCOPE] Secret issue
- **Concern**: focus-area=security secret.
### FINDING_3: [OUT_OF_SCOPE] Rejected cleanup
- **Concern**: Do not file.
Vote tally: YES=0 NO=3 EXON=0 JUDGE_ERROR=0 Result=rejected
### FINDING_4: [OUT_OF_SCOPE] Result accepted cleanup
- **Concern**: File only accepted result.
Vote tally: YES=3 NO=0 EXON=0 JUDGE_ERROR=0 Result=accepted
### FINDING_5: [OUT_OF_SCOPE] ordinary security cleanup
- **Concern**: Public non-sensitive title.
### FINDING_6: [OUT_OF_SCOPE] `[security]` tagged title
- **Concern**: Header tag must hold.
### FINDING_7: [OUT_OF_SCOPE] Backtick value
- **focus-area**: `security-hardening`
### FINDING_8: [OUT_OF_SCOPE] Cited security heading
- **Concern**: This mentions a later example heading.
### Example [security] policy
### FINDING_9: [OUT_OF_SCOPE] Prose result token
- **Concern**: Mentions Result=rejected in prose, but has no tally footer.
EOF

out=$("$DIR/oos-serialize.sh" --findings-file "$TMP/findings.md" --output-file "$TMP/oos.md")
grep -Fq 'OOS_ACCEPTED=5' <<< "$out"
grep -Fq 'OOS_HELD_SECURITY=3' <<< "$out"
grep -Fq 'Public cleanup' "$TMP/oos.md"
grep -Fq 'Result accepted cleanup' "$TMP/oos.md"
grep -Fq 'ordinary security cleanup' "$TMP/oos.md"
grep -Fq 'Cited security heading' "$TMP/oos.md"
grep -Fq 'Prose result token' "$TMP/oos.md"
grep -Eq '^### OOS_1:' "$TMP/oos.md"
grep -Eq '^### OOS_2:' "$TMP/oos.md"
grep -Eq '^### OOS_3:' "$TMP/oos.md"
grep -Eq '^### OOS_4:' "$TMP/oos.md"
grep -Eq '^### OOS_5:' "$TMP/oos.md"
if grep -Fq 'Secret issue' "$TMP/oos.md"; then
    echo "FAIL: security OOS item leaked" >&2
    exit 1
fi
if grep -Fq 'Rejected cleanup' "$TMP/oos.md"; then
    echo "FAIL: rejected OOS item leaked" >&2
    exit 1
fi
if grep -Fq 'tagged title' "$TMP/oos.md" || grep -Fq 'Backtick value' "$TMP/oos.md"; then
    echo "FAIL: backtick-wrapped security tag leaked" >&2
    exit 1
fi

mkdir -p "$TMP/fail-python-bin"
cat > "$TMP/fail-python-bin/python3" <<'EOF'
#!/usr/bin/env bash
exit 1
EOF
chmod +x "$TMP/fail-python-bin/python3"
set +e
PATH="$TMP/fail-python-bin:$PATH" "$DIR/oos-serialize.sh" --findings-file "$TMP/findings.md" --output-file "$TMP/fail.md" >/dev/null 2>"$TMP/fail.err"
rc=$?
set -e
if [[ "$rc" -ne 2 ]]; then
    echo "FAIL: classifier failure should exit 2, got $rc" >&2
    exit 1
fi
grep -Fq 'python3 security classifier smoke test failed' "$TMP/fail.err"
if [[ -s "$TMP/fail.md" ]]; then
    echo "FAIL: classifier failure should not serialize a partial public sink" >&2
    exit 1
fi

echo "All assertions passed."
