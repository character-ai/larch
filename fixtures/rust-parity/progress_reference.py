"""Frozen Python behavior for the issue #8084 progress and statusline cutover.

This reproduces `python/larch/report/progress_file.py` and `statusline.py` as
they behaved at cutover for `progress activate`, `deactivate`, `clear`, `note`,
`statusline`, and `session-reset`.

Deliberate omissions, none of them observable through a golden capture:

* The `openat`/`O_NOFOLLOW` directory traversal. The retired writer walked the
  clone directory with fd-relative opens so a symlink swapped in mid-write could
  not redirect a create. The Rust owner keeps an equivalent confinement check on
  every component; this reference uses plain path operations because no golden
  case races a symlink swap.

Known differences, each stated so a reviewer can weigh it:

* `prog=` and `-h`. The retired verbs were spelled `cli.py progress <verb>` and
  accepted `-h`. The Rust owner uses `progress <verb>` and reserves no help
  flag, so this reference matches the Rust spelling with `add_help=False`. No
  production caller passes `-h` or parses the usage line.
* `install-statusline` is absent from this reference. Its launcher body changes
  by design in this cutover: it now runs `scripts/larch.sh progress statusline`
  instead of `python3 <plugin>/python/cli.py progress statusline`, and the
  launcher lands inside the captured sandbox `HOME`. Comparing it against a
  hand-written reference would only prove the fixture and the Rust owner agree,
  so installation idempotence, the custom-statusline refusal, and the
  invalid-settings refusal are covered in `crates/larch-cli/tests/progress.rs`
  and in the `larch-adapters` installation unit test instead.

Staleness rendering depends on the breadcrumb log's mtime, which a parity
sandbox cannot freeze, so the stale and hidden branches are covered by the
`crates/larch-cli/tests/progress.rs` cases and by the `classify_staleness` unit
tests instead of by a byte-compared golden.
"""
# ruff: noqa: C901, PLR0911, PLR0912, PLR0913, S108

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
import time
from pathlib import Path

PROGRESS_DIRNAME = "progress"
CURRENT_RUN_FILENAME = "current"
CURRENT_RUN_LOCK_FILENAME = ".current.lock"
RUN_BREADCRUMB_FILENAME = "breadcrumbs.log"
YELLOW = "\033[33m"
RESET = "\033[0m"
DEFAULT_STALE_AFTER_S = 300
DEFAULT_HIDE_AFTER_S = 3600
MAX_LINES = 3
RESET_SESSION_SOURCES = frozenset({"startup", "clear"})
RUN_ID_PATTERN = re.compile(r"[A-Za-z0-9._-]{1,128}")


def cache_home() -> Path:
    override = os.environ.get("LARCH_TEST_CACHE_HOME")
    if override:
        return Path(override)
    xdg = os.environ.get("XDG_CACHE_HOME")
    if xdg:
        return Path(xdg)
    return Path.home() / ".cache"


def clone_dir(repo_root: str) -> Path:
    path = Path(repo_root).expanduser()
    try:
        canonical = path.resolve()
    except OSError:
        canonical = path.absolute()
    digest = hashlib.sha256(str(canonical).encode("utf-8")).hexdigest()[:16]
    return cache_home() / "larch" / PROGRESS_DIRNAME / digest


def validate_run_id(run_id: str) -> str | None:
    if not run_id or run_id in {".", "..", CURRENT_RUN_FILENAME}:
        return None
    return run_id if RUN_ID_PATTERN.fullmatch(run_id) else None


def read_active_run_id(directory: Path) -> str | None:
    pointer = directory / CURRENT_RUN_FILENAME
    try:
        if pointer.is_symlink() or not pointer.is_file():
            return None
        first_line = pointer.read_bytes().split(b"\n")[0].decode("utf-8", "replace")
    except OSError:
        return None
    return validate_run_id(first_line.rstrip())


def reject_line_part(value: str, *, label: str) -> str | None:
    text = value.strip()
    if not text or "\t" in text or "\n" in text or "\r" in text:
        return None
    if any(ord(ch) < 32 or ord(ch) == 127 or 0x80 <= ord(ch) <= 0x9F for ch in text):  # noqa: PLR2004
        return None
    if label == "text" and "://" in text:
        return None
    return text


def breadcrumb_line(*, skill: str, step: str, text: str) -> str | None:
    parts = [
        reject_line_part(skill, label="skill"),
        reject_line_part(step, label="step"),
        reject_line_part(text, label="text"),
    ]
    if any(part is None for part in parts):
        return None
    return f"[{parts[0]} {parts[1]}] {parts[2]}\n"


def touch_lock(directory: Path) -> None:
    lock = directory / CURRENT_RUN_LOCK_FILENAME
    with lock.open("a", encoding="utf-8"):
        pass
    lock.chmod(0o600)


def run_id_error(run_id: str) -> str | None:
    if validate_run_id(run_id) is not None:
        return None
    if not run_id:
        return "run ID must be non-empty"
    if run_id in {".", "..", CURRENT_RUN_FILENAME}:
        return f"reserved run ID: {run_id}"
    return "run ID must contain only letters, digits, dot, underscore, or dash"


def activate_run(repo_root: str, run_id: str) -> None:
    rejection = run_id_error(run_id)
    if rejection is not None:
        raise ValueError(rejection)
    safe = validate_run_id(run_id) or run_id
    directory = clone_dir(repo_root)
    (directory / safe).mkdir(parents=True, exist_ok=True)
    touch_lock(directory)
    pointer = directory / CURRENT_RUN_FILENAME
    pointer.write_text(f"{safe}\n", encoding="utf-8")
    pointer.chmod(0o600)


def clear_pointer(repo_root: str, expected: str | None) -> bool:
    directory = clone_dir(repo_root)
    if not directory.is_dir():
        return False
    touch_lock(directory)
    pointer = directory / CURRENT_RUN_FILENAME
    if pointer.is_symlink() or not pointer.is_file():
        return False
    if expected is not None and read_active_run_id(directory) != expected:
        return False
    pointer.unlink()
    return True


def append_line(path: Path, line: str) -> bool:
    if path.is_symlink():
        return False
    try:
        with path.open("a", encoding="utf-8") as handle:
            handle.write(line)
        path.chmod(0o600)
    except OSError:
        return False
    return True


def append_breadcrumb(repo_root: str, run_id: str | None, skill: str, step: str, text: str) -> bool:
    line = breadcrumb_line(skill=skill, step=step, text=text)
    if line is None:
        return False
    directory = clone_dir(repo_root)
    if run_id is None:
        active = read_active_run_id(directory)
        if active is None:
            return False
        return append_line(directory / active / RUN_BREADCRUMB_FILENAME, line)
    safe = validate_run_id(run_id)
    if safe is None:
        return False
    (directory / safe).mkdir(parents=True, exist_ok=True)
    return append_line(directory / safe / RUN_BREADCRUMB_FILENAME, line)


def positive_int(raw: str | None, *, default: int, max_value: int | None = None) -> int:
    value = int(raw) if raw and raw.isdigit() and int(raw) > 0 else default
    return min(value, max_value) if max_value is not None else value


def payload_object(text: str) -> dict[str, object]:
    try:
        parsed = json.loads(text or "{}")
    except json.JSONDecodeError:
        return {}
    return parsed if isinstance(parsed, dict) else {}


def statusline_directory(payload: dict[str, object]) -> str:
    workspace = payload.get("workspace")
    workspace_map = workspace if isinstance(workspace, dict) else {}
    current_dir = workspace_map.get("current_dir")
    cwd = payload.get("cwd")
    if isinstance(current_dir, str) and current_dir:
        return current_dir
    return cwd if isinstance(cwd, str) else ""


def truncate(text: str, *, columns: int) -> str:
    if columns <= 0 or len(text) <= columns:
        return text
    if columns <= 1:
        return text[:columns]
    return text[: columns - 1] + "…"


def render_statusline(stdin_text: str) -> str:
    payload = payload_object(stdin_text)
    raw = statusline_directory(payload)
    if not raw or not Path(raw).is_absolute():
        return ""
    directory = clone_dir(raw)
    run_id = read_active_run_id(directory)
    if run_id is None:
        return ""
    log = directory / run_id / RUN_BREADCRUMB_FILENAME
    if log.is_symlink() or not log.is_file():
        return ""
    try:
        lines = log.read_text(encoding="utf-8", errors="replace").splitlines()
    except OSError:
        return ""
    rows = [line for line in lines if line.startswith("[") and "] " in line and "\t" not in line]
    count = positive_int(os.environ.get("LARCH_STATUSLINE_LINES"), default=1, max_value=MAX_LINES)
    rows = rows[-count:]
    if not rows:
        return ""
    now = float(os.environ.get("LARCH_TEST_STATUSLINE_NOW", "") or time.time())
    try:
        modified = log.stat().st_mtime
    except OSError:
        return ""
    age_s = max(0, int(now - modified))
    stale_after = positive_int(os.environ.get("LARCH_STATUSLINE_STALE_AFTER_S"), default=DEFAULT_STALE_AFTER_S)
    hide_after = positive_int(os.environ.get("LARCH_STATUSLINE_HIDE_AFTER_S"), default=DEFAULT_HIDE_AFTER_S)
    if age_s < stale_after:
        suffix = ""
    elif age_s >= hide_after:
        return ""
    else:
        suffix = f" (stale {max(1, age_s // 60)}m)"
    stamp = time.strftime("%H:%M", time.localtime(modified))
    rendered = "\n".join(f"larch {stamp}: {row}{suffix}" for row in rows)
    columns = positive_int(os.environ.get("COLUMNS"), default=0)
    if columns:
        rendered = "\n".join(truncate(row, columns=columns) for row in rendered.splitlines())
    return f"{YELLOW}{rendered}{RESET}\n"


def usage_error(usage: str, program: str, message: str) -> int:
    print(f"{usage}\n{program}: error: {message}", file=sys.stderr)
    return 2


def parser_for(program: str) -> argparse.ArgumentParser:
    return argparse.ArgumentParser(prog=program, add_help=False)


def activate_main(argv: list[str]) -> int:
    parser = parser_for("progress activate")
    _ = parser.add_argument("--repo-root", default=str(Path.cwd()))
    _ = parser.add_argument("--run-id")
    args = parser.parse_args(argv)
    usage = "usage: progress activate [--repo-root REPO_ROOT] --run-id RUN_ID"
    if args.run_id is None:
        return usage_error(usage, "progress activate", "the following arguments are required: --run-id")
    try:
        activate_run(args.repo_root, args.run_id)
    except (OSError, ValueError) as exc:
        print(f"progress activate failed: {exc}", file=sys.stderr)
        return 2
    return 0


def deactivate_main(argv: list[str]) -> int:
    parser = parser_for("progress deactivate")
    _ = parser.add_argument("--repo-root", default=str(Path.cwd()))
    _ = parser.add_argument("--run-id")
    args = parser.parse_args(argv)
    usage = "usage: progress deactivate [--repo-root REPO_ROOT] --run-id RUN_ID"
    if args.run_id is None:
        return usage_error(usage, "progress deactivate", "the following arguments are required: --run-id")
    safe = validate_run_id(args.run_id)
    if safe is not None:
        _ = clear_pointer(args.repo_root, safe)
    return 0


def clear_main(argv: list[str]) -> int:
    parser = parser_for("progress clear")
    _ = parser.add_argument("--repo-root", default=str(Path.cwd()))
    args = parser.parse_args(argv)
    _ = clear_pointer(args.repo_root, None)
    return 0


def note_main(argv: list[str]) -> int:
    parser = parser_for("progress note")
    _ = parser.add_argument("--repo-root", default=str(Path.cwd()))
    _ = parser.add_argument("--run-id")
    _ = parser.add_argument("--skill")
    _ = parser.add_argument("--step")
    _ = parser.add_argument("text", nargs="*")
    args = parser.parse_args(argv)
    usage = (
        "usage: progress note [--repo-root REPO_ROOT] [--run-id RUN_ID] "
        "--skill SKILL --step STEP text [text ...]"
    )
    missing = [name for name, value in (("--skill", args.skill), ("--step", args.step)) if value is None]
    if missing:
        return usage_error(usage, "progress note", f"the following arguments are required: {', '.join(missing)}")
    if not args.text:
        return usage_error(usage, "progress note", "the following arguments are required: text")
    _ = append_breadcrumb(args.repo_root, args.run_id, args.skill, args.step, " ".join(args.text))
    return 0


def statusline_main(argv: list[str]) -> int:
    _ = parser_for("progress statusline").parse_args(argv)
    rendered = render_statusline(sys.stdin.read())
    if rendered:
        _ = sys.stdout.write(rendered)
    return 0


def session_reset_main(argv: list[str]) -> int:
    _ = parser_for("progress session-reset").parse_args(argv)
    if os.environ.get("LARCH_STATUSLINE_DISABLE") == "1":
        return 0
    payload = payload_object(sys.stdin.read())
    source = payload.get("source")
    if not isinstance(source, str) or source not in RESET_SESSION_SOURCES:
        return 0
    raw = statusline_directory(payload)
    if not raw:
        return 0
    run_id = read_active_run_id(clone_dir(raw))
    if run_id is not None:
        _ = clear_pointer(raw, run_id)
    return 0


COMMANDS = {
    "activate": activate_main,
    "deactivate": deactivate_main,
    "clear": clear_main,
    "note": note_main,
    "statusline": statusline_main,
    "session-reset": session_reset_main,
}


def main() -> int:
    command, *arguments = sys.argv[1:]
    handler = COMMANDS.get(command)
    if handler is None:
        print(f"unknown progress reference command: {command}", file=sys.stderr)
        return 2
    return handler(arguments)


if __name__ == "__main__":
    raise SystemExit(main())
