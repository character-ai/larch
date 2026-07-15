"""CLI entry point for the bare grep probe lint."""
from __future__ import annotations
from larch.lint.shell_lints import main
def main_entry(argv: list[str] | None = None) -> int:
    return main("bare-grep-probe", argv)
