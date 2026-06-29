# pyright: reportPrivateUsage=false, reportUnusedCallResult=false
# ruff: noqa: PLR2004
"""review gather-context command."""

from __future__ import annotations

import re
import shutil
from pathlib import Path

from larch.core import logging_util
from larch.review.review_pipeline_shared import (
    _emit_kv,
    _get,
    _parse_args,
    _run_capture,
    _run_python_cli,
)


def _valid_rel_file(path: str) -> bool:
    if not path or path.startswith("/") or ".." in path or any(ch in path for ch in "\n\r\t"):
        return False
    return Path(path).is_file() and not Path(path).is_symlink()


def gather_context(argv: list[str]) -> int:
    logging_util.quiet_init(argv0="review-gather-context")
    usage = "Usage: review gather-context --mode diff|description --output-dir DIR [--description-text TEXT --scope-files FILE]"
    parsed = _parse_args(argv=argv, usage=usage, options={"--mode", "--output-dir", "--description-text", "--scope-files"})
    if parsed is None:
        return 0
    if not parsed:
        return 2
    mode = _get(parsed=parsed, key="--mode")
    output_dir = Path(_get(parsed=parsed, key="--output-dir"))
    description_text = _get(parsed=parsed, key="--description-text")
    scope_files = _get(parsed=parsed, key="--scope-files")
    if mode not in {"diff", "description"}:
        logging_util.diagnostic("review gather-context: --mode must be diff or description")
        return 2
    if not str(output_dir):
        logging_util.diagnostic("review gather-context: --output-dir is required")
        return 2
    output_dir.mkdir(parents=True, exist_ok=True)
    if mode == "diff":
        branch_context_env = output_dir / "gather-branch-context.env"
        result = _run_python_cli(["agent", "gather-branch-context", "--output-dir", str(output_dir)])
        from larch import io as larch_io  # noqa: PLC0415
        larch_io.write_text(path=branch_context_env, text=result.stdout)
        for line in result.stdout.splitlines():
            logging_util.emit(line)
        if result.stderr:
            for line in result.stderr.splitlines():
                logging_util.diagnostic(line)
        _emit_kv(key="SCOPE_FILES_COUNT", value=0)
        _emit_kv(key="MODE", value="diff")
        return result.returncode

    file_list = Path(scope_files) if scope_files else output_dir / "scope-files.txt"
    file_list.parent.mkdir(parents=True, exist_ok=True)
    file_list.write_text("", encoding="utf-8")
    tokens = [token.lower() for token in re.split(r"[^A-Za-z0-9_./-]+", description_text) if len(token) >= 3]
    tokens = tokens[:20]
    matches: set[str] = set()
    if tokens:
        git_result = _run_capture(["git", "ls-files"])
        for path in git_result.stdout.splitlines():
            lower = path.lower()
            if any(token in lower for token in tokens) and _valid_rel_file(path):
                matches.add(path)
    if not matches and description_text:
        rg = shutil.which("rg")
        if rg:
            rg_result = _run_capture([rg, "-l", "--fixed-strings", "--ignore-case", "--", description_text, "."])
            for raw in rg_result.stdout.splitlines():
                path = raw.removeprefix("./")
                if _valid_rel_file(path):
                    matches.add(path)
    file_list.write_text("".join(f"{path}\n" for path in sorted(matches)), encoding="utf-8")
    _emit_kv(key="DIFF_FILE", value="")
    _emit_kv(key="FILE_LIST_FILE", value=file_list)
    _emit_kv(key="COMMIT_LOG_FILE", value="")
    _emit_kv(key="COMMIT_COUNT", value=0)
    _emit_kv(key="SCOPE_FILES_COUNT", value=len(matches))
    _emit_kv(key="MODE", value="description")
    return 0


def gather_context_main(argv: list[str]) -> int:
    return gather_context(argv)
