"""Python-side parity pins for the Rust redaction fixtures."""

from __future__ import annotations

from pathlib import Path

from larch.core import redact

ROOT = Path(__file__).resolve().parents[3]
FIXTURES = ROOT / "fixtures" / "rust-redaction"


def _fixture_rows(name: str, columns: int) -> list[tuple[str, ...]]:
    rows: list[tuple[str, ...]] = []
    for line in (FIXTURES / name).read_text(encoding="utf-8").splitlines():
        if not line or line.startswith("#"):
            continue
        row = tuple(line.split("\t", maxsplit=columns - 1))
        assert len(row) == columns
        rows.append(row)
    return rows


def test_rust_secret_family_fixtures_match_live_python_contract() -> None:
    for family, prefix, suffix in _fixture_rows("secret-families.tsv", 3):
        secret = prefix + suffix
        text = secret if family == "pem-private-key" else f"before {secret} after"

        result = redact.scrub_log_secrets(text)

        assert result.findings[family] == 1
        assert secret not in result.scrubbed


def test_rust_sensitive_path_fixtures_match_live_python_contract() -> None:
    for input_text, expected in _fixture_rows("sensitive-paths.tsv", 2):
        assert redact.redact_tmpdir_paths(input_text) == expected
