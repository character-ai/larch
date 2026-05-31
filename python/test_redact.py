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


def _bash_redact_pipeline(text: str) -> str:
    tmpdir_proc = subprocess.run(
        [str(TMPDIR_SH)],
        input=text,
        capture_output=True,
        text=True,
        check=False,
    )
    secrets_proc = subprocess.run(
        [str(SECRETS_SH)],
        input=tmpdir_proc.stdout,
        capture_output=True,
        text=True,
        check=False,
    )
    return secrets_proc.stdout


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


@pytest.mark.parametrize(
    ("vector", "expected"),
    [
        ("cwd=/Users/example/foo,bar,", "cwd=<OPERATOR_REPO_PATH>,bar,"),
        ("cwd=/Users/example/foo;bar;", "cwd=<OPERATOR_REPO_PATH>;bar;"),
        ("cwd=/Users/example/foo:bar:", "cwd=<OPERATOR_REPO_PATH>:bar:"),
        ('{"cwd":"/Users/example/my}repo"}', '{"cwd":"/Users/example/my}repo"}'),
        (
            r"foo\n/Users/example/my,repo,",
            r"foo\n<OPERATOR_REPO_PATH>,repo,",
        ),
    ],
)
def test_operator_delimiter_repo_segments(vector: str, expected: str) -> None:
    assert redact.redact(vector).rstrip("\n") == expected


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
@pytest.mark.parametrize(
    "vector",
    [
        "/tmp/claude-implement-larch1-G2GITf",
        "/tmp/claude-implement-AbC123",
        "/Users/example/larch3/scripts/foo.sh",
        "cwd=/Users/example/my.repo,",
        'cwd=/home/example/my.repo,',
        '{"cwd":"/Users/example/my.repo"}',
        '{"cwd":"/Users/example/my.repo","x":1}',
        r"foo\n/Users/example/larch3/scripts/foo.sh",
        "cwd=/Users/example/foo,bar,",
        '{"cwd":"/Users/example/my}repo"}',
    ],
)
def test_parity_redact_tmpdir_vectors(vector: str) -> None:
    py_out = redact.redact(vector)
    bash_out = _bash_redact(TMPDIR_SH, vector)
    assert _parity_normalize(py_out) == _parity_normalize(bash_out)


@pytest.mark.skipif(
    not SECRETS_SH.is_file()
    or not TMPDIR_SH.is_file()
    or shutil.which("bash") is None,
    reason="bash redaction pipeline unavailable",
)
@pytest.mark.parametrize(
    "vector",
    [
        "sk-ant-abcdefghijklmnopqrstuvwxyz0123456789ABCD",
        "ghp_abcdefghijklmnopqrstuvwxyz0123456789ABCDEFGH",
        "AKIAIOSFODNN7EXAMPLE",
        "eyJhbGciOiJIUzI1NiJ9.eyJzdWIiOiIxMjM0NTY3ODkwIn0."
        "SflKxwRJSMeKKF2QT4fwpMeJf36POk6yJV_adQssw5c",
        "/tmp/claude-implement-larch1-G2GITf",
        "prefix sk-ant-abcdefghijklmnopqrstuvwxyz0123456789ABCD suffix",
    ],
)
def test_parity_redact_pipeline_vectors(vector: str) -> None:
    py_out = redact.redact(vector)
    bash_out = _bash_redact_pipeline(vector)
    assert _parity_normalize(py_out) == _parity_normalize(bash_out)


UNTERMINATED_BODY = (
    "opening text\n"
    "-----BEGIN RSA PRIVATE KEY-----\n"
    "MIIBOgIBAAJBAKj34GkxFhD90vcNLYLInFEX6Ppy1tPf9Cnzj4p4WGeKLs1Pt8Q\n"
    "KUpRKfFLfRYC9AIKjbJTWit+CqvjWYzvQwECAwEAAQJAIJLixBy2qpFoS4DSmoEm\n"
    "tail-that-should-not-silently-survive"
)

INDENTED_BODY = (
    "prefix line\n"
    "> -----BEGIN RSA PRIVATE KEY-----\n"
    "> MIIBOgIBAAJBAKj34GkxFhD90vcNLYLInFEX6Ppy1tPf9Cnzj4p4WGeKLs1Pt8Q\n"
    "> -----END RSA PRIVATE KEY-----\n"
    "    -----BEGIN OPENSSH PRIVATE KEY-----\n"
    "    b3BlbnNzaC1rZXktdjEAAAAABG5vbmUAAAAEbm9uZQAAAAAAAAABAAABlwAAAA\n"
    "    -----END OPENSSH PRIVATE KEY-----\n"
    "suffix line"
)


@pytest.mark.skipif(
    not SECRETS_SH.is_file()
    or not TMPDIR_SH.is_file()
    or shutil.which("bash") is None,
    reason="bash redaction pipeline unavailable",
)
def test_parity_unterminated_pem_pipeline() -> None:
    py_out = redact.redact(UNTERMINATED_BODY)
    bash_out = _bash_redact_pipeline(UNTERMINATED_BODY)
    assert _parity_normalize(py_out) == _parity_normalize(bash_out)
    assert "tail-that-should-not-silently-survive" not in py_out
    assert "content truncated" in py_out


@pytest.mark.skipif(
    not SECRETS_SH.is_file()
    or not TMPDIR_SH.is_file()
    or shutil.which("bash") is None,
    reason="bash redaction pipeline unavailable",
)
def test_parity_indented_pem_pipeline() -> None:
    py_out = redact.redact(INDENTED_BODY)
    bash_out = _bash_redact_pipeline(INDENTED_BODY)
    assert _parity_normalize(py_out) == _parity_normalize(bash_out)
    assert "<REDACTED-PRIVATE-KEY>" in py_out
    assert "MIIBOgIBAAJB" not in py_out
    assert "prefix line" in py_out
    assert "suffix line" in py_out
