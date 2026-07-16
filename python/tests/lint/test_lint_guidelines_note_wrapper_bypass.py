from __future__ import annotations

from pathlib import Path

from typing import Protocol

from larch.lint import lint_guidelines_note_wrapper_bypass as lgnwb
from tests.lint.conftest import write_project as _write_project


class CaptureResult(Protocol):
    err: str
    out: str


class CaptureFixture(Protocol):
    def readouterr(self) -> CaptureResult: ...


def _module(body: str) -> str:
    return "from __future__ import annotations\n\n" + body


def test_direct_call_outside_owner_exits_1(
    tmp_path: Path, capsys: CaptureFixture
) -> None:
    _write_project(
        tmp_path,
        files={"larch/implement/rebase.py": _module("def run() -> None:\n    _invalidate_guidelines_note()\n")},
    )

    assert lgnwb.main(["--root", str(tmp_path)]) == 1
    assert "use _pin_or_invalidate_guidelines_note instead" in capsys.readouterr().err


def test_attribute_call_outside_owner_exits_1(tmp_path: Path) -> None:
    _write_project(
        tmp_path,
        files={
            "larch/implement/rebase.py": _module(
                "def run(module: object) -> None:\n    module._invalidate_guidelines_note()\n"
            )
        },
    )

    assert lgnwb.main(["--root", str(tmp_path)]) == 1


def test_calls_inside_ship_guidelines_are_allowed(tmp_path: Path) -> None:
    _write_project(
        tmp_path,
        files={
            "larch/implement/ship_guidelines.py": _module(
                "def run() -> None:\n    _invalidate_guidelines_note()\n"
            )
        },
    )

    assert lgnwb.main(["--root", str(tmp_path)]) == 0


def test_no_call_exits_0(tmp_path: Path) -> None:
    _write_project(
        tmp_path,
        files={
            "larch/implement/rebase.py": _module(
                "def run() -> None:\n    _pin_or_invalidate_guidelines_note()\n"
            )
        },
    )

    assert lgnwb.main(["--root", str(tmp_path)]) == 0


def test_definitions_are_not_flagged_unless_called(tmp_path: Path) -> None:
    _write_project(
        tmp_path,
        files={
            "larch/implement/rebase.py": _module(
                "def _invalidate_guidelines_note() -> None:\n    pass\n"
                "def clean() -> None:\n    pass\n"
            )
        },
    )

    assert lgnwb.main(["--root", str(tmp_path)]) == 0


def test_scope_excludes_tests_and_helper_files(tmp_path: Path) -> None:
    _write_project(
        tmp_path,
        files={
            "larch/test_mod.py": _module("def run() -> None:\n    _invalidate_guidelines_note()\n"),
            "larch/pkg/test_nested.py": _module("def run() -> None:\n    _invalidate_guidelines_note()\n"),
            "larch/pkg/conftest.py": _module("def run() -> None:\n    _invalidate_guidelines_note()\n"),
            "larch/pkg/test_support.py": _module("def run() -> None:\n    _invalidate_guidelines_note()\n"),
            "larch/pkg/review_test_support.py": _module("def run() -> None:\n    _invalidate_guidelines_note()\n"),
            "larch/pkg/tests/helper.py": _module("def run() -> None:\n    _invalidate_guidelines_note()\n"),
            "larch/pkg/__pycache__/generated.py": _module("def run() -> None:\n    _invalidate_guidelines_note()\n"),
            "larch/pkg/prod.py": _module("VALUE = 'clean'\n"),
        },
    )
    larch_dir: Path = tmp_path / "python" / "larch"

    assert [path.relative_to(larch_dir.parent).as_posix() for path in lgnwb.iter_source_files(larch_dir)] == [
        "larch/pkg/prod.py"
    ]
    assert lgnwb.main(["--root", str(tmp_path)]) == 0


def test_same_line_suppression_requires_reason(tmp_path: Path) -> None:
    _write_project(
        tmp_path,
        files={
            "larch/ok.py": _module(
                "def run() -> None:\n"
                "    _invalidate_guidelines_note()  # lint-guidelines-note-wrapper-bypass: ok fixture\n"
            ),
            "larch/bad.py": _module(
                "def run() -> None:\n"
                "    _invalidate_guidelines_note()  # lint-guidelines-note-wrapper-bypass: ok\n"
            ),
        },
    )

    assert lgnwb.main(["--root", str(tmp_path)]) == 1


def test_pragma_like_string_literals_do_not_suppress_findings(tmp_path: Path) -> None:
    _write_project(
        tmp_path,
        files={
            "larch/mod.py": _module(
                "def run() -> None:\n"
                "    message = '# lint-guidelines-note-wrapper-bypass: ok fixture'\n"
                "    _invalidate_guidelines_note()\n"
            )
        },
    )

    assert lgnwb.main(["--root", str(tmp_path)]) == 1


def test_parse_failure_exits_2(tmp_path: Path) -> None:
    _write_project(tmp_path, files={"larch/broken.py": "def run(:\n"})

    assert lgnwb.main(["--root", str(tmp_path)]) == 2


def test_non_utf8_source_reads_exit_2(tmp_path: Path, capsys: CaptureFixture) -> None:
    python_dir: Path = tmp_path / "python"
    path: Path = python_dir / "larch/binary.py"
    path.parent.mkdir(parents=True, exist_ok=True)
    _ = path.write_bytes(b"def run() -> None:\n\xff\n")

    assert lgnwb.main(["--root", str(tmp_path)]) == 2
    assert "cannot read source" in capsys.readouterr().err
