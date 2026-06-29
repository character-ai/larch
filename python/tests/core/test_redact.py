"""Tests for redact.py including bash parity."""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

import pytest

from larch.core import redact

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


def test_operator_multiline_eol_redaction() -> None:
    text = "line one\n/Users/example/myrepo\nline three"
    out = redact.redact(text)
    assert "/Users/example/myrepo" not in out
    assert "<OPERATOR_REPO_PATH>" in out


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
        "cwd=/home/example/my.repo,",
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


GATE_SH = REPO_ROOT / "scripts" / "scrub-log-secrets.sh"


def test_scrub_log_secrets_redacts_cursor_key() -> None:
    text = (
        "cursor agent --api-key "
        "crsr_1620abcdefghijklmnopqrstuvwxyz0123456789 --workspace /x\n"
    )
    scrubbed, findings = redact.scrub_log_secrets(text)
    assert "crsr_1620" not in scrubbed
    assert "<REDACTED-TOKEN>" in scrubbed
    assert findings == {"cursor-api-key": 1}


def test_scrub_log_secrets_leaves_clean_text_unchanged() -> None:
    text = "prose line\nuuid AAAAAAAA-1111-2222-3333-444444444444\n"
    scrubbed, findings = redact.scrub_log_secrets(text)
    assert scrubbed == text
    assert not findings


def test_scrub_log_secrets_backstops_github_token() -> None:
    # Split prefix so this fixture is not itself a scanner hit.
    token = "ghp_" + "abcdefghijklmnopqrstuvwxyz0123456789AB"
    scrubbed, findings = redact.scrub_log_secrets(f"token {token} end\n")
    assert token not in scrubbed
    assert findings == {"github-token": 1}


@pytest.mark.skipif(
    not GATE_SH.is_file() or shutil.which("bash") is None,
    reason="scrub-log-secrets.sh unavailable",
)
def test_scrub_log_secrets_parity_with_shell_gate(tmp_path: Path) -> None:
    text = (
        "cursor --api-key crsr_1620abcdefghijklmnopqrstuvwxyz0123456789 --workspace /x\n"
        # Split the Slack prefix across adjacent literals so this fixture is not
        # itself a secret-scanner hit; Python concatenates to the same value.
        "slack xox"
        "b-1234567890-abcdefghijklmnop trailing\n"
        "clean prose line\n"
    )
    py_scrubbed, _ = redact.scrub_log_secrets(text)
    target = tmp_path / "findings.md"
    _ = target.write_text(text, encoding="utf-8")
    _ = subprocess.run(
        [str(GATE_SH), str(tmp_path)],
        capture_output=True,
        text=True,
        check=False,
    )
    sh_scrubbed = target.read_text(encoding="utf-8")
    assert py_scrubbed == sh_scrubbed
    assert "crsr_1620" not in sh_scrubbed


def test_report_tokens_tmpdir_redacted() -> None:
    text = "see /tmp/larch-report-tokens.abc123/report-cache.ndjson and /var/folders/aa/bb/T/larch-report-tokens-plot.xyz/x.png"
    redacted = redact.redact(text)
    assert "/tmp/larch-report-tokens" not in redacted
    assert "/var/folders" not in redacted


def test_redact_outbound_covers_cursor_cli_key() -> None:
    token = "crsr_0123456789abcdefghijklmnopqrstuvwxyzABCDEF"
    out = redact.redact_outbound(f"publish {token}")
    assert "<REDACTED-TOKEN>" in out
    assert token not in out


def _fake_submodule_paths(_cwd: Path) -> set[str]:
    return {"vendor/libfoo"}


def test_scrub_submodule_paths_bold_label_and_exact_dir(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    # Production findings use the markdown-bold `- **Location**:` / `- **File**:`
    # form, and reference submodules as a bare directory, a `:line` suffix, or a
    # path inside the submodule -- none of which the trailing-slash-only match
    # caught (issue #4780).
    monkeypatch.setattr(redact, "discover_submodule_paths", _fake_submodule_paths)
    findings = (
        "### FINDING_1:\n"
        "- **Location**: vendor/libfoo:120\n"
        "- **Concern**: bare submodule dir with :line suffix\n\n"
        "### FINDING_2:\n"
        "- **Location**: vendor/libfoo\n"
        "- **Concern**: bare submodule dir, no trailing slash\n\n"
        "### FINDING_3:\n"
        "- **File**: vendor/libfoo/src/x.py\n"
        "- **Concern**: path inside the submodule\n\n"
        "### FINDING_4:\n"
        "- **Location**: python/redact.py:553\n"
        "- **Concern**: not a submodule path; must survive\n\n"
    )
    input_path = tmp_path / "findings.md"
    output_path = tmp_path / "scrubbed.md"
    log_path = tmp_path / "audit.log"
    _ = input_path.write_text(findings, encoding="utf-8")
    count, ok = redact.scrub_submodule_paths(input_path=input_path, output_path=output_path, log_path=log_path)
    assert ok
    assert count == 3
    out = output_path.read_text(encoding="utf-8")
    assert "FINDING_1" not in out
    assert "FINDING_2" not in out
    assert "FINDING_3" not in out
    assert "FINDING_4" in out
    assert "python/redact.py" in out


def test_scrub_submodule_paths_plain_label_still_matches(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    # The non-bold `Location:` form remains supported for backward compatibility.
    monkeypatch.setattr(redact, "discover_submodule_paths", _fake_submodule_paths)
    findings = "### FINDING_1:\nLocation: vendor/libfoo\n- **Concern**: plain label\n\n"
    input_path = tmp_path / "findings.md"
    output_path = tmp_path / "scrubbed.md"
    log_path = tmp_path / "audit.log"
    _ = input_path.write_text(findings, encoding="utf-8")
    count, ok = redact.scrub_submodule_paths(input_path=input_path, output_path=output_path, log_path=log_path)
    assert ok
    assert count == 1
    assert "FINDING_1" not in output_path.read_text(encoding="utf-8")


def test_scrub_submodule_paths_does_not_overmatch_sibling(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    # A sibling path that merely shares the submodule-name prefix must not match.
    monkeypatch.setattr(redact, "discover_submodule_paths", _fake_submodule_paths)
    findings = (
        "### FINDING_1:\n"
        "- **Location**: vendor/libfoobar/x.py:9\n"
        "- **Concern**: sibling sharing the submodule name prefix\n\n"
    )
    input_path = tmp_path / "findings.md"
    output_path = tmp_path / "scrubbed.md"
    log_path = tmp_path / "audit.log"
    _ = input_path.write_text(findings, encoding="utf-8")
    count, ok = redact.scrub_submodule_paths(input_path=input_path, output_path=output_path, log_path=log_path)
    assert ok
    assert count == 0
    out = output_path.read_text(encoding="utf-8")
    assert "FINDING_1" in out
    assert "vendor/libfoobar/x.py" in out


def test_scrub_submodule_paths_inline_mention_without_label(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    # A submodule path referenced outside a Location/File label line is still
    # scrubbed by the inline match alone -- exercises the broadened inline branch
    # independently of the label branch (the trailing-slash-only match missed it).
    monkeypatch.setattr(redact, "discover_submodule_paths", _fake_submodule_paths)
    findings = "### FINDING_1:\n- **Concern**: the helper in vendor/libfoo breaks on empty input\n\n"
    input_path = tmp_path / "findings.md"
    output_path = tmp_path / "scrubbed.md"
    log_path = tmp_path / "audit.log"
    _ = input_path.write_text(findings, encoding="utf-8")
    count, ok = redact.scrub_submodule_paths(input_path=input_path, output_path=output_path, log_path=log_path)
    assert ok
    assert count == 1
    assert "FINDING_1" not in output_path.read_text(encoding="utf-8")
