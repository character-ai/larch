# pyright: reportUnknownVariableType=false, reportUnknownMemberType=false, reportUnknownArgumentType=false, reportPrivateUsage=false, reportUnknownLambdaType=false, reportUnusedCallResult=false, reportOptionalMemberAccess=false, reportMissingTypeStubs=false
# ruff: noqa: PLC0415, PLW0603, SLF001
"""Parallel duplicate-code lint runner for pylint==4.0.5.

This module delegates similarity semantics to Pylint 4.0.5's symilar engine.
Pylint reports duplicate-code only when ``filter_noncode_lines`` finds an
effective common block that is strictly greater than
``namespace.min_similarity_lines``.
"""

from __future__ import annotations

import argparse
import configparser
import contextlib
import itertools
import json
import multiprocessing
import os
import sys
from collections.abc import Callable, Generator, Iterable, Iterator, Sequence
from concurrent.futures import ProcessPoolExecutor
from dataclasses import dataclass
from pathlib import Path
from types import MethodType
from typing import Any, TextIO

MESSAGE_ID = "R0801"
# pylint ``Run`` returns ``linter.msg_status`` when score is below fail-under;
# R0801 sets the refactor bit (8).
REFACTOR_MSG_STATUS = 8
DEFAULT_ROOT = "python"
DEFAULT_RCFILE = "python/.pylintrc"
SIMILARITY_FLAGS = (
    "ignore-comments",
    "ignore-docstrings",
    "ignore-imports",
    "ignore-signatures",
)

_worker_symilar: Any | None = None
_worker_linesets: Sequence[Any] | None = None


@dataclass(frozen=True)
class DuplicateCodeConfig:
    root: Path
    rcfile: Path
    min_similarity_lines: int
    ignore_comments: bool
    ignore_docstrings: bool
    ignore_imports: bool
    ignore_signatures: bool
    ignore: tuple[str, ...]
    ignore_patterns: tuple[str, ...]
    ignore_paths: tuple[str, ...]

    @classmethod
    def load(cls, *, root: Path, rcfile: Path) -> DuplicateCodeConfig:
        if not rcfile.is_file():
            raise DuplicateCodeError(f"missing rcfile: {rcfile}")
        parser = configparser.ConfigParser(inline_comment_prefixes=("#", ";"), strict=False)
        try:
            with rcfile.open(encoding="utf-8") as handle:
                parser.read_file(handle)
        except configparser.Error as exc:
            raise DuplicateCodeError(f"invalid rcfile {rcfile}: {exc}") from exc

        similarities = parser["SIMILARITIES"] if parser.has_section("SIMILARITIES") else {}
        main = parser["MAIN"] if parser.has_section("MAIN") else {}
        min_lines_text = similarities.get("min-similarity-lines", "4")
        try:
            min_lines = int(min_lines_text)
        except ValueError as exc:
            raise DuplicateCodeError(
                f"invalid min-similarity-lines {min_lines_text!r}: expected integer"
            ) from exc
        if min_lines < 1:
            raise DuplicateCodeError("invalid min-similarity-lines: expected positive integer")

        flags = {
            name.replace("-", "_"): _parse_yn(similarities.get(name, "yes"))
            for name in SIMILARITY_FLAGS
        }
        return cls(
            root=root,
            rcfile=rcfile,
            min_similarity_lines=min_lines,
            ignore_comments=flags["ignore_comments"],
            ignore_docstrings=flags["ignore_docstrings"],
            ignore_imports=flags["ignore_imports"],
            ignore_signatures=flags["ignore_signatures"],
            ignore=_split_csv(main.get("ignore", "CVS")),
            ignore_patterns=_split_csv(main.get("ignore-patterns", "^\\.#")),
            ignore_paths=_split_csv(main.get("ignore-paths", "")),
        )


@dataclass(frozen=True)
class PylintBackend:
    PyLinter: Any
    FileState: Any
    TextReporter: Any
    _config_initialization: Callable[..., list[str]]
    utils: Any
    SimilaritiesChecker: Any
    astroid_exceptions: Any


@dataclass(frozen=True)
class DuplicateCluster:
    lines: int
    spans: tuple[tuple[str, int, int], ...]


@dataclass(frozen=True)
class DuplicateCodeResult:
    exit_code: int
    clusters: tuple[DuplicateCluster, ...]
    digest: str
    findings: str
    files: tuple[str, ...]
    pair_count: int


class DuplicateCodeError(Exception):
    """Expected runner failure that maps to exit code 2."""


def _split_csv(value: str) -> tuple[str, ...]:
    return tuple(part.strip() for part in value.replace("\n", ",").split(",") if part.strip())


def _parse_yn(value: str) -> bool:
    normalized = value.strip().lower()
    if normalized in {"yes", "true", "y"}:
        return True
    if normalized in {"no", "false", "n"}:
        return False
    raise DuplicateCodeError(f"invalid yn value {value!r}; expected yes/no")


def _import_pylint_backend() -> PylintBackend:
    try:
        from pylint.checkers.symilar import SimilaritiesChecker
        from pylint.lint import PyLinter
        from pylint.config.config_initialization import _config_initialization
        from pylint.reporters.text import TextReporter
        from pylint.utils import FileState
        from pylint.utils import utils
        import astroid.exceptions as astroid_exceptions
    except Exception as exc:  # pragma: no cover - monkeypatched in tests.
        raise DuplicateCodeError(f"failed to import pylint==4.0.5 backend: {exc}") from exc

    _assert_backend_api(SimilaritiesChecker)
    return PylintBackend(
        PyLinter=PyLinter,
        FileState=FileState,
        TextReporter=TextReporter,
        _config_initialization=_config_initialization,
        utils=utils,
        SimilaritiesChecker=SimilaritiesChecker,
        astroid_exceptions=astroid_exceptions,
    )


def _assert_backend_api(similarities_checker: Any) -> None:
    missing = [
        name
        for name in ("process_module", "open", "_find_common", "_compute_sims", "append_stream")
        if not hasattr(similarities_checker, name)
    ]
    if missing:
        raise DuplicateCodeError("pylint symilar API drift: missing " + ", ".join(missing))


@contextlib.contextmanager
def _pushd(path: Path) -> Generator[None]:
    previous = Path.cwd()
    os.chdir(path)
    try:
        yield
    finally:
        os.chdir(previous)


def _bootstrap_linter( *,config: DuplicateCodeConfig, backend: PylintBackend) -> tuple[Any, Any, list[Any]]:
    output = _StringSink()
    reporter = backend.TextReporter(output=output)
    linter = backend.PyLinter(reporter=reporter)
    linter.load_default_plugins()
    args = backend._config_initialization(
        linter,
        ["--disable=all", "--enable=duplicate-code", "--reports=no", "--persistent=no", "."],
        reporter=reporter,
        config_file=str(config.rcfile),
    )
    if not linter.is_message_enabled(MESSAGE_ID):
        raise DuplicateCodeError("pylint bootstrap failed to enable duplicate-code/R0801")
    linter.initialize()
    checker = _get_similarities_checker(linter=linter, backend=backend)
    _configure_checker_namespace(checker=checker, config=config)
    checker.open()
    fileitems = sorted(linter._iterate_file_descrs(args), key=lambda item: item.filepath)
    return linter, checker, fileitems


def _get_similarities_checker( *,linter: Any, backend: PylintBackend) -> Any:
    for checker in linter.get_checkers():
        if isinstance(checker, backend.SimilaritiesChecker):
            return checker
    raise DuplicateCodeError("pylint symilar API drift: SimilaritiesChecker not registered")


def _configure_checker_namespace( *,checker: Any, config: DuplicateCodeConfig) -> None:
    checker.namespace.min_similarity_lines = config.min_similarity_lines
    checker.namespace.ignore_comments = config.ignore_comments
    checker.namespace.ignore_docstrings = config.ignore_docstrings
    checker.namespace.ignore_imports = config.ignore_imports
    checker.namespace.ignore_signatures = config.ignore_signatures
    if hasattr(checker, "min_similarity_lines"):
        raise DuplicateCodeError("pylint symilar API drift: unexpected min_similarity_lines attribute")


def _ingest_files( *,linter: Any, checker: Any, fileitems: Sequence[Any], backend: PylintBackend) -> tuple[str, ...]:
    scanned: list[str] = []
    for fileitem in fileitems:
        linter.set_current_module(fileitem.name, fileitem.filepath)
        try:
            ast_node = linter.get_ast(fileitem.filepath, fileitem.name)
        except backend.astroid_exceptions.AstroidError as exc:
            raise DuplicateCodeError(f"astroid parse failed for {fileitem.filepath}: {exc}") from exc
        if ast_node is None:
            raise DuplicateCodeError(f"astroid parse failed for {fileitem.filepath}")
        if not ast_node.pure_python:
            continue
        linter._ignore_file = False
        linter.file_state = backend.FileState(fileitem.modpath, linter.msgs_store, ast_node)
        linter.current_file = ast_node.file
        try:
            tokens = backend.utils.tokenize_module(ast_node)
        except Exception as exc:
            raise DuplicateCodeError(f"tokenize failed for {fileitem.filepath}: {exc}") from exc
        linter.process_tokens(tokens)
        if linter._ignore_file:
            continue
        checker.process_module(ast_node)
        scanned.append(fileitem.filepath)
    return tuple(scanned)


def run_duplicate_code(
    *,
    root: Path,
    rcfile: Path,
    jobs: int | None = None,
    stdout: TextIO | None = None,
) -> DuplicateCodeResult:
    config = DuplicateCodeConfig.load(root=root.resolve(), rcfile=rcfile.resolve())
    backend = _import_pylint_backend()
    if not config.root.is_dir():
        raise DuplicateCodeError(f"missing root: {config.root}")
    with _pushd(config.root):
        linter, checker, fileitems = _bootstrap_linter(config=config, backend=backend)
        files = _ingest_files(linter=linter, checker=checker, fileitems=fileitems, backend=backend)
        linesets = tuple(checker.linesets)
        pairs: list[tuple[int, int]] = list(itertools.combinations(range(len(linesets)), 2))
        commonalities = _find_commonalities(symilar=checker, linesets=linesets, pairs=pairs, jobs=_resolve_jobs(requested=jobs, pair_count=len(pairs)))
        clusters = _clusters_from_commonalities(symilar=checker, commonalities=commonalities)
        exit_code = _exit_code_like_pylint(linter=linter, checker=checker)
    digest = _render_digest(clusters)
    findings = _render_findings(clusters)
    if stdout is not None and findings:
        stdout.write(findings)
    return DuplicateCodeResult(
        exit_code=exit_code,
        clusters=tuple(clusters),
        digest=digest,
        findings=findings,
        files=files,
        pair_count=len(pairs),
    )


def _resolve_jobs( *,requested: int | None, pair_count: int) -> int:
    if pair_count == 0:
        return 1
    value = requested
    if value is None:
        env_value = os.environ.get("LARCH_DUPLICATE_CODE_JOBS")
        if env_value:
            try:
                value = int(env_value)
            except ValueError as exc:
                raise DuplicateCodeError("invalid LARCH_DUPLICATE_CODE_JOBS: expected integer") from exc
    if value is None or value == 0:
        value = os.cpu_count() or 1
    if value < 1:
        raise DuplicateCodeError("invalid --jobs: expected 0 or positive integer")
    return min(value, pair_count)


def _find_commonalities( *,
    symilar: Any,
    linesets: Sequence[Any],
    pairs: Sequence[tuple[int, int]],
    jobs: int,
) -> list[Any]:
    if not pairs:
        return []
    if jobs == 1:
        return _find_common_chunk_with(symilar=symilar, linesets=linesets, pairs=pairs)
    chunks = _chunk_pairs(pairs=pairs, jobs=jobs)
    if "fork" in multiprocessing.get_all_start_methods():
        commonalities = _find_commonalities_fork(symilar=symilar, linesets=linesets, chunks=chunks, jobs=jobs)
    else:
        commonalities = _find_commonalities_spawn(symilar=symilar, linesets=linesets, chunks=chunks, jobs=jobs)
    return _canonicalize_commonalities(commonalities=commonalities, linesets=linesets)


def _canonicalize_commonalities( *,commonalities: Sequence[Any], linesets: Sequence[Any]) -> list[Any]:
    """Rebind worker-returned commonalities to the parent's LineSet objects.

    Workers return commonalities whose LineSet objects are unpickled copies.
    ``Symilar._compute_sims`` deduplicates couples in a set keyed by LineSet
    identity (``LineSet.__hash__`` is ``id``-based), so copies of the same file
    from different chunks never collapse. Rebinding every commonality to the one
    canonical LineSet per name restores serial dedup semantics.
    """
    canonical = {lineset.name: lineset for lineset in linesets}
    rebound: list[Any] = []
    for commonality in commonalities:
        fst_name = commonality.fst_lset.name
        snd_name = commonality.snd_lset.name
        if fst_name not in canonical:
            raise DuplicateCodeError(
                f"duplicate-code canonicalization failed: unknown lineset {fst_name!r}"
            )
        if snd_name not in canonical:
            raise DuplicateCodeError(
                f"duplicate-code canonicalization failed: unknown lineset {snd_name!r}"
            )
        rebound.append(
            commonality._replace(
                fst_lset=canonical[fst_name],
                snd_lset=canonical[snd_name],
            )
        )
    return rebound


def _chunk_pairs( *,pairs: Sequence[tuple[int, int]], jobs: int) -> list[list[tuple[int, int]]]:
    chunk_size = max(1, (len(pairs) + jobs - 1) // jobs)
    return [list(pairs[start : start + chunk_size]) for start in range(0, len(pairs), chunk_size)]


def _find_common_chunk_with( *,
    symilar: Any, linesets: Sequence[Any], pairs: Iterable[tuple[int, int]]
) -> list[Any]:
    commonalities: list[Any] = []
    for first, second in pairs:
        commonalities.extend(symilar._find_common(linesets[first], linesets[second]))
    return commonalities


def _worker_find_common_chunk(pairs: list[tuple[int, int]]) -> list[Any]:
    if _worker_symilar is None or _worker_linesets is None:
        raise RuntimeError("duplicate-code worker was not initialized")
    return _find_common_chunk_with(symilar=_worker_symilar, linesets=_worker_linesets, pairs=pairs)


def _spawn_worker_find_common_chunk(payload: tuple[Any, Sequence[Any], list[tuple[int, int]]]) -> list[Any]:
    symilar, linesets, pairs = payload
    return _find_common_chunk_with(symilar=symilar, linesets=linesets, pairs=pairs)


def _find_commonalities_fork( *,
    symilar: Any, linesets: Sequence[Any], chunks: Sequence[list[tuple[int, int]]], jobs: int
) -> list[Any]:
    global _worker_symilar, _worker_linesets
    _worker_symilar = symilar
    _worker_linesets = linesets
    context = multiprocessing.get_context("fork")
    try:
        # ``collected`` distinguishes a pool-startup OSError (fall back to serial)
        # from an OSError raised by pool teardown after results were already
        # collected: a teardown failure must not discard the results or recompute.
        commonalities: list[Any] = []
        collected = False
        try:
            with ProcessPoolExecutor(max_workers=jobs, mp_context=context) as executor:
                futures = [executor.submit(_worker_find_common_chunk, chunk) for chunk in chunks]
                commonalities = _collect_worker_results(futures)
                collected = True
        except OSError:
            if not collected:
                return _find_common_chunk_with(symilar=symilar, linesets=linesets, pairs=_flatten_pair_chunks(chunks))
        return commonalities
    finally:
        _worker_symilar = None
        _worker_linesets = None


def _find_commonalities_spawn( *,
    symilar: Any, linesets: Sequence[Any], chunks: Sequence[list[tuple[int, int]]], jobs: int
) -> list[Any]:
    payloads = [(symilar, linesets, chunk) for chunk in chunks]
    # ``collected`` distinguishes a pool-startup OSError (fall back to serial)
    # from an OSError raised by pool teardown after results were already
    # collected: a teardown failure must not discard the results or recompute.
    commonalities: list[Any] = []
    collected = False
    try:
        with ProcessPoolExecutor(max_workers=jobs) as executor:
            futures = [executor.submit(_spawn_worker_find_common_chunk, payload) for payload in payloads]
            commonalities = _collect_worker_results(futures)
            collected = True
    except OSError:
        if not collected:
            return _find_common_chunk_with(symilar=symilar, linesets=linesets, pairs=_flatten_pair_chunks(chunks))
    return commonalities


def _flatten_pair_chunks(chunks: Sequence[Sequence[tuple[int, int]]]) -> list[tuple[int, int]]:
    return [pair for chunk in chunks for pair in chunk]


def _collect_worker_results(futures: Sequence[Any]) -> list[Any]:
    commonalities: list[Any] = []
    for future in futures:
        try:
            commonalities.extend(future.result())
        except Exception as exc:
            raise DuplicateCodeError(f"duplicate-code worker failed: {exc}") from exc
    return commonalities


def _clusters_from_commonalities( *,symilar: Any, commonalities: Sequence[Any]) -> list[DuplicateCluster]:
    original_iter_sims = symilar._iter_sims

    def iter_sims(_self: Any) -> Iterator[Any]:
        yield from commonalities

    symilar._iter_sims = MethodType(iter_sims, symilar)
    try:
        sims = symilar._compute_sims()
    finally:
        symilar._iter_sims = original_iter_sims

    return _clusters_from_sims(sims)


def _clusters_from_sims(sims: Sequence[tuple[int, set[Any]]]) -> list[DuplicateCluster]:
    clusters: list[DuplicateCluster] = []
    for line_count, couples in sims:
        spans = tuple(
            sorted(
                (str(lineset.name), int(start_line), int(end_line))
                for lineset, start_line, end_line in couples
            )
        )
        clusters.append(DuplicateCluster(lines=int(line_count), spans=spans))
    return sorted(clusters, key=lambda cluster: cluster.spans)


def _exit_code_like_pylint( *,linter: Any, checker: Any) -> int:
    """Mirror pylint ``Run`` exit semantics after ``SimilaritiesChecker.close()``."""
    checker.close()
    score_value = linter.generate_reports(verbose=False)
    if linter.config.exit_zero:
        return 0
    if linter.any_fail_on_issues():
        return int(linter.msg_status or 1)
    if score_value is not None:
        if score_value >= linter.config.fail_under:
            return 0
        return int(linter.msg_status or 1)
    return int(linter.msg_status)


def _render_digest(clusters: Sequence[DuplicateCluster]) -> str:
    payload = [
        {"lines": cluster.lines, "spans": list(cluster.spans)}
        for cluster in clusters
    ]
    return json.dumps(payload, sort_keys=True, separators=(",", ":"))


def _render_findings(clusters: Sequence[DuplicateCluster]) -> str:
    if not clusters:
        return ""
    blocks: list[str] = []
    for cluster in clusters:
        header = f"duplicate-code: {len(cluster.spans)} similar blocks, {cluster.lines} lines"
        spans = "\n".join(f"=={name}:[{start}:{end}]" for name, start, end in cluster.spans)
        blocks.append(f"{header}\n{spans}")
    return "\n\n".join(blocks) + "\n"


class _StringSink:
    def __init__(self) -> None:
        self.parts: list[str] = []
        self.encoding = "utf-8"

    def write(self, text: str) -> int:
        self.parts.append(text)
        return len(text)

    def flush(self) -> None:
        return None


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run Pylint duplicate-code checks in parallel.")
    parser.add_argument("--root", default=DEFAULT_ROOT, help="Python source root to lint.")
    parser.add_argument("--rcfile", default=DEFAULT_RCFILE, help="Pylint rcfile to load.")
    parser.add_argument(
        "--jobs",
        type=int,
        default=None,
        help="Pair-comparison workers. 0 means auto; defaults to LARCH_DUPLICATE_CODE_JOBS or auto.",
    )
    parser.add_argument(
        "--emit-cluster-digest",
        action="store_true",
        help="Print the normalized reportable-cluster digest instead of findings.",
    )
    return parser


def duplicate_code_main(argv: Sequence[str] | None = None) -> int:
    parser = _build_parser()
    try:
        args = parser.parse_args(list(argv) if argv is not None else None)
        emit_digest = bool(args.emit_cluster_digest)
        result = run_duplicate_code(
            root=Path(str(args.root)),
            rcfile=Path(str(args.rcfile)),
            jobs=args.jobs if args.jobs is None else int(args.jobs),
            stdout=None if emit_digest else sys.stdout,
        )
        if emit_digest:
            print(result.digest)
        return result.exit_code
    except DuplicateCodeError as exc:
        print(f"duplicate-code: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(duplicate_code_main())
