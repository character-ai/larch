"""CLI entry point for the Bash 3.2 compatibility lint."""
from __future__ import annotations
from larch.lint.shell_lints import main
def main_entry(argv: list[str] | None = None) -> int:
    return main("bash32", argv)
