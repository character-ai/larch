#!/usr/bin/env bash
# Generate docs/topology.md from skills/shared/topology.tsv.

set -euo pipefail
export LC_ALL=C

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=scripts/lib-quiet.sh
source "$SCRIPT_DIR/lib-quiet.sh"
larch_quiet_init
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
# LARCH_TOPOLOGY_TSV and LARCH_TOPOLOGY_DOC are dev/CI overrides used by
# scripts/test-generate-topology-docs.sh. They are trusted-only — operators must not pass
# untrusted values. The `--check` mode is the only public surface and uses the in-repo
# defaults; if you need to extend the schema to accept untrusted overrides, gate them
# behind an explicit repo-root prefix check (see `require_within_repo_root` git history
# for a prior implementation that proved too strict for the harness's mktemp paths).
TOPOLOGY_TSV="${LARCH_TOPOLOGY_TSV:-$REPO_ROOT/skills/shared/topology.tsv}"
TOPOLOGY_DOC="${LARCH_TOPOLOGY_DOC:-$REPO_ROOT/docs/topology.md}"

MODE="write"
if [[ "${1:-}" == "--check" ]]; then
  MODE="check"
elif [[ -n "${1:-}" ]]; then
  larch_err "Usage: $0 [--check]"
  exit 2
fi

fail() {
  larch_err "generate-topology-docs: $*"
  exit 1
}

path_has_segment() {
  local path="$1"
  local segment="$2"
  [[ "$path" == "$segment" || "$path" == "$segment/"* || "$path" == */"$segment" || "$path" == */"$segment"/* ]]
}

validate_repo_path() {
  local row="$1"
  local path="$2"

  [[ -n "$path" ]] || fail "row $row: empty runtime_authority"
  [[ "$path" != /* ]] || fail "row $row: runtime_authority must be repo-relative: $path"
  [[ "$path" != ./* ]] || fail "row $row: runtime_authority must not start with ./ : $path"
  [[ "$path" != -* ]] || fail "row $row: runtime_authority must not start with -: $path"
  [[ "$path" != :* ]] || fail "row $row: runtime_authority must not start with : (reserved for git pathspec magic): $path"
  [[ "$path" != *"//"* ]] || fail "row $row: runtime_authority must not contain duplicate slash: $path"
  [[ "$path" != *$'\t'* ]] || fail "row $row: runtime_authority must not contain tabs"
  [[ "$path" != *$'\n'* ]] || fail "row $row: runtime_authority must not contain newlines"
  if path_has_segment "$path" ".."; then
    fail "row $row: runtime_authority must not contain parent traversal: $path"
  fi
  if path_has_segment "$path" "."; then
    fail "row $row: runtime_authority must not contain . path segments: $path"
  fi
}

validate_key() {
  local row="$1"
  local key="$2"

  [[ -n "$key" ]] || fail "row $row: empty key"
  [[ "$key" != *:* ]] || fail "row $row: key must not contain colon: $key"
  [[ "$key" =~ ^[a-z0-9_.]+$ ]] || fail "row $row: key must match [a-z0-9_.]+: $key"
}

validate_display_text() {
  local row="$1"
  local label="$2"
  local text="$3"
  local allow_empty="$4"

  if [[ -z "$text" ]]; then
    [[ "$allow_empty" == "yes" ]] && return 0
    fail "row $row: empty $label"
  fi
  case "$text" in
    *$'\t'*|*$'\n'*)
      fail "row $row: $label contains a tab or newline"
      ;;
    *"<"*|*">"*|*"["*|*"]"*|*'`'*)
      fail "row $row: $label contains a forbidden character or marker"
      ;;
  esac
  case "$text" in
    *[!A-Za-z0-9\ ./+-]*)
      fail "row $row: $label contains characters outside [A-Za-z0-9 ./+-]: $text"
      ;;
  esac
}

# Anchor derivation MUST be injective so two distinct keys never collide on the same
# `<a id="...">` fragment. We use the key verbatim (HTML5 allows `.` and `_` in id
# attributes per the URL fragment grammar). This is trivially injective because the
# key grammar `[a-z0-9_.]+` is preserved byte-for-byte. The duplicate-anchor check
# below is defense-in-depth: any future change to either the key grammar or this
# function that breaks injectivity will be caught at generate time.
anchor_for_key() {
  printf '%s' "$1"
}

[[ -f "$TOPOLOGY_TSV" ]] || fail "topology TSV not found: $TOPOLOGY_TSV"

TMP="$(mktemp)"
ROWS_TMP="$(mktemp)"
ENCODED_TMP="$(mktemp)"
ENCODED_ERR="$(mktemp)"
trap 'rm -f "$TMP" "$ROWS_TMP" "$ENCODED_TMP" "$ENCODED_ERR"' EXIT

cd "$REPO_ROOT"

# Bash 3.2-compatible dedup: track seen keys and anchors as newline-delimited
# strings (cheap, deterministic). Each entry is `<row>|<value>` so duplicate
# diagnostics can name both rows.
SEEN_KEYS=""
SEEN_ANCHORS=""

if ! awk -F '\t' '
    {
      if ($0 ~ /\r$/) {
        printf("generate-topology-docs: row %d: CRLF line endings not allowed\n", NR) > "/dev/stderr"
        exit 1
      }
      if ($0 == "" || substr($0, 1, 1) == "#") next
      if (NF != 4 || $1 == "" || $2 == "" || $4 == "") {
        printf("generate-topology-docs: row %d: malformed row; expected exactly four tab-separated columns with key, value, and runtime_authority non-empty\n", NR) > "/dev/stderr"
        exit 1
      }
      printf("%d\034%s\034%s\034%s\034%s\n", NR, $1, $2, $3, $4)
    }
  ' "$TOPOLOGY_TSV" > "$ENCODED_TMP" 2> "$ENCODED_ERR"; then
  while IFS= read -r line; do
    [[ -n "$line" ]] && larch_err "$line"
  done < "$ENCODED_ERR"
  exit 1
fi

while IFS= read -r encoded; do
  row="${encoded%%$'\034'*}"
  rest="${encoded#*$'\034'}"
  key="${rest%%$'\034'*}"
  rest="${rest#*$'\034'}"
  value="${rest%%$'\034'*}"
  rest="${rest#*$'\034'}"
  composition="${rest%%$'\034'*}"
  runtime_authority="${rest#*$'\034'}"

  validate_key "$row" "$key"
  validate_display_text "$row" "value" "$value" "no"
  validate_display_text "$row" "composition" "$composition" "yes"
  validate_repo_path "$row" "$runtime_authority"

  # Reject bare-numeric or otherwise too-short values so substring grep validation
  # against the runtime authority cannot be silently satisfied by an unrelated digit
  # (e.g. value `2` matching `Step 2a` or `2-agent`). A non-digit anchor is required
  # for any value <= 3 chars or composed solely of digits.
  if [[ "$value" =~ ^[0-9]+$ ]] || (( ${#value} < 3 )); then
    fail "row $row: value '$value' is too short or purely numeric — use a longer anchor phrase that uniquely identifies the topology fact in the runtime authority (e.g. '4 regular' instead of '4')"
  fi

  prior_key_row="$(printf '%s\n' "$SEEN_KEYS" | awk -F'|' -v k="$key" '$2 == k { print $1; exit }')"
  if [[ -n "$prior_key_row" ]]; then
    fail "row $row: duplicate key '$key' (also defined on row $prior_key_row)"
  fi
  SEEN_KEYS="${SEEN_KEYS}${row}|${key}"$'\n'

  anchor="$(anchor_for_key "$key")"
  prior_anchor_entry="$(printf '%s\n' "$SEEN_ANCHORS" | awk -F'|' -v a="$anchor" '$2 == a { print $1 "|" $3; exit }')"
  if [[ -n "$prior_anchor_entry" ]]; then
    prior_anchor_row="${prior_anchor_entry%%|*}"
    prior_anchor_key="${prior_anchor_entry##*|}"
    fail "row $row: derived anchor '$anchor' collides with key '$prior_anchor_key' on row $prior_anchor_row"
  fi
  SEEN_ANCHORS="${SEEN_ANCHORS}${row}|${anchor}|${key}"$'\n'

  [[ -f "$runtime_authority" ]] || fail "row $row: runtime_authority not found: $runtime_authority"
  git ls-files --error-unmatch -- "$runtime_authority" >/dev/null 2>&1 || fail "row $row: runtime_authority is not tracked by git: $runtime_authority"
  grep -Fq -- "$value" "$runtime_authority" || fail "row $row: value '$value' not found in runtime_authority: $runtime_authority"

  # Use ASCII record-separator (\035) inside the rendered intermediate so empty
  # `composition` columns survive the read-back step. IFS=$'\t' would collapse adjacent
  # tabs as IFS-whitespace, shifting `runtime_authority` into `composition`.
  printf '%s\035%s\035%s\035%s\035%s\n' "$anchor" "$key" "$value" "$composition" "$runtime_authority" >>"$ROWS_TMP"
done < "$ENCODED_TMP"

cat >"$TMP" <<'HEADER'
# Topology Projection

<!-- AUTO-GENERATED: Derived from skills/shared/topology.tsv. Do not edit. Regenerate via: bash scripts/generate-topology-docs.sh -->

This document is a consumer-doc projection of runtime authorities. The runtime authority listed for each row remains the source of truth; the projection exists so consumer docs can link to stable row anchors instead of repeating drift-prone counts.

`/implement` Step 5 phrases pinned by `scripts/test-quick-mode-docs-sync.sh` (for example `5 rounds`, `--panel hard`, `3-judge panel on round 1`, and `6 Cursor specialists`) are intentionally excluded from this projection. They remain owned by that harness's edit-in-sync rule.

| Key | Value | Composition | Runtime Authority |
|---|---:|---|---|
HEADER

while IFS=$'\035' read -r anchor key value composition runtime_authority; do
  # shellcheck disable=SC2016
  printf '| <a id="%s"></a>`%s` | %s | %s | `%s` |\n' \
    "$anchor" "$key" "$value" "${composition:- }" "$runtime_authority" >>"$TMP"
done <"$ROWS_TMP"

if [[ "$MODE" == "check" ]]; then
  if ! diff -u "$TOPOLOGY_DOC" "$TMP"; then
    larch_err ""
    larch_err "docs/topology.md is out of sync with skills/shared/topology.tsv."
    larch_err "Run: bash scripts/generate-topology-docs.sh"
    exit 1
  fi
  exit 0
fi

mkdir -p "$(dirname "$TOPOLOGY_DOC")"
cp "$TMP" "$TOPOLOGY_DOC"
emit "Wrote $TOPOLOGY_DOC"
