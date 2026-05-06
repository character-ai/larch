#!/usr/bin/env bash
# Generate docs/topology.md from skills/shared/topology.tsv.

set -euo pipefail
export LC_ALL=C

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
TOPOLOGY_TSV="${LARCH_TOPOLOGY_TSV:-$REPO_ROOT/skills/shared/topology.tsv}"
TOPOLOGY_DOC="${LARCH_TOPOLOGY_DOC:-$REPO_ROOT/docs/topology.md}"

MODE="write"
if [[ "${1:-}" == "--check" ]]; then
  MODE="check"
elif [[ -n "${1:-}" ]]; then
  echo "Usage: $0 [--check]" >&2
  exit 2
fi

fail() {
  echo "generate-topology-docs: $*" >&2
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

anchor_for_key() {
  printf '%s' "$1" | tr '._' '--'
}

[[ -f "$TOPOLOGY_TSV" ]] || fail "topology TSV not found: $TOPOLOGY_TSV"

TMP="$(mktemp)"
ROWS_TMP="$(mktemp)"
trap 'rm -f "$TMP" "$ROWS_TMP"' EXIT

cd "$REPO_ROOT"

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

  [[ -f "$runtime_authority" ]] || fail "row $row: runtime_authority not found: $runtime_authority"
  git ls-files --error-unmatch -- "$runtime_authority" >/dev/null 2>&1 || fail "row $row: runtime_authority is not tracked by git: $runtime_authority"
  grep -Fq -- "$value" "$runtime_authority" || fail "row $row: value '$value' not found in runtime_authority: $runtime_authority"

  anchor="$(anchor_for_key "$key")"
  printf '%s\t%s\t%s\t%s\t%s\n' "$anchor" "$key" "$value" "$composition" "$runtime_authority" >>"$ROWS_TMP"
done < <(
  awk -F '\t' '
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
  ' "$TOPOLOGY_TSV"
)

cat >"$TMP" <<'HEADER'
# Topology Projection

<!-- AUTO-GENERATED: Derived from skills/shared/topology.tsv. Do not edit. Regenerate via: bash scripts/generate-topology-docs.sh -->

This document is a consumer-doc projection of runtime authorities. The runtime authority listed for each row remains the source of truth; the projection exists so consumer docs can link to stable row anchors instead of repeating drift-prone counts.

Quick-mode `/implement` reviewer-loop phrases such as `7 rounds`, `rounds 1-3`, `5 Cursor specialists`, and `generic Codex` are intentionally excluded. They are byte-pinned by `scripts/test-quick-mode-docs-sync.sh` and remain owned by that harness's edit-in-sync rule.

| Key | Value | Composition | Runtime Authority |
|---|---:|---|---|
HEADER

while IFS=$'\t' read -r anchor key value composition runtime_authority; do
  # shellcheck disable=SC2016
  printf '| <a id="%s"></a>`%s` | %s | %s | `%s` |\n' \
    "$anchor" "$key" "$value" "${composition:- }" "$runtime_authority" >>"$TMP"
done <"$ROWS_TMP"

if [[ "$MODE" == "check" ]]; then
  if ! diff -u "$TOPOLOGY_DOC" "$TMP"; then
    echo "" >&2
    echo "docs/topology.md is out of sync with skills/shared/topology.tsv." >&2
    echo "Run: bash scripts/generate-topology-docs.sh" >&2
    exit 1
  fi
  exit 0
fi

mkdir -p "$(dirname "$TOPOLOGY_DOC")"
cp "$TMP" "$TOPOLOGY_DOC"
echo "Wrote $TOPOLOGY_DOC"
