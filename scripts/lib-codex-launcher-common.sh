# shellcheck shell=bash
# Sourced-only library: no shebang and no `set -e`; callers own exit semantics.
if [[ -n "${LARCH_LIB_CODEX_LAUNCHER_COMMON_LOADED:-}" ]]; then
    return 0
fi

# Canonical bodies live in lib-external-launcher-common.sh; the wrappers
# below preserve the codex_launcher_* names so existing call sites in
# launch-review.sh --tool codex stay untouched.
# shellcheck source=scripts/lib-external-launcher-common.sh
# shellcheck disable=SC1091
source "${BASH_SOURCE[0]%/*}/lib-external-launcher-common.sh"

# Codex stdin contract: every background Codex spawn is launched with stdin
# redirected from /dev/null in scripts/run-external-agent.sh at the actual
# spawn site (default, --capture-stdout, and --capture-stdout-only branches).
# Codex keeps stdin open for interactive input; inheriting the parent stdin
# lets parent-shell EOF surface as "write_stdin failed: stdin is closed for
# this session" in long background runs (issues #2962 / #2973).

codex_launcher_promote_inner_done() {
    external_launcher_promote_inner_done "$@"
}

codex_launcher_append_outer_meta() {
    external_launcher_append_outer_meta "$@"
}

codex_launcher_record_usage_from_events() {
    external_launcher_record_usage_from_events "$@"
}

LARCH_LIB_CODEX_LAUNCHER_COMMON_LOADED=1
