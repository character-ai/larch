#!/usr/bin/env bash
# classify-bump.sh — Deterministic semver classifier for the release skill.
#
# Scope: only inspects public plugin surface (skills/**, agents/**).
# Changes under .claude/**, scripts/**, hooks/**, docs/**, .github/**, etc.
# contribute only to the default PATCH baseline.
#
# Rules (highest severity wins):
#   MAJOR — deleted/renamed SKILL.md or agents/*.md, changed `name:` frontmatter,
#           removed `--flag` bullet, removed `--flag` in argument-hint
#   MINOR — new SKILL.md or agents/*.md, new `--flag` bullet, new `--flag` in argument-hint
#   PATCH — default when no MAJOR or MINOR public-surface evidence is found
#
# Idempotent no-op: without --base, if HEAD is a version commit (possibly after
# transparent CHANGELOG/larch-log commits), emits BUMP_TYPE=NONE and exits 0.
#
# Optional: --base <ref> — use <ref> as BASE directly (skip merge-base + idempotency).
#   Consumer: /release via release-prepare.sh.
#
# Output (stdout, KEY=VALUE):
#   CURRENT_VERSION=<x.y.z>
#   NEW_VERSION=<x.y.z>                (same as current if BUMP_TYPE=NONE)
#   BUMP_TYPE=MAJOR|MINOR|PATCH|NONE
#   REASONING_FILE=<path>
#
# Reasoning log: $IMPLEMENT_TMPDIR/bump-version-reasoning.md when available,
# otherwise a mktemp-created bump-version-reasoning.XXXXXX under ${TMPDIR:-/tmp}.
#
# Exit codes: 0 success, 1 validation failure

set -euo pipefail

PLUGIN_JSON="$PWD/.claude-plugin/plugin.json"
BASE_REF=""
HEAD_REF=""
SKIP_IDEMPOTENCY=false

err() {
  echo "ERROR: $*" >&2
  exit 1
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --base)
      [[ $# -ge 2 ]] || err "--base requires a ref"
      BASE_REF="$2"
      shift 2
      ;;
    --head)
      [[ $# -ge 2 ]] || err "--head requires a ref"
      HEAD_REF="$2"
      shift 2
      ;;
    -h|--help)
      echo "Usage: classify-bump.sh [--base <git-ref>] [--head <git-ref>]" >&2
      exit 0
      ;;
    *)
      err "unknown argument: $1"
      ;;
  esac
done

# Validate plugin.json exists and parses.
[[ -f "$PLUGIN_JSON" ]] || err "$PLUGIN_JSON not found"
jq empty "$PLUGIN_JSON" 2>/dev/null || err "$PLUGIN_JSON is not valid JSON"

# Resolve BASE: explicit --base ref (e.g. /release baseline tag) or merge-base path.
BASE=""
if [[ -n "$BASE_REF" ]]; then
  git rev-parse --verify "$BASE_REF^{commit}" >/dev/null 2>&1 \
    || err "could not resolve --base ref: $BASE_REF"
  BASE=$(git rev-parse "$BASE_REF^{commit}")
  SKIP_IDEMPOTENCY=true
else
  # Best-effort fetch so origin/main is fresh. Non-fatal.
  git fetch origin main --quiet 2>/dev/null || true

  # Resolve BASE: prefer local main, fall back to origin/main.
  if git rev-parse --verify main >/dev/null 2>&1; then
    BASE=$(git merge-base main HEAD 2>/dev/null || true)
  fi
  if [[ -z "$BASE" ]] && git rev-parse --verify origin/main >/dev/null 2>&1; then
    BASE=$(git merge-base origin/main HEAD 2>/dev/null || true)
  fi
  [[ -n "$BASE" ]] || err "could not resolve merge-base against main or origin/main"
fi

HEAD_COMPARE="HEAD"
if [[ -n "$HEAD_REF" ]]; then
  git rev-parse --verify "$HEAD_REF^{commit}" >/dev/null 2>&1 \
    || err "could not resolve --head ref: $HEAD_REF"
  HEAD_COMPARE="$(git rev-parse "$HEAD_REF^{commit}")"
fi

# Read current version (worktree by default; --head ref when set for /release).
CURRENT_VERSION=$(jq -r '.version // empty' "$PLUGIN_JSON")
if [[ -n "$HEAD_REF" ]]; then
  head_plugin_json="$(git show "${HEAD_COMPARE}:.claude-plugin/plugin.json" 2>/dev/null)" \
    || err "could not read plugin.json at --head ref: $HEAD_REF"
  head_version="$(printf '%s\n' "$head_plugin_json" | jq -r '.version // empty' 2>/dev/null)" \
    || err "could not parse plugin.json at --head ref: $HEAD_REF"
  [[ -n "$head_version" ]] || err "plugin.json at --head ref missing .version field"
  if [[ -n "$CURRENT_VERSION" && "$CURRENT_VERSION" != "$head_version" ]]; then
    err "worktree plugin.json version ($CURRENT_VERSION) != --head ref ($head_version)"
  fi
  CURRENT_VERSION="$head_version"
fi
[[ -n "$CURRENT_VERSION" ]] || err "$PLUGIN_JSON missing .version field"
[[ "$CURRENT_VERSION" =~ ^[0-9]+\.[0-9]+\.[0-9]+$ ]] || err "version '$CURRENT_VERSION' is not semver (expected X.Y.Z)"

# Reasoning log path. Prefer the session-owned tmpdir when it is writable. If
# it is unavailable, create a unique file in TMPDIR instead of using a fixed
# fallback basename in a shared directory.
REASONING_DIR="${IMPLEMENT_TMPDIR:-}"
if [[ -n "$REASONING_DIR" ]]; then
  mkdir -p "$REASONING_DIR" 2>/dev/null || true
fi
if [[ -n "$REASONING_DIR" && -w "$REASONING_DIR" ]]; then
  REASONING_FILE="$REASONING_DIR/bump-version-reasoning.md"
else
  REASONING_DIR="${TMPDIR:-/tmp}"
  mkdir -p "$REASONING_DIR" 2>/dev/null || true
  REASONING_FILE=$(mktemp "$REASONING_DIR/bump-version-reasoning.XXXXXX") \
    || err "could not create reasoning log in $REASONING_DIR"
fi

# Helper: append to reasoning log.
log() {
  printf '%s\n' "$*" >> "$REASONING_FILE"
}

# Initialize log.
{
  echo "# Version Bump Reasoning"
  echo ""
  echo "- **Base commit**: \`$(git rev-parse --short "$BASE")\` ($(git log -1 --format=%s "$BASE" 2>/dev/null || echo '?'))"
  echo "- **Current version**: \`$CURRENT_VERSION\`"
  echo "- **Classification scope**: \`skills/**\` and \`agents/**\` only (public plugin surface)."
  echo ""
} > "$REASONING_FILE"

# Idempotency check: is HEAD itself a version-bump commit?
# The only safe way to treat a branch as "already bumped" is when the bump
# commit is HEAD, or when HEAD is followed only by transparent commits created
# by the bump/logging pipeline. If a bump exists earlier in BASE..HEAD but
# additional non-transparent commits have landed on top, a fresh bump is
# required to cover those. The subject match is anchored at ^ and $ so subjects
# like "chore: Bump version to 1.2.3" or "Revert Bump version to 1.0.0" do not
# false-match.
idempotency_commit_is_transparent() {
  local ref=$1 subject changed file
  subject=$(git log -1 --format=%s "$ref" 2>/dev/null || true)
  changed=$(git diff-tree --no-commit-id --name-only -r "$ref" 2>/dev/null || true)
  case "$subject" in
    "Update CHANGELOG for "*) ;;
    "chore(larch-logs): "*) ;;
    *) return 1 ;;
  esac
  [ -n "$changed" ] || return 1
  while IFS= read -r file; do
    [ -n "$file" ] || continue
    case "$subject" in
      "Update CHANGELOG for "*)
        [ "$file" = "CHANGELOG.md" ] || return 1
        ;;
      "chore(larch-logs): "*)
        case "$file" in larch-logs/*) ;; *) return 1 ;; esac
        ;;
    esac
  done <<< "$changed"
  return 0
}

IDEMPOTENCY_REF="$HEAD_COMPARE"
IDEMPOTENCY_DEPTH=0
while [[ "$IDEMPOTENCY_DEPTH" -lt 3 ]]; do
  git rev-parse --verify "$IDEMPOTENCY_REF" >/dev/null 2>&1 || break
  if idempotency_commit_is_transparent "$IDEMPOTENCY_REF"; then
    IDEMPOTENCY_DEPTH=$((IDEMPOTENCY_DEPTH + 1))
    IDEMPOTENCY_REF="${HEAD_COMPARE}~$IDEMPOTENCY_DEPTH"
    continue
  fi
  break
done
if [[ "$SKIP_IDEMPOTENCY" != "true" ]]; then
  HEAD_SUBJECT=$(git log -1 --format=%s "$IDEMPOTENCY_REF" 2>/dev/null || true)
  if [[ "$HEAD_SUBJECT" =~ ^Bump\ version\ to\ [0-9]+\.[0-9]+\.[0-9]+$ ]]; then
    log "## Result: NONE (already bumped)"
    log ""
    log "The idempotency HEAD after transparent CHANGELOG/larch-log commits is a version commit: \`$(git rev-parse --short "$IDEMPOTENCY_REF")\` — \"$HEAD_SUBJECT\""
    log ""
    log "No additional bump will be applied."

    echo "CURRENT_VERSION=$CURRENT_VERSION"
    echo "NEW_VERSION=$CURRENT_VERSION"
    echo "BUMP_TYPE=NONE"
    echo "REASONING_FILE=$REASONING_FILE"
    exit 0
  fi
fi

# Collect file-level changes in public surface.
# Use -M for rename detection.
NAME_STATUS=$(git diff -M --name-status "$BASE" "$HEAD_COMPARE" -- skills agents 2>/dev/null || true)

# Track evidence.
MAJOR_REASONS=()
MINOR_REASONS=()

# Process file-level changes.
while IFS=$'\t' read -r status old new_or_blank; do
  [[ -z "${status:-}" ]] && continue

  case "$status" in
    D)
      # Deleted file in public surface.
      if [[ "$old" == skills/*/SKILL.md || "$old" == agents/*.md ]]; then
        MAJOR_REASONS+=("Deleted \`$old\`")
      fi
      ;;
    A)
      # Added file in public surface.
      if [[ "$old" == skills/*/SKILL.md || "$old" == agents/*.md ]]; then
        MINOR_REASONS+=("Added \`$old\`")
      fi
      ;;
    R*)
      # Renamed file: $old is source, $new_or_blank is destination.
      if [[ "$old" == skills/*/SKILL.md ]]; then
        MAJOR_REASONS+=("Renamed skill \`$old\` → \`$new_or_blank\`")
      elif [[ "$old" == agents/*.md ]]; then
        MAJOR_REASONS+=("Renamed agent \`$old\` → \`$new_or_blank\`")
      fi
      ;;
    M)
      # Modified file — inspect full file content (not diff text) for flag/name
      # changes. Reading the full old and new file contents lets us scope
      # extraction to the YAML frontmatter block and compute flag-token sets
      # so wording-only edits to a flag bullet do not trigger MAJOR.
      if [[ "$old" == skills/*/SKILL.md || "$old" == agents/*.md ]]; then
        OLD_FILE=$(git show "$BASE:$old" 2>/dev/null || true)
        NEW_FILE=$(git show "${HEAD_COMPARE}:${old}" 2>/dev/null || true)

        # Extract the first YAML frontmatter block (between two `---` lines at
        # column 0). Returns empty if no frontmatter, or if the opening `---`
        # exists but no matching closing `---` is found — in that case we must
        # NOT treat the body as frontmatter. The buffer approach defers printing
        # until the closing delimiter is confirmed.
        extract_frontmatter() {
          awk '
            BEGIN { state=0; n=0 }
            state==0 && /^---$/ { state=1; next }
            state==1 && /^---$/ {
              for (i=1; i<=n; i++) print buf[i]
              exit
            }
            state==1 { buf[++n]=$0 }
          '
        }

        # Use herestring instead of `printf | awk` because awk's `exit` on the
        # closing `---` line causes SIGPIPE back to `printf` for large files;
        # with `set -euo pipefail` the whole script would abort with exit 141.
        # Herestrings don't create an intermediate pipe sensitive to SIGPIPE.
        OLD_FRONTMATTER=$(extract_frontmatter <<< "$OLD_FILE")
        NEW_FRONTMATTER=$(extract_frontmatter <<< "$NEW_FILE")

        # name: frontmatter field (scoped to frontmatter block only).
        OLD_NAME=$(printf '%s\n' "$OLD_FRONTMATTER" | awk '/^name: / { sub(/^name: */, ""); print; exit }')
        NEW_NAME=$(printf '%s\n' "$NEW_FRONTMATTER" | awk '/^name: / { sub(/^name: */, ""); print; exit }')
        if [[ -n "$OLD_NAME" && -z "$NEW_NAME" ]]; then
          MAJOR_REASONS+=("Removed \`name:\` frontmatter from \`$old\`")
        elif [[ -n "$OLD_NAME" && -n "$NEW_NAME" && "$OLD_NAME" != "$NEW_NAME" ]]; then
          MAJOR_REASONS+=("Renamed \`name:\` frontmatter in \`$old\` ($OLD_NAME → $NEW_NAME)")
        fi

        # argument-hint: frontmatter field — compare flag token SETS.
        # Token cancellation: a token present in both old and new is an edit
        # or a description change, not a removal/addition.
        OLD_ARG_HINT=$(printf '%s\n' "$OLD_FRONTMATTER" | awk '/^argument-hint: / { sub(/^argument-hint: */, ""); print; exit }')
        NEW_ARG_HINT=$(printf '%s\n' "$NEW_FRONTMATTER" | awk '/^argument-hint: / { sub(/^argument-hint: */, ""); print; exit }')
        if [[ -n "$OLD_ARG_HINT" || -n "$NEW_ARG_HINT" ]]; then
          OLD_AH_TOKENS=$(printf '%s\n' "$OLD_ARG_HINT" | grep -oE '\-\-[a-zA-Z0-9_-]+' | sort -u || true)
          NEW_AH_TOKENS=$(printf '%s\n' "$NEW_ARG_HINT" | grep -oE '\-\-[a-zA-Z0-9_-]+' | sort -u || true)
          # Emit tokens one-per-line if non-empty, or nothing at all if empty,
          # so comm never receives a spurious blank line that would otherwise
          # round-trip through the token-diff and trigger an empty loop
          # iteration (see round-2 review).
          _emit_tokens() {
            if [[ -n "$1" ]]; then printf '%s\n' "$1"; fi
          }
          REMOVED_TOKENS=$(comm -23 <(_emit_tokens "$OLD_AH_TOKENS") <(_emit_tokens "$NEW_AH_TOKENS") 2>/dev/null || true)
          ADDED_TOKENS=$(comm -13 <(_emit_tokens "$OLD_AH_TOKENS") <(_emit_tokens "$NEW_AH_TOKENS") 2>/dev/null || true)
          if [[ -n "$REMOVED_TOKENS" ]]; then
            while IFS= read -r tok; do
              [[ -n "$tok" ]] && MAJOR_REASONS+=("Removed \`$tok\` from argument-hint in \`$old\`")
            done <<< "$REMOVED_TOKENS"
          fi
          if [[ -n "$ADDED_TOKENS" ]]; then
            while IFS= read -r tok; do
              [[ -n "$tok" ]] && MINOR_REASONS+=("Added \`$tok\` to argument-hint in \`$old\`")
            done <<< "$ADDED_TOKENS"
          fi
        fi
      fi
      ;;
  esac
done <<< "$NAME_STATUS"

# Determine bump type.
if [[ ${#MAJOR_REASONS[@]} -gt 0 ]]; then
  BUMP_TYPE="MAJOR"
elif [[ ${#MINOR_REASONS[@]} -gt 0 ]]; then
  BUMP_TYPE="MINOR"
else
  BUMP_TYPE="PATCH"
fi

# Compute new version.
IFS='.' read -r MAJ MIN PAT <<< "$CURRENT_VERSION"
case "$BUMP_TYPE" in
  MAJOR) NEW_VERSION="$((10#${MAJ} + 1)).0.0" ;;
  MINOR) NEW_VERSION="${MAJ}.$((10#${MIN} + 1)).0" ;;
  PATCH) NEW_VERSION="${MAJ}.${MIN}.$((10#${PAT} + 1))" ;;
esac

# Log reasoning.
log "## Result: $BUMP_TYPE"
log ""
log "- **New version**: \`$NEW_VERSION\`"
log ""

if [[ ${#MAJOR_REASONS[@]} -gt 0 ]]; then
  log "### MAJOR evidence"
  for r in "${MAJOR_REASONS[@]}"; do log "- $r"; done
fi

if [[ ${#MINOR_REASONS[@]} -gt 0 ]]; then
  log "### MINOR evidence"
  for r in "${MINOR_REASONS[@]}"; do log "- $r"; done
fi

if [[ "$BUMP_TYPE" == "PATCH" ]]; then
  log "### PATCH rationale"
  log ""
  log "No MAJOR or MINOR evidence found in the public plugin surface. Defaulting to PATCH for this release classification."
fi

# Emit machine-parseable output.
echo "CURRENT_VERSION=$CURRENT_VERSION"
echo "NEW_VERSION=$NEW_VERSION"
echo "BUMP_TYPE=$BUMP_TYPE"
echo "REASONING_FILE=$REASONING_FILE"
