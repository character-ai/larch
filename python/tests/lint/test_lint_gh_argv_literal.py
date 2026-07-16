from __future__ import annotations

from pathlib import Path

from typing import Protocol

from larch.lint import lint_gh_argv_literal as lgal
from tests.lint.conftest import write_project as _write_project


class CaptureResult(Protocol):
    err: str


class CaptureFixture(Protocol):
    def readouterr(self) -> CaptureResult: ...


def test_lists_in_every_expression_context_are_reported(tmp_path: Path, capsys: CaptureFixture) -> None:
    _write_project(
        tmp_path,
        files={
            "prod.py": (
                "argv = ['gh', 'issue', 'view']\n"
                "call(['gh', 'api'])\n"
                "nested = {'commands': [['gh', 'pr', 'view']]}\n"
            )
        },
    )

    assert lgal.main(["--root", str(tmp_path)]) == 1
    assert capsys.readouterr().err.splitlines() == [
        'python/prod.py: line 1 contains raw ["gh", ...] argv; use larch.git.gh instead',
        'python/prod.py: line 2 contains raw ["gh", ...] argv; use larch.git.gh instead',
        'python/prod.py: line 3 contains raw ["gh", ...] argv; use larch.git.gh instead',
    ]


def test_non_matching_lists_and_tuple_route_keys_are_clean(tmp_path: Path) -> None:
    _write_project(
        tmp_path,
        files={
            "clean.py": (
                "empty = []\n"
                "not_first = ['git', 'gh']\n"
                "dynamic = [executable, 'issue']\n"
                "other = ['GH', 'issue']\n"
                "registry = {('gh', 'resolve-repo'): 'handler'}\n"
            )
        },
    )

    assert lgal.main(["--root", str(tmp_path)]) == 0


def test_git_wrapper_subtree_is_the_only_source_exemption(tmp_path: Path) -> None:
    _write_project(
        tmp_path,
        files={
            "larch/git/gh.py": "argv = ['gh', 'api']\n",
            "larch/git/nested/helper.py": "argv = ['gh', 'api']\n",
            "larch/other.py": "argv = ['gh', 'api']\n",
        },
    )

    assert lgal.main(["--root", str(tmp_path)]) == 1


def test_fixture_pragma_requires_same_line_non_empty_reason(tmp_path: Path) -> None:
    _write_project(
        tmp_path,
        files={
            "tests/ok.py": "argv = ['gh', 'api']  # lint-gh-argv-literal: ok assertion fixture\n",
            "tests/empty.py": "argv = ['gh', 'api']  # lint-gh-argv-literal: ok\n",
            "tests/previous.py": "# lint-gh-argv-literal: ok previous line\nargv = ['gh', 'api']\n",
            "tests/string.py": "note = '# lint-gh-argv-literal: ok string text'\nargv = ['gh', 'api']\n",
        },
    )

    assert lgal.main(["--root", str(tmp_path)]) == 1


def test_production_pragma_never_suppresses(tmp_path: Path) -> None:
    _write_project(
        tmp_path,
        files={
            "prod.py": "argv = ['gh', 'api']  # lint-gh-argv-literal: ok not a fixture\n"
        },
    )

    assert lgal.main(["--root", str(tmp_path)]) == 1


def test_test_support_files_remain_scanned(tmp_path: Path) -> None:
    _write_project(
        tmp_path,
        files={
            "tests/conftest.py": "argv = ['gh', 'api']\n",
            "tests/helpers.py": "argv = ['gh', 'api']\n",
        },
    )

    assert lgal.main(["--root", str(tmp_path)]) == 1


def test_diagnostics_sort_by_repository_relative_path_and_line(
    tmp_path: Path, capsys: CaptureFixture
) -> None:
    _write_project(
        tmp_path,
        files={
            "z.py": "one = ['gh']\n",
            "a.py": "one = ['gh']\ntwo = ['gh']\n",
        },
    )

    assert lgal.main(["--root", str(tmp_path)]) == 1
    lines = capsys.readouterr().err.splitlines()
    assert [line.split(" contains", maxsplit=1)[0] for line in lines] == [
        "python/a.py: line 1",
        "python/a.py: line 2",
        "python/z.py: line 1",
    ]


def test_clean_tree_and_missing_root_exit_codes(tmp_path: Path) -> None:
    _write_project(tmp_path, files={"clean.py": "value = ['git', 'status']\n"})

    assert lgal.main(["--root", str(tmp_path)]) == 0
    assert lgal.main(["--root", str(tmp_path / "missing")]) == 2


def test_invalid_python_and_non_utf8_source_fail_closed(tmp_path: Path) -> None:
    _write_project(tmp_path, files={"broken.py": "def broken(:\n"})
    assert lgal.main(["--root", str(tmp_path)]) == 2

    binary_root = tmp_path / "binary"
    path = binary_root / "python" / "binary.py"
    path.parent.mkdir(parents=True)
    _ = path.write_bytes(b"argv = ['gh']\n\xff\n")
    assert lgal.main(["--root", str(binary_root)]) == 2


def test_invalid_arguments_exit_2() -> None:
    assert lgal.main(["--unknown"]) == 2
