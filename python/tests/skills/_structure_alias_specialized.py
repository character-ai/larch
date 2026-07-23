"""Complete port of test-alias-structure.sh."""
from __future__ import annotations

import re
from pathlib import Path

LEGACY_LABELS: frozenset[str] = frozenset(
    {
        "(A) expected python/cli.py alias resolve-target to be referenced in SKILL.md, found 0",
        "(B) expected --private flag documented in SKILL.md",
        "(C) expected canonical allowlist 'REPO_ROOT|PLUGIN_REPO|TARGET_DIR' in Step 2 parser block",
        '(D) expected Check 6 to use \'test -e "$TARGET_DIR"\'',
        '(D-neg) old hardcoded collision check \'test -d ".claude/skills/<alias-name>"\' still present',
        "(E) expected E_COLLISION row to reference $TARGET_DIR",
        '(F.1) expected \'mkdir -p "$TARGET_DIR"\' in Step 3 recipe',
        '(F.2) expected \'--target-dir "$TARGET_DIR"\' in Step 3 recipe',
        '(F.3) expected redirect \'> "$TARGET_DIR/SKILL.md"\' in Step 3 recipe',
        "(F-neg) old hardcoded recipe path '.claude/skills/<alias-name>/...' still in Step 3",
        "(G) expected announce line to interpolate $TARGET_DIR",
        '(H.1) expected --sentinel-file "$TARGET_DIR/SKILL.md" in Step 4',
        "(H.2) expected Step 4 verification to launch cli.py with python3",
        "(H.3-neg) Step 4 must not quote the cli path and subcommand as one executable",
        "(H.2-neg) old 'REPO_ROOT=$(git rev-parse ... || pwd -P)' still present in Step 4",
        "(I.1) NEVER #5 should mention both flags (--merge, --private)",
        "(I.2) NEVER list should include the TARGET_DIR-threading rule",
        "(I.3) NEVER list should forbid eval of alias resolve-target stdout",
        "(J) frontmatter argument-hint must include [--private]",
    }
)


def run(repo_root: Path) -> list[str]:
    failures: list[str] = []
    skill = repo_root / "skills/alias/SKILL.md"
    if not skill.is_file():
        return [f"skills/alias/SKILL.md missing: {skill}"]
    text = skill.read_text(encoding="utf-8")

    if text.count('python3 "${CLAUDE_PLUGIN_ROOT}/python/cli.py" alias resolve-target') < 1:
        failures.append(
            "(A) expected python/cli.py alias resolve-target to be referenced in SKILL.md, found 0"
        )
    if "--private" not in text:
        failures.append("(B) expected --private flag documented in SKILL.md")
    if "REPO_ROOT|PLUGIN_REPO|TARGET_DIR" not in text:
        failures.append(
            "(C) expected canonical allowlist 'REPO_ROOT|PLUGIN_REPO|TARGET_DIR' in Step 2 parser block"
        )
    # bash: grep -q 'test -e "\$TARGET_DIR"' → BRE treats \$ as literal $
    if re.search(r'test -e "\$TARGET_DIR"', text) is None:
        failures.append('(D) expected Check 6 to use \'test -e "$TARGET_DIR"\'')
    if re.search(r'test -d "\.claude/skills/<alias-name>"', text) is not None:
        failures.append(
            '(D-neg) old hardcoded collision check \'test -d ".claude/skills/<alias-name>"\' still present'
        )
    if re.search(r"E_COLLISION.*\$TARGET_DIR", text) is None:
        failures.append("(E) expected E_COLLISION row to reference $TARGET_DIR")
    if 'mkdir -p "$TARGET_DIR"' not in text:
        failures.append('(F.1) expected \'mkdir -p "$TARGET_DIR"\' in Step 3 recipe')
    if '--target-dir "$TARGET_DIR"' not in text:
        failures.append('(F.2) expected \'--target-dir "$TARGET_DIR"\' in Step 3 recipe')
    if '> "$TARGET_DIR/SKILL.md"' not in text:
        failures.append('(F.3) expected redirect \'> "$TARGET_DIR/SKILL.md"\' in Step 3 recipe')
    if (
        re.search(r"mkdir -p \.claude/skills/<alias-name>$", text, re.MULTILINE) is not None
        or re.search(r'> "\.claude/skills/<alias-name>/SKILL\.md"', text) is not None
    ):
        failures.append(
            "(F-neg) old hardcoded recipe path '.claude/skills/<alias-name>/...' still in Step 3"
        )
    if "target: $TARGET_DIR" not in text:
        failures.append("(G) expected announce line to interpolate $TARGET_DIR")
    if '--sentinel-file "$TARGET_DIR/SKILL.md"' not in text:
        failures.append('(H.1) expected --sentinel-file "$TARGET_DIR/SKILL.md" in Step 4')
    verification_fence = (
        f'python3 "${{CLAUDE_PLUGIN_ROOT}}/python/cli.py" verify skill-called {chr(92)}\n'
        '  --sentinel-file "$TARGET_DIR/SKILL.md"'
    )
    if verification_fence not in text:
        failures.append("(H.2) expected Step 4 verification to launch cli.py with python3")
    if '"${CLAUDE_PLUGIN_ROOT}/python/cli.py verify skill-called"' in text:
        failures.append(
            "(H.3-neg) Step 4 must not quote the cli path and subcommand as one executable"
        )
    if "REPO_ROOT=$(git rev-parse --show-toplevel 2>/dev/null || pwd -P)" in text:
        failures.append(
            "(H.2-neg) old 'REPO_ROOT=$(git rev-parse ... || pwd -P)' still present in Step 4"
        )
    if re.search(r"NEVER parse.*--merge.*--private", text) is None:
        failures.append("(I.1) NEVER #5 should mention both flags (--merge, --private)")
    if "NEVER hardcode" not in text:
        failures.append("(I.2) NEVER list should include the TARGET_DIR-threading rule")
    if re.search(r"NEVER use .eval", text) is None:
        failures.append("(I.3) NEVER list should forbid eval of alias resolve-target stdout")
    if 'argument-hint: "[--merge] [--private]' not in text:
        failures.append("(J) frontmatter argument-hint must include [--private]")
    return failures
