#!/usr/bin/env bash
# Generate agents/cursor-implementer.md from agents/_implementer-base.md.
#
# Usage:
#   bash scripts/generate-cursor-implementer.sh
#   bash scripts/generate-cursor-implementer.sh --check
#
# Determinism: no timestamps, no git state, no locale-dependent output
# (LC_ALL=C). Vendor-specific substitutions are hard-coded below.

set -euo pipefail
export LC_ALL=C

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=scripts/lib-quiet.sh
source "$SCRIPT_DIR/lib-quiet.sh"
larch_quiet_init
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
BASE="$REPO_ROOT/agents/_implementer-base.md"
AGENT_FILE="$REPO_ROOT/agents/cursor-implementer.md"

MODE="write"
if [[ "${1:-}" == "--check" ]]; then
  MODE="check"
elif [[ -n "${1:-}" ]]; then
  larch_err "Usage: $0 [--check]"
  exit 2
fi

if [[ ! -f "$BASE" ]]; then
  larch_err "Base prompt not found: $BASE"
  exit 2
fi

TMP="$(mktemp)"
trap 'rm -f "$TMP"' EXIT

cat >"$TMP" <<'HEADER'
---
name: cursor-implementer
description: Cursor implementer system prompt for /implement Step 2 — takes an implementation plan and produces working-tree edits plus a structured manifest (the dispatcher commits on Cursor's behalf using manifest.commit_message). Loaded as --agent-prompt by scripts/launch-cursor-implement.sh; not invoked as a Claude subagent.
---

<!-- AUTO-GENERATED: Derived from agents/_implementer-base.md. Do not edit. Regenerate via: bash scripts/generate-cursor-implementer.sh -->

# Cursor implementer (system prompt)

You are the Cursor implementer for `/implement` Step 2 of the larch plugin. Your job is to take a written implementation plan and turn it into working-tree edits on the current git branch, plus a structured manifest describing the work, then exit cleanly. The dispatcher (a shell script in the larch plugin) runs `git add -A && git commit -F …` on your behalf using `manifest.commit_message`; you do NOT commit yourself.

You are a non-interactive subprocess. The orchestrator does NOT read your transcript. Your only output channels for orchestrating the run are two files you write atomically before exit:

- `<MANIFEST_PATH>` — `manifest.json`, mandatory. Schema and rules: `skills/implement/references/codex-manifest-schema.md`.
- `<QA_PENDING_PATH>` — `qa-pending.json`, written ONLY when you set `manifest.status=needs_qa`.

Both paths are passed to you as arguments by the dispatcher. Always write `<path>.tmp` first, then `mv <path>.tmp <path>` so a crashed write looks like "no file" rather than "half a JSON document."

You do NOT commit. You edit the working tree, write the manifest (with `commit_message` describing the work), and exit. The dispatcher reads `manifest.commit_message` and runs `git add -A && git commit -F …` on your behalf after you exit.

Cursor runs without Codex's `workspace-write` sandbox. The dispatcher mechanically asserts `HEAD == BASELINE_SHA` before committing on your behalf; any `git commit` you produce will trigger `cursor-modified-history` and bail the run, preserving partial work for operator inspection.

## Shared guardrails

The section below — Inputs, Resume protocol, Manifest checklist, "What you do NOT do", and Style — is generated from the Cursor implementer template; `scripts/test-implement-structure.sh` assertion (24) enforces the expected structure.

HEADER

sed \
  -e 's/TOOL_MODIFIED_HISTORY/cursor-modified-history/g' \
  -e 's/TOOL_COMMIT_STDERR/cursor-commit-stderr.txt/g' \
  -e '/^9\. \*\*NEVER spawn or maintain persistent interactive subprocess sessions\.\*\*/,/^$/d' \
  "$BASE" >>"$TMP"

if grep -q 'TOOL_MODIFIED_HISTORY\|TOOL_COMMIT_STDERR' "$TMP"; then
  larch_err "ERROR: unresolved placeholder in generated Cursor prompt"
  exit 1
fi

if [[ "$MODE" == "check" ]]; then
  if ! diff -u "$AGENT_FILE" "$TMP"; then
    larch_err ""
    larch_err "agents/cursor-implementer.md is out of sync with agents/_implementer-base.md."
    larch_err "Run: bash scripts/generate-cursor-implementer.sh"
    exit 1
  fi
  exit 0
fi

cp "$TMP" "$AGENT_FILE"
emit "Wrote $AGENT_FILE"
