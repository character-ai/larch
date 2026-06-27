"""Check that flags used in SKILL.md script invocations exist in target scripts."""

from __future__ import annotations

import argparse
import re
import shlex
import sys
from pathlib import Path

PLUGIN_BRACED = "${CLAUDE_PLUGIN_ROOT}"
PLUGIN_PLAIN = "$CLAUDE_PLUGIN_ROOT"
FLAG_RE = re.compile(r"(^|\s)--([A-Za-z0-9][A-Za-z0-9_-]*)")
FENCE_OPEN_RE = re.compile(r"^\s*```(bash|sh|shell)(\s.*)?$")
FENCE_ANY_RE = re.compile(r"^\s*```")
MIN_QUOTED_LENGTH = 2


def _parse_args(argv: list[str]) -> argparse.Namespace | None:
    parser = argparse.ArgumentParser(
        prog="cli.py lint skill-md-flag-signature",
        description=__doc__,
    )
    _ = parser.add_argument("--root", default=str(Path(__file__).resolve().parents[3]))
    try:
        return parser.parse_args(argv)
    except SystemExit as exc:
        if exc.code == 0:
            raise
        return None


def _strip_token(token: str) -> str:
    token = token.rstrip("\\")
    if len(token) >= MIN_QUOTED_LENGTH and token[0] == token[-1] and token[0] in {"'", '"'}:
        return token[1:-1]
    return token.strip("'\"")


def resolve_script_path( *,token: str, root: Path) -> Path | None:
    token = _strip_token(token)
    root_text = str(root)
    if token.startswith(f"{PLUGIN_BRACED}/"):
        return root / token.removeprefix(f"{PLUGIN_BRACED}/")
    if token.startswith(f"{PLUGIN_PLAIN}/"):
        return root / token.removeprefix(f"{PLUGIN_PLAIN}/")
    if token.startswith(f"{root_text}/"):
        return Path(token)
    if token.startswith("/") and "/scripts/" in token and token.endswith(".sh"):
        return Path(token)
    return None


def script_from_command( *,command: str, root: Path) -> Path | None:
    try:
        tokens = shlex.split(command, posix=True)
    except ValueError:
        tokens = command.split()
    for raw in tokens:
        token = _strip_token(raw)
        if "/scripts/" in token and token.endswith(".sh"):
            resolved = resolve_script_path(token=token, root=root)
            if resolved is not None:
                return resolved
    return None


def declare_case_arm_exists( *,script: Path, flag: str) -> bool:
    try:
        text = script.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return False
    return re.search(rf"(^|\s)--{re.escape(flag)}([|)])", text) is not None


def _rel( *,path: Path, root: Path) -> str:
    try:
        return str(path.relative_to(root))
    except ValueError:
        return str(path)


def report_command_flags( *,
    skill_file: Path,
    line_no: int,
    command: str,
    previous_line: str,
    root: Path,
) -> bool:
    if "--" not in command:
        return False
    script = script_from_command(command=command, root=root)
    if script is None:
        return False
    flags = [match.group(2) for match in FLAG_RE.finditer(command)]
    if not flags:
        return False
    if "# lint-skill-md-flag-signature: ok " in command or "# lint-skill-md-flag-signature: ok " in previous_line:
        return False
    rel_skill = _rel(path=skill_file, root=root)
    rel_script = _rel(path=script, root=root)
    if not script.is_file():
        print(f"{rel_skill}:{line_no}: WARN target script not found: {rel_script}", file=sys.stderr)
        return False
    finding = False
    for flag in flags:
        if not declare_case_arm_exists(script=script, flag=flag):
            print(
                f"{rel_skill}:{line_no}: invocation uses --{flag} but {rel_script} does not declare it",
                file=sys.stderr,
            )
            finding = True
    return finding


def scan_skill_file( *,path: Path, root: Path) -> bool:
    finding = False
    try:
        lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
    except OSError:
        return False
    previous = ""
    in_fence = False
    logical = ""
    logical_start = 0
    logical_previous = ""
    for lineno, line in enumerate(lines, 1):
        if FENCE_OPEN_RE.match(line):
            in_fence = True
            previous = line
            continue
        if FENCE_ANY_RE.match(line):
            if in_fence and logical:
                finding = report_command_flags(skill_file=path, line_no=logical_start, command=logical, previous_line=logical_previous, root=root) or finding
                logical = ""
            in_fence = False
            previous = line
            continue
        if not in_fence:
            previous = line
            continue
        if not logical:
            logical = line
            logical_start = lineno
            logical_previous = previous
        else:
            logical = f"{logical} {line}"
        if line.endswith("\\"):
            previous = line
            continue
        finding = report_command_flags(skill_file=path, line_no=logical_start, command=logical, previous_line=logical_previous, root=root) or finding
        logical = ""
        logical_start = 0
        logical_previous = ""
        previous = line
    return finding


def main(argv: list[str] | None = None) -> int:
    parsed = _parse_args(argv=argv if argv is not None else sys.argv[1:])
    if parsed is None:
        return 2
    root = Path(parsed.root)
    finding = False
    skills_dir = root / "skills"
    if skills_dir.is_dir():
        for path in sorted(skills_dir.glob("*/SKILL.md")):
            finding = scan_skill_file(path=path, root=root) or finding
    return 1 if finding else 0


if __name__ == "__main__":
    raise SystemExit(main())
