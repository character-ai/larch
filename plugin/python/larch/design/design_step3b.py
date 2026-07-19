"""In-process entry points for /design Step 3b and Step 5b.5.

This module owns the former ``design-step3b-entry.sh`` boundary.  It calls the
plan-finalize and Gate C probe owners directly, and preserves the small
``KEY=value`` handoffs consumed by the design prompt.
"""

from __future__ import annotations

import contextlib
import io
import re
import sys
import time
from enum import StrEnum
from pathlib import Path
from collections.abc import Callable, Sequence

from larch import io as larch_io
from larch.design import design_dialectic, design_session, plan_grammar
from larch.review import plan_review_loop
from larch.state import session_env


class Step3bMode(StrEnum):
    """The only supported Step 3b entry modes."""

    FINALIZE = "finalize"
    DIAGRAM = "diagram"


_PROBE_KEY = "DIALECTIC_GATEC_DEBATE_REQUIRED"
_STEP4_MODE_KEY = "STEP4_MODE"
_DIAGRAM_REQUIRED_KEY = "DIAGRAM_REQUIRED"
_PROBE_ROW_RE = re.compile(rf"^{_PROBE_KEY}=(true|false)$")
_KNOWN_DOCUMENT_EXTENSIONS = frozenset(
    {
        ".adoc",
        ".cfg",
        ".conf",
        ".csv",
        ".ini",
        ".json",
        ".jsonl",
        ".md",
        ".rst",
        ".toml",
        ".tsv",
        ".txt",
        ".yaml",
        ".yml",
    }
)
_PLAN_HEADING_LEVEL = 3
_BACKTICK_PAIR_LENGTH = 2


def _mode_from_argv(argv: Sequence[str]) -> Step3bMode | None:
    """Read the last ``--mode`` value, matching the retired shell wrapper."""
    mode = ""
    index = 0
    args = list(argv)
    while index < len(args):
        if args[index] == "--mode":
            if index + 1 >= len(args):
                return None
            mode = args[index + 1]
            index += 2
            continue
        index += 1
    if mode == "entry":
        mode = Step3bMode.FINALIZE.value
    try:
        return Step3bMode(mode)
    except ValueError:
        return None


def _parse_probe_value(stdout: str) -> str | None:
    """Accept exactly one valid probe row and reject malformed lookalikes."""
    parsed = larch_io.parse_kv(stdout, duplicate_policy="all", allowed_keys={_PROBE_KEY})
    rows = parsed.get(_PROBE_KEY, [])
    malformed = any(line.startswith(f"{_PROBE_KEY}=") and _PROBE_ROW_RE.fullmatch(line) is None for line in stdout.splitlines())
    return rows[0] if len(rows) == 1 and rows[0] in {"true", "false"} and not malformed else None


def _run_captured(callable_obj: Callable[[Sequence[str]], int], argv: Sequence[str]) -> tuple[int, str, str]:
    """Capture an in-process CLI owner's output for the wrapper-compatible logs."""
    stdout = io.StringIO()
    stderr = io.StringIO()
    with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
        rc = callable_obj(list(argv))
    return int(rc), stdout.getvalue(), stderr.getvalue()


def _write_capture(*, path: Path, text: str) -> None:
    larch_io.atomic_write(path=path, text=text, create_parent=False, nofollow=True, mode=0o600)


def _pause_if_requested(*, design_tmpdir: Path) -> int | None:
    if (design_tmpdir / ".pause-requested").is_file():
        return design_session.pause_save_for_request(design_tmpdir=design_tmpdir)
    return None


def _run_finalize(*, design_tmpdir: Path) -> int:
    stdout_path = design_tmpdir / "step3b-finalize-driver.stdout"
    stderr_path = design_tmpdir / "step3b-finalize-driver.stderr"
    rc, stdout, stderr = _run_captured(plan_review_loop.finalize_plan, ["--design-tmpdir", str(design_tmpdir)])
    try:
        _write_capture(path=stdout_path, text=stdout)
        _write_capture(path=stderr_path, text=stderr)
    except OSError:
        return 1
    if rc != 0:
        print("**⚠ FINALIZE failed; repair the missing artifact before Step 5.**", file=sys.stderr)
        if stderr:
            print(stderr, end="", file=sys.stderr)
    return rc


def _run_step4_mode_probe(*, design_tmpdir: Path) -> int:
    stdout_path = design_tmpdir / "dialectic-gatec-probe.stdout"
    stderr_path = design_tmpdir / "dialectic-gatec-probe.stderr"
    rc, stdout, stderr = _run_captured(design_dialectic.gatec_main, ["--design-tmpdir", str(design_tmpdir), "--probe-only"])
    try:
        _write_capture(path=stdout_path, text=stdout)
        _write_capture(path=stderr_path, text=stderr)
    except OSError:
        return 1
    if rc != 0:
        print("**⚠ dialectic Gate C probe failed; repair before Step 4.**", file=sys.stderr)
        if stderr:
            print(stderr, end="", file=sys.stderr)
        return rc
    required = _parse_probe_value(stdout)
    if required is None:
        print("**⚠ dialectic Gate C probe did not emit exactly one valid debate-required row; repair before Step 4.**", file=sys.stderr)
        return 1
    step4_mode = "background" if required == "true" else "foreground"
    try:
        larch_io.atomic_write(
            path=design_tmpdir / ".step4-mode.env",
            text=f"{_STEP4_MODE_KEY}={step4_mode}\n",
            create_parent=False,
            nofollow=True,
            mode=0o600,
        )
        larch_io.atomic_write(
            path=design_tmpdir / ".completed" / "step-3b",
            text="",
            create_parent=False,
            nofollow=True,
            mode=0o600,
        )
    except OSError:
        return 1
    print(f"{_STEP4_MODE_KEY}={step4_mode}")
    return 0


def _is_architectural_path(path: str) -> bool:
    path = path.strip()
    if len(path) >= _BACKTICK_PAIR_LENGTH and path.startswith("`") and path.endswith("`"):
        path = path[1:-1].strip()
    parts = [part for part in path.replace("\\", "/").split("/") if part]
    if not parts or any(part == "SKILL.md" for part in parts):
        return True
    base = parts[-1]
    if "." not in base or base.endswith("."):
        return True
    extension = Path(base).suffix.lower()
    return extension not in _KNOWN_DOCUMENT_EXTENSIONS


def diagram_required(*, plan_file: Path) -> bool:
    """Classify the Step 5b.5 plan surface without inspecting prose bodies."""
    try:
        resolved_plan = plan_file.resolve()
        text = larch_io.read_trusted_text(path=resolved_plan, root=resolved_plan.parent)
    except (OSError, UnicodeDecodeError, ValueError):
        return True
    if not text:
        return True
    headings = [heading for heading in plan_grammar.iter_plan_headings(text) if heading.level == _PLAN_HEADING_LEVEL]
    return not headings or any(_is_architectural_path(heading.path) for heading in headings)


def _unlink_diagram_artifacts(*, design_tmpdir: Path, names: Sequence[str]) -> None:
    for name in names:
        with contextlib.suppress(FileNotFoundError):
            (design_tmpdir / name).unlink()


def _run_diagram(*, design_tmpdir: Path) -> int:
    completed = design_tmpdir / ".completed"
    if not (completed / "step-4").is_file():
        print("**⚠ 5b.5: missing .completed/step-4; Gate C approval incomplete; repair Step 4 before diagram", file=sys.stderr)
        return 1
    if not (completed / "step-5b").is_file():
        print("**⚠ 5b.5: missing .completed/step-5b; OOS filing incomplete; repair Step 5b before diagram", file=sys.stderr)
        return 1
    paused = _pause_if_requested(design_tmpdir=design_tmpdir)
    if paused is not None:
        return paused
    started = time.monotonic()
    design_session.mark_design_timing(label="design Step 5b.5 — arch diagram")
    if diagram_required(plan_file=design_tmpdir / "plan.txt"):
        _unlink_diagram_artifacts(
            design_tmpdir=design_tmpdir,
            names=(
                "architecture-diagram.md",
                "architecture-diagram.candidate.md",
                "architecture-diagram.skipped",
                "architecture-diagram-generation.failure.log",
                "architecture-diagram-sanitizer.failure.log",
            ),
        )
        print(f"{_DIAGRAM_REQUIRED_KEY}=true")
        return 0
    _unlink_diagram_artifacts(
        design_tmpdir=design_tmpdir,
        names=(
            "architecture-diagram.md",
            "architecture-diagram.candidate.md",
            "architecture-diagram-generation.failure.log",
            "architecture-diagram-sanitizer.failure.log",
        ),
    )
    try:
        larch_io.atomic_write(
            path=design_tmpdir / "architecture-diagram.skipped",
            text="",
            create_parent=False,
            nofollow=True,
            mode=0o600,
        )
        larch_io.atomic_write(
            path=completed / "step-5b.5",
            text="",
            create_parent=False,
            nofollow=True,
            mode=0o600,
        )
    except OSError:
        return 1
    print(f"{_DIAGRAM_REQUIRED_KEY}=false")
    print(f"⏩ 5b.5: arch diagram status=skip reason=no-architectural-change elapsed={int(time.monotonic() - started)}s")
    return 0


def step3b_entry_main(argv: Sequence[str] | None = None) -> int:  # noqa: PLR0911 - each wrapper boundary failure has a distinct exit contract
    """Run the Step 3b finalize or Step 5b.5 diagram entry boundary."""
    args = list(argv or [])
    mode = _mode_from_argv(args)
    if mode is None:
        print("cli.py design step3b-entry: --mode finalize|diagram required", file=sys.stderr)
        return 2
    try:
        request = design_session.load_design_session_request(args)
    except design_session.DesignSessionRequestError as exc:
        print(exc, file=sys.stderr)
        return 1
    if session_env.require_plugin_root() != 0:
        return 1
    allowed, message = session_env.validate_design_tmpdir(request.design_tmpdir)
    if not allowed:
        print(message, file=sys.stderr)
        return 2
    design_tmpdir = Path(request.design_tmpdir).resolve()
    completed = design_tmpdir / ".completed"
    try:
        completed.mkdir(parents=True, exist_ok=True)
    except OSError:
        return 1
    if mode is Step3bMode.DIAGRAM:
        return _run_diagram(design_tmpdir=design_tmpdir)
    for path in (completed / "step-3b", design_tmpdir / ".step4-mode.env", design_tmpdir / ".step4-mode.env.tmp"):
        with contextlib.suppress(FileNotFoundError):
            path.unlink()
    try:
        larch_io.atomic_write(
            path=completed / "step-3.5",
            text="",
            create_parent=False,
            nofollow=True,
            mode=0o600,
        )
    except OSError:
        return 1
    paused = _pause_if_requested(design_tmpdir=design_tmpdir)
    if paused is not None:
        return paused
    design_session.mark_design_timing(label="design Step 3b — finalize")
    rc = _run_finalize(design_tmpdir=design_tmpdir)
    return _run_step4_mode_probe(design_tmpdir=design_tmpdir) if rc == 0 else rc
