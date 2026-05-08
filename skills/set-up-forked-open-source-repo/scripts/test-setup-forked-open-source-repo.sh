#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SCRIPT="$SCRIPT_DIR/setup-forked-open-source-repo.sh"
ROOT="$(cd "$SCRIPT_DIR/../../.." && pwd)"

TMPROOT="$(mktemp -d "${TMPDIR:-/tmp}/larch-forked-repo-test.XXXXXX")"
trap 'rm -rf "$TMPROOT"' EXIT

PASS=0

pass() {
  PASS=$((PASS + 1))
  printf 'ok %s - %s\n' "$PASS" "$1"
}

fail() {
  printf 'not ok - %s\n' "$1" >&2
  exit 1
}

assert_contains() {
  local file pattern label
  file="$1"
  pattern="$2"
  label="$3"
  grep -Fq -- "$pattern" "$file" || fail "$label"
  pass "$label"
}

# Wait until a path exists (file, directory, or symlink), polling at a
# 100ms cadence up to ~30s. Replaces fixed `sleep 1` synchronization in
# lock-contention tests, which can flake under heavy CI load if the
# background lock holder hasn't yet reached the lock-acquisition point
# inside the 1-second window.
wait_for_path() {
  local path label deadline_iters i
  path="$1"
  label="$2"
  # 300 * 0.1s = 30s ceiling; under load the inner sleep can drift, but
  # 30s is generous compared to the ~50ms first lock-acquisition path on
  # the slowest macOS CI runner observed.
  deadline_iters=300
  i=0
  while [[ $i -lt $deadline_iters ]]; do
    if [[ -e "$path" ]]; then
      return 0
    fi
    sleep 0.1
    i=$((i + 1))
  done
  fail "$label timed out waiting for $path"
}

assert_not_contains() {
  local file pattern label
  file="$1"
  pattern="$2"
  label="$3"
  if grep -Fq -- "$pattern" "$file"; then
    fail "$label"
  fi
  pass "$label"
}

assert_eq() {
  local expected actual label
  expected="$1"
  actual="$2"
  label="$3"
  [[ "$expected" == "$actual" ]] || fail "$label: expected '$expected', got '$actual'"
  pass "$label"
}

make_gh_stub() {
  local bin
  bin="$1"
  mkdir -p "$bin"
cat >"$bin/gh" <<'STUB'
#!/usr/bin/env bash
set -euo pipefail
mode="${GH_STUB_MODE:-ok}"
record="${GH_STUB_RECORD:-}"
record_line() {
  [[ -n "$record" ]] || return 0
  printf '%s\n' "$*" >>"$record"
}
assert_host() {
  local actual label
  actual="$1"
  label="$2"
  if [[ -n "${GH_STUB_EXPECT_HOST:-}" && "$actual" != "$GH_STUB_EXPECT_HOST" ]]; then
    echo "$label host mismatch: expected $GH_STUB_EXPECT_HOST got ${actual:-<empty>}" >&2
    exit 3
  fi
}
if [[ "$1" == "auth" && "${2:-}" == "status" ]]; then
  shift 2
  auth_host=""
  while [[ $# -gt 0 ]]; do
    case "$1" in
      --hostname)
        auth_host="${2:-}"
        shift 2
        ;;
      *)
        shift
        ;;
    esac
  done
  record_line "auth_status hostname=${auth_host:-} env=${GH_HOST:-}"
  assert_host "${auth_host:-}" "auth status --hostname"
  assert_host "${GH_HOST:-}" "auth status GH_HOST"
  [[ "$mode" == "auth-fail" ]] && { echo "auth failed token ghp_example" >&2; exit 1; }
  exit 0
fi
if [[ "$1" == "repo" && "${2:-}" == "view" ]]; then
  record_line "repo_view env=${GH_HOST:-} args=$*"
  assert_host "${GH_HOST:-}" "repo view GH_HOST"
  [[ "$mode" == "missing" ]] && { echo "HTTP 404: Could not resolve to a Repository" >&2; exit 1; }
  [[ "$mode" == "api-fail" ]] && { echo "HTTP 403: rate limited" >&2; exit 1; }
  if [[ "$mode" == "parent-split-fields" ]]; then
    cat <<'JSON'
{"nameWithOwner":"me/project","parent":{"owner":{"login":"acme"},"name":"project"},"defaultBranchRef":{"name":"main"}}
JSON
    exit 0
  fi
  if [[ "$mode" == "parent-malformed-owner" ]]; then
    # Pathological shape: `.parent.owner` is a string rather than an object.
    # Exercises the type guard in `phase_github`'s jq program — without the
    # guard, jq aborts indexing `.login` on a string before the parent gate
    # can run, so the operator never sees the stable `fork parent mismatch`
    # wording.
    cat <<'JSON'
{"nameWithOwner":"me/project","parent":{"owner":"acme","name":"project"},"defaultBranchRef":{"name":"main"}}
JSON
    exit 0
  fi
  if [[ "$mode" == "parent-numeric-fields" ]]; then
    # Pathological shape: `.parent.owner.login` and `.parent.name` are
    # numbers, not strings. Without the string-type guard the jq program
    # would compose `1/2` and pass the parent gate against a numeric
    # `--upstream 1/2`, since `validate_owner_repo` accepts purely numeric
    # owner/repo segments.
    cat <<'JSON'
{"nameWithOwner":"me/project","parent":{"owner":{"login":1},"name":2},"defaultBranchRef":{"name":"main"}}
JSON
    exit 0
  fi
  if [[ "$mode" == "parent-invalid-json" ]]; then
    # gh repo view emits something that is not valid JSON. The phase MUST
    # short-circuit with a clear "invalid JSON" diagnostic instead of
    # falling through to the shape-error path or aborting on a raw jq
    # parse failure.
    printf 'this is not json\n'
    exit 0
  fi
  cat <<'JSON'
{"nameWithOwner":"me/project","parent":{"nameWithOwner":"acme/project"},"defaultBranchRef":{"name":"main"}}
JSON
  exit 0
fi
echo "unexpected gh invocation: $*" >&2
exit 2
STUB
  chmod +x "$bin/gh"
}

git_identity() {
  git config user.name "Larch Test"
  git config user.email "larch-test@example.invalid"
}

commit_file() {
  local name content
  name="$1"
  content="$2"
  printf '%s\n' "$content" >"$name"
  git add "$name"
  git commit -m "commit $name" >/dev/null
}

new_fixture() {
  local name base upstream fork work bin
  name="$1"
  base="$TMPROOT/$name"
  upstream="$base/upstream.git"
  fork="$base/fork.git"
  work="$base/work"
  bin="$base/bin"
  mkdir -p "$base"
  git init --bare "$upstream" >/dev/null
  git init --bare "$fork" >/dev/null
  git init "$base/seed" >/dev/null
  (
    cd "$base/seed"
    git_identity
    git checkout -b main >/dev/null
    commit_file README.md "base"
    git remote add upstream "$upstream"
    git push upstream main >/dev/null
    git remote add fork "$fork"
    git push fork main >/dev/null
  )
  git clone "$upstream" "$work" >/dev/null
  (
    cd "$work"
    git checkout main >/dev/null
    git_identity
    git config url."$upstream".insteadOf "https://github.com/acme/project.git"
    git config --add url."$upstream".insteadOf "git@github.com:acme/project.git"
    git config url."$fork".insteadOf "https://github.com/me/project.git"
    git config --add url."$fork".insteadOf "git@github.com:me/project.git"
    git remote set-url origin "https://github.com/acme/project.git"
  )
  make_gh_stub "$bin"
  printf '%s\n%s\n%s\n%s\n' "$base" "$upstream" "$fork" "$work"
}

run_setup() {
  local work out rc
  work="$1"
  out="$2"
  shift 2
  (
    cd "$work"
    PATH="$GH_BIN:$PATH" \
      CLAUDE_PLUGIN_ROOT="$ROOT" \
      LARCH_FORKED_REPO_ALLOW_URL_OVERRIDE=1 \
      LARCH_FORKED_REPO_URL_OVERRIDE_UPSTREAM_HTTPS="$UPSTREAM_BARE" \
      LARCH_FORKED_REPO_URL_OVERRIDE_UPSTREAM_SSH="$UPSTREAM_BARE" \
      LARCH_FORKED_REPO_URL_OVERRIDE_FORK_HTTPS="$FORK_BARE" \
      LARCH_FORKED_REPO_URL_OVERRIDE_FORK_SSH="$FORK_BARE" \
      LARCH_FORKED_REPO_INJECT_FAILURE="${LARCH_FORKED_REPO_INJECT_FAILURE:-}" \
      LARCH_FORKED_REPO_FORCE_MKDIR_LOCK="${LARCH_FORKED_REPO_FORCE_MKDIR_LOCK:-}" \
      LARCH_FORKED_REPO_PAUSE_AFTER_LOCK_S="${LARCH_FORKED_REPO_PAUSE_AFTER_LOCK_S:-}" \
      GH_STUB_EXPECT_HOST="${GH_STUB_EXPECT_HOST:-}" \
      GH_STUB_RECORD="${GH_STUB_RECORD:-}" \
      "$SCRIPT" --upstream acme/project --fork me/project "$@"
  ) >"$out" 2>&1
}

run_setup_rc() {
  local work out rc
  work="$1"
  out="$2"
  shift 2
  set +e
  (
    cd "$work"
    PATH="$GH_BIN:$PATH" \
      CLAUDE_PLUGIN_ROOT="$ROOT" \
      LARCH_FORKED_REPO_ALLOW_URL_OVERRIDE=1 \
      LARCH_FORKED_REPO_URL_OVERRIDE_UPSTREAM_HTTPS="$UPSTREAM_BARE" \
      LARCH_FORKED_REPO_URL_OVERRIDE_UPSTREAM_SSH="$UPSTREAM_BARE" \
      LARCH_FORKED_REPO_URL_OVERRIDE_FORK_HTTPS="$FORK_BARE" \
      LARCH_FORKED_REPO_URL_OVERRIDE_FORK_SSH="$FORK_BARE" \
      LARCH_FORKED_REPO_INJECT_FAILURE="${LARCH_FORKED_REPO_INJECT_FAILURE:-}" \
      LARCH_FORKED_REPO_FORCE_MKDIR_LOCK="${LARCH_FORKED_REPO_FORCE_MKDIR_LOCK:-}" \
      LARCH_FORKED_REPO_PAUSE_AFTER_LOCK_S="${LARCH_FORKED_REPO_PAUSE_AFTER_LOCK_S:-}" \
      GH_STUB_EXPECT_HOST="${GH_STUB_EXPECT_HOST:-}" \
      GH_STUB_RECORD="${GH_STUB_RECORD:-}" \
      "$SCRIPT" --upstream acme/project --fork me/project "$@"
  ) >"$out" 2>&1
  rc="$?"
  set -e
  return "$rc"
}

read_fixture() {
  local data
  data="$(new_fixture "$1")"
  BASE="$(printf '%s\n' "$data" | sed -n '1p')"
  UPSTREAM_BARE="$(printf '%s\n' "$data" | sed -n '2p')"
  FORK_BARE="$(printf '%s\n' "$data" | sed -n '3p')"
  WORK="$(printf '%s\n' "$data" | sed -n '4p')"
  GH_BIN="$BASE/bin"
}

assert_configured() {
  local work origin_url
  work="$1"
  origin_url="$(git -C "$work" config --get remote.origin.url)"
  case "$origin_url" in
    https://github.com/me/project.git|git@github.com:me/project.git|"$FORK_BARE")
      pass "origin points at fork"
      ;;
    *)
      fail "origin points at fork: got '$origin_url'"
      ;;
  esac
  assert_eq "https://github.com/acme/project.git" "$(git -C "$work" config --get remote.upstream.url)" "upstream points at upstream"
  assert_eq "larch-disabled://upstream-push-disabled" "$(git -C "$work" config --get remote.upstream.pushurl)" "upstream push disabled"
  assert_eq "origin" "$(git -C "$work" config --get branch.main.remote)" "main tracks origin"
  assert_eq "refs/heads/main" "$(git -C "$work" config --get branch.main.merge)" "main merge ref set"
}

read_fixture state_origin_only
OUT="$BASE/out.txt"
run_setup "$WORK" "$OUT"
assert_contains "$OUT" "SETUP_FORKED_REPO_RESULT=ok" "origin-only run succeeds"
assert_configured "$WORK"

read_fixture state_named_fork
OUT="$BASE/out.txt"
git -C "$WORK" remote add zhupanov "https://github.com/me/project.git"
run_setup "$WORK" "$OUT"
assert_configured "$WORK"
assert_eq "origin upstream" "$(git -C "$WORK" remote | sort | tr '\n' ' ' | sed 's/ $//')" "named fork remote renamed"

# Regression for FINDING_2: dotted remote names (e.g. `my.fork` → config key
# `remote.my.fork.url`) used to be silently skipped by a flat
# `^remote\.[^.][^.]*\.url$` regex over `git config --get-regexp`, which would
# misclassify the layout as `state-origin-upstream-only` and leak the dotted
# fork remote alongside a freshly-added `origin`. The classifier now enumerates
# via `git remote` so dotted names participate in classification correctly.
read_fixture state_dotted_named_fork
OUT="$BASE/out.txt"
git -C "$WORK" remote add my.fork "https://github.com/me/project.git"
run_setup "$WORK" "$OUT"
assert_contains "$OUT" "SETUP_FORKED_REPO_RESULT=ok" "dotted named fork remote handled"
assert_configured "$WORK"
assert_eq "origin upstream" "$(git -C "$WORK" remote | sort | tr '\n' ' ' | sed 's/ $//')" "dotted fork remote renamed to origin"

read_fixture state_already
OUT="$BASE/out.txt"
git -C "$WORK" remote rename origin upstream
git -C "$WORK" remote add origin "https://github.com/me/project.git"
git -C "$WORK" config --add remote.upstream.pushurl 'larch-disabled://upstream-push-disabled'
run_setup "$WORK" "$OUT"
assert_configured "$WORK"

read_fixture ambiguous_duplicate
OUT="$BASE/out.txt"
git -C "$WORK" remote add mine "https://github.com/me/project.git"
git -C "$WORK" remote add also-mine "git@github.com:me/project.git"
if run_setup_rc "$WORK" "$OUT"; then fail "ambiguous duplicate fork remotes refuse"; fi
assert_contains "$OUT" "ambiguous remote state" "ambiguous duplicate fork remotes refuse"
assert_eq "also-mine mine origin" "$(git -C "$WORK" remote | sort | tr '\n' ' ' | sed 's/ $//')" "ambiguous state is not mutated"

read_fixture non_main
OUT="$BASE/out.txt"
git -C "$WORK" checkout -b feature >/dev/null
if run_setup_rc "$WORK" "$OUT"; then fail "non-main checkout refuses"; fi
assert_contains "$OUT" "current checkout must be main" "non-main checkout refuses"

read_fixture dirty
OUT="$BASE/out.txt"
printf 'dirty\n' >"$WORK/dirty.txt"
if run_setup_rc "$WORK" "$OUT"; then fail "dirty worktree refuses"; fi
assert_contains "$OUT" "working tree is dirty" "dirty worktree refuses"

read_fixture ahead
OUT="$BASE/out.txt"
(
  cd "$WORK"
  commit_file local.txt "ahead"
)
if run_setup_rc "$WORK" "$OUT"; then fail "main ahead refuses"; fi
assert_contains "$OUT" "local main is ahead" "main ahead refuses"

read_fixture diverged
OUT="$BASE/out.txt"
(
  cd "$WORK"
  commit_file local.txt "ahead"
)
git clone "$UPSTREAM_BARE" "$BASE/upstream-work" >/dev/null
(
  cd "$BASE/upstream-work"
  git checkout main >/dev/null
  git_identity
  commit_file remote.txt "remote"
  git push origin main >/dev/null
)
if run_setup_rc "$WORK" "$OUT"; then fail "diverged main refuses"; fi
assert_contains "$OUT" "diverged" "diverged main refuses"

read_fixture missing_fork
OUT="$BASE/out.txt"
GH_STUB_MODE=missing run_setup "$WORK" "$OUT"
assert_contains "$OUT" "SETUP_FORKED_REPO_RESULT=fork_missing" "missing fork exits with marker"
assert_eq "https://github.com/acme/project.git" "$(git -C "$WORK" config --get remote.origin.url)" "missing fork does not mutate remotes"

read_fixture parent_split_fields
OUT="$BASE/out.txt"
GH_STUB_MODE=parent-split-fields run_setup "$WORK" "$OUT"
assert_contains "$OUT" "SETUP_FORKED_REPO_RESULT=mirror_skipped_in_sync" "parent split owner/name fields pass"

# Regression: pathological `.parent.owner` shape (string instead of object)
# must yield the intended `fork parent mismatch ... got <none>` error,
# not a raw `jq` index/type abort. Exercises the type guard in phase_github.
read_fixture parent_malformed_owner
OUT="$BASE/out.txt"
if GH_STUB_MODE=parent-malformed-owner run_setup_rc "$WORK" "$OUT"; then fail "malformed parent.owner refuses"; fi
assert_contains "$OUT" "fork parent mismatch" "malformed parent.owner produces clean mismatch error"
assert_contains "$OUT" "got <none>" "malformed parent.owner reports <none>"

# Regression: numeric `parent.owner.login` and `parent.name` must NOT compose
# into `1/2` and pass the gate against a numeric `--upstream 1/2`
# (validate_owner_repo accepts purely numeric segments). The string type
# guard rejects the shape and the gate falls into `got <none>`.
read_fixture parent_numeric_fields
OUT="$BASE/out.txt"
if GH_STUB_MODE=parent-numeric-fields run_setup_rc "$WORK" "$OUT"; then fail "numeric parent fields refuses"; fi
assert_contains "$OUT" "fork parent mismatch" "numeric parent fields produce clean mismatch error"
assert_contains "$OUT" "got <none>" "numeric parent fields report <none>"

# Regression: syntactically invalid JSON from `gh repo view` must surface
# as a clean "invalid JSON" diagnostic rather than the shape-error
# `fork parent mismatch ... got <none>` path or a raw jq parse abort.
read_fixture parent_invalid_json
OUT="$BASE/out.txt"
if GH_STUB_MODE=parent-invalid-json run_setup_rc "$WORK" "$OUT"; then fail "invalid gh JSON exits non-zero"; fi
assert_contains "$OUT" "gh repo view returned invalid JSON" "invalid gh JSON yields clear diagnostic"
assert_not_contains "$OUT" "fork parent mismatch" "invalid gh JSON does NOT misclassify as parent mismatch"
assert_eq "https://github.com/acme/project.git" "$(git -C "$WORK" config --get remote.origin.url)" "invalid gh JSON does not mutate remotes"

read_fixture auth_failure
OUT="$BASE/out.txt"
if GH_STUB_MODE=auth-fail run_setup_rc "$WORK" "$OUT"; then fail "auth failure exits non-zero"; fi
assert_contains "$OUT" "gh auth status failed" "auth failure exits non-zero"

# Regression for FINDING_R2_4: the skill's contract distinguishes 404
# (fork_missing) from non-404 gh failures (auth, rate-limit, SSO, network),
# but the harness was missing a case for the non-404 path. Without coverage,
# the 404-vs-other branch in phase_github could regress and start masking
# real API errors as fork_missing.
read_fixture api_failure
OUT="$BASE/out.txt"
if GH_STUB_MODE=api-fail run_setup_rc "$WORK" "$OUT"; then fail "non-404 gh repo view failure exits non-zero"; fi
assert_contains "$OUT" "gh repo view failed" "non-404 gh repo view failure exits non-zero"
assert_not_contains "$OUT" "SETUP_FORKED_REPO_RESULT=fork_missing" "non-404 gh failure does NOT classify as fork_missing"
assert_eq "https://github.com/acme/project.git" "$(git -C "$WORK" config --get remote.origin.url)" "non-404 gh failure does not mutate remotes"

read_fixture mirror_in_sync
OUT="$BASE/out.txt"
run_setup "$WORK" "$OUT"
assert_contains "$OUT" "SETUP_FORKED_REPO_RESULT=mirror_skipped_in_sync" "mirror in sync marker emitted"

read_fixture mirror_no_confirm
OUT="$BASE/out.txt"
git clone "$UPSTREAM_BARE" "$BASE/upstream-edit" >/dev/null
(
  cd "$BASE/upstream-edit"
  git checkout main >/dev/null
  git_identity
  commit_file upstream.txt "new upstream"
  git push origin main >/dev/null
)
if run_setup_rc "$WORK" "$OUT"; then fail "mirror divergence needs confirmation in non-tty"; fi
assert_contains "$OUT" "rerun with --mirror-confirmed" "mirror divergence needs confirmation in non-tty"

read_fixture mirror_confirmed
OUT="$BASE/out.txt"
git clone "$UPSTREAM_BARE" "$BASE/upstream-edit" >/dev/null
(
  cd "$BASE/upstream-edit"
  git checkout main >/dev/null
  git_identity
  commit_file upstream.txt "new upstream"
  git push origin main >/dev/null
  sha="$(git rev-parse HEAD)"
  git push origin "$sha:refs/changes/1" >/dev/null
)
run_setup "$WORK" "$OUT" --mirror-confirmed
assert_contains "$OUT" "SETUP_FORKED_REPO_RESULT=mirror_synced" "mirror confirmed syncs"
assert_eq "$(git -C "$UPSTREAM_BARE" rev-parse refs/heads/main)" "$(git -C "$FORK_BARE" rev-parse refs/heads/main)" "fork main matches upstream after sync"
if git -C "$FORK_BARE" show-ref --verify --quiet refs/changes/1; then fail "scoped mirror excludes non-head/tag refs"; fi
pass "scoped mirror excludes non-head/tag refs"

read_fixture rollback_fetch
OUT="$BASE/out.txt"
export LARCH_FORKED_REPO_INJECT_FAILURE=fetch
if run_setup_rc "$WORK" "$OUT"; then fail "fetch failure triggers rollback"; fi
unset LARCH_FORKED_REPO_INJECT_FAILURE
assert_eq "https://github.com/acme/project.git" "$(git -C "$WORK" config --get remote.origin.url)" "rollback restores origin after fetch failure"
if git -C "$WORK" remote | grep -Fxq upstream; then fail "rollback removes added upstream remote"; fi
pass "rollback removes added upstream remote"

read_fixture rollback_failed
OUT="$BASE/out.txt"
export LARCH_FORKED_REPO_INJECT_FAILURE=rollback
if run_setup_rc "$WORK" "$OUT"; then fail "rollback failure exits non-zero"; fi
unset LARCH_FORKED_REPO_INJECT_FAILURE
assert_contains "$OUT" "RECOVERY_REPORT rollback_failed=true" "rollback failure emits recovery report"

# Regression for FINDING_R3_6: round-2 FINDING_R2_1 moved REMOTE_PHASE_ACTIVE=false
# to AFTER phase_verify so a late-phase failure (after remote rewrites) still
# triggers rollback. Without the in-verify failure-injection point this guarantee
# was untested. The injection raises a non-zero command (NOT die / exit) inside
# phase_verify so the ERR trap fires restore_remote_state — confirming both the
# late REMOTE_PHASE_ACTIVE clear AND the verify_die-vs-die fix from FINDING_R3_1.
read_fixture rollback_in_verify
OUT="$BASE/out.txt"
export LARCH_FORKED_REPO_INJECT_FAILURE=in-verify
if run_setup_rc "$WORK" "$OUT"; then fail "in-verify failure triggers rollback"; fi
unset LARCH_FORKED_REPO_INJECT_FAILURE
assert_contains "$OUT" "remote rewrite failed; attempting rollback" "in-verify failure attempts rollback"
assert_eq "https://github.com/acme/project.git" "$(git -C "$WORK" config --get remote.origin.url)" "in-verify rollback restores origin URL"
if git -C "$WORK" remote | grep -Fxq upstream; then fail "in-verify rollback removes added upstream remote"; fi
pass "in-verify rollback removes added upstream remote"

read_fixture push_disabled
OUT="$BASE/out.txt"
run_setup "$WORK" "$OUT"
if git -C "$WORK" push upstream main >"$BASE/push.txt" 2>&1; then fail "disabled upstream push fails"; fi
assert_contains "$BASE/push.txt" "larch-disabled" "disabled upstream push fails"

read_fixture submodules_default
OUT="$BASE/out.txt"
printf '[submodule "child"]\n\tpath = child\n\turl = https://github.com/acme/child.git\n' >"$WORK/.gitmodules"
git -C "$WORK" add .gitmodules
git -C "$WORK" commit -m "add gitmodules" >/dev/null
git -C "$WORK" push origin main >/dev/null
git -C "$WORK" remote set-url origin "https://github.com/acme/project.git"
git -C "$FORK_BARE" fetch "$UPSTREAM_BARE" main:main >/dev/null
run_setup "$WORK" "$OUT"
assert_contains "$OUT" "SETUP_FORKED_REPO_RESULT=ok" "default run ignores submodule init"

read_fixture normalize_ghe_urls
LIB="$SCRIPT_DIR/lib-remotes.sh"
tuple="$(bash -c 'source "$1"; normalize_github_url "$2"' bash "$LIB" "https://ghe.example.com/acme/proj.git")"
assert_eq "$(printf 'ghe.example.com\tacme/proj')" "$tuple" "normalize https GHE URL returns host and slug"
tuple="$(bash -c 'source "$1"; normalize_github_url "$2"' bash "$LIB" "git@ghe.example.com:acme/proj.git")"
assert_eq "$(printf 'ghe.example.com\tacme/proj')" "$tuple" "normalize scp-style GHE URL returns host and slug"
tuple="$(bash -c 'source "$1"; normalize_github_url "$2"' bash "$LIB" "ssh://git@ghe.example.com/acme/proj.git")"
assert_eq "$(printf 'ghe.example.com\tacme/proj')" "$tuple" "normalize ssh GHE URL returns host and slug"
tuple="$(bash -c 'source "$1"; normalize_github_url "$2"' bash "$LIB" "git://ghe.example.com/acme/proj")"
assert_eq "$(printf 'ghe.example.com\tacme/proj')" "$tuple" "normalize git protocol GHE URL returns host and slug"
set +e
tuple="$(bash -c 'source "$1"; normalize_github_url "$2"' bash "$LIB" "http://github.com/acme/proj")"
rc="$?"
set -e
assert_eq "1" "$rc" "normalize rejects http URL"
assert_eq "" "$tuple" "normalize rejected http URL prints empty"
set +e
tuple="$(bash -c 'source "$1"; normalize_github_url "$2"' bash "$LIB" "https://acme@github.com/acme/proj")"
rc="$?"
set -e
assert_eq "1" "$rc" "normalize rejects malformed host"
assert_eq "" "$tuple" "normalize rejected malformed host prints empty"

read_fixture ghe_host_forwarding
OUT="$BASE/out.txt"
RECORD="$BASE/gh-record.txt"
git -C "$WORK" config --add url."$UPSTREAM_BARE".insteadOf "https://ghe.example.com/acme/project.git"
git -C "$WORK" remote set-url origin "https://ghe.example.com/acme/project.git"
GH_STUB_EXPECT_HOST=ghe.example.com GH_STUB_RECORD="$RECORD" run_setup "$WORK" "$OUT"
assert_contains "$OUT" "SETUP_FORKED_REPO_RESULT=ok" "GHE origin run succeeds"
assert_contains "$RECORD" "auth_status hostname=ghe.example.com env=ghe.example.com" "GHE auth status receives host"
assert_contains "$RECORD" "repo_view env=ghe.example.com" "GHE repo view receives GH_HOST"

read_fixture github_host_baseline
OUT="$BASE/out.txt"
RECORD="$BASE/gh-record.txt"
GH_STUB_EXPECT_HOST=github.com GH_STUB_RECORD="$RECORD" run_setup "$WORK" "$OUT"
assert_contains "$OUT" "SETUP_FORKED_REPO_RESULT=ok" "github.com host baseline succeeds"
assert_contains "$RECORD" "auth_status hostname=github.com env=github.com" "github.com auth status receives host"
assert_contains "$RECORD" "repo_view env=github.com" "github.com repo view receives GH_HOST"
assert_configured "$WORK"

read_fixture host_mismatch
OUT="$BASE/out.txt"
RECORD="$BASE/gh-record.txt"
git -C "$WORK" remote add mine "https://ghe.example.com/me/project.git"
if GH_STUB_RECORD="$RECORD" run_setup_rc "$WORK" "$OUT"; then fail "mixed host remotes refuse"; fi
assert_contains "$OUT" "ambiguous remote state" "mixed host remotes refuse before GitHub repo view"
assert_not_contains "$RECORD" "repo_view" "mixed host refusal skips gh repo view"

read_fixture multi_url_origin
OUT="$BASE/out.txt"
RECORD="$BASE/gh-record.txt"
git -C "$WORK" config --add remote.origin.url "https://github.com/acme/project.git"
if GH_STUB_RECORD="$RECORD" run_setup_rc "$WORK" "$OUT"; then fail "multi-URL origin refuses"; fi
assert_contains "$OUT" "multiple remote.origin.url entries" "multi-URL origin refuses early"
if [[ -f "$RECORD" ]]; then
  assert_not_contains "$RECORD" "auth_status" "multi-URL origin skips gh auth"
else
  pass "multi-URL origin skips gh auth"
fi

read_fixture sibling_dirty
OUT="$BASE/out.txt"
SIBLING="$BASE/sibling"
git -C "$WORK" worktree add -b sibling "$SIBLING" main >/dev/null
printf 'dirty\n' >"$SIBLING/dirty.txt"
if run_setup_rc "$WORK" "$OUT"; then fail "dirty sibling worktree refuses"; fi
assert_contains "$OUT" "is dirty; commit or stash before running" "dirty sibling worktree refuses with path"

read_fixture sibling_op_in_progress
OUT="$BASE/out.txt"
SIBLING="$BASE/sibling"
git -C "$WORK" worktree add -b sibling "$SIBLING" main >/dev/null
mkdir -p "$(git -C "$SIBLING" rev-parse --absolute-git-dir)/rebase-merge"
if run_setup_rc "$WORK" "$OUT"; then fail "sibling rebase refuses from primary"; fi
assert_contains "$OUT" "git operation in progress in" "sibling rebase refuses from primary"
assert_contains "$OUT" "rebase-merge" "sibling rebase reports sentinel from primary"

read_fixture sibling_op_in_progress_from_sibling
OUT="$BASE/out-sibling.txt"
SIBLING="$BASE/sibling"
git -C "$WORK" checkout -b feature >/dev/null
git -C "$WORK" worktree add "$SIBLING" main >/dev/null
mkdir -p "$(git -C "$SIBLING" rev-parse --absolute-git-dir)/rebase-merge"
OUT="$BASE/out-sibling.txt"
if run_setup_rc "$SIBLING" "$OUT"; then fail "sibling rebase refuses from sibling cwd"; fi
assert_contains "$OUT" "git operation in progress in" "sibling rebase refuses from sibling cwd"
assert_contains "$OUT" "rebase-merge" "sibling rebase reports sentinel from sibling cwd"

read_fixture prunable_worktree
OUT="$BASE/out.txt"
PRUNABLE="$BASE/prunable"
git -C "$WORK" worktree add -b prunable "$PRUNABLE" main >/dev/null
rm -rf "$PRUNABLE"
run_setup "$WORK" "$OUT"
assert_contains "$OUT" "SETUP_FORKED_REPO_RESULT=ok" "prunable worktree is skipped"

read_fixture lock_contention_mkdir
OUT1="$BASE/out-first.txt"
OUT2="$BASE/out-second.txt"
COMMON_DIR="$(git -C "$WORK" rev-parse --absolute-git-dir)"
LOCK_FILE="$COMMON_DIR/larch-fork-setup.lock"
LARCH_FORKED_REPO_FORCE_MKDIR_LOCK=1 LARCH_FORKED_REPO_PAUSE_AFTER_LOCK_S=2 run_setup "$WORK" "$OUT1" &
pid="$!"
wait_for_path "$LOCK_FILE.d" "mkdir lock contention precondition"
if LARCH_FORKED_REPO_FORCE_MKDIR_LOCK=1 run_setup_rc "$WORK" "$OUT2"; then fail "mkdir lock contention refuses"; fi
wait "$pid"
assert_contains "$OUT2" "another setup-forked-open-source-repo run is in progress" "mkdir lock contention refuses"
assert_contains "$OUT2" "lock=" "mkdir lock contention reports lock"
assert_contains "$OUT2" "holder=" "mkdir lock contention reports holder"

read_fixture lock_contention_mixed_mode
OUT1="$BASE/out-first.txt"
OUT2="$BASE/out-second.txt"
COMMON_DIR="$(git -C "$WORK" rev-parse --absolute-git-dir)"
LOCK_FILE="$COMMON_DIR/larch-fork-setup.lock"
LARCH_FORKED_REPO_FORCE_MKDIR_LOCK=1 LARCH_FORKED_REPO_PAUSE_AFTER_LOCK_S=2 run_setup "$WORK" "$OUT1" &
pid="$!"
wait_for_path "$LOCK_FILE.d" "mixed-mode lock contention precondition"
if run_setup_rc "$WORK" "$OUT2"; then fail "mixed-mode lock contention refuses"; fi
wait "$pid"
assert_contains "$OUT2" "another setup-forked-open-source-repo run is in progress" "mixed-mode lock contention refuses"

read_fixture holder_sidecar_cleanup
OUT="$BASE/out.txt"
COMMON_DIR="$(git -C "$WORK" rev-parse --absolute-git-dir)"
LOCK_FILE="$COMMON_DIR/larch-fork-setup.lock"
LARCH_FORKED_REPO_FORCE_MKDIR_LOCK=1 LARCH_FORKED_REPO_PAUSE_AFTER_LOCK_S=1 run_setup "$WORK" "$OUT"
if [[ -e "$LOCK_FILE.d/holder" || -d "$LOCK_FILE.d" ]]; then fail "lock holder sidecar cleaned after release"; fi
pass "lock holder sidecar cleaned after release"

if command -v flock >/dev/null 2>&1; then
  read_fixture lock_contention_flock
  OUT="$BASE/out.txt"
  COMMON_DIR="$(git -C "$WORK" rev-parse --absolute-git-dir)"
  LOCK_FILE="$COMMON_DIR/larch-fork-setup.lock"
  FLOCK_READY="$BASE/flock-ready"
  (
    exec 8>"$LOCK_FILE"
    flock -x 8
    : >"$FLOCK_READY"
    sleep 2
  ) &
  pid="$!"
  wait_for_path "$FLOCK_READY" "flock lock contention precondition"
  if run_setup_rc "$WORK" "$OUT"; then fail "flock lock contention refuses"; fi
  wait "$pid"
  assert_contains "$OUT" "another setup-forked-open-source-repo run is in progress" "flock lock contention refuses"
else
  pass "flock lock contention skipped because flock is unavailable"
fi

printf 'All set-up-forked-open-source-repo harness checks passed.\n'
