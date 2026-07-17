"""Tests for the checksum-pinned Gitleaks bootstrap and scan wrapper."""

from __future__ import annotations

import hashlib
import io
import tarfile
import urllib.error
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from pathlib import Path
from typing import Self

import pytest

from larch.core.proc import CommandResult
from larch.lint import gitleaks

REPO_ROOT = Path(__file__).resolve().parents[3]


def _archive(binary: bytes, *, member_name: str = "gitleaks") -> bytes:
    payload = io.BytesIO()
    with tarfile.open(fileobj=payload, mode="w:gz") as bundle:
        info = tarfile.TarInfo(member_name)
        info.size = len(binary)
        bundle.addfile(info, io.BytesIO(binary))
    return payload.getvalue()


def _empty_calls() -> list[tuple[str, ...]]:
    return []


def _patch_ensure_binary(monkeypatch: pytest.MonkeyPatch, binary: Path) -> None:
    def fake_ensure_binary(
        *,
        cache_root: Path,
        system: str,
        machine: str,
        fetcher: gitleaks.Fetcher,
    ) -> Path:
        _ = cache_root, system, machine, fetcher
        return binary

    monkeypatch.setattr(gitleaks, "ensure_gitleaks_binary", fake_ensure_binary)


@dataclass
class StubRunner:
    responses: list[CommandResult]
    calls: list[tuple[str, ...]] = field(default_factory=_empty_calls)

    def run(
        self,
        argv: Sequence[str],
        *,
        timeout: float | None = None,
        cwd: str | None = None,
        env: Mapping[str, str] | None = None,
        check: bool = False,
        stdout: int | None = None,
        stderr: int | None = None,
    ) -> CommandResult:
        _ = timeout, cwd, env, check, stdout, stderr
        self.calls.append(tuple(argv))
        return self.responses.pop(0)


def _result(*, stdout: str = "", stderr: str = "", returncode: int = 0) -> CommandResult:
    return CommandResult(argv=(), returncode=returncode, stdout=stdout, stderr=stderr, duration=0.0)


@pytest.mark.parametrize(
    ("system", "machine", "expected"),
    [
        ("Darwin", "arm64", ("darwin", "arm64")),
        ("Darwin", "x86_64", ("darwin", "x64")),
        ("Linux", "aarch64", ("linux", "arm64")),
        ("Linux", "amd64", ("linux", "x64")),
    ],
)
def test_platform_key_normalizes_supported_release_names(
    system: str,
    machine: str,
    expected: tuple[str, str],
) -> None:
    assert gitleaks._platform_key(system, machine) == expected  # pyright: ignore[reportPrivateUsage]


def test_platform_key_rejects_unsupported_platform() -> None:
    with pytest.raises(ValueError, match="unsupported gitleaks platform"):
        _ = gitleaks._platform_key("Windows", "AMD64")  # pyright: ignore[reportPrivateUsage]


def test_ensure_binary_verifies_archive_and_extracted_binary(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    binary = b"verified binary"
    archive = _archive(binary)
    artifact = gitleaks.ReleaseArtifact(
        filename="fixture.tar.gz",
        archive_sha256=hashlib.sha256(archive).hexdigest(),
        binary_sha256=hashlib.sha256(binary).hexdigest(),
    )
    monkeypatch.setitem(gitleaks._ARTIFACTS, ("linux", "x64"), artifact)  # pyright: ignore[reportPrivateUsage]
    urls: list[str] = []

    def fetch(url: str) -> bytes:
        urls.append(url)
        return archive

    path = gitleaks.ensure_gitleaks_binary(
        cache_root=tmp_path,
        system="Linux",
        machine="x86_64",
        fetcher=fetch,
    )

    assert path.read_bytes() == binary
    assert path.stat().st_mode & 0o111
    assert urls == [f"{gitleaks._RELEASE_ROOT}/fixture.tar.gz"]  # pyright: ignore[reportPrivateUsage]


def test_fetch_release_retries_transient_network_errors(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    payload = b"release archive"
    attempts = 0
    delays: list[float] = []

    class Response:
        def __enter__(self) -> Self:
            return self

        def __exit__(self, *_args: object) -> None:
            return None

        def read(self, _limit: int) -> bytes:
            return payload

    def fake_urlopen(_request: object, *, timeout: float) -> Response:
        nonlocal attempts
        _ = timeout
        attempts += 1
        if attempts < 3:
            raise urllib.error.URLError("transient")
        return Response()

    def fake_sleep(seconds: float) -> None:
        delays.append(seconds)

    monkeypatch.setattr(gitleaks.urllib.request, "urlopen", fake_urlopen)
    monkeypatch.setattr(gitleaks.time, "sleep", fake_sleep)

    assert gitleaks._fetch_release("https://example.invalid/release") == payload  # pyright: ignore[reportPrivateUsage]
    assert attempts == 3
    assert delays == [1.0, 2.0]


def test_ensure_binary_rejects_archive_checksum_mismatch(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    artifact = gitleaks.ReleaseArtifact("fixture.tar.gz", "0" * 64, "1" * 64)
    monkeypatch.setitem(gitleaks._ARTIFACTS, ("linux", "x64"), artifact)  # pyright: ignore[reportPrivateUsage]

    with pytest.raises(ValueError, match="checksum mismatch"):
        _ = gitleaks.ensure_gitleaks_binary(
            cache_root=tmp_path,
            system="Linux",
            machine="x86_64",
            fetcher=lambda _url: b"tampered",
        )


def test_ensure_binary_rejects_archive_without_regular_binary(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    archive = _archive(b"wrong member", member_name="README.md")
    artifact = gitleaks.ReleaseArtifact(
        "fixture.tar.gz",
        hashlib.sha256(archive).hexdigest(),
        "1" * 64,
    )
    monkeypatch.setitem(gitleaks._ARTIFACTS, ("linux", "x64"), artifact)  # pyright: ignore[reportPrivateUsage]

    with pytest.raises(ValueError, match="no gitleaks binary"):
        _ = gitleaks.ensure_gitleaks_binary(
            cache_root=tmp_path,
            system="Linux",
            machine="x86_64",
            fetcher=lambda _url: archive,
        )


def test_gitleaks_main_verifies_version_then_runs_working_tree(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    _ = (repo / ".gitleaks.toml").write_text('title = "fixture"\n')
    binary = tmp_path / "gitleaks"
    _ = binary.write_bytes(b"binary")
    _patch_ensure_binary(monkeypatch, binary)
    runner = StubRunner([_result(stdout="8.18.4\n"), _result()])

    rc = gitleaks.gitleaks_main(
        ("--mode", "working-tree", "--repo-root", str(repo), "--cache-dir", str(tmp_path / "cache")),
        runner=runner,
        system="Linux",
        machine="x86_64",
    )

    assert rc == 0
    assert runner.calls[0] == (str(binary), "version")
    assert runner.calls[1] == (
        str(binary),
        "detect",
        "--source",
        ".",
        "--config",
        str(repo / ".gitleaks.toml"),
        "--redact",
        "--no-banner",
        "--no-git",
    )


def test_gitleaks_main_history_requires_bounded_revision_range(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    _ = (tmp_path / ".gitleaks.toml").write_text('title = "fixture"\n')
    binary = tmp_path / "gitleaks"
    _ = binary.write_bytes(b"binary")
    _patch_ensure_binary(monkeypatch, binary)
    runner = StubRunner([_result(stdout="8.18.4\n")])

    rc = gitleaks.gitleaks_main(
        ("--mode", "history", "--repo-root", str(tmp_path), "--cache-dir", str(tmp_path / "cache")),
        runner=runner,
        system="Linux",
        machine="x86_64",
    )

    assert rc == 2
    assert "--log-opts is required" in capsys.readouterr().err
    assert len(runner.calls) == 1


def test_gitleaks_main_propagates_history_scan_result(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _ = (tmp_path / ".gitleaks.toml").write_text('title = "fixture"\n', encoding="utf-8")
    binary = tmp_path / "gitleaks"
    _ = binary.write_bytes(b"binary")
    _patch_ensure_binary(monkeypatch, binary)
    runner = StubRunner([_result(stdout="8.18.4\n"), _result(returncode=1)])

    rc = gitleaks.gitleaks_main(
        (
            "--mode",
            "history",
            "--log-opts",
            "base..HEAD",
            "--repo-root",
            str(tmp_path),
            "--cache-dir",
            str(tmp_path / "cache"),
        ),
        runner=runner,
        system="Linux",
        machine="x86_64",
    )

    assert rc == 1
    assert runner.calls[1] == (
        str(binary),
        "detect",
        "--source",
        ".",
        "--config",
        str(tmp_path / ".gitleaks.toml"),
        "--redact",
        "--no-banner",
        "--log-opts",
        "base..HEAD",
    )


def test_gitleaks_main_fails_closed_on_wrong_release_version(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    _ = (tmp_path / ".gitleaks.toml").write_text('title = "fixture"\n')
    binary = tmp_path / "gitleaks"
    _ = binary.write_bytes(b"binary")
    _patch_ensure_binary(monkeypatch, binary)
    runner = StubRunner([_result(stdout="8.30.1\n")])

    rc = gitleaks.gitleaks_main(
        ("--mode", "verify", "--repo-root", str(tmp_path), "--cache-dir", str(tmp_path / "cache")),
        runner=runner,
        system="Linux",
        machine="x86_64",
    )

    assert rc == 2
    assert "expected gitleaks version 8.18.4" in capsys.readouterr().err


def test_precommit_and_ci_share_the_same_release_wrapper() -> None:
    precommit = (REPO_ROOT / ".pre-commit-config.yaml").read_text(encoding="utf-8")
    workflow = (REPO_ROOT / ".github/workflows/ci.yaml").read_text(encoding="utf-8")
    wrapper = "python3 python/cli.py checks gitleaks"

    assert f"entry: {wrapper} --mode working-tree" in precommit
    assert "repo: https://github.com/gitleaks/gitleaks" not in precommit
    assert f"run: {wrapper} --mode verify" in workflow
    assert f"run: {wrapper} --mode working-tree" in workflow
    assert f'{wrapper} --mode history --log-opts "${{BASE}}..HEAD"' in workflow
    assert "hashFiles('python/larch/lint/gitleaks.py')" in workflow
    assert "run: gitleaks detect" not in workflow
