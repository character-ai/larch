#!/usr/bin/env bash
# parse-args.sh — Parse /create-skill arguments.
#
# Flags (stop at first non-flag token):
#   --plugin      Write to skills/<name>/ with ${CLAUDE_PLUGIN_ROOT} path token.
#                 Default: .claude/skills/<name>/ with $PWD path token.
#   --multi-step  Emit the multi-step scaffold.
#                 Default: minimal single-step scaffold.
#   --merge       Accepted for backward compatibility. /create-skill delegates via /im
#                 (which prepends --merge), so this flag is redundant and is NOT forwarded
#                 to the child skill. Kept in the parser to avoid breaking existing
#                 invocations that pass it explicitly.
# Positional (after flags):
#   <skill-name>  First positional. Leading '/' is stripped.
#   <description> Remainder of the argument string, verbatim.
#
# Output (stdout, key=value lines):
#   NAME=<name>
#   DESCRIPTION=<description>
#   PLUGIN=true|false
#   MULTI_STEP=true|false
#   MERGE=true|false
#
# On failure, emits `ERROR=<msg>` to stdout and exits non-zero.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)"
PLUGIN_ROOT="${CLAUDE_PLUGIN_ROOT:-$(cd "$SCRIPT_DIR/../../.." && pwd -P)}"
# shellcheck source=scripts/lib-quiet.sh
source "$PLUGIN_ROOT/scripts/lib-quiet.sh"
larch_quiet_init

PLUGIN=false
MULTI_STEP=false
MERGE=false

while [[ $# -gt 0 ]]; do
  case "$1" in
    --plugin)     PLUGIN=true;     shift ;;
    --multi-step) MULTI_STEP=true; shift ;;
    --merge)      MERGE=true;      shift ;;
    --*)
      emit_kv ERROR "Unknown flag '$1'. Valid flags: --plugin, --multi-step, --merge."
      exit 1
      ;;
    *) break ;;
  esac
done

if [[ $# -lt 1 ]]; then
  emit_kv ERROR "Missing <skill-name>. Usage: /create-skill [--plugin] [--multi-step] [--merge] <skill-name> <description>"
  exit 1
fi

NAME="$1"
shift

# Strip a single leading '/' if the user passed /foo instead of foo.
NAME="${NAME#/}"

if [[ $# -lt 1 ]]; then
  emit_kv ERROR "Missing <description>. Usage: /create-skill [--plugin] [--multi-step] [--merge] <skill-name> <description>"
  exit 1
fi

# Description is the verbatim remainder, space-joined.
DESCRIPTION="$*"

emit_kv NAME "$NAME"
emit_kv DESCRIPTION "$DESCRIPTION"
emit_kv PLUGIN "$PLUGIN"
emit_kv MULTI_STEP "$MULTI_STEP"
emit_kv MERGE "$MERGE"
