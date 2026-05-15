# shellcheck shell=bash
# Sourced by setup-forked-open-source-repo.sh.

_remotes_user_err() {
  local msg=$1
  if command -v larch_err >/dev/null 2>&1; then
    larch_err "$msg"
  else
    printf '%s\n' "$msg" >&2
  fi
}

normalize_github_url() {
  local url host owner repo rest tuple
  url="${1:-}"
  url="${url%/}"
  url="${url%.git}"

  case "$url" in
    git@*:*)
      host="${url#git@}"
      host="${host%%:*}"
      rest="${url#git@"$host":}"
      ;;
    ssh://git@*/*)
      tuple="${url#ssh://git@}"
      host="${tuple%%/*}"
      rest="${tuple#*/}"
      ;;
    ssh://*/*)
      tuple="${url#ssh://}"
      host="${tuple%%/*}"
      rest="${tuple#*/}"
      ;;
    https://*/*)
      tuple="${url#https://}"
      host="${tuple%%/*}"
      rest="${tuple#*/}"
      ;;
    git://*/*)
      tuple="${url#git://}"
      host="${tuple%%/*}"
      rest="${tuple#*/}"
      ;;
    *)
      printf '\n'
      return 1
      ;;
  esac

  if [[ -z "$host" || "$host" == *"/"* || "$host" == *"@"* || "$host" == *"://"* || ! "$host" =~ ^[A-Za-z0-9.-]+(:[0-9]+)?$ ]]; then
    printf '\n'
    return 1
  fi

  owner="${rest%%/*}"
  repo="${rest#*/}"
  repo="${repo%%/*}"

  if [[ -z "$owner" || -z "$repo" || "$repo" == "$rest" ]]; then
    printf '\n'
    return 1
  fi

  printf '%s\t%s/%s\n' "$host" "$owner" "$repo" | tr '[:upper:]' '[:lower:]'
}

remote_fetch_urls() {
  # Enumerate via `git remote` so dotted remote names (e.g., `my.fork`,
  # config key `remote.my.fork.url`) are not silently skipped by a flat regex.
  local name url
  while IFS= read -r name; do
    [[ -z "$name" ]] && continue
    while IFS= read -r url; do
      [[ -z "$url" ]] && continue
      printf 'remote.%s.url %s\n' "$name" "$url"
    done < <(git config --get-all "remote.$name.url" 2>/dev/null || true)
  done < <(git remote 2>/dev/null || true)
}

remote_push_urls() {
  # Same as remote_fetch_urls; per-remote query covers dotted remote names.
  local name url
  while IFS= read -r name; do
    [[ -z "$name" ]] && continue
    while IFS= read -r url; do
      [[ -z "$url" ]] && continue
      printf 'remote.%s.pushurl %s\n' "$name" "$url"
    done < <(git config --get-all "remote.$name.pushurl" 2>/dev/null || true)
  done < <(git remote 2>/dev/null || true)
}

classify_remote_state() {
  local upstream fork line key value remote tuple canonical_host canonical
  local remotes remote_count origin_seen upstream_seen fork_count fork_remote
  local origin_canonical upstream_canonical bad multi_url multi_push push_remote
  local fetch_keys push_keys
  local expected_host

  upstream="$1"
  fork="$2"
  expected_host="${GH_HOST:-github.com}"
  expected_host="$(printf '%s\n' "$expected_host" | tr '[:upper:]' '[:lower:]')"
  remotes=""
  remote_count=0
  origin_seen=false
  upstream_seen=false
  fork_count=0
  fork_remote=""
  origin_canonical=""
  upstream_canonical=""
  bad=false
  multi_url=false
  multi_push=false
  fetch_keys="$(mktemp "${TMPDIR:-/tmp}/larch-forked-fetch-keys.XXXXXX")"
  push_keys="$(mktemp "${TMPDIR:-/tmp}/larch-forked-push-keys.XXXXXX")"

  remote_fetch_urls | while IFS= read -r line; do
    key="${line%% *}"
    printf '%s\n' "$key"
  done | sort | uniq -d >"$fetch_keys"
  if [[ -s "$fetch_keys" ]]; then
    multi_url=true
  fi

  remote_push_urls | while IFS= read -r line; do
    key="${line%% *}"
    push_remote="${key#remote.}"
    push_remote="${push_remote%.pushurl}"
    printf '%s\n' "$push_remote"
  done | sort | uniq -d >"$push_keys"
  if [[ -s "$push_keys" ]]; then
    multi_push=true
  fi

  rm -f "$fetch_keys" "$push_keys"

  if [[ "$multi_url" == "true" || "$multi_push" == "true" ]]; then
    printf 'state-ambiguous\n'
    return 0
  fi

  while IFS= read -r line; do
    [[ -z "$line" ]] && continue
    key="${line%% *}"
    value="${line#* }"
    remote="${key#remote.}"
    remote="${remote%.url}"
    tuple="$(normalize_github_url "$value" || true)"
    if [[ -z "$tuple" ]]; then
      bad=true
      continue
    fi
    canonical_host="${tuple%%	*}"
    canonical="${tuple#*	}"
    if [[ "$canonical_host" != "$expected_host" ]]; then
      bad=true
      continue
    fi

    case " $remotes " in
      *" $remote "*) ;;
      *)
        remotes="$remotes $remote"
        remote_count=$((remote_count + 1))
        ;;
    esac

    [[ "$remote" == "origin" ]] && origin_seen=true && origin_canonical="$canonical"
    [[ "$remote" == "upstream" ]] && upstream_seen=true && upstream_canonical="$canonical"
    if [[ "$canonical" == "$fork" ]]; then
      fork_count=$((fork_count + 1))
      fork_remote="$remote"
    elif [[ "$canonical" != "$upstream" ]]; then
      bad=true
    fi
  done < <(remote_fetch_urls)

  if [[ "$bad" == "true" || "$origin_seen" != "true" ]]; then
    printf 'state-ambiguous\n'
    return 0
  fi

  if [[ "$origin_canonical" == "$fork" && "$upstream_seen" == "true" && "$upstream_canonical" == "$upstream" ]]; then
    if [[ "$fork_count" -eq 1 && "$remote_count" -eq 2 ]]; then
      printf 'state-already-configured\n'
    else
      printf 'state-ambiguous\n'
    fi
    return 0
  fi

  if [[ "$origin_canonical" == "$upstream" && "$upstream_seen" != "true" ]]; then
    if [[ "$fork_count" -eq 0 && "$remote_count" -eq 1 ]]; then
      printf 'state-origin-upstream-only\n'
      return 0
    fi
    if [[ "$fork_count" -eq 1 && "$remote_count" -eq 2 && "$fork_remote" != "origin" ]]; then
      printf 'state-origin-upstream-named-fork %s\n' "$fork_remote"
      return 0
    fi
  fi

  printf 'state-ambiguous\n'
}

acquire_clone_lock() {
  local lock_file lock_dir holder holder_tmp
  lock_file="$1"
  lock_dir="$lock_file.d"

  if ! mkdir "$lock_dir" 2>/dev/null; then
    holder="unknown"
    if [[ -r "$lock_dir/holder" ]]; then
      holder="$(cat "$lock_dir/holder" 2>/dev/null || true)"
      [[ -n "$holder" ]] || holder="unknown"
    fi
    die "another setup-forked-open-source-repo run is in progress (lock=$lock_dir, holder=$holder)"
  fi

  holder_tmp="$lock_dir/.holder.$$"
  printf '%s\n' "$$" >"$holder_tmp"
  mv "$holder_tmp" "$lock_dir/holder"

  if command -v flock >/dev/null 2>&1 && [[ -z "${LARCH_FORKED_REPO_FORCE_MKDIR_LOCK:-}" ]]; then
    if ! exec 9>"$lock_file"; then
      rm -f "$lock_dir/holder"
      rmdir "$lock_dir" 2>/dev/null || true
      die "unable to open setup lock file $lock_file"
    fi
    if ! flock -n 9; then
      rm -f "$lock_dir/holder"
      rmdir "$lock_dir" 2>/dev/null || true
      die "another setup-forked-open-source-repo run is in progress (lock=$lock_dir, holder=$$)"
    fi
  fi
}

release_clone_lock() {
  local lock_file lock_dir
  lock_file="${1:-}"
  [[ -n "$lock_file" ]] || return 0
  lock_dir="$lock_file.d"
  rm -f "$lock_dir/holder"
  rmdir "$lock_dir" 2>/dev/null || true
  exec 9>&- 2>/dev/null || true
}

_for_each_live_worktree() {
  local callback line path prunable
  callback="$1"
  path=""
  prunable=false

  while IFS= read -r line; do
    if [[ -z "$line" ]]; then
      if [[ -n "$path" && "$prunable" != "true" ]]; then
        "$callback" "$path" || return 1
      fi
      path=""
      prunable=false
      continue
    fi
    case "$line" in
      worktree\ *)
        path="${line#worktree }"
        ;;
      prunable*)
        prunable=true
        ;;
    esac
  done < <(git worktree list --porcelain)

  if [[ -n "$path" && "$prunable" != "true" ]]; then
    "$callback" "$path" || return 1
  fi
}

_assert_worktree_clean() {
  local path
  path="$1"
  if [[ -n "$(git -C "$path" status --porcelain)" ]]; then
    _remotes_user_err "$(printf "ERROR: working tree '%s' is dirty; commit or stash before running\n" "$path")"
    return 1
  fi
}

assert_all_worktrees_clean() {
  _for_each_live_worktree _assert_worktree_clean
}

_assert_worktree_no_op_in_progress() {
  local path git_dir sentinel
  path="$1"
  git_dir="$(git -C "$path" rev-parse --absolute-git-dir 2>/dev/null)" || return 1
  for sentinel in MERGE_HEAD REBASE_HEAD rebase-apply rebase-merge CHERRY_PICK_HEAD REVERT_HEAD; do
    if [[ -e "$git_dir/$sentinel" ]]; then
      _remotes_user_err "$(printf "ERROR: git operation in progress in '%s' (%s); resolve it before running\n" "$path" "$sentinel")"
      return 1
    fi
  done
}

assert_all_worktrees_no_op_in_progress() {
  _for_each_live_worktree _assert_worktree_no_op_in_progress
}

journal_record() {
  local journal
  journal="$1"
  shift
  printf '%s\n' "$*" >>"$journal"
}
