"""Complete port of scripts/test-bug-structure.sh."""
from __future__ import annotations
from pathlib import Path

LEGACY_LABELS: frozenset[str] = frozenset(["(A) frontmatter argument-hint must include [--urgent]", "(B) contract must document --urgent as the only flag", "(D) contract must strip leading --urgent before validation", "(E) Step 5 invocation must pass --title-prefix", "(F.1) default [BUG] prefix literal missing", "(F.2) urgent [BUG] (URGENT) prefix literal missing", "(G) skill must still say not to pass --no-dedup", "(H.1) Write hook matcher must remain present", "(H.2) Write hook command must pass the bug token", "(H.3) Step 2 must create bug-$PPID activation sentinel", "(H.4) sentinel write failure must abort loudly", "(H.5) Step 3 security abort must remove sentinel with BUG_TMPDIR", "(H.6) Step 5 security abort must remove sentinel with BUG_TMPDIR", "(H.7) Step 6 failure must remove sentinel while leaving BUG_TMPDIR", "(H.8) Step 7 cleanup must remove sentinel"])

def run(repo_root: Path) -> list[str]:
    failures: list[str] = []
    skill = repo_root / "skills/bug/SKILL.md"
    if not skill.is_file():
        return [f"skills/bug/SKILL.md missing: {skill}"]
    text = skill.read_text(encoding="utf-8")
    if 'argument-hint: "[--urgent] <bug description>"' not in text:
        failures.append("(A) frontmatter argument-hint must include [--urgent]")
    if "`--urgent` is the only flag." not in text:
        failures.append("(B) contract must document --urgent as the only flag")
    if "Remove one or more leading `--urgent` tokens from the description before validation." not in text:
        failures.append("(D) contract must strip leading --urgent before validation")
    if "--title-prefix" not in text:
        failures.append("(E) Step 5 invocation must pass --title-prefix")
    if "[BUG]" not in text:
        failures.append("(F.1) default [BUG] prefix literal missing")
    if "[BUG] (URGENT)" not in text:
        failures.append("(F.2) urgent [BUG] (URGENT) prefix literal missing")
    if "Do not include `--no-dedup`." not in text:
        failures.append("(G) skill must still say not to pass --no-dedup")
    if 'matcher: "Write"' not in text:
        failures.append("(H.1) Write hook matcher must remain present")
    if 'command: "${CLAUDE_PLUGIN_ROOT}/scripts/deny-edit-write.sh bug"' not in text:
        failures.append("(H.2) Write hook command must pass the bug token")
    if 'BUG_DENY_ACTIVE_SENTINEL="$BUG_DENY_ACTIVE_DIR/bug-$PPID"' not in text:
        failures.append("(H.3) Step 2 must create bug-$PPID activation sentinel")
    if "**⚠ /bug: failed to activate Write hook. Aborting.**" not in text:
        failures.append("(H.4) sentinel write failure must abort loudly")
    if 'Remove `"$BUG_DENY_ACTIVE_SENTINEL"` and `$BUG_TMPDIR` if they exist, then stop.' not in text:
        failures.append("(H.5) Step 3 security abort must remove sentinel with BUG_TMPDIR")
    if 'Remove `"$BUG_DENY_ACTIVE_SENTINEL"` and `$BUG_TMPDIR`, then stop.' not in text:
        failures.append("(H.6) Step 5 security abort must remove sentinel with BUG_TMPDIR")
    if 'remove `"$BUG_DENY_ACTIVE_SENTINEL"`, surface the failure and parsed counters when available, stop without claiming that an issue was filed, and **do not run Step 7**. Leave `$BUG_TMPDIR` in place for debugging.' not in text:
        failures.append("(H.7) Step 6 failure must remove sentinel while leaving BUG_TMPDIR")
    if 'rm -f "$BUG_DENY_ACTIVE_SENTINEL"' not in text:
        failures.append("(H.8) Step 7 cleanup must remove sentinel")
    return failures

