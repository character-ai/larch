"""Drift guard between the Rust and Python run-log batch registries.

`run-log write` and `run-log append` are Rust-owned (issue #8073), so
`crates/larch-core/src/run_log/batch.rs` is the registry the commands read. The
Python table in `larch.report.run_log_batch` still backs the flush, archive, and
publication verbs. Until those cut over, the two tables describe the same
artifacts and must agree on every field.
"""

from __future__ import annotations

import re
from pathlib import Path

from larch.report import run_log_batch

_RUST_REGISTRY = (
    Path(__file__).resolve().parents[3] / "crates" / "larch-core" / "src" / "run_log" / "batch.rs"
)

_SANITIZER_BY_RUST_NAME: dict[str, str] = {
    "Passthrough": "none",
    "JsonObject": "json-object",
    "JsonLines": "json-lines",
    "PlanGoals": "plan-goals",
}

_BATCH_CONSTANTS: dict[str, str] = {
    "BATCH_GUIDELINE_SHIP_OUTCOME": "architectural-guideline-outcome",
    "BATCH_INVARIANT_SHIP_OUTCOME": "architectural-invariant-outcome",
}

_ROW_RE = re.compile(
    r"\b(?P<kind>row|debate_row|capped_row)\(\s*"
    r'(?P<name>"[^"]+"|[A-Z_]+),\s*'
    r'"(?P<extension>[^"]*)",\s*'
    r"BatchMode::(?P<mode>Replace|Append),\s*"
    r"Sanitizer::(?P<sanitizer>Passthrough|JsonObject|JsonLines|PlanGoals)",
)


def _rust_registry() -> dict[str, tuple[str, str, str, bool]]:
    source = _RUST_REGISTRY.read_text(encoding="utf-8")
    body = source[source.index("static BATCHES") : source.index("/// Look up a batch")]
    rows: dict[str, tuple[str, str, str, bool]] = {}
    for match in _ROW_RE.finditer(body):
        raw_name = match.group("name")
        name = raw_name.strip('"') if raw_name.startswith('"') else _BATCH_CONSTANTS[raw_name]
        rows[name] = (
            match.group("extension"),
            match.group("mode").lower(),
            _SANITIZER_BY_RUST_NAME[match.group("sanitizer")],
            match.group("kind") == "debate_row",
        )
    return rows


def test_rust_registry_parses_every_declared_batch() -> None:
    rust = _rust_registry()
    assert len(rust) == len(run_log_batch._LARCH_LOG_BATCHES)  # pyright: ignore[reportPrivateUsage]


def test_rust_and_python_batch_registries_agree() -> None:
    rust = _rust_registry()
    python: dict[str, tuple[str, str, str, bool]] = {
        name: (info.extension, info.mode, info.sanitizer, info.reject_session_tmpdir)
        for name, info in run_log_batch._LARCH_LOG_BATCHES.items()  # pyright: ignore[reportPrivateUsage]
    }
    assert rust == python


def test_codex_transcript_is_the_only_capped_batch() -> None:
    source = _RUST_REGISTRY.read_text(encoding="utf-8")
    capped = _ROW_RE.finditer(source[source.index("static BATCHES") :])
    names = [
        match.group("name").strip('"')
        for match in capped
        if match.group("kind") == "capped_row"
    ]
    assert names == ["codex-impl-transcript"]
