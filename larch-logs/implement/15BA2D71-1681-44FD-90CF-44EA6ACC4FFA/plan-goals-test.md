## Goal
Wire append-tool-failure.sh into all 6 vendor launchers and add verdict/retry-count flags for auth-failure classification

## Implementation Plan
## Implementation Plan

### Goal
Wire `append-tool-failure.sh` into all 6 unwired per-vendor launchers on terminal failure, and add `--verdict`/`--retry-count` flags to surface auth-failure classification in execution-issues logs.

### Part 1 — Extend `lib-external-launcher-common.sh`

Add `external_auth_verdict(tool, sidecar1, [sidecar2])` after `external_is_auth_failure`:
- Returns `auth` when either sidecar matches auth-failure patterns
- Returns `non-auth` when sidecars are readable but no auth pattern matches
- Returns `unclassified` when no sidecar is readable
- Two-file form supports cursor launchers that check both SIDECAR_LOG and .diag

### Part 2 — Extend `scripts/append-tool-failure.sh`

Add optional `--verdict` (string) and `--retry-count` (non-negative integer) flags.
Update header template line to thread them in:
```
- **Step <site> — <tool> failed (exit <N>[— <verdict>][— retries=<N>])**:
```
Backward-compatible: empty/absent flags produce no suffix.

### Part 3 — Add `append_launch_failure` to each launcher

Pattern (based on dispatch-panel.sh:70-81 + collect-findings.sh:51-62):
```bash
append_launch_failure() {
    local site="$1" tool_label="$2" rc="$3" diag_file="$4" verdict="${5:-}" retry_count="${6:-}"
    [[ -x "$PLUGIN_ROOT/scripts/append-tool-failure.sh" ]] || return 0
    [[ -n "${IMPLEMENT_TMPDIR:-}" ]] || return 0
    local _args=()
    [[ -n "$verdict" ]] && _args+=(--verdict "$verdict")
    [[ -n "$retry_count" ]] && _args+=(--retry-count "$retry_count")
    "$PLUGIN_ROOT/scripts/append-tool-failure.sh" \
        --log "${IMPLEMENT_TMPDIR}/execution-issues.md" \
        --site "$site" --tool "$tool_label" --exit-code "$rc" \
        --category "Tool Failures" --output-file "$diag_file" \
        "${_args[@]}" --redact >/dev/null 2>&1 || true
}
```

After the auth-retry loop on each launcher, when LAUNCHER_EXIT != 0:
```bash
if (( LAUNCHER_EXIT != 0 )); then
    _AUTH_VERDICT=$(external_auth_verdict "<tool>" "$SIDECAR_LOG" [extra_sidecar])
    [[ "$_AUTH_VERDICT" == "auth" ]] && _VERDICT="auth-retries-exhausted" || _VERDICT="$_AUTH_VERDICT"
    append_launch_failure "Step 2" "<tool>-implement" "$LAUNCHER_EXIT" "$SIDECAR_LOG" "$_VERDICT" "$AUTH_ATTEMPT"
fi
```

### Files to modify

1. `scripts/lib-external-launcher-common.sh` — add `external_auth_verdict` (~9 lines)
2. `scripts/lib-external-launcher-common.md` — document new function (~2 lines)
3. `scripts/append-tool-failure.sh` — add --verdict + --retry-count flags + update header (~25 lines total)
4. `scripts/append-tool-failure.md` — document new flags (~12 lines)
5. `scripts/launch-codex-implement.sh` — add helper + invoke (~18 lines)
6. `scripts/launch-codex-ci.sh` — add helper + invoke (~18 lines, category: Tool Failures)
7. `scripts/launch-cursor-implement.sh` — add helper + invoke with both sidecars (~19 lines)
8. `scripts/launch-cursor-ci.sh` — add helper + invoke (~18 lines, uses .diag)
9. `scripts/launch-gemini-implement.sh` — add helper + invoke (~18 lines)
10. `scripts/launch-review.sh` — add helper (category: External Reviewer Issues) + invoke at Codex path + Cursor path (~28 lines)
11. `scripts/test-append-tool-failure.sh` — add 4 verdict/retry-count cases (~30 lines)

### Verification
- `/relevant-checks` must be clean
- `scripts/test-append-tool-failure.sh` new cases must pass

## Test plan
(no test plan section in plan-file)
