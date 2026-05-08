# shellcheck shell=bash
# Sourced by setup-forked-open-source-repo.sh.

normalize_github_url() {
  local url owner repo rest
  url="${1:-}"
  url="${url%/}"
  url="${url%.git}"

  case "$url" in
    git@github.com:*)
      rest="${url#git@github.com:}"
      ;;
    ssh://git@github.com/*)
      rest="${url#ssh://git@github.com/}"
      ;;
    https://github.com/*)
      rest="${url#https://github.com/}"
      ;;
    git://github.com/*)
      rest="${url#git://github.com/}"
      ;;
    *)
      printf '\n'
      return 1
      ;;
  esac

  owner="${rest%%/*}"
  repo="${rest#*/}"
  repo="${repo%%/*}"

  if [[ -z "$owner" || -z "$repo" || "$repo" == "$rest" ]]; then
    printf '\n'
    return 1
  fi

  printf '%s/%s\n' "$owner" "$repo" | tr '[:upper:]' '[:lower:]'
}

remote_fetch_urls() {
  git config --get-regexp '^remote\.[^.][^.]*\.url$' 2>/dev/null || true
}

remote_push_urls() {
  git config --get-regexp '^remote\.[^.][^.]*\.pushurl$' 2>/dev/null || true
}

classify_remote_state() {
  local upstream fork line key value remote canonical
  local remotes remote_count origin_seen upstream_seen fork_count fork_remote
  local origin_canonical upstream_canonical bad multi_url multi_push push_remote
  local fetch_keys push_keys

  upstream="$1"
  fork="$2"
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
    canonical="$(normalize_github_url "$value" || true)"
    if [[ -z "$canonical" ]]; then
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

journal_record() {
  local journal
  journal="$1"
  shift
  printf '%s\n' "$*" >>"$journal"
}
