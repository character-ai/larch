"""Python-side parity pins for the Rust I/O golden fixtures."""

from __future__ import annotations

import stat
from pathlib import Path

from larch import io as larch_io

ROOT = Path(__file__).resolve().parents[3]
FIXTURES = ROOT / "fixtures" / "rust-io"


def test_rust_kv_fixture_matches_live_python_duplicate_and_cr_contracts() -> None:
    text = larch_io.read_text(FIXTURES / "kv-input.env", errors="strict")

    assert larch_io.kv_value(text=text, key="KEEP", duplicate_policy="first") == "one=two"
    assert larch_io.kv_value(text=text, key="KEEP", duplicate_policy="last") == "last"
    assert larch_io.kv_value(text=text, key="EMPTY", duplicate_policy="last-non-empty") == "before"
    assert larch_io.parse_kv(text, duplicate_policy="all")["KEEP"] == ["one=two", "last"]
    assert larch_io.parse_kv(text)["LONE"] == "one\rTWO=two"
    assert larch_io.parse_kv("A=one\r\nB=two\r\n") == {"A": "one", "B": "two"}


def test_rust_render_goldens_match_live_python_exact_bytes() -> None:
    rendered = larch_io.format_kvs([("B", "two=2"), ("A", "one")], sort_keys=True)
    assert rendered.encode() == (FIXTURES / "kv-render.golden").read_bytes()

    env = larch_io.parse_kv("B=old\nA=keep\n", duplicate_policy="last")
    env.update({"B": "new", "C": "three"})
    assert larch_io.format_kvs(env, sort_keys=True).encode() == (
        FIXTURES / "env-update.golden"
    ).read_bytes()


def test_rust_atomic_contract_matches_live_python_publication(tmp_path: Path) -> None:
    destination = tmp_path / "state.env"
    expected = (FIXTURES / "env-update.golden").read_text(encoding="utf-8")

    larch_io.atomic_write(destination, expected, mode=0o600, prefix=".state.")

    assert destination.read_bytes() == expected.encode()
    assert stat.S_IMODE(destination.stat().st_mode) == 0o600
    assert not list(tmp_path.glob(".state.*.tmp"))
