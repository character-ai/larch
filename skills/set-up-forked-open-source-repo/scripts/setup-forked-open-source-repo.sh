#!/usr/bin/env bash
set -Eeuo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=skills/set-up-forked-open-source-repo/scripts/lib-remotes.sh
source "$SCRIPT_DIR/lib-remotes.sh"

PLUGIN_ROOT="${CLAUDE_PLUGIN_ROOT:-$(cd "$SCRIPT_DIR/../../.." && pwd)}"
REDACTOR="$PLUGIN_ROOT/scripts/redact-secrets.sh"

UPSTREAM=""
FORK=""
MIRROR_CONFIRMED=false
INIT_SUBMODULES=false
SNAPSHOT_FILE=""
JOURNAL_FILE=""
REMOTE_PHASE_ACTIVE=false

usage() {
  cat >&2 <<'EOF'
Usage: setup-forked-open-source-repo.sh --upstream owner/repo --fork owner/repo [--mirror-confirmed] [--init-submodules]
EOF
}

redact_file() {
  local file
  file="$1"
  if [[ -x "$REDACTOR" ]]; then
    "$REDACTOR" <"$file"
  else
    cat "$file"
  fi
}

die() {
  printf 'ERROR: %s\n' "$*" >&2
  exit 1
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
  local kind owner_repo env_name
  kind="$1"
  owner_repo="$2"
  env_name="LARCH_FORKED_REPO_URL_OVERRIDE_${kind}_HTTPS"
  if [[ -n "${!env_name:-}" ]]; then
    printf '%s\n' "${!env_name}"
  else
    printf 'https://github.com/%s.git\n' "$owner_repo"
  fi
}

ssh_url() {
  local kind owner_repo env_name
  kind="$1"
  owner_repo="$2"
  env_name="LARCH_FORKED_REPO_URL_OVERRIDE_${kind}_SSH"
  if [[ -n "${!env_name:-}" ]]; then
    printf '%s\n' "${!env_name}"
  else
    printf 'git@github.com:%s.git\n' "$owner_repo"
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
    printf 'RECOVERY_REPORT rollback_failed=true reason=injected-rollback-failure\n' >&2
    printf 'RECOVERY_REPORT snapshot=%s journal=%s\n' "$SNAPSHOT_FILE" "$JOURNAL_FILE" >&2
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
    printf 'ERROR: remote rewrite failed; attempting rollback\n' >&2
    if ! restore_remote_state; then
      printf 'RECOVERY_REPORT rollback_failed=true forward_exit=%s\n' "$rc" >&2
    fi
  fi
  exit "$rc"
}

trap remote_phase_error ERR

trigger_remote_failure() {
  remote_phase_error 1
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
  local root current git_dir gh_err has_origin
  root="$(git rev-parse --show-toplevel 2>/dev/null)" || die "not inside a git repository"
  cd "$root"

  if [[ -n "$(git status --porcelain)" ]]; then
    die "working tree is dirty; commit or stash before running"
  fi

  git_dir="$(git rev-parse --git-dir)"
  for path in MERGE_HEAD REBASE_HEAD rebase-apply rebase-merge CHERRY_PICK_HEAD REVERT_HEAD; do
    if [[ -e "$git_dir/$path" ]]; then
      die "git operation in progress ($path); resolve it before running"
    fi
  done

  git show-ref --verify --quiet refs/heads/main || die "local refs/heads/main is absent"
  current="$(git symbolic-ref --short HEAD 2>/dev/null || true)"
  [[ "$current" == "main" ]] || die "current checkout must be main"

  gh_err="$(mktemp "${TMPDIR:-/tmp}/larch-forked-gh-auth.XXXXXX")"
  if ! gh auth status >/dev/null 2>"$gh_err"; then
    printf 'ERROR: gh auth status failed:\n' >&2
    redact_file "$gh_err" >&2
    rm -f "$gh_err"
    exit 1
  fi
  rm -f "$gh_err"

  has_origin=false
  if git remote | grep -Fxq origin; then
    has_origin=true
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
  local gh_out gh_err parent upstream_https upstream_sha fork_https fork_ssh fork_sha tmp clone_dir sha_after_confirm fork_after_confirm post_sha
  gh_out="$(mktemp "${TMPDIR:-/tmp}/larch-forked-gh-view.XXXXXX")"
  gh_err="$(mktemp "${TMPDIR:-/tmp}/larch-forked-gh-view-err.XXXXXX")"

  if ! gh repo view "$FORK" --json nameWithOwner,parent,defaultBranchRef >"$gh_out" 2>"$gh_err"; then
    if grep -Eiq '404|not[_ -]?found|Could not resolve to a Repository' "$gh_err" "$gh_out"; then
      printf 'Fork %s was not found. Create it at https://github.com/%s/fork, then rerun this skill.\n' "$FORK" "$UPSTREAM"
      printf 'SETUP_FORKED_REPO_RESULT=fork_missing\n'
      rm -f "$gh_out" "$gh_err"
      exit 0
    fi
    printf 'ERROR: gh repo view failed:\n' >&2
    redact_file "$gh_err" >&2
    rm -f "$gh_out" "$gh_err"
    exit 1
  fi

  parent="$(jq -r '.parent.nameWithOwner // empty' "$gh_out")"
  rm -f "$gh_out" "$gh_err"
  if [[ "$parent" != "$UPSTREAM" ]]; then
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
    printf 'SETUP_FORKED_REPO_RESULT=mirror_skipped_in_sync\n'
    return 0
  fi

  printf 'Fork main differs from upstream main: upstream=%s fork=%s. Confirming will overwrite fork branches/tags to match upstream.\n' "$upstream_sha" "$fork_sha"
  if [[ "$MIRROR_CONFIRMED" != "true" ]]; then
    if [[ ! -t 0 ]]; then
      die "mirror divergence detected; rerun with --mirror-confirmed"
    fi
    printf 'Mirror-sync fork now? [y/N] '
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

  tmp="$(mktemp -d "${TMPDIR:-/tmp}/larch-forked-mirror.XXXXXX")"
  clone_dir="$tmp/upstream.git"
  git clone --mirror "$upstream_https" "$clone_dir"
  git -C "$clone_dir" push --prune "$fork_ssh" '+refs/heads/*:refs/heads/*' '+refs/tags/*:refs/tags/*'
  post_sha="$(remote_main_sha "$fork_https" 2>/dev/null || true)"
  rm -rf "$tmp"
  [[ "$post_sha" == "$upstream_sha" ]] || die "fork refs/heads/main did not match upstream after mirror sync"
  printf 'SETUP_FORKED_REPO_RESULT=mirror_synced\n'
}

phase_remotes() {
  local upstream_canonical fork_canonical fork_ssh classification state named_fork
  upstream_canonical="$(printf '%s\n' "$UPSTREAM" | tr '[:upper:]' '[:lower:]')"
  fork_canonical="$(printf '%s\n' "$FORK" | tr '[:upper:]' '[:lower:]')"
  fork_ssh="$(ssh_url FORK "$FORK")"

  snapshot_remote_state
  REMOTE_PHASE_ACTIVE=true
  classification="$(classify_remote_state "$upstream_canonical" "$fork_canonical")"
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
      printf 'ERROR: ambiguous remote state; refusing to mutate.\n' >&2
      git remote -v >&2 || true
      git config --get-regexp '^remote\.' >&2 || true
      exit 1
      ;;
  esac

  git config --unset-all remote.upstream.pushurl 2>/dev/null || true
  git config --add remote.upstream.pushurl 'larch-disabled://upstream-push-disabled'

  case "${LARCH_FORKED_REPO_INJECT_FAILURE:-}" in
    fetch|rollback) trigger_remote_failure ;;
  esac
  git fetch origin --prune --tags
  git branch --set-upstream-to=origin/main main

  if [[ -n "$(git status --porcelain)" ]]; then
    die "working tree became dirty before fast-forward"
  fi
  if ! git merge-base --is-ancestor origin/main main; then
    git merge --ff-only origin/main
  fi

  REMOTE_PHASE_ACTIVE=false
}

phase_submodules() {
  if [[ "$INIT_SUBMODULES" == "true" && -f .gitmodules ]]; then
    git submodule update --init --recursive
  fi
}

phase_verify() {
  printf '\nFinal remotes:\n'
  git remote -v
  printf '\nDisabled upstream push sentinel:\n'
  git config --get-regexp '^remote\.upstream\.pushurl$'
  [[ "$(git config --get branch.main.remote)" == "origin" ]] || die "branch.main.remote is not origin"
  [[ "$(git config --get branch.main.merge)" == "refs/heads/main" ]] || die "branch.main.merge is not refs/heads/main"
  printf '\nFork workflow: branch off origin/main, push topic branches to origin, and open PRs from %s:<branch> to %s:main.\n' "$FORK" "$UPSTREAM"
  printf 'SETUP_FORKED_REPO_RESULT=ok\n'
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
