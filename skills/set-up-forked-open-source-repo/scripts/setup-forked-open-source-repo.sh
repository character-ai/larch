#!/usr/bin/env bash
set -Eeuo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=skills/set-up-forked-open-source-repo/scripts/lib-remotes.sh
source "$SCRIPT_DIR/lib-remotes.sh"

PLUGIN_ROOT="${CLAUDE_PLUGIN_ROOT:-}"
if [[ -z "$PLUGIN_ROOT" || ! -f "$PLUGIN_ROOT/scripts/lib-quiet.sh" ]]; then
  PLUGIN_ROOT="$(cd "$SCRIPT_DIR/../../.." && pwd -P)"
fi
# shellcheck source=scripts/lib-quiet.sh
source "$PLUGIN_ROOT/scripts/lib-quiet.sh"
larch_quiet_init
REDACTOR="$PLUGIN_ROOT/scripts/redact-secrets.sh"

UPSTREAM=""
FORK=""
MIRROR_CONFIRMED=false
INIT_SUBMODULES=false
SNAPSHOT_FILE=""
JOURNAL_FILE=""
REMOTE_PHASE_ACTIVE=false
LOCK_FILE=""
GH_HOST="github.com"
PREFLIGHT_REMOTE_CLASSIFICATION=""

usage() {
  local fd=2
  [[ "${LARCH_QUIET_PID:-}" == "$$" ]] && fd=4
  cat >&"$fd" <<'EOF'
Usage: setup-forked-open-source-repo.sh --upstream owner/repo --fork owner/repo [--mirror-confirmed] [--init-submodules]
EOF
}

redact_file() {
  local file outfd
  file="$1"
  outfd=2
  [[ "${LARCH_QUIET_PID:-}" == "$$" ]] && outfd=4
  if [[ -x "$REDACTOR" ]]; then
    "$REDACTOR" <"$file" >&"$outfd"
  else
    cat "$file" >&"$outfd"
  fi
}

die() {
  larch_err "ERROR: $*"
  exit 1
}

# phase_die: like `die` but goes through the ERR trap so `restore_remote_state`
# fires when an assertion fails inside any phase that requires ERR-trap-driven
# rollback (today: `phase_remotes` post-rewrite checks and `phase_verify`
# assertions). Using plain `die` from inside those phases would `exit 1`
# directly, bypassing the `trap remote_phase_error ERR` chain — leaving the
# repo with rewritten remotes and no rollback. The `false` line below is an
# explicit non-zero command (not an exit), so `set -Ee` triggers the trap;
# `restore_remote_state` inside `remote_phase_error` runs while
# `REMOTE_PHASE_ACTIVE=true` (cleared only on success at the tail of
# `phase_verify`). Pre-rewrite die calls (`phase_preflight`, `phase_github`)
# may use plain `die` because no remote mutation has happened yet.
phase_die() {
  larch_err "ERROR: $*"
  false
}

validate_owner_repo() {
  local value label
  value="$1"
  label="$2"
  if [[ ! "$value" =~ ^[A-Za-z0-9._-]+/[A-Za-z0-9._-]+$ ]]; then
    die "$label must have owner/repo shape"
  fi
}

https_url() {
  local host kind owner_repo env_name
  if [[ $# -ge 3 ]]; then
    host="$1"
    kind="$2"
    owner_repo="$3"
  else
    host="${GH_HOST:-github.com}"
    kind="$1"
    owner_repo="$2"
  fi
  env_name="LARCH_FORKED_REPO_URL_OVERRIDE_${kind}_HTTPS"
  # Test seam: the harness sets these env vars to point at local bare repos.
  # In production the override is a footgun — a leaked CI env var or stale
  # operator export would direct the destructive mirror push to the URL named
  # by the env var, independent of the verified `gh repo view` parent. Require
  # explicit `LARCH_FORKED_REPO_ALLOW_URL_OVERRIDE=1` so the override only
  # fires when the caller has opted in (the harness sets both).
  if [[ -n "${!env_name:-}" && "${LARCH_FORKED_REPO_ALLOW_URL_OVERRIDE:-}" == "1" ]]; then
    printf '%s\n' "${!env_name}"
  else
    printf 'https://%s/%s.git\n' "$host" "$owner_repo"
  fi
}

ssh_url() {
  local host kind owner_repo env_name
  if [[ $# -ge 3 ]]; then
    host="$1"
    kind="$2"
    owner_repo="$3"
  else
    host="${GH_HOST:-github.com}"
    kind="$1"
    owner_repo="$2"
  fi
  env_name="LARCH_FORKED_REPO_URL_OVERRIDE_${kind}_SSH"
  if [[ -n "${!env_name:-}" && "${LARCH_FORKED_REPO_ALLOW_URL_OVERRIDE:-}" == "1" ]]; then
    printf '%s\n' "${!env_name}"
  else
    printf 'git@%s:%s.git\n' "$host" "$owner_repo"
  fi
}

remote_main_sha() {
  local url
  url="$1"
  git ls-remote "$url" refs/heads/main | awk '$2 == "refs/heads/main" {print $1; found=1} END {exit !found}'
}

snapshot_remote_state() {
  SNAPSHOT_FILE="$(mktemp "${TMPDIR:-/tmp}/larch-forked-remote-snapshot.XXXXXX")"
  JOURNAL_FILE="$(mktemp "${TMPDIR:-/tmp}/larch-forked-remote-journal.XXXXXX")"
  git config --get-regexp '^(remote|branch)\.' >"$SNAPSHOT_FILE" 2>/dev/null || true
}

restore_remote_state() {
  local keys key line value
  if [[ "${LARCH_FORKED_REPO_INJECT_FAILURE:-}" == "rollback" ]]; then
    larch_err "RECOVERY_REPORT rollback_failed=true reason=injected-rollback-failure"
    larch_err "RECOVERY_REPORT snapshot=$SNAPSHOT_FILE journal=$JOURNAL_FILE"
    return 1
  fi

  keys="$(mktemp "${TMPDIR:-/tmp}/larch-forked-remote-keys.XXXXXX")"
  git config --name-only --get-regexp '^(remote|branch)\.' >"$keys" 2>/dev/null || true
  while IFS= read -r key; do
    [[ -z "$key" ]] && continue
    git config --unset-all "$key" 2>/dev/null || true
  done <"$keys"
  rm -f "$keys"

  while IFS= read -r line; do
    [[ -z "$line" ]] && continue
    key="${line%% *}"
    value="${line#* }"
    git config --add "$key" "$value"
  done <"$SNAPSHOT_FILE"
}

remote_phase_error() {
  local rc
  rc="${1:-$?}"
  if [[ "$REMOTE_PHASE_ACTIVE" == "true" ]]; then
    larch_err "ERROR: remote rewrite failed; attempting rollback"
    if ! restore_remote_state; then
      larch_err "RECOVERY_REPORT rollback_failed=true forward_exit=$rc"
    fi
  fi
  exit "$rc"
}

trap remote_phase_error ERR

trigger_remote_failure() {
  remote_phase_error 1
}

release_lock_on_exit() {
  release_clone_lock "$LOCK_FILE"
}

parse_args() {
  while [[ $# -gt 0 ]]; do
    case "$1" in
      --upstream)
        [[ $# -ge 2 ]] || die "--upstream requires a value"
        UPSTREAM="$2"
        shift 2
        ;;
      --fork)
        [[ $# -ge 2 ]] || die "--fork requires a value"
        FORK="$2"
        shift 2
        ;;
      --mirror-confirmed)
        MIRROR_CONFIRMED=true
        shift
        ;;
      --init-submodules)
        INIT_SUBMODULES=true
        shift
        ;;
      -h|--help)
        usage
        exit 0
        ;;
      *)
        usage
        die "unknown argument: $1"
        ;;
    esac
  done

  [[ -n "$UPSTREAM" ]] || die "missing --upstream"
  [[ -n "$FORK" ]] || die "missing --fork"
  validate_owner_repo "$UPSTREAM" "--upstream"
  validate_owner_repo "$FORK" "--fork"
}

phase_preflight() {
  local root current gh_err has_origin upstream_canonical fork_canonical origin_url_count
  root="$(git rev-parse --show-toplevel 2>/dev/null)" || die "not inside a git repository"
  cd "$root"

  # Hard runtime dependencies. `gh` and `git` are universally expected; `jq`
  # parses `gh repo view --json` output in phase_github. Fail loudly here with
  # an actionable message instead of letting a mid-run `command not found`
  # escape from inside a captured pipeline.
  command -v jq >/dev/null 2>&1 || die "jq is required but not installed; install jq (e.g., 'brew install jq' or your package manager) and rerun"

  LOCK_DIR="$(git rev-parse --git-common-dir)"
  LOCK_DIR="$(cd "$LOCK_DIR" && pwd)"
  LOCK_FILE="$LOCK_DIR/larch-fork-setup.lock"
  acquire_clone_lock "$LOCK_FILE"
  trap release_lock_on_exit EXIT

  if [[ -n "${LARCH_FORKED_REPO_PAUSE_AFTER_LOCK_S:-}" ]]; then
    sleep "$LARCH_FORKED_REPO_PAUSE_AFTER_LOCK_S"
  fi

  git show-ref --verify --quiet refs/heads/main || die "local refs/heads/main is absent"
  current="$(git symbolic-ref --short HEAD 2>/dev/null || true)"
  [[ "$current" == "main" ]] || die "current checkout must be main"

  has_origin=false
  if git remote | grep -Fxq origin; then
    has_origin=true
    # Pre-fetch URL classification inspects origin's stored fetch URL via
    # `lib-remotes.sh::normalize_github_url` before the first network fetch.
    # Multi-URL origins are refused before any `gh` invocation so a mixed or
    # ambiguous transport shape cannot reach the destructive phases.
    local origin_url tuple canonical_host canonical_slug
    origin_url_count="$(git config --get-all remote.origin.url | wc -l | tr -d '[:space:]')"
    if [[ "$origin_url_count" -gt 1 ]]; then
      die "multiple remote.origin.url entries; refuse early"
    fi
    origin_url="$(git config --get remote.origin.url 2>/dev/null || true)"
    tuple="$(normalize_github_url "$origin_url" 2>/dev/null || true)"
    if [[ -z "$tuple" ]]; then
      die "origin remote URL '$origin_url' is not a recognized GitHub-compatible URL; refusing to fetch"
    fi
    canonical_host="${tuple%%	*}"
    canonical_slug="${tuple#*	}"
    [[ -n "$canonical_slug" ]] || die "origin remote URL '$origin_url' is not a recognized GitHub-compatible URL; refusing to fetch"
    GH_HOST="$canonical_host"
  else
    GH_HOST="github.com"
  fi
  export GH_HOST

  gh_err="$(mktemp "${TMPDIR:-/tmp}/larch-forked-gh-auth.XXXXXX")"
  if ! gh auth status --hostname "$GH_HOST" >/dev/null 2>"$gh_err"; then
    larch_err "ERROR: gh auth status failed:"
    redact_file "$gh_err"
    rm -f "$gh_err"
    exit 1
  fi
  rm -f "$gh_err"

  assert_all_worktrees_clean || die "working tree is dirty; commit or stash before running"
  assert_all_worktrees_no_op_in_progress || die "git operation in progress; resolve it before running"

  if [[ "$has_origin" == "true" ]]; then
    upstream_canonical="$(printf '%s\n' "$UPSTREAM" | tr '[:upper:]' '[:lower:]')"
    fork_canonical="$(printf '%s\n' "$FORK" | tr '[:upper:]' '[:lower:]')"
    PREFLIGHT_REMOTE_CLASSIFICATION="$(classify_remote_state "$upstream_canonical" "$fork_canonical")"
    if [[ "${PREFLIGHT_REMOTE_CLASSIFICATION%% *}" == "state-ambiguous" ]]; then
      die "ambiguous remote state; refusing to call GitHub before remotes are resolved"
    fi
    git fetch origin
  fi

  if [[ "$has_origin" == "true" ]]; then
    git show-ref --verify --quiet refs/remotes/origin/main || die "origin/main is absent after fetch"
    if ! git merge-base --is-ancestor main origin/main; then
      if git merge-base --is-ancestor origin/main main; then
        die "local main is ahead of origin/main; push or reset manually before running"
      fi
      die "local main and origin/main have diverged"
    fi
  fi
}

phase_github() {
  local gh_out gh_err parent parent_lc upstream_lc upstream_https upstream_sha fork_https fork_ssh fork_sha tmp clone_dir sha_after_confirm fork_after_confirm pushed_sha post_sha
  gh_out="$(mktemp "${TMPDIR:-/tmp}/larch-forked-gh-view.XXXXXX")"
  gh_err="$(mktemp "${TMPDIR:-/tmp}/larch-forked-gh-view-err.XXXXXX")"

  if ! gh repo view "$FORK" --json nameWithOwner,parent,defaultBranchRef >"$gh_out" 2>"$gh_err"; then
    if grep -Eiq '404|not[_ -]?found|Could not resolve to a Repository' "$gh_err" "$gh_out"; then
      emit_breadcrumb --category=warn "Fork $FORK was not found. Create it at https://${GH_HOST:-github.com}/$UPSTREAM/fork, then rerun this skill."
      emit_kv SETUP_FORKED_REPO_RESULT "fork_missing"
      rm -f "$gh_out" "$gh_err"
      exit 0
    fi
    larch_err "ERROR: gh repo view failed:"
    redact_file "$gh_err"
    rm -f "$gh_out" "$gh_err"
    exit 1
  fi

  # Reject corrupt JSON up front so syntactically-invalid `gh` output yields
  # a clear "gh repo view returned invalid JSON" diagnostic rather than the
  # generic `fork parent mismatch ... got <none>` shape error below.
  # Using `jq -e 'type == "object"'` (rather than `jq -e .`) so a valid-JSON
  # but root-`null`/`false` payload — which `jq -e .` would treat as an exit-1
  # falsy value — does not get misclassified as a syntax error; the gate
  # accepts only an object root, which is the only shape `gh repo view --json`
  # ever returns.
  if ! jq -e 'type == "object"' "$gh_out" >/dev/null 2>"$gh_err"; then
    larch_err "ERROR: gh repo view returned invalid JSON:"
    redact_file "$gh_err"
    rm -f "$gh_out" "$gh_err"
    exit 1
  fi
  # Treat any malformed shape (non-object .parent.owner, non-string
  # .login/.name) as "no parent" so the operator gets the stable
  # `fork parent mismatch ... got <none>` message rather than a raw jq
  # index/type error. The pre-parse gate above already rejected JSON-syntax
  # failures, so this fallback is shape-only.
  parent="$(jq -r '
    if .parent == null then
      empty
    elif (.parent.nameWithOwner // "") != "" then
      .parent.nameWithOwner
    elif ((.parent.owner | type) == "object"
          and ((.parent.owner.login // null) | type) == "string"
          and ((.parent.name // null) | type) == "string"
          and (.parent.owner.login // "") != ""
          and (.parent.name // "") != "") then
      "\(.parent.owner.login)/\(.parent.name)"
    else
      empty
    end
  ' "$gh_out" 2>/dev/null || true)"
  rm -f "$gh_out" "$gh_err"
  # GitHub treats owner/repo names as case-insensitive; `gh repo view` returns
  # canonical-case parent fields while `--upstream` is operator input. Compare
  # lowercased so an operator passing `acme/project` against a canonical
  # `Acme/Project` parent does not spuriously fail this gate.
  parent_lc="$(printf '%s' "$parent" | tr '[:upper:]' '[:lower:]')"
  upstream_lc="$(printf '%s' "$UPSTREAM" | tr '[:upper:]' '[:lower:]')"
  if [[ "$parent_lc" != "$upstream_lc" ]]; then
    die "fork parent mismatch: expected $UPSTREAM, got ${parent:-<none>}"
  fi

  upstream_https="$(https_url UPSTREAM "$UPSTREAM")"
  fork_https="$(https_url FORK "$FORK")"
  fork_ssh="$(ssh_url FORK "$FORK")"

  upstream_sha="$(remote_main_sha "$upstream_https" 2>/dev/null || true)"
  [[ -n "$upstream_sha" ]] || die "upstream has no refs/heads/main"
  fork_sha="$(remote_main_sha "$fork_https" 2>/dev/null || true)"
  [[ -n "$fork_sha" ]] || die "fork has no refs/heads/main"

  if [[ "$upstream_sha" == "$fork_sha" ]]; then
    emit_kv SETUP_FORKED_REPO_RESULT "mirror_skipped_in_sync"
    return 0
  fi

  emit_breadcrumb --category=warn "Fork main differs from upstream main: upstream=$upstream_sha fork=$fork_sha. Confirming will overwrite fork branches/tags to match upstream."
  if [[ "$MIRROR_CONFIRMED" != "true" ]]; then
    if [[ ! -t 0 ]]; then
      die "mirror divergence detected; rerun with --mirror-confirmed"
    fi
    emit_breadcrumb --category=progress "Mirror-sync fork now? [y/N] "
    read -r reply
    case "$reply" in
      y|Y|yes|YES) ;;
      *) die "mirror sync declined" ;;
    esac
  fi

  sha_after_confirm="$(remote_main_sha "$upstream_https" 2>/dev/null || true)"
  fork_after_confirm="$(remote_main_sha "$fork_https" 2>/dev/null || true)"
  if [[ "$sha_after_confirm" != "$upstream_sha" || "$fork_after_confirm" != "$fork_sha" ]]; then
    die "remote moved during confirmation; rerun"
  fi

  assert_all_worktrees_clean || die "working tree became dirty before mirror push"
  assert_all_worktrees_no_op_in_progress || die "git operation started before mirror push"

  tmp="$(mktemp -d "${TMPDIR:-/tmp}/larch-forked-mirror.XXXXXX")"
  clone_dir="$tmp/upstream.git"
  git clone --mirror "$upstream_https" "$clone_dir"
  # Compare the post-push fork SHA to what we actually pushed (the mirror clone's
  # refs/heads/main), not to upstream_sha captured at line 239. Upstream main can
  # advance between the re-probe and the clone — the push then succeeds against
  # the newer SHA, and asserting against the stale pre-confirm value would
  # spuriously fail an already-completed destructive sync.
  pushed_sha="$(git -C "$clone_dir" rev-parse refs/heads/main 2>/dev/null || true)"
  [[ -n "$pushed_sha" ]] || { rm -rf "$tmp"; die "mirror clone has no refs/heads/main"; }
  git -C "$clone_dir" push --prune "$fork_ssh" '+refs/heads/*:refs/heads/*' '+refs/tags/*:refs/tags/*'
  post_sha="$(remote_main_sha "$fork_https" 2>/dev/null || true)"
  rm -rf "$tmp"
  [[ "$post_sha" == "$pushed_sha" ]] || die "fork refs/heads/main did not match what was pushed (expected $pushed_sha, got ${post_sha:-<none>})"
  emit_kv SETUP_FORKED_REPO_RESULT "mirror_synced"
}

phase_remotes() {
  local upstream_canonical fork_canonical fork_ssh classification state named_fork
  upstream_canonical="$(printf '%s\n' "$UPSTREAM" | tr '[:upper:]' '[:lower:]')"
  fork_canonical="$(printf '%s\n' "$FORK" | tr '[:upper:]' '[:lower:]')"
  fork_ssh="$(ssh_url FORK "$FORK")"

  snapshot_remote_state
  REMOTE_PHASE_ACTIVE=true
  if [[ -n "$PREFLIGHT_REMOTE_CLASSIFICATION" ]]; then
    classification="$PREFLIGHT_REMOTE_CLASSIFICATION"
  else
    classification="$(classify_remote_state "$upstream_canonical" "$fork_canonical")"
  fi
  state="${classification%% *}"
  named_fork="${classification#* }"

  case "$state" in
    state-already-configured)
      ;;
    state-origin-upstream-only)
      journal_record "$JOURNAL_FILE" RENAME origin upstream
      git remote rename origin upstream
      case "${LARCH_FORKED_REPO_INJECT_FAILURE:-}" in
        after-rename-origin-upstream) trigger_remote_failure ;;
      esac
      journal_record "$JOURNAL_FILE" ADD origin "$fork_ssh"
      git remote add origin "$fork_ssh"
      ;;
    state-origin-upstream-named-fork)
      journal_record "$JOURNAL_FILE" RENAME origin upstream
      git remote rename origin upstream
      case "${LARCH_FORKED_REPO_INJECT_FAILURE:-}" in
        after-rename-origin-upstream) trigger_remote_failure ;;
      esac
      journal_record "$JOURNAL_FILE" RENAME "$named_fork" origin
      git remote rename "$named_fork" origin
      ;;
    *)
      local ufd=2
      [[ "${LARCH_QUIET_PID:-}" == "$$" ]] && ufd=4
      printf 'ERROR: ambiguous remote state; refusing to mutate.\n' >&"$ufd"
      git remote -v >&"$ufd" || true
      git config --get-regexp '^remote\.' >&"$ufd" || true
      exit 1
      ;;
  esac

  git config --unset-all remote.upstream.pushurl 2>/dev/null || true
  git config --add remote.upstream.pushurl 'larch-disabled://upstream-push-disabled'

  # Clear any pushurl that may have been carried over from a renamed remote.
  # `state-origin-upstream-named-fork`'s `git remote rename <named_fork> origin`
  # preserves `remote.<named_fork>.pushurl` as `remote.origin.pushurl`; without
  # this unset, a stale or hostile pushurl could redirect future pushes to the
  # wrong repository while origin's fetch URL still correctly points at the
  # declared fork. Unsetting forces git to fall back to `remote.origin.url`
  # for both fetch and push.
  git config --unset-all remote.origin.pushurl 2>/dev/null || true

  case "${LARCH_FORKED_REPO_INJECT_FAILURE:-}" in
    fetch|rollback) trigger_remote_failure ;;
  esac
  git fetch origin --prune --tags
  git branch --set-upstream-to=origin/main main

  assert_all_worktrees_clean || phase_die "working tree became dirty before fast-forward"
  if ! git merge-base --is-ancestor origin/main main; then
    git merge --ff-only origin/main
  fi

  # Keep REMOTE_PHASE_ACTIVE=true until phase_verify succeeds. Any failure in
  # phase_submodules or phase_verify happens AFTER the remote rewrites, so the
  # ERR trap must still call restore_remote_state to roll back. Without this
  # guarding through verify, a partial submodule update or a failed verify
  # assertion would leave a half-configured clone with no automatic recovery.
}

phase_submodules() {
  if [[ "$INIT_SUBMODULES" == "true" && -f .gitmodules ]]; then
    git submodule update --init --recursive
  fi
}

phase_verify() {
  # Late-phase failure injection (harness-only). Triggers a non-zero command
  # AFTER remote rewrites have completed, so the harness can prove that
  # REMOTE_PHASE_ACTIVE is still true here and the ERR trap fires
  # `restore_remote_state` on a verify-time failure (FINDING_R3_6 regression).
  case "${LARCH_FORKED_REPO_INJECT_FAILURE:-}" in
    in-verify) trigger_remote_failure ;;
  esac
  emit_breadcrumb --category=progress ""
  emit_breadcrumb --category=progress "Final remotes:"
  git remote -v
  emit_breadcrumb --category=progress ""
  emit_breadcrumb --category=progress "Disabled upstream push sentinel:"
  git config --get-regexp '^remote\.upstream\.pushurl$'
  [[ "$(git config --get branch.main.remote)" == "origin" ]] || phase_die "branch.main.remote is not origin"
  [[ "$(git config --get branch.main.merge)" == "refs/heads/main" ]] || phase_die "branch.main.merge is not refs/heads/main"
  emit_breadcrumb --category=progress ""
  emit_breadcrumb --category=progress "Fork workflow: branch off origin/main, push topic branches to origin, and open PRs from $FORK:<branch> to $UPSTREAM:main."
  emit_kv SETUP_FORKED_REPO_RESULT "ok"
  # Now that all assertions and the success marker have been emitted, drop the
  # rollback flag so subsequent (non-existent) phases or post-main shutdown do
  # not accidentally re-trigger a restore on benign exit signals.
  REMOTE_PHASE_ACTIVE=false
}

main() {
  parse_args "$@"
  phase_preflight
  phase_github
  phase_remotes
  phase_submodules
  phase_verify
}

main "$@"
