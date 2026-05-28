#!/usr/bin/env bash
# Offline regression harness for lint-renderer-substitution-safety.sh.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd -P)"
LINT="$SCRIPT_DIR/lint-renderer-substitution-safety.sh"

fail() {
    printf '%s\n' "FAIL: $1" >&2
    exit 1
}

TMPROOT="$(mktemp -d "${TMPDIR:-/tmp}/larch-renderer-substitution-lint-test.XXXXXX")"
trap 'rm -rf "$TMPROOT"' EXIT

make_root() {
    local root="$1"
    mkdir -p "$root/scripts" "$root/skills/design/scripts"
}

assert_lint_ok() {
    local label="$1"
    local root="$2"
    local out="$TMPROOT/${label}.out"
    local err="$TMPROOT/${label}.err"
    bash "$LINT" --root "$root" >"$out" 2>"$err" || fail "$label: expected lint success: $(cat "$err")"
    [ ! -s "$err" ] || fail "$label: expected empty stderr"
}

assert_lint_fails_for() {
    local label="$1"
    local root="$2"
    local expected="$3"
    local out="$TMPROOT/${label}.out"
    local err="$TMPROOT/${label}.err"
    local rc

    set +e
    bash "$LINT" --root "$root" >"$out" 2>"$err"
    rc=$?
    set -e

    [ "$rc" -ne 0 ] || fail "$label: expected lint failure"
    grep -Fq -- "$expected" "$err" || fail "$label: stderr missing '$expected': $(cat "$err")"
}

# shellcheck disable=SC2016 # literal diagnostic fixture, assembled to avoid the linter pattern.
unsafe_fragment='unsafe ${VAR'
unsafe_fragment="${unsafe_fragment}//pat/"
# shellcheck disable=SC2016 # literal diagnostic fixture suffix.
unsafe_fragment="${unsafe_fragment}"'$rep} substitution'

safe_split="$TMPROOT/safe-split"
make_root "$safe_split"
cat > "$safe_split/scripts/render.sh" <<'EOF'
#!/usr/bin/env bash
set -euo pipefail
before="${body%%TOKEN*}"
after="${body##*TOKEN}"
body="${before}${replacement}${after}"
EOF
assert_lint_ok safe-split "$safe_split"

ansi_escape="$TMPROOT/ansi-escape"
make_root "$ansi_escape"
cat > "$ansi_escape/scripts/render.sh" <<'EOF'
#!/usr/bin/env bash
set -euo pipefail
out="${out//$'\n'/$'\n    '}"
EOF
assert_lint_ok ansi-escape "$ansi_escape"

unsafe_bare="$TMPROOT/unsafe-bare"
make_root "$unsafe_bare"
cat > "$unsafe_bare/scripts/render.sh" <<'EOF'
#!/usr/bin/env bash
set -euo pipefail
out="${out//TOKEN/$rep}"
EOF
assert_lint_fails_for unsafe-bare "$unsafe_bare" "scripts/render.sh:3: $unsafe_fragment"

unsafe_braced="$TMPROOT/unsafe-braced"
make_root "$unsafe_braced"
cat > "$unsafe_braced/scripts/render.sh" <<'EOF'
#!/usr/bin/env bash
set -euo pipefail
out="${out//TOKEN/${rep}}"
EOF
assert_lint_fails_for unsafe-braced "$unsafe_braced" "scripts/render.sh:3: $unsafe_fragment"

unsafe_array="$TMPROOT/unsafe-array"
make_root "$unsafe_array"
cat > "$unsafe_array/scripts/render.sh" <<'EOF'
#!/usr/bin/env bash
set -euo pipefail
out="${out//TOKEN/$arr[0]}"
EOF
assert_lint_fails_for unsafe-array "$unsafe_array" "scripts/render.sh:3: $unsafe_fragment"

waiver_same="$TMPROOT/waiver-same"
make_root "$waiver_same"
cat > "$waiver_same/scripts/render.sh" <<'EOF'
#!/usr/bin/env bash
set -euo pipefail
out="${out//TOKEN/$rep}" # lint-renderer-safe: ok trusted constant replacement
EOF
assert_lint_ok waiver-same "$waiver_same"

waiver_previous="$TMPROOT/waiver-previous"
make_root "$waiver_previous"
cat > "$waiver_previous/scripts/render.sh" <<'EOF'
#!/usr/bin/env bash
set -euo pipefail
# lint-renderer-safe: ok trusted constant replacement
out="${out//TOKEN/$rep}"
EOF
assert_lint_ok waiver-previous "$waiver_previous"

heredoc="$TMPROOT/heredoc"
make_root "$heredoc"
cat > "$heredoc/scripts/render.sh" <<'EOF'
#!/usr/bin/env bash
set -euo pipefail
cat > "$fixture" <<'INNER'
out="${out//TOKEN/$rep}"
INNER
EOF
assert_lint_ok heredoc "$heredoc"

pr3051_pre="$TMPROOT/pr3051-pre"
make_root "$pr3051_pre"
cat > "$pr3051_pre/skills/design/scripts/render-plan-review-prompt.sh" <<'EOF'
#!/usr/bin/env bash
set -euo pipefail
prompt_body="${prompt_body//__READABILITY_STYLE_BLOCK__/$readability_style}"
EOF
assert_lint_fails_for pr3051-pre "$pr3051_pre" "skills/design/scripts/render-plan-review-prompt.sh:3: $unsafe_fragment"

pr3051_post="$TMPROOT/pr3051-post"
make_root "$pr3051_post"
cat > "$pr3051_post/skills/design/scripts/render-plan-review-prompt.sh" <<'EOF'
#!/usr/bin/env bash
set -euo pipefail
before="${prompt_body%%__READABILITY_STYLE_BLOCK__*}"
after="${prompt_body##*__READABILITY_STYLE_BLOCK__}"
prompt_body="${before}${readability_style}${after}"
EOF
assert_lint_ok pr3051-post "$pr3051_post"

printf '%s\n' "test-lint-renderer-substitution-safety: ok"
