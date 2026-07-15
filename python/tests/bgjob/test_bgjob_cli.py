from __future__ import annotations

import sys
from pathlib import Path
import pytest

from larch import io as larch_io
from larch.bgjob import cli, model
from larch.core import config


def test_wait_empty_tmpdir_uses_implement_tmpdir_env(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    result = model.result_env_path(tmpdir=tmp_path, step="implement-step3-checks")
    larch_io.write_kvs(path=result, values=[("BGJOB_RC", "0")])
    monkeypatch.setenv(config.ENV_IMPLEMENT_TMPDIR, str(tmp_path))

    rc = cli.wait_main(["--step", "implement-step3-checks", "--tmpdir", "", "--max-wait-s", "0"])
    out = capsys.readouterr().out

    assert rc == 0
    assert "BGJOB_STATUS=DONE" in out
    assert "BGJOB_RC=0" in out


@pytest.mark.parametrize(
    "argv",
    [
        ["--step", "implement-step3-checks", "--tmpdir", "", "--max-wait-s", "0"],
        ["--step", "implement-step3-checks", "--max-wait-s", "0"],
    ],
)
def test_wait_empty_or_missing_tmpdir_falls_back_to_env(
    argv: list[str],
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    captured: list[Path] = []

    def fake_wait_once(
        *, tmpdir: Path, step: str, max_wait_s: int, run_id: str | None = None, poll_interval_s: float = 1.0
    ) -> int:
        _ = (step, max_wait_s, run_id, poll_interval_s)
        captured.append(tmpdir)
        return 0

    monkeypatch.setenv(config.ENV_IMPLEMENT_TMPDIR, str(tmp_path))
    monkeypatch.setattr(cli.wait, "wait_once", fake_wait_once)

    rc = cli.wait_main(argv)
    out = capsys.readouterr().out

    assert rc == 0
    assert out == ""
    assert captured == [tmp_path]


def test_wait_reports_missing_tmpdir_without_arg_or_env(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.delenv(config.ENV_IMPLEMENT_TMPDIR, raising=False)

    rc = cli.wait_main(["--step", "demo-step", "--max-wait-s", "0"])
    out = capsys.readouterr().out

    assert rc == 2
    assert out == "BGJOB_ERROR=missing-tmpdir\n"


@pytest.mark.parametrize(
    "argv",
    [
        ["--step", "demo-step", "--tmpdir", "", "--budget-s", "1", "--", "true"],
        ["--step", "demo-step", "--budget-s", "1", "--", "true"],
    ],
)
def test_start_empty_or_omitted_tmpdir_uses_implement_tmpdir_env(
    argv: list[str],
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured: list[model.JobSpec] = []

    def fake_owner_identity(_raw: str | None) -> model.OwnerIdentity:
        return model.OwnerIdentity(recorded=None)

    def fake_start_daemon(spec: model.JobSpec) -> int:
        captured.append(spec)
        return 0

    monkeypatch.setenv(config.ENV_IMPLEMENT_TMPDIR, str(tmp_path))
    monkeypatch.setattr(cli.daemon, "owner_identity_from_env", fake_owner_identity)
    monkeypatch.setattr(cli.daemon, "start_daemon", fake_start_daemon)

    rc = cli.start_main(argv)

    assert rc == 0
    assert len(captured) == 1
    assert captured[0].tmpdir == tmp_path.resolve()


def test_start_reports_missing_tmpdir_without_arg_or_env(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    started = False

    def fake_start_daemon(_spec: model.JobSpec) -> int:
        nonlocal started
        started = True
        return 0

    monkeypatch.delenv(config.ENV_IMPLEMENT_TMPDIR, raising=False)
    monkeypatch.setattr(cli.daemon, "start_daemon", fake_start_daemon)

    rc = cli.start_main(["--step", "demo-step", "--budget-s", "1", "--", "true"])
    out = capsys.readouterr().out

    assert rc == 2
    assert out == "BGJOB_ERROR=missing-tmpdir\n"
    assert started is False


def test_rejects_bad_step_slug(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    rc = cli.wait_main(["--step", "../bad", "--tmpdir", str(tmp_path), "--max-wait-s", "0"])
    out = capsys.readouterr().out
    assert rc == 2
    assert "BGJOB_ERROR" in out


def test_wait_rejects_too_large_chunk(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    rc = cli.wait_main([
        "--step",
        "demo-step",
        "--tmpdir",
        str(tmp_path),
        "--max-wait-s",
        str(config.BGJOB_WAIT_MAX_CHUNK_S + 1),
    ])
    out = capsys.readouterr().out
    assert rc == 2
    assert "max-wait-too-large" in out


def test_start_rejects_sentinel_symlink_escape(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    def fake_owner_identity(_raw: str | None) -> model.OwnerIdentity:
        return model.OwnerIdentity(recorded=None)

    monkeypatch.setattr(cli.daemon, "owner_identity_from_env", fake_owner_identity)
    outside = tmp_path.parent / "bgjob-sentinel-outside"
    _ = outside.write_text("escape\n", encoding="utf-8")
    link = tmp_path / "sentinel-link"
    link.symlink_to(outside)
    rc = cli.start_main(
        [
            "--step",
            "demo-step",
            "--tmpdir",
            str(tmp_path),
            "--budget-s",
            "1",
            "--sentinel",
            str(link),
            "--",
            sys.executable,
            "-c",
            "print('hello')",
        ]
    )
    out = capsys.readouterr().out
    assert rc == 2
    assert "BGJOB_ERROR" in out


def test_start_rejects_merge_result_env_symlink(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    def fake_owner_identity(_raw: str | None) -> model.OwnerIdentity:
        return model.OwnerIdentity(recorded=None)

    monkeypatch.setattr(cli.daemon, "owner_identity_from_env", fake_owner_identity)
    outside = tmp_path.parent / "bgjob-merge-outside"
    _ = outside.write_text("escape\n", encoding="utf-8")
    link = tmp_path / "merge-link.env"
    link.symlink_to(outside)
    rc = cli.start_main(
        [
            "--step",
            "demo-step",
            "--tmpdir",
            str(tmp_path),
            "--budget-s",
            "1",
            "--merge-result-env",
            str(link),
            "--",
            sys.executable,
            "-c",
            "print('hello')",
        ]
    )
    out = capsys.readouterr().out
    assert rc == 2
    assert "BGJOB_ERROR" in out


@pytest.mark.parametrize(
    ("env_name", "raw_value"),
    [
        (config.ENV_TEST_BGJOB_OWNER_GRACE_S, "not-a-float"),
        (config.ENV_TEST_BGJOB_DAEMON_POLL_INTERVAL_S, "-0.01"),
    ],
)
def test_start_rejects_invalid_timing_overrides_before_pipe(
    env_name: str,
    raw_value: str,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.setenv(env_name, raw_value)

    def fake_owner_identity(_raw: str | None) -> model.OwnerIdentity:
        return model.OwnerIdentity(recorded=None)

    def fail_pipe() -> tuple[int, int]:
        pytest.fail("daemon startup pipe should not be opened for invalid timing overrides")

    monkeypatch.setattr(cli.daemon, "owner_identity_from_env", fake_owner_identity)
    monkeypatch.setattr(cli.daemon.os, "pipe", fail_pipe)

    rc = cli.start_main(
        [
            "--step",
            "demo-step",
            "--tmpdir",
            str(tmp_path),
            "--budget-s",
            "1",
            "--",
            sys.executable,
            "-c",
            "print('hello')",
        ]
    )
    out = capsys.readouterr().out

    assert rc == 2
    assert "BGJOB_ERROR" in out


def test_model_rejects_path_escape_slug() -> None:
    with pytest.raises(ValueError, match="invalid step"):
        _ = model.validate_slug("bad/step", label="step")
