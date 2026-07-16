from __future__ import annotations

from pathlib import Path
from typing import Protocol

from larch.lint import lint_git_push_refspec as lgpr


class CaptureResult(Protocol):
    err: str


class CaptureFixture(Protocol):
    def readouterr(self) -> CaptureResult: ...


def _write_project(root: Path, *, files: dict[str, str]) -> None:
    for relpath, source in files.items():
        path = root / "python" / relpath
        path.parent.mkdir(parents=True, exist_ok=True)
        _ = path.write_text(source, encoding="utf-8")


def test_flags_bare_push_and_accepts_explicit_refspec(tmp_path: Path, capsys: CaptureFixture) -> None:
    _write_project(
        tmp_path,
        files={
            "bare.py": 'argv = ["git", "push", "origin"]\n',
            "explicit.py": (
                'argv = ["git", "push", "--force-with-lease=refs/heads/feat:abc", '
                '"origin", "HEAD:refs/heads/feat"]\n'
            ),
        },
    )

    assert lgpr.main(["--root", str(tmp_path)]) == 1
    assert capsys.readouterr().err.splitlines() == [
        "python/bare.py: line 1 contains git push without an explicit refspec",
    ]


def test_fixture_pragma_suppresses_intentional_config_resolved_push(tmp_path: Path) -> None:
    _write_project(
        tmp_path,
        files={
            "tests/fixture.py": (
                'argv = ["git", "push", "origin"] '
                "# lint-git-push-refspec: ok fixture checks config resolution\n"
            ),
        },
    )

    assert lgpr.main(["--root", str(tmp_path)]) == 0


def test_production_pragma_does_not_suppress(tmp_path: Path) -> None:
    _write_project(
        tmp_path,
        files={
            "prod.py": (
                'argv = ["git", "push", "origin"] '
                "# lint-git-push-refspec: ok production exception\n"
            ),
        },
    )

    assert lgpr.main(["--root", str(tmp_path)]) == 1


def test_dynamic_argv_elements_remain_tolerant(tmp_path: Path) -> None:
    _write_project(
        tmp_path,
        files={
            "dynamic.py": 'argv = ["git", "push", remote, refspec]\n',
            "fstring.py": (
                'argv = ["git", "push", f"--force-with-lease={lease}", '
                'remote, f"HEAD:refs/heads/{branch}"]\n'
            ),
        },
    )

    assert lgpr.main(["--root", str(tmp_path)]) == 0


def test_invalid_source_and_arguments_fail_closed(tmp_path: Path) -> None:
    _write_project(tmp_path, files={"broken.py": "def broken(:\n"})

    assert lgpr.main(["--root", str(tmp_path)]) == 2
    assert lgpr.main(["--unknown"]) == 2
