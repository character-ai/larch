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

codex_launcher_promote_inner_done() {
    external_launcher_promote_inner_done "$@"
}

codex_launcher_append_outer_meta() {
    external_launcher_append_outer_meta "$@"
}

LARCH_LIB_CODEX_LAUNCHER_COMMON_LOADED=1
