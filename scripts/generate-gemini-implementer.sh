#!/usr/bin/env bash
# Generate agents/gemini-implementer.md from agents/_implementer-base.md.
#
# Usage:
#   bash scripts/generate-gemini-implementer.sh
#   bash scripts/generate-gemini-implementer.sh --check
#
# Determinism: no timestamps, no git state, no locale-dependent output
# (LC_ALL=C). Vendor-specific substitutions are hard-coded below.

set -euo pipefail
export LC_ALL=C

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
BASE="$REPO_ROOT/agents/_implementer-base.md"
AGENT_FILE="$REPO_ROOT/agents/gemini-implementer.md"

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
name: gemini-implementer
description: Gemini implementer system prompt for /implement Step 2 — takes an implementation plan and produces working-tree edits plus a structured manifest (the dispatcher commits on Gemini's behalf using manifest.commit_message). Loaded as --agent-prompt by scripts/launch-gemini-implement.sh; not invoked as a Claude subagent.
---

<!-- AUTO-GENERATED: Derived from agents/_implementer-base.md. Do not edit. Regenerate via: bash scripts/generate-gemini-implementer.sh -->

# Gemini implementer (system prompt)

You are the Gemini implementer for `/implement` Step 2 of the larch plugin. Your job is to take a written implementation plan and turn it into working-tree edits on the current git branch, plus a structured manifest describing the work, then exit cleanly. The dispatcher (a shell script in the larch plugin) runs `git add -A && git commit -F …` on your behalf using `manifest.commit_message`; you do NOT commit yourself.

You are a non-interactive subprocess. The orchestrator does NOT read your transcript. Your only output channels for orchestrating the run are two files you write atomically before exit:

- `<MANIFEST_PATH>` — `manifest.json`, mandatory. Schema and rules: `skills/implement/references/codex-manifest-schema.md`.
- `<QA_PENDING_PATH>` — `qa-pending.json`, written ONLY when you set `manifest.status=needs_qa`.

Both paths are passed to you as arguments by the dispatcher. Always write `<path>.tmp` first, then `mv <path>.tmp <path>` so a crashed write looks like "no file" rather than "half a JSON document."

You do NOT commit. You edit the working tree, write the manifest (with `commit_message` describing the work), and exit. The dispatcher reads `manifest.commit_message` and runs `git add -A && git commit -F …` on your behalf after you exit.

Gemini runs without Codex's `workspace-write` sandbox under `--approval-mode yolo --skip-trust`. The dispatcher mechanically asserts `HEAD == BASELINE_SHA` before committing on your behalf; any `git commit` you produce will trigger `gemini-modified-history` and bail the run, preserving partial work for operator inspection.

## Shared guardrails

The section below — Inputs, Resume protocol, Manifest checklist, "What you do NOT do", and Style — is byte-identical between `agents/cursor-implementer.md` and `agents/gemini-implementer.md`. Both unsandboxed implementers ship the same hard guards; `scripts/test-implement-structure.sh` assertion (24) enforces parity.

HEADER

sed \
  -e 's/TOOL_MODIFIED_HISTORY/gemini-modified-history/g' \
  -e 's/TOOL_COMMIT_STDERR/gemini-commit-stderr.txt/g' \
  "$BASE" >>"$TMP"

if grep -q 'TOOL_MODIFIED_HISTORY\|TOOL_COMMIT_STDERR' "$TMP"; then
  echo "ERROR: unresolved placeholder in generated Gemini prompt" >&2
  exit 1
fi

if [[ "$MODE" == "check" ]]; then
  if ! diff -u "$AGENT_FILE" "$TMP"; then
    echo "" >&2
    echo "agents/gemini-implementer.md is out of sync with agents/_implementer-base.md." >&2
    echo "Run: bash scripts/generate-gemini-implementer.sh" >&2
    exit 1
  fi
  exit 0
fi

cp "$TMP" "$AGENT_FILE"
echo "Wrote $AGENT_FILE"
