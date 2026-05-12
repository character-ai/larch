#!/usr/bin/env bash
# Generate agents/reviewer-plan-fidelity.md from the canonical archetype in
# skills/shared/reviewer-templates.md. The generated file is not hand-edited;
# CI enforces that the committed agent file matches generator output.
#
# Usage:
#   bash scripts/generate-reviewer-plan-fidelity-agent.sh
#   bash scripts/generate-reviewer-plan-fidelity-agent.sh --check
#
# Determinism: no timestamps, no git state, no locale-dependent output
# (LC_ALL=C). The YAML frontmatter and preamble comment are hard-coded below.

set -euo pipefail
export LC_ALL=C

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
TEMPLATE="$REPO_ROOT/skills/shared/reviewer-templates.md"
AGENT_FILE="$REPO_ROOT/agents/reviewer-plan-fidelity.md"
SECTION_HEADING="## Reviewer: Plan Fidelity"

MODE="write"
if [[ "${1:-}" == "--check" ]]; then
  MODE="check"
elif [[ -n "${1:-}" ]]; then
  echo "Usage: $0 [--check]" >&2
  exit 2
fi

if [[ ! -f "$TEMPLATE" ]]; then
  echo "Template not found: $TEMPLATE" >&2
  exit 2
fi

TMP="$(mktemp)"
trap 'rm -f "$TMP"' EXIT

cat >"$TMP" <<'HEADER'
---
name: reviewer-plan-fidelity
description: "Specialist code reviewer concentrating on plan fidelity: plan-to-implementation traceability, completeness against design requirements, correctness against stated intent, stale replacement surfaces, generated artifact coverage, and explicit loud failure when the design plan is missing."
model: sonnet
tools:
  - Read
  - Grep
  - Glob
---

<!-- AUTO-GENERATED: Derived from skills/shared/reviewer-templates.md. Do not edit. Regenerate via: bash scripts/generate-reviewer-plan-fidelity-agent.sh -->

HEADER

awk -v heading="$SECTION_HEADING" '
  $0 == heading { in_section = 1; next }
  found { next }
  in_section && /<!-- BEGIN GENERATED_BODY -->/ { in_body = 1; skipped_open = 0; next }
  in_body && /<!-- END GENERATED_BODY -->/   { in_body = 0; in_section = 0; found = 1; next }
  in_body {
    if (!skipped_open) { skipped_open = 1; next }
    buf[bn++] = $0
  }
  END {
    if (!found || bn == 0) {
      print "ERROR: no content found for " heading " between BEGIN/END GENERATED_BODY markers" > "/dev/stderr"
      exit 1
    }
    if (buf[bn-1] != "```") {
      print "ERROR: expected outer close fence ``` as last line inside GENERATED_BODY markers; got: " buf[bn-1] > "/dev/stderr"
      exit 1
    }
    bn--
    for (i = 0; i < bn; i++) print buf[i]
  }
' "$TEMPLATE" >>"$TMP"

if [[ "$MODE" == "check" ]]; then
  if ! diff -u "$AGENT_FILE" "$TMP"; then
    echo "" >&2
    echo "agents/reviewer-plan-fidelity.md is out of sync with skills/shared/reviewer-templates.md." >&2
    echo "Run: bash scripts/generate-reviewer-plan-fidelity-agent.sh" >&2
    exit 1
  fi
  exit 0
fi

cp "$TMP" "$AGENT_FILE"
echo "Wrote $AGENT_FILE"
