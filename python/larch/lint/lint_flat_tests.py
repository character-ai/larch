"""Lint non-exempt flat python/test_*.py modules at repo root."""

from __future__ import annotations

from pathlib import Path

from larch.lint import lint_common
from larch.lint.lint_common import LintError

# Shared pytest helper, not a test module. All real tests belong under python/tests/.
EXEMPT_ROOT_TESTS = frozenset({"test_support.py"})
ROOT_TEST_PATTERN = "python/test_*.py"


def _rel(*, path: Path, root: Path) -> str:
    try:
        return str(path.relative_to(root))
    except ValueError:
        return str(path)


def _is_flat_root_test(path: Path, *, python_dir: Path) -> bool:
    try:
        is_file = path.is_file()
    except OSError as exc:
        raise LintError(f"lint-flat-tests: cannot stat {_rel(path=path, root=python_dir.parent)}: {exc}") from exc
    return is_file and path.parent == python_dir and path.name.startswith("test_") and path.suffix == ".py"


def find_flat_root_tests(root: Path) -> list[Path]:
    python_dir = root / "python"
    if not python_dir.exists():
        return []
    if lint_common.git_rooted(root):
        files = lint_common.git_ls_files_z(
            root=root,
            pattern=ROOT_TEST_PATTERN,
            error_prefix="lint-flat-tests: cannot enumerate git files",
        )
    else:
        try:
            files = list(python_dir.glob("test_*.py"))
        except OSError as exc:
            raise LintError(f"lint-flat-tests: cannot enumerate {python_dir}: {exc}") from exc
    return sorted(path for path in files if _is_flat_root_test(path, python_dir=python_dir))


def lint_file(*, path: Path, root: Path) -> list[str]:
    if path.name in EXEMPT_ROOT_TESTS:
        return []
    return [
        f"lint-flat-tests: {_rel(path=path, root=root)}: flat root tests are not allowed; "
        "move test modules under python/tests/ (only python/test_support.py is exempt as a shared pytest helper)"
    ]


def main(argv: list[str] | None = None) -> int:
    return lint_common.run_file_lint(
        argv,
        prog="lint-flat-tests",
        description=(__doc__ or "").splitlines()[0],
        iter_files=find_flat_root_tests,
        lint_file=lint_file,
    )


if __name__ == "__main__":
    raise SystemExit(main())
