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
import hashlib
import itertools
import json
import multiprocessing
import os
import stat
import sys
from collections.abc import Callable, Generator, Iterable, Iterator, Sequence
from concurrent.futures import ProcessPoolExecutor
from dataclasses import dataclass
from pathlib import Path
from types import MethodType
from typing import Any, Final, TextIO, cast

MESSAGE_ID = "R0801"
# pylint ``Run`` returns ``linter.msg_status`` when score is below fail-under;
# R0801 sets the refactor bit (8).
REFACTOR_MSG_STATUS = 8
DEFAULT_ROOT = "python"
DEFAULT_RCFILE = "python/.pylintrc"
DEFAULT_BASELINE = "python/duplicate-code-baseline.json"
HASH_PREFIX_LEN: Final = 16
CONTENT_HASH_SEPARATOR: Final = "\0"
MODULE_PAIR_SIZE: Final = 2
BASELINE_RECORD_KEYS: Final = frozenset({"modules", "hash", "lines", "normalized_lines", "reason"})
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
class DuplicateObservation:
    """One unmerged Pylint commonality with a durable content identity."""

    modules: tuple[str, str]
    normalized_lines: tuple[str, ...]
    content_hash: str

    @property
    def lines(self) -> int:
        return len(self.normalized_lines)


@dataclass(frozen=True)
class BaselineRecord:
    """One reason-bearing allowance for a durable duplicate observation."""

    modules: tuple[str, str]
    content_hash: str
    lines: int
    normalized_lines: tuple[str, ...]
    reason: str


@dataclass(frozen=True)
class BaselineEvaluation:
    """Injective baseline matching outcome, including diagnostics for CI."""

    accepted: tuple[tuple[DuplicateObservation, BaselineRecord], ...]
    new: tuple[DuplicateObservation, ...]
    grown: tuple[DuplicateObservation, ...]
    stale: tuple[BaselineRecord, ...]

    @property
    def exit_code(self) -> int:
        return 0 if not (self.new or self.grown or self.stale) else 1


@dataclass(frozen=True)
class DuplicateCodeResult:
    exit_code: int
    clusters: tuple[DuplicateCluster, ...]
    digest: str
    findings: str
    files: tuple[str, ...]
    pair_count: int
    observations: tuple[DuplicateObservation, ...] = ()


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
    include_clusters: bool = True,
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
        observations = _observations_from_commonalities(commonalities)
        if include_clusters:
            clusters = _clusters_from_commonalities(symilar=checker, commonalities=commonalities)
            exit_code = _exit_code_like_pylint(linter=linter, checker=checker)
        else:
            clusters = []
            exit_code = 0
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
        observations=tuple(observations),
    )


def _observations_from_commonalities(commonalities: Sequence[Any]) -> list[DuplicateObservation]:
    """Extract stable identities before Pylint merges commonalities for display."""
    observations: list[DuplicateObservation] = []
    observed_by_identity: dict[tuple[tuple[str, str], str], DuplicateObservation] = {}
    hash_text: dict[str, tuple[str, ...]] = {}
    for commonality in commonalities:
        first_lines = _commonality_normalized_lines(
            lineset=commonality.fst_lset,
            start_line=int(commonality.fst_file_start),
            line_count=int(commonality.cmn_lines_nb),
        )
        second_lines = _commonality_normalized_lines(
            lineset=commonality.snd_lset,
            start_line=int(commonality.snd_file_start),
            line_count=int(commonality.cmn_lines_nb),
        )
        if first_lines != second_lines:
            raise DuplicateCodeError("duplicate-code normalized commonality text differs between modules")
        first_name = str(commonality.fst_lset.name)
        second_name = str(commonality.snd_lset.name)
        if first_name == second_name:
            raise DuplicateCodeError("duplicate-code commonality unexpectedly references one module twice")
        sorted_modules = sorted((first_name, second_name))
        modules: tuple[str, str] = (sorted_modules[0], sorted_modules[1])
        content_hash = _content_hash(first_lines)
        identity = (modules, content_hash)
        existing = observed_by_identity.get(identity)
        if existing is not None:
            if existing.normalized_lines != first_lines:
                raise DuplicateCodeError(
                    "duplicate-code live identity collision: "
                    f"{modules[0]} <-> {modules[1]} ({content_hash})"
                )
            # Pylint can emit more than one positional commonality for the
            # same durable pair-and-content identity. Positions are expressly
            # excluded from this baseline, so retain one canonical observation.
            continue
        prior_text = hash_text.setdefault(content_hash, first_lines)
        if prior_text != first_lines:
            raise DuplicateCodeError(
                f"duplicate-code content hash-prefix collision: {content_hash}"
            )
        observation = DuplicateObservation(
            modules=modules,
            normalized_lines=first_lines,
            content_hash=content_hash,
        )
        observed_by_identity[identity] = observation
        observations.append(observation)
    return sorted(observations, key=_observation_sort_key)


def _commonality_normalized_lines(*, lineset: Any, start_line: int, line_count: int) -> tuple[str, ...]:
    """Slice the canonical Pylint ``stripped_lines`` span for one commonality."""
    if line_count < 1:
        raise DuplicateCodeError("duplicate-code commonality has no normalized lines")
    start_indices = [
        index
        for index, line in enumerate(lineset.stripped_lines)
        if int(line.line_number) == start_line
    ]
    if len(start_indices) != 1:
        raise DuplicateCodeError(
            "duplicate-code canonical normalized span unavailable: "
            f"{lineset.name!s}:{start_line}"
        )
    normalized = tuple(
        str(line.text)
        for line in lineset.stripped_lines[start_indices[0] : start_indices[0] + line_count]
    )
    if len(normalized) != line_count or not all(normalized):
        raise DuplicateCodeError(
            "duplicate-code canonical normalized span is incomplete: "
            f"{lineset.name!s}:{start_line}"
        )
    if any(CONTENT_HASH_SEPARATOR in line for line in normalized):
        raise DuplicateCodeError("duplicate-code normalized text contains the hash separator")
    return normalized


def _content_hash(normalized_lines: Sequence[str]) -> str:
    """Return the fixed-width identity hash for Pylint-normalized common text."""
    if not normalized_lines:
        raise DuplicateCodeError("duplicate-code cannot hash an empty normalized block")
    encoded = CONTENT_HASH_SEPARATOR.join(normalized_lines).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()[:HASH_PREFIX_LEN]


def _observation_sort_key(observation: DuplicateObservation) -> tuple[tuple[str, str], str]:
    return observation.modules, observation.content_hash


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


def _read_baseline(*, path: Path, allow_missing: bool) -> tuple[BaselineRecord, ...]:
    """Load a strict, non-symlinked reason-bearing baseline."""
    try:
        metadata = path.lstat()
    except FileNotFoundError:
        if allow_missing:
            return ()
        raise DuplicateCodeError(f"missing duplicate-code baseline: {path}") from None
    except OSError as exc:
        raise DuplicateCodeError(f"unable to inspect duplicate-code baseline {path}: {exc}") from exc
    if stat.S_ISLNK(metadata.st_mode) or not stat.S_ISREG(metadata.st_mode):
        raise DuplicateCodeError(f"duplicate-code baseline must be a regular non-symlink file: {path}")
    try:
        with path.open(encoding="utf-8") as handle:
            payload: object = json.load(handle)
    except (OSError, json.JSONDecodeError) as exc:
        raise DuplicateCodeError(f"invalid duplicate-code baseline {path}: {exc}") from exc
    if not isinstance(payload, list):
        raise DuplicateCodeError("duplicate-code baseline must contain a top-level array")

    records: list[BaselineRecord] = []
    seen: set[tuple[tuple[str, str], str]] = set()
    hash_text: dict[str, tuple[str, ...]] = {}
    for index, raw_record in enumerate(payload):
        record = _parse_baseline_record(raw_record=raw_record, index=index)
        identity = (record.modules, record.content_hash)
        if identity in seen:
            raise DuplicateCodeError(
                "duplicate-code baseline contains a duplicate identity: "
                f"{record.modules[0]} <-> {record.modules[1]} ({record.content_hash})"
            )
        previous = hash_text.setdefault(record.content_hash, record.normalized_lines)
        if previous != record.normalized_lines:
            raise DuplicateCodeError(
                f"duplicate-code baseline content hash-prefix collision: {record.content_hash}"
            )
        seen.add(identity)
        records.append(record)
    return tuple(sorted(records, key=_record_sort_key))


def _parse_baseline_record(*, raw_record: object, index: int) -> BaselineRecord:
    if not isinstance(raw_record, dict):
        raise DuplicateCodeError(
            f"duplicate-code baseline row {index} must have exactly "
            f"{', '.join(sorted(BASELINE_RECORD_KEYS))}"
        )
    record_payload = cast("dict[str, object]", raw_record)
    if frozenset(record_payload) != BASELINE_RECORD_KEYS:
        raise DuplicateCodeError(
            f"duplicate-code baseline row {index} must have exactly "
            f"{', '.join(sorted(BASELINE_RECORD_KEYS))}"
        )
    raw_modules = record_payload["modules"]
    if (
        not isinstance(raw_modules, list)
        or len(raw_modules) != MODULE_PAIR_SIZE
        or not all(isinstance(module, str) and module.strip() == module and module for module in raw_modules)
        or raw_modules[0] >= raw_modules[1]
    ):
        raise DuplicateCodeError(f"duplicate-code baseline row {index} has invalid sorted modules")
    raw_lines = record_payload["normalized_lines"]
    if (
        not isinstance(raw_lines, list)
        or not raw_lines
        or not all(isinstance(line, str) and line and CONTENT_HASH_SEPARATOR not in line for line in raw_lines)
    ):
        raise DuplicateCodeError(f"duplicate-code baseline row {index} has invalid normalized_lines")
    raw_allowance = record_payload["lines"]
    if not isinstance(raw_allowance, int) or isinstance(raw_allowance, bool) or raw_allowance != len(raw_lines):
        raise DuplicateCodeError(
            f"duplicate-code baseline row {index} has lines inconsistent with normalized_lines"
        )
    raw_hash = record_payload["hash"]
    if (
        not isinstance(raw_hash, str)
        or len(raw_hash) != HASH_PREFIX_LEN
        or any(character not in "0123456789abcdef" for character in raw_hash)
    ):
        raise DuplicateCodeError(f"duplicate-code baseline row {index} has invalid hash")
    normalized_lines = tuple(raw_lines)
    if raw_hash != _content_hash(normalized_lines):
        raise DuplicateCodeError(f"duplicate-code baseline row {index} hash does not match normalized_lines")
    raw_reason = record_payload["reason"]
    if not isinstance(raw_reason, str) or not raw_reason.strip():
        raise DuplicateCodeError(f"duplicate-code baseline row {index} has a blank reason")
    return BaselineRecord(
        modules=(raw_modules[0], raw_modules[1]),
        content_hash=raw_hash,
        lines=raw_allowance,
        normalized_lines=normalized_lines,
        reason=raw_reason,
    )


def _record_sort_key(record: BaselineRecord) -> tuple[tuple[str, str], str]:
    return record.modules, record.content_hash


def _evaluate_baseline(
    *, observations: Sequence[DuplicateObservation], records: Sequence[BaselineRecord]
) -> BaselineEvaluation:
    """Classify live observations with exact-first, injective shrink matching."""
    records_by_identity = {(record.modules, record.content_hash): record for record in records}
    accepted: list[tuple[DuplicateObservation, BaselineRecord]] = []
    residual_observations: list[DuplicateObservation] = []
    consumed_records: set[BaselineRecord] = set()
    for observation in observations:
        exact = records_by_identity.get((observation.modules, observation.content_hash))
        if exact is None:
            residual_observations.append(observation)
            continue
        if observation.normalized_lines != exact.normalized_lines:
            raise DuplicateCodeError(
                "duplicate-code baseline identity hash maps to different normalized text: "
                f"{observation.content_hash}"
            )
        accepted.append((observation, exact))
        consumed_records.add(exact)

    residual_records = [record for record in records if record not in consumed_records]
    candidate_map: dict[DuplicateObservation, tuple[BaselineRecord, ...]] = {
        observation: tuple(
            record
            for record in residual_records
            if _is_shrink_candidate(observation=observation, record=record)
        )
        for observation in residual_observations
    }
    candidate_observations = [
        observation for observation in residual_observations if candidate_map[observation]
    ]
    shrink_matches = _unique_injective_matches(candidate_map=candidate_map, observations=candidate_observations)
    accepted.extend(shrink_matches)
    consumed_records.update(record for _, record in shrink_matches)
    matched_observations = {observation for observation, _ in shrink_matches}

    new: list[DuplicateObservation] = []
    grown: list[DuplicateObservation] = []
    for observation in residual_observations:
        if observation in matched_observations:
            continue
        if any(_is_growth(observation=observation, record=record) for record in residual_records):
            grown.append(observation)
        else:
            new.append(observation)
    stale = [record for record in records if record not in consumed_records]
    return BaselineEvaluation(
        accepted=tuple(sorted(accepted, key=lambda item: _observation_sort_key(item[0]))),
        new=tuple(sorted(new, key=_observation_sort_key)),
        grown=tuple(sorted(grown, key=_observation_sort_key)),
        stale=tuple(sorted(stale, key=_record_sort_key)),
    )


def _is_shrink_candidate(*, observation: DuplicateObservation, record: BaselineRecord) -> bool:
    return (
        observation.modules == record.modules
        and observation.lines <= record.lines
        and _contains_window(haystack=record.normalized_lines, needle=observation.normalized_lines)
    )


def _is_growth(*, observation: DuplicateObservation, record: BaselineRecord) -> bool:
    return (
        observation.modules == record.modules
        and observation.lines > record.lines
        and _contains_window(haystack=observation.normalized_lines, needle=record.normalized_lines)
    )


def _contains_window(*, haystack: Sequence[str], needle: Sequence[str]) -> bool:
    width = len(needle)
    return width > 0 and any(tuple(haystack[index : index + width]) == tuple(needle) for index in range(len(haystack) - width + 1))


def _unique_injective_matches(
    *,
    candidate_map: dict[DuplicateObservation, tuple[BaselineRecord, ...]],
    observations: Sequence[DuplicateObservation],
) -> tuple[tuple[DuplicateObservation, BaselineRecord], ...]:
    """Return the sole full matching, rejecting ambiguity and surplus observations."""
    if not observations:
        return ()
    ordered = tuple(sorted(observations, key=lambda item: (len(candidate_map[item]), _observation_sort_key(item))))
    matchings: list[tuple[tuple[DuplicateObservation, BaselineRecord], ...]] = []

    def search(index: int, used: frozenset[BaselineRecord], matched: tuple[tuple[DuplicateObservation, BaselineRecord], ...]) -> None:
        if len(matchings) > 1:
            return
        if index == len(ordered):
            matchings.append(matched)
            return
        observation = ordered[index]
        for record in candidate_map[observation]:
            if record not in used:
                search(index + 1, used | {record}, (*matched, (observation, record)))

    search(0, frozenset(), ())
    if not matchings:
        raise DuplicateCodeError("duplicate-code baseline shrink matching has surplus observations")
    if len(matchings) > 1:
        raise DuplicateCodeError("duplicate-code baseline shrink matching is ambiguous")
    return matchings[0]


def _render_baseline_diagnostics(evaluation: BaselineEvaluation) -> str:
    diagnostics: list[str] = []
    for label, items in (("new", evaluation.new), ("grown", evaluation.grown)):
        diagnostics.extend(
            f"duplicate-code baseline {label}: {observation.modules[0]} <-> "
            f"{observation.modules[1]} ({observation.lines} normalized lines, {observation.content_hash})"
            for observation in items
        )
    diagnostics.extend(
        f"duplicate-code baseline stale: {record.modules[0]} <-> {record.modules[1]} "
        f"({record.lines} normalized lines, {record.content_hash})"
        for record in evaluation.stale
    )
    if diagnostics:
        diagnostics.append("Regenerate with make regen-duplicate-code-baseline after resolving or documenting changes.")
    return "\n".join(diagnostics) + ("\n" if diagnostics else "")


def _write_baseline(
    *, path: Path, observations: Sequence[DuplicateObservation], initial_reason: str | None
) -> None:
    records = _read_baseline(path=path, allow_missing=True)
    evaluation = _evaluate_baseline(observations=observations, records=records)
    reasons = {observation: record.reason for observation, record in evaluation.accepted}
    new_observations = [observation for observation in observations if observation not in reasons]
    if new_observations and initial_reason is None:
        raise DuplicateCodeError("--write found new duplicate-code identities; provide --initial-reason")
    if initial_reason is not None and not initial_reason.strip():
        raise DuplicateCodeError("--initial-reason must be non-empty")
    payload = [
        {
            "modules": list(observation.modules),
            "hash": observation.content_hash,
            "lines": observation.lines,
            "normalized_lines": list(observation.normalized_lines),
            "reason": reasons.get(observation, initial_reason),
        }
        for observation in sorted(observations, key=_observation_sort_key)
    ]
    path.parent.mkdir(parents=True, exist_ok=True)
    serialized = json.dumps(payload, indent=2, ensure_ascii=False) + "\n"
    try:
        path.write_text(serialized, encoding="utf-8")
    except OSError as exc:
        raise DuplicateCodeError(f"failed to write duplicate-code baseline {path}: {exc}") from exc


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
    parser.add_argument(
        "--baseline",
        default=DEFAULT_BASELINE,
        help="Reason-bearing shrink-only baseline JSON path.",
    )
    parser.add_argument(
        "--write",
        action="store_true",
        help="Regenerate the duplicate-code baseline from live observations.",
    )
    parser.add_argument(
        "--initial-reason",
        help="Reason required for new identities while regenerating a baseline.",
    )
    return parser


def duplicate_code_main(argv: Sequence[str] | None = None) -> int:
    parser = _build_parser()
    try:
        args = parser.parse_args(list(argv) if argv is not None else None)
        emit_digest = bool(args.emit_cluster_digest)
        write_baseline = bool(args.write)
        initial_reason = None if args.initial_reason is None else str(args.initial_reason)
        if initial_reason is not None and not write_baseline:
            raise DuplicateCodeError("--initial-reason requires --write")
        if write_baseline and emit_digest:
            raise DuplicateCodeError("--write cannot be combined with --emit-cluster-digest")
        result = run_duplicate_code(
            root=Path(str(args.root)),
            rcfile=Path(str(args.rcfile)),
            jobs=args.jobs if args.jobs is None else int(args.jobs),
            stdout=None if emit_digest or write_baseline else sys.stdout,
            include_clusters=emit_digest,
        )
        if emit_digest:
            print(result.digest)
            return result.exit_code
        baseline_path = Path(str(args.baseline))
        if write_baseline:
            _write_baseline(
                path=baseline_path,
                observations=result.observations,
                initial_reason=initial_reason,
            )
            return 0
        records = _read_baseline(path=baseline_path, allow_missing=False)
        evaluation = _evaluate_baseline(observations=result.observations, records=records)
        diagnostics = _render_baseline_diagnostics(evaluation)
        if diagnostics:
            print(diagnostics, file=sys.stderr, end="")
        return evaluation.exit_code
    except DuplicateCodeError as exc:
        print(f"duplicate-code: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(duplicate_code_main())
