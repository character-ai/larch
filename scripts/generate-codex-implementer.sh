#!/usr/bin/env bash
# Generate agents/codex-implementer.md from agents/_implementer-base.md.
#
# Usage:
#   bash scripts/generate-codex-implementer.sh
#   bash scripts/generate-codex-implementer.sh --check
#
# Determinism: no timestamps, no git state, no locale-dependent output
# (LC_ALL=C). Codex-specific substitutions are hard-coded below.

set -euo pipefail
export LC_ALL=C

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
BASE="$REPO_ROOT/agents/_implementer-base.md"
AGENT_FILE="$REPO_ROOT/agents/codex-implementer.md"

MODE="write"
if [[ "${1:-}" == "--check" ]]; then
  MODE="check"
elif [[ -n "${1:-}" ]]; then
  echo "Usage: $0 [--check]" >&2
  exit 2
fi

if [[ ! -f "$BASE" ]]; then
  echo "Base prompt not found: $BASE" >&2
  exit 2
fi

TMP="$(mktemp)"
trap 'rm -f "$TMP"' EXIT

cat >"$TMP" <<'HEADER'
---
name: codex-implementer
description: Codex implementer system prompt for /implement Step 2 — takes an implementation plan and produces working-tree edits plus a structured manifest (the dispatcher commits on Codex's behalf using manifest.commit_message). Loaded as --agent-prompt by scripts/launch-codex-implement.sh; not invoked as a Claude subagent.
---

<!-- AUTO-GENERATED: Derived from agents/_implementer-base.md. Do not edit. Regenerate via: bash scripts/generate-codex-implementer.sh -->

# Codex implementer (system prompt)

You are the Codex implementer for `/implement` Step 2 of the larch plugin. Your job is to take a written implementation plan and turn it into working-tree edits on the current git branch, plus a structured manifest describing the work, then exit cleanly. The dispatcher (a shell script in the larch plugin) runs `git add -A && git commit -F …` on your behalf using `manifest.commit_message`; you do NOT commit yourself.

You are a non-interactive subprocess. The orchestrator does NOT read your transcript. Your only output channels for orchestrating the run are two files you write atomically before exit:

- `<MANIFEST_PATH>` — `manifest.json`, mandatory. Schema and rules: `skills/implement/references/codex-manifest-schema.md`.
- `<QA_PENDING_PATH>` — `qa-pending.json`, written ONLY when you set `manifest.status=needs_qa`.

Both paths are passed to you as arguments by the dispatcher. Always write `<path>.tmp` first, then `mv <path>.tmp <path>` so a crashed write looks like "no file" rather than "half a JSON document."

You do NOT commit. You edit the working tree, write the manifest (with `commit_message` describing the work), and exit. The dispatcher reads `manifest.commit_message` and runs `git add -A && git commit -F …` on your behalf after you exit. This keeps you inside `workspace-write` sandbox semantics (which forbids `.git/` writes).

HEADER

# shellcheck disable=SC2016 # Literal markdown backticks/placeholders in sed expressions.
sed \
  -e 's/TOOL_COMMIT_STDERR/codex-commit-stderr.txt/g' \
  -e 's/^2\. \*\*NEVER `git add`.*$/2. **NEVER `git add` or `git commit`.** Committing is the dispatcher'"'"'s job. Your output is the working-tree edits plus `manifest.json`. Running `git add` or `git commit` from `workspace-write` sandbox will fail with `Operation not permitted` on `.git\/index.lock` anyway, so just do not try./' \
  -e 's/\. `TOOL_MODIFIED_HISTORY` is dispatcher-emitted only; do not emit it yourself\.$/./' \
  "$BASE" >>"$TMP"

if grep -q 'TOOL_MODIFIED_HISTORY' "$TMP"; then
  echo "ERROR: unresolved TOOL_MODIFIED_HISTORY placeholder in generated Codex prompt" >&2
  exit 1
fi

if [[ "$MODE" == "check" ]]; then
  if ! diff -u "$AGENT_FILE" "$TMP"; then
    echo "" >&2
    echo "agents/codex-implementer.md is out of sync with agents/_implementer-base.md." >&2
    echo "Run: bash scripts/generate-codex-implementer.sh" >&2
    exit 1
  fi
  exit 0
fi

cp "$TMP" "$AGENT_FILE"
echo "Wrote $AGENT_FILE"
