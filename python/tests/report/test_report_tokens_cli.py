from __future__ import annotations

import tempfile
from pathlib import Path

import pytest

from larch.core import config
from larch.errors import ShipError
from larch.report import report_tokens_cli
from larch.report.report_tokens_models import RunRecord, VendorTotals
from larch.report.report_tokens_scan import ScanResult


def _record() -> RunRecord:
    return RunRecord(1, "t", "u", "2026-01-01T00:00:00Z", "2026-01-01T00:00:00Z", "", VendorTotals(total=1), VendorTotals(), VendorTotals(), (), {})


def _isolate_cli_temp_root(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    original_mkdtemp = tempfile.mkdtemp

    def fake_mkdtemp(suffix: str = "", prefix: str = "tmp", **kwargs: object) -> str:
        requested_dir = kwargs.get("dir")
        target_dir = str(tmp_path) if requested_dir is None else str(requested_dir)
        return original_mkdtemp(suffix=suffix, prefix=prefix, dir=target_dir)

    monkeypatch.setattr(report_tokens_cli.tempfile, "mkdtemp", fake_mkdtemp)


def _single_cache_path(tmp_path: Path) -> Path:
    paths = list(tmp_path.glob("larch-report-tokens.*/report-cache.ndjson"))
    assert len(paths) == 1
    return paths[0]


def test_reject_plot_from() -> None:
    with pytest.raises(SystemExit):
        _ = report_tokens_cli.parse_args(["--skill", "design", "--plot-from", "1"])


def test_env_bool_no_issue(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv(config.ENV_LARCH_REPORT_TOKENS_NO_ISSUE, "1")
    assert report_tokens_cli.env_flag_enabled(config.ENV_LARCH_REPORT_TOKENS_NO_ISSUE) is True


def test_main_success_posts_issue_and_keeps_single_cache_trailer(monkeypatch: pytest.MonkeyPatch, tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    record = RunRecord(1, "t", "u", "2026-01-01T00:00:00Z", "2026-01-01T00:00:00Z", "", VendorTotals(total=1), VendorTotals(), VendorTotals(), (), {})
    posted: list[tuple[str, str]] = []

    def fake_scan(_runner: object, skill: str, repo_override: str | None = None) -> ScanResult:
        _ = (skill, repo_override)
        return ScanResult(tmp_path, "o/r", (record,))

    def fake_price(_runner: object, record: RunRecord) -> RunRecord:
        return record

    def fake_render(*args: object, **kwargs: object) -> tuple[str, list[object], str]:
        _ = (args, kwargs)
        return "## Report Tokens Analysis\n\nCache JSON: /tmp/cache.ndjson", [], "/tmp/cache.ndjson"

    def fake_plot(*args: object, **kwargs: object) -> list[object]:
        _ = (args, kwargs)
        return []

    def fake_post(_runner: object, repo: str | None, title: str, sections: list[object], skill: str) -> None:
        _ = (title, sections, skill)
        posted.append((repo or "", skill))

    monkeypatch.setattr(report_tokens_cli, "scan", fake_scan)
    monkeypatch.setattr(report_tokens_cli, "price_run", fake_price)
    monkeypatch.setattr(report_tokens_cli, "render", fake_render)
    monkeypatch.setattr(report_tokens_cli, "plot", fake_plot)
    monkeypatch.setattr(report_tokens_cli, "post_issue", fake_post)
    assert report_tokens_cli.main(["--skill", "implement"]) == config.EXIT_OK
    out = capsys.readouterr().out
    assert out.count("Cache JSON:") == 1
    assert posted == [("o/r", "implement")]


def test_main_design_posts_issue_with_design_skill(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    record = RunRecord(1, "t", "u", "2026-01-01T00:00:00Z", "2026-01-01T00:00:00Z", "", VendorTotals(total=1), VendorTotals(), VendorTotals(), (), {})
    posted: list[str] = []

    def fake_scan(_runner: object, skill: str, repo_override: str | None = None) -> ScanResult:
        _ = (skill, repo_override)
        return ScanResult(tmp_path, "o/r", (record,))

    def fake_price(_runner: object, record: RunRecord) -> RunRecord:
        return record

    def fake_render(*args: object, **kwargs: object) -> tuple[str, list[object], str]:
        _ = (args, kwargs)
        return "## Report Tokens Analysis\n\nCache JSON: /tmp/cache.ndjson", [], "/tmp/cache.ndjson"

    def fake_plot(*args: object, **kwargs: object) -> list[object]:
        _ = (args, kwargs)
        return []

    def fake_post(_runner: object, repo: str | None, title: str, sections: list[object], skill: str) -> None:
        _ = (repo, title, sections)
        posted.append(skill)

    monkeypatch.setattr(report_tokens_cli, "scan", fake_scan)
    monkeypatch.setattr(report_tokens_cli, "price_run", fake_price)
    monkeypatch.setattr(report_tokens_cli, "render", fake_render)
    monkeypatch.setattr(report_tokens_cli, "plot", fake_plot)
    monkeypatch.setattr(report_tokens_cli, "post_issue", fake_post)
    assert report_tokens_cli.main(["--skill", "design"]) == config.EXIT_OK
    assert posted == ["design"]


def test_main_fails_before_post_when_repo_missing(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    record = RunRecord(1, "t", "", "2026-01-01T00:00:00Z", "2026-01-01T00:00:00Z", "", VendorTotals(total=1), VendorTotals(), VendorTotals(), (), {})

    def fake_scan(_runner: object, skill: str, repo_override: str | None = None) -> ScanResult:
        _ = (skill, repo_override)
        return ScanResult(tmp_path, None, (record,))

    def fake_price(_runner: object, record: RunRecord) -> RunRecord:
        return record

    def fake_render(*args: object, **kwargs: object) -> tuple[str, list[object], str]:
        _ = (args, kwargs)
        return "## Report Tokens Analysis\n\nCache JSON: /tmp/cache.ndjson", [], "/tmp/cache.ndjson"

    def fake_plot(*args: object, **kwargs: object) -> list[object]:
        _ = (args, kwargs)
        return []

    def fail_post(*args: object, **kwargs: object) -> None:
        _ = (args, kwargs)
        pytest.fail("posted without repo")

    monkeypatch.setattr(report_tokens_cli, "scan", fake_scan)
    monkeypatch.setattr(report_tokens_cli, "price_run", fake_price)
    monkeypatch.setattr(report_tokens_cli, "render", fake_render)
    monkeypatch.setattr(report_tokens_cli, "plot", fake_plot)
    monkeypatch.setattr(report_tokens_cli, "post_issue", fail_post)
    assert report_tokens_cli.main(["--skill", "implement"]) == config.EXIT_BAIL


def test_main_no_issue_and_no_plot_forwarding(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    record = RunRecord(1, "t", "u", "2026-01-01T00:00:00Z", "2026-01-01T00:00:00Z", "", VendorTotals(total=1), VendorTotals(), VendorTotals(), (), {})
    plotted: list[bool] = []
    posted: list[tuple[str, str]] = []

    def fake_scan(_runner: object, skill: str, repo_override: str | None = None) -> ScanResult:
        _ = (skill, repo_override)
        return ScanResult(tmp_path, "o/r", (record,))

    def fake_price(_runner: object, record: RunRecord) -> RunRecord:
        return record

    def fake_render(*args: object, **kwargs: object) -> tuple[str, list[object], str]:
        _ = (args, kwargs)
        return "body", [], "/tmp/cache.ndjson"

    def fake_plot(*args: object, **kwargs: object) -> list[object]:
        _ = args
        plotted.append(bool(kwargs.get("no_plot")))
        return []

    def fake_post(_runner: object, repo: str | None, title: str, sections: list[object], skill: str) -> None:
        _ = (title, sections, skill)
        posted.append((repo or "", skill))

    monkeypatch.setattr(report_tokens_cli, "scan", fake_scan)
    monkeypatch.setattr(report_tokens_cli, "price_run", fake_price)
    monkeypatch.setattr(report_tokens_cli, "render", fake_render)
    monkeypatch.setattr(report_tokens_cli, "plot", fake_plot)
    monkeypatch.setattr(report_tokens_cli, "post_issue", fake_post)
    assert report_tokens_cli.main(["--skill", "implement", "--no-issue", "--no-plot"]) == config.EXIT_OK
    assert plotted == [True]
    assert not posted


def test_main_no_issue_disables_repo_resolution(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    seen: list[bool] = []

    def fake_scan(_runner: object, skill: str, repo_override: str | None = None, resolve_repo: bool = True) -> ScanResult:
        _ = (skill, repo_override)
        seen.append(resolve_repo)
        return ScanResult(tmp_path, None, ())

    monkeypatch.setattr(report_tokens_cli, "scan", fake_scan)
    assert report_tokens_cli.main(["--skill", "implement", "--no-issue"]) == config.EXIT_OK
    assert seen == [False]


def test_empty_scan_cli_success_path(monkeypatch: pytest.MonkeyPatch, tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    def fake_scan(_runner: object, skill: str, repo_override: str | None = None) -> ScanResult:
        _ = (skill, repo_override)
        return ScanResult(tmp_path, "o/r", ())

    monkeypatch.setattr(report_tokens_cli, "scan", fake_scan)
    assert report_tokens_cli.main(["--skill", "implement"]) == config.EXIT_OK
    out = capsys.readouterr().out
    assert "No parseable token reports found." in out
    assert "Cache JSON:" in out


def test_scan_shiperror_removes_unadvertised_temp_root(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    _isolate_cli_temp_root(monkeypatch, tmp_path)

    def fake_scan(_runner: object, skill: str, repo_override: str | None = None, resolve_repo: bool = True) -> ScanResult:
        _ = (_runner, skill, repo_override, resolve_repo)
        raise ShipError("scan failed")

    monkeypatch.setattr(report_tokens_cli, "scan", fake_scan)
    assert report_tokens_cli.main(["--skill", "implement", "--no-issue"]) == config.EXIT_BAIL
    assert not list(tmp_path.glob("larch-report-tokens.*"))


def test_empty_scan_preserves_advertised_cache_root(monkeypatch: pytest.MonkeyPatch, tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    _isolate_cli_temp_root(monkeypatch, tmp_path)

    def fake_scan(_runner: object, skill: str, repo_override: str | None = None, resolve_repo: bool = True) -> ScanResult:
        _ = (_runner, skill, repo_override, resolve_repo)
        return ScanResult(tmp_path, None, ())

    monkeypatch.setattr(report_tokens_cli, "scan", fake_scan)
    assert report_tokens_cli.main(["--skill", "implement", "--no-issue"]) == config.EXIT_OK
    assert "Cache JSON:" in capsys.readouterr().out
    cache_path = _single_cache_path(tmp_path)
    assert cache_path.is_file()


def test_no_plot_success_preserves_advertised_cache_root(monkeypatch: pytest.MonkeyPatch, tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    _isolate_cli_temp_root(monkeypatch, tmp_path)
    record = _record()

    def fake_scan(_runner: object, skill: str, repo_override: str | None = None, resolve_repo: bool = True) -> ScanResult:
        _ = (_runner, skill, repo_override, resolve_repo)
        return ScanResult(tmp_path, None, (record,))

    def fake_price(_runner: object, record: RunRecord) -> RunRecord:
        return record

    def fake_plot(*args: object, **kwargs: object) -> list[Path]:
        _ = (args, kwargs)
        return []

    monkeypatch.setattr(report_tokens_cli, "scan", fake_scan)
    monkeypatch.setattr(report_tokens_cli, "price_run", fake_price)
    monkeypatch.setattr(report_tokens_cli, "plot", fake_plot)
    assert report_tokens_cli.main(["--skill", "implement", "--no-issue", "--no-plot"]) == config.EXIT_OK
    assert "Cache JSON:" in capsys.readouterr().out
    cache_path = _single_cache_path(tmp_path)
    assert cache_path.is_file()


def test_plot_success_on_linux_preserves_plot_root(monkeypatch: pytest.MonkeyPatch, tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    _isolate_cli_temp_root(monkeypatch, tmp_path)
    record = _record()
    plot_file: Path | None = None

    def fake_scan(_runner: object, skill: str, repo_override: str | None = None, resolve_repo: bool = True) -> ScanResult:
        _ = (_runner, skill, repo_override, resolve_repo)
        return ScanResult(tmp_path, None, (record,))

    def fake_price(_runner: object, record: RunRecord) -> RunRecord:
        return record

    def fake_plot(*args: object, **kwargs: object) -> list[Path]:
        _ = args
        nonlocal plot_file
        plot_parent_dir = kwargs["plot_parent_dir"]
        assert isinstance(plot_parent_dir, Path)
        plot_file = plot_parent_dir / "plot.png"
        _ = plot_file.write_text("plot", encoding="utf-8")
        return [plot_file]

    monkeypatch.setattr(report_tokens_cli.sys, "platform", "linux")
    monkeypatch.setattr(report_tokens_cli, "scan", fake_scan)
    monkeypatch.setattr(report_tokens_cli, "price_run", fake_price)
    monkeypatch.setattr(report_tokens_cli, "plot", fake_plot)
    assert report_tokens_cli.main(["--skill", "implement", "--no-issue"]) == config.EXIT_OK
    out = capsys.readouterr().out
    assert "Plots written to:" in out
    assert plot_file is not None
    assert plot_file.is_file()


def test_darwin_no_open_with_plots_preserves_plot_root(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    _isolate_cli_temp_root(monkeypatch, tmp_path)
    record = _record()
    plot_file: Path | None = None

    def fake_scan(_runner: object, skill: str, repo_override: str | None = None, resolve_repo: bool = True) -> ScanResult:
        _ = (_runner, skill, repo_override, resolve_repo)
        return ScanResult(tmp_path, None, (record,))

    def fake_price(_runner: object, record: RunRecord) -> RunRecord:
        return record

    def fake_plot(*args: object, **kwargs: object) -> list[Path]:
        _ = args
        nonlocal plot_file
        plot_parent_dir = kwargs["plot_parent_dir"]
        assert isinstance(plot_parent_dir, Path)
        plot_file = plot_parent_dir / "plot-darwin.png"
        _ = plot_file.write_text("plot", encoding="utf-8")
        return [plot_file]

    monkeypatch.setenv(config.ENV_LARCH_REPORT_TOKENS_NO_OPEN, "1")
    monkeypatch.setattr(report_tokens_cli.sys, "platform", "darwin")
    monkeypatch.setattr(report_tokens_cli, "scan", fake_scan)
    monkeypatch.setattr(report_tokens_cli, "price_run", fake_price)
    monkeypatch.setattr(report_tokens_cli, "plot", fake_plot)
    assert report_tokens_cli.main(["--skill", "implement", "--no-issue"]) == config.EXIT_OK
    assert plot_file is not None
    assert plot_file.is_file()


def test_post_failure_after_cache_output_preserves_root(monkeypatch: pytest.MonkeyPatch, tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    _isolate_cli_temp_root(monkeypatch, tmp_path)
    record = _record()

    def fake_scan(_runner: object, skill: str, repo_override: str | None = None, resolve_repo: bool = True) -> ScanResult:
        _ = (_runner, skill, repo_override, resolve_repo)
        return ScanResult(tmp_path, "o/r", (record,))

    def fake_price(_runner: object, record: RunRecord) -> RunRecord:
        return record

    def fake_plot(*args: object, **kwargs: object) -> list[Path]:
        _ = (args, kwargs)
        return []

    def fake_post(_runner: object, repo: str | None, title: str, sections: list[object], skill: str) -> None:
        _ = (_runner, repo, title, sections, skill)
        raise ShipError("post failed")

    monkeypatch.setattr(report_tokens_cli, "scan", fake_scan)
    monkeypatch.setattr(report_tokens_cli, "price_run", fake_price)
    monkeypatch.setattr(report_tokens_cli, "plot", fake_plot)
    monkeypatch.setattr(report_tokens_cli, "post_issue", fake_post)
    assert report_tokens_cli.main(["--skill", "implement"]) == config.EXIT_BAIL
    assert "Cache JSON:" in capsys.readouterr().out
    cache_path = _single_cache_path(tmp_path)
    assert cache_path.is_file()


def test_exception_during_print_after_preserve_decision_preserves_root(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    _isolate_cli_temp_root(monkeypatch, tmp_path)
    record = _record()
    original_print_analysis = report_tokens_cli._print_analysis

    def exploding_print_analysis(*, analysis: str, plot_paths: list[Path], no_plot: bool) -> None:
        original_print_analysis(analysis=analysis, plot_paths=plot_paths, no_plot=no_plot)
        raise BrokenPipeError()

    def fake_scan(_runner: object, skill: str, repo_override: str | None = None, resolve_repo: bool = True) -> ScanResult:
        _ = (_runner, skill, repo_override, resolve_repo)
        return ScanResult(tmp_path, None, (record,))

    def fake_price(_runner: object, record: RunRecord) -> RunRecord:
        return record

    def fake_plot(*args: object, **kwargs: object) -> list[Path]:
        _ = (args, kwargs)
        return []

    monkeypatch.setattr(report_tokens_cli, "scan", fake_scan)
    monkeypatch.setattr(report_tokens_cli, "price_run", fake_price)
    monkeypatch.setattr(report_tokens_cli, "plot", fake_plot)
    monkeypatch.setattr(report_tokens_cli, "_print_analysis", exploding_print_analysis)
    with pytest.raises(BrokenPipeError):
        _ = report_tokens_cli.main(["--skill", "implement", "--no-issue", "--no-plot"])
    assert "Cache JSON:" in capsys.readouterr().out
    cache_path = _single_cache_path(tmp_path)
    assert cache_path.is_file()


def _cache_path_from_stdout(out: str) -> Path:
    for line in out.splitlines():
        if line.startswith("Cache JSON:"):
            return Path(line.removeprefix("Cache JSON:").strip())
    raise AssertionError("Cache JSON line missing from stdout")


def test_stdout_advertised_cache_path_is_concrete_and_exists(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    _isolate_cli_temp_root(monkeypatch, tmp_path)
    record = _record()

    def fake_scan(_runner: object, skill: str, repo_override: str | None = None, resolve_repo: bool = True) -> ScanResult:
        _ = (_runner, skill, repo_override, resolve_repo)
        return ScanResult(tmp_path, None, (record,))

    def fake_price(_runner: object, record: RunRecord) -> RunRecord:
        return record

    def fake_plot(*args: object, **kwargs: object) -> list[Path]:
        _ = (args, kwargs)
        return []

    monkeypatch.setattr(report_tokens_cli, "scan", fake_scan)
    monkeypatch.setattr(report_tokens_cli, "price_run", fake_price)
    monkeypatch.setattr(report_tokens_cli, "plot", fake_plot)
    assert report_tokens_cli.main(["--skill", "implement", "--no-issue", "--no-plot"]) == config.EXIT_OK
    out = capsys.readouterr().out
    cache_path = _cache_path_from_stdout(out)
    assert config.REDACTED_TMPDIR not in str(cache_path)
    assert "larch-report-tokens" in str(cache_path)
    assert cache_path.is_file()


def test_stdout_advertised_plot_path_is_concrete_and_exists(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    _isolate_cli_temp_root(monkeypatch, tmp_path)
    record = _record()
    plot_file: Path | None = None

    def fake_scan(_runner: object, skill: str, repo_override: str | None = None, resolve_repo: bool = True) -> ScanResult:
        _ = (_runner, skill, repo_override, resolve_repo)
        return ScanResult(tmp_path, None, (record,))

    def fake_price(_runner: object, record: RunRecord) -> RunRecord:
        return record

    def fake_plot(*args: object, **kwargs: object) -> list[Path]:
        _ = args
        nonlocal plot_file
        plot_parent_dir = kwargs["plot_parent_dir"]
        assert isinstance(plot_parent_dir, Path)
        plot_file = plot_parent_dir / "plot-advertised.png"
        _ = plot_file.write_text("plot", encoding="utf-8")
        return [plot_file]

    monkeypatch.setattr(report_tokens_cli.sys, "platform", "linux")
    monkeypatch.setattr(report_tokens_cli, "scan", fake_scan)
    monkeypatch.setattr(report_tokens_cli, "price_run", fake_price)
    monkeypatch.setattr(report_tokens_cli, "plot", fake_plot)
    assert report_tokens_cli.main(["--skill", "implement", "--no-issue"]) == config.EXIT_OK
    out = capsys.readouterr().out
    plot_lines = [line.removeprefix("- ").strip() for line in out.splitlines() if line.startswith("- ") and "plot" in line]
    assert plot_lines
    plot_path = Path(plot_lines[0])
    assert config.REDACTED_TMPDIR not in str(plot_path)
    assert plot_path.is_file()
