"""Tests for redact.py including bash parity."""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

import pytest

import redact

REPO_ROOT = Path(__file__).resolve().parents[1]
SECRETS_SH = REPO_ROOT / "scripts" / "redact-secrets.sh"
TMPDIR_SH = REPO_ROOT / "scripts" / "redact-tmpdir-paths.sh"


def _bash_redact(helper: Path, text: str) -> str:
    proc = subprocess.run(
        [str(helper)],
        input=text,
        capture_output=True,
        text=True,
        check=False,
    )
    return proc.stdout


@pytest.mark.parametrize(
    "vector",
    [
        "sk-ant-abcdefghijklmnopqrstuvwxyz0123456789ABCD",
        "ghp_abcdefghijklmnopqrstuvwxyz0123456789ABCDEFGH",
        "AKIAIOSFODNN7EXAMPLE",
        "eyJhbGciOiJIUzI1NiJ9.eyJzdWIiOiIxMjM0NTY3ODkwIn0."
            "SflKxwRJSMeKKF2QT4fwpMeJf36POk6yJV_adQssw5c",
    ],
)
def test_secret_families(vector: str) -> None:
    out = redact.redact(vector)
    assert "<REDACTED-TOKEN>" in out
    assert vector not in out


def test_pem_block_redacted() -> None:
    pem = (
        "-----BEGIN RSA PRIVATE KEY-----\n"
        "MIIBOgIBAAJBAKj34GkxFhD90vcNLYLInFEX6Ppy1tPf9Cnzj4p4WGeKLs1Pt8Qu\n"
        "-----END RSA PRIVATE KEY-----"
    )
    out = redact.redact(pem)
    assert "<REDACTED-PRIVATE-KEY>" in out
    assert "MIIBOgIBAAJB" not in out


def test_unterminated_pem_fail_closed() -> None:
    body = (
        "opening text\n"
        "-----BEGIN RSA PRIVATE KEY-----\n"
        "MIIBOgIBAAJBAKj34GkxFhD90vcNLYLInFEX6Ppy1tPf9Cnzj4p4WGeKLs1Pt8Q\n"
        "tail-that-should-not-silently-survive"
    )
    out = redact.redact(body)
    assert "opening text" in out
    assert "<REDACTED-PRIVATE-KEY>" in out
    assert "content truncated" in out
    assert "tail-that-should-not-silently-survive" not in out


def test_tmpdir_and_operator_paths() -> None:
    assert redact.redact("/tmp/claude-implement-AbC123").rstrip("\n") == "<TMPDIR>"
    assert (
        redact.redact("/Users/example/larch3/scripts/foo.sh").rstrip("\n")
        == "<OPERATOR_REPO_PATH>/scripts/foo.sh"
    )


def test_idempotent() -> None:
    once = redact.redact("/tmp/larch-design-breadcrumbs.ABC123/private.txt")
    twice = redact.redact(once)
    assert once == twice


def test_tmpdir_redaction_precedes_secret_redaction() -> None:
    text = "/tmp/claude-implement-sk-ant-abcdefghijklmnopqrstuvwxyz0123456789ABCD/file"
    out = redact.redact(text)
    assert out == "<TMPDIR>/file\n"
    assert "<REDACTED-TOKEN>" not in out


def _parity_normalize(text: str) -> str:
    return text.rstrip("\n")


@pytest.mark.skipif(
    not SECRETS_SH.is_file() or shutil.which("bash") is None,
    reason="bash or redact-secrets.sh unavailable",
)
def test_parity_redact_secrets_sample() -> None:
    vector = "prefix sk-ant-abcdefghijklmnopqrstuvwxyz0123456789ABCD suffix"
    py_out = redact.redact(vector)
    bash_out = _bash_redact(SECRETS_SH, vector)
    assert _parity_normalize(py_out) == _parity_normalize(bash_out)


@pytest.mark.skipif(
    not TMPDIR_SH.is_file() or shutil.which("bash") is None,
    reason="bash or redact-tmpdir-paths.sh unavailable",
)
def test_parity_redact_tmpdir_sample() -> None:
    vector = "/tmp/claude-implement-larch1-G2GITf"
    py_out = redact.redact(vector)
    bash_out = _bash_redact(TMPDIR_SH, vector)
    assert _parity_normalize(py_out) == _parity_normalize(bash_out)
