#!/usr/bin/env bash
# Regression test for scripts/external-tool-registry.sh.

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
REGISTRY="$REPO_ROOT/scripts/external-tool-registry.sh"

PASS=0
FAIL=0
FAIL_DETAILS=()

fail() {
    FAIL=$((FAIL + 1))
    FAIL_DETAILS+=("$1")
}

pass() {
    PASS=$((PASS + 1))
}

assert_equals() {
    local label="$1"
    local expected="$2"
    local actual="$3"
    if [[ "$actual" == "$expected" ]]; then
        pass
    else
        fail "$label: expected '$expected', got '$actual'"
    fi
}

assert_success() {
    local label="$1"
    shift
    if "$@"; then
        pass
    else
        fail "$label: command failed"
    fi
}

assert_failure() {
    local label="$1"
    shift
    if "$@"; then
        fail "$label: command unexpectedly succeeded"
    else
        pass
    fi
}

assert_contains() {
    local label="$1"
    local needle="$2"
    local haystack="$3"
    if [[ "$haystack" == *"$needle"* ]]; then
        pass
    else
        fail "$label: expected output to contain '$needle'; got '$haystack'"
    fi
}

# 1. Source succeeds.
# shellcheck source=scripts/external-tool-registry.sh
source "$REGISTRY"
pass

# 2-3. Ordered arrays.
assert_equals "external tool order" "codex cursor" "${LARCH_EXTERNAL_TOOLS[*]}"
assert_equals "implementer coder order" "claude codex cursor" "${LARCH_IMPLEMENTER_CODERS[*]}"

# 4. External tool positives.
for tool in codex cursor; do
    assert_success "larch_is_external_tool $tool" larch_is_external_tool "$tool"
done

# 5-6. External tool negatives.
assert_failure "larch_is_external_tool claude" larch_is_external_tool claude
assert_failure "larch_is_external_tool empty" larch_is_external_tool ""
assert_failure "larch_is_external_tool unknown" larch_is_external_tool unknown

# 7-8. Implementer coder predicates.
for coder in claude codex cursor; do
    assert_success "larch_is_implementer_coder $coder" larch_is_implementer_coder "$coder"
done
assert_failure "larch_is_implementer_coder unknown" larch_is_implementer_coder unknown

# 9-10. Brace formatters.
assert_equals "external tools braced" "{codex,cursor}" "$(larch_external_tools_braced)"
assert_equals "implementer coders braced" "{claude,codex,cursor}" "$(larch_implementer_coders_braced)"

# 11. Double source is idempotent and keeps sentinel set.
if bash -c 'source "$1"; source "$1"; [[ "${LARCH_EXTERNAL_TOOL_REGISTRY_LOADED:-}" == "1" ]]' bash "$REGISTRY"; then
    pass
else
    fail "double source should be idempotent"
fi

# 12. Source preserves strict shell options and predicates can be used safely in if ! context.
if bash -c 'set -euo pipefail; source "$1"; if ! larch_is_external_tool unknown; then :; else exit 1; fi; [[ "$-" == *e* ]] && [[ "$-" == *u* ]] && set -o | grep -q "^pipefail[[:space:]]*on"' bash "$REGISTRY"; then
    pass
else
    fail "source should preserve set -euo pipefail and not trip predicates in if context"
fi

# 13. Registry is sourced-only.
if head -n 1 "$REGISTRY" | grep -qv '^#!' && [[ ! -x "$REGISTRY" ]]; then
    pass
else
    fail "registry should have no shebang and should not be executable"
fi

# 14. Registry-driven consumers handle every registered external tool and step2 resolves paths from a nested cwd.
reviewer_err="$(mktemp /tmp/larch-registry-reviewers-err-XXXXXX)"
reviewer_output=""
if reviewer_output=$("$REPO_ROOT/scripts/check-reviewers.sh" 2>"$reviewer_err"); then
    for tool in codex cursor; do
        upper=$(printf '%s' "$tool" | tr '[:lower:]' '[:upper:]')
        assert_contains "check-reviewers availability key for $tool" "${upper}_AVAILABLE=" "$reviewer_output"
    done
    if grep -q 'internal error: unsupported reviewer tool' "$reviewer_err"; then
        fail "check-reviewers emitted unsupported-tool internal error"
    else
        pass
    fi
else
    fail "check-reviewers should not fail: $(cat "$reviewer_err")"
fi
rm -f "$reviewer_err"

# 14b. agent-model-args.sh handles every registered external tool with non-empty
# stdout (catches drift where the registry grows but the per-tool model `case`
# arm is forgotten — without coverage the script would silently exit 0 with
# empty stdout and callers would launch probes with no --model).
agent_err="$(mktemp /tmp/larch-registry-agent-model-err-XXXXXX)"
for tool in "${LARCH_EXTERNAL_TOOLS[@]}"; do
    if model_out=$("$REPO_ROOT/scripts/agent-model-args.sh" --tool "$tool" 2>"$agent_err"); then
        if [[ -n "$model_out" ]]; then
            pass
        else
            fail "agent-model-args.sh --tool $tool returned empty stdout"
        fi
    else
        fail "agent-model-args.sh --tool $tool exited non-zero: $(cat "$agent_err")"
    fi
    if grep -q 'internal error: unsupported reviewer tool' "$agent_err"; then
        fail "agent-model-args.sh --tool $tool emitted unsupported-tool internal error"
    fi
done
rm -f "$agent_err"

step_tmp="$(mktemp -d /tmp/larch-registry-step2-XXXXXX)"
step_plan="$step_tmp/plan.txt"
step_feature="$step_tmp/feature.txt"
printf 'plan\n' >"$step_plan"
printf 'feature\n' >"$step_feature"
step_output="$(cd /tmp && "$REPO_ROOT/skills/implement/scripts/step2-implement.sh" \
    --coder claude \
    --tmpdir "$step_tmp" \
    --plan-file "$step_plan" \
    --feature-file "$step_feature" \
    --auto-mode false)"
assert_contains "step2 nested-cwd claude fallback" "STATUS=claude_fallback" "$step_output"
rm -rf "$step_tmp"

# 15-16. Source-time stdout/stderr are empty, including double-source.
tmpdir="$(mktemp -d /tmp/larch-registry-source-XXXXXX)"
trap 'rm -rf "$tmpdir"' EXIT
if bash -c 'source "$1"' bash "$REGISTRY" >"$tmpdir/stdout1" 2>"$tmpdir/stderr1" \
    && [[ ! -s "$tmpdir/stdout1" ]] \
    && [[ ! -s "$tmpdir/stderr1" ]]; then
    pass
else
    fail "single source should emit no stdout/stderr"
fi

if bash -c 'source "$1"; source "$1"' bash "$REGISTRY" >"$tmpdir/stdout2" 2>"$tmpdir/stderr2" \
    && [[ ! -s "$tmpdir/stdout2" ]] \
    && [[ ! -s "$tmpdir/stderr2" ]]; then
    pass
else
    fail "double source should emit no stdout/stderr"
fi

if [[ "$FAIL" -ne 0 ]]; then
    printf 'FAIL: test-external-tool-registry.sh - %s failed, %s passed\n' "$FAIL" "$PASS" >&2
    printf '  %s\n' "${FAIL_DETAILS[@]}" >&2
    exit 1
fi

printf 'PASS: test-external-tool-registry.sh - %s assertions passed\n' "$PASS"
