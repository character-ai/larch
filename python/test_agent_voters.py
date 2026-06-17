# pyright: reportUnusedCallResult=false
# pyright: reportMissingParameterType=false, reportUnknownMemberType=false, reportUnknownArgumentType=false, reportArgumentType=false
from __future__ import annotations

import os
import subprocess
from pathlib import Path
from collections.abc import Sequence
from typing import Any

import pytest

import agent_voters
import proc


class FakePopen:
    def __init__(self, harness: FakeHarness, argv: Sequence[str], stdout: object = None, stderr: object = None) -> None:
        self.harness = harness
        self.argv = [str(item) for item in argv]
        self.returncode = harness.claude_rc
        harness.popen_calls.append((self.argv, stdout, stderr))
        output = _value_after(self.argv, "--output")
        if output and harness.claude_write_output:
            Path(output).write_text(harness.claude_output, encoding="utf-8")
        if output and harness.claude_write_done:
            Path(output + ".done").write_text(f"{harness.claude_done_rc}\n", encoding="utf-8")

    def wait(self) -> int:
        return self.returncode


class FakeHarness:
    def __init__(self, review_tmpdir: Path) -> None:
        self.review_tmpdir = review_tmpdir
        self.run_calls: list[list[str]] = []
        self.popen_calls: list[tuple[list[str], object, object]] = []
        self.append_calls: list[list[str]] = []
        self.render_missing_pointer = False
        self.render_rc = 0
        self.waterfall_rc = 0
        self.waterfall_mode = "both"
        self.wait_stdout = ""
        self.wait_rc = 0
        self.parse_status: dict[str, str] = {}
        self.claude_rc = 0
        self.claude_output = "FINDING_1: YES CORRECTNESS=true SEVERITY=minor QUALITY=good UNCERTAIN=false\n"
        self.claude_write_output = True
        self.claude_write_done = True
        self.claude_done_rc = 0

    def popen(self, argv: Sequence[str], stdout: object = None, stderr: object = None) -> FakePopen:
        return FakePopen(self, argv, stdout=stdout, stderr=stderr)

    def run(self, argv: Sequence[str], **kwargs: Any) -> proc.CommandResult:
        args = [str(item) for item in argv]
        self.run_calls.append(args)
        verb = _verb(args)
        if verb == ("render", "voter"):
            text = "stub voter prompt\n"
            if not self.render_missing_pointer:
                text += "Read the ballot from this path: /tmp/ballot\n"
            return _result(args, self.render_rc, stdout=text)
        if verb == ("agent", "dispatch-waterfall"):
            return self._waterfall(args)
        if verb == ("agent", "wait-reviewers"):
            stdout_fd = kwargs.get("stdout")
            if isinstance(stdout_fd, int):
                os.write(stdout_fd, self.wait_stdout.encode("utf-8"))
                return _result(args, self.wait_rc)
            return _result(args, self.wait_rc, stdout=self.wait_stdout)
        if verb == ("voting", "parse-rate-retry"):
            tool = _value_after(args, "--voter-tool") or ""
            return _result(args, 0, stdout=self.parse_status.get(tool, "OK") + "\n")
        if verb == ("run-log", "append-failure"):
            self.append_calls.append(args)
            return _result(args, 0, stdout="APPENDED=true\nLOG=/tmp/log\n")
        return _result(args, 2, stderr=f"unexpected args: {args}\n")

    def _waterfall(self, args: list[str]) -> proc.CommandResult:
        codex = self.review_tmpdir / "codex-vote-output.txt"
        cursor = self.review_tmpdir / "cursor-vote-output.txt"
        outputs: list[str] = []
        tools: list[str] = []
        if self.waterfall_mode in {"both", "codex"}:
            codex.write_text("FINDING_1: YES CORRECTNESS=true SEVERITY=minor QUALITY=good UNCERTAIN=false\n", encoding="utf-8")
            (Path(str(codex) + ".done")).write_text("0\n", encoding="utf-8")
            outputs.append(str(codex))
            tools.append("codex")
        if self.waterfall_mode in {"both", "cursor"}:
            cursor.write_text("FINDING_1: NO CORRECTNESS=true SEVERITY=minor QUALITY=good UNCERTAIN=false\n", encoding="utf-8")
            (Path(str(cursor) + ".done")).write_text("0\n", encoding="utf-8")
            outputs.append(str(cursor))
            tools.append("cursor")
        stdout = "ALL_OUTPUT_FILES=" + " ".join(outputs) + "\n"
        stdout += "ALL_OUTPUT_TOOLS=" + " ".join(tools) + "\n"
        stdout += "DISPATCH_OK=true\n"
        stdout += "WARN=waterfall-warning\n"
        return _result(args, self.waterfall_rc, stdout=stdout)


def _result(argv: Sequence[str], returncode: int, *, stdout: str = "", stderr: str = "") -> proc.CommandResult:
    return proc.CommandResult(tuple(str(item) for item in argv), returncode, stdout, stderr, 0.0)


def _verb(argv: Sequence[str]) -> tuple[str, ...]:
    return tuple(argv[2:4]) if len(argv) >= 4 else tuple(argv[2:])


def _value_after(argv: Sequence[str], flag: str) -> str:
    try:
        idx = list(argv).index(flag)
    except ValueError:
        return ""
    if idx + 1 >= len(argv):
        return ""
    return str(argv[idx + 1])


def _make_stub_plugin(tmp_path: Path) -> Path:
    root = tmp_path / "stub-plugin"
    (root / "python").mkdir(parents=True)
    (root / "python" / "cli.py").write_text("# stub\n", encoding="utf-8")
    return root


def _opts(ballot: Path, review: Path, *, codex: str = "true", cursor: str = "true") -> agent_voters.Options:
    return agent_voters.Options(
        ballot_file=str(ballot),
        review_tmpdir=str(review),
        codex_available=codex,
        cursor_available=cursor,
    )


def _install_harness(monkeypatch: pytest.MonkeyPatch, tmp_path: Path, review: Path) -> FakeHarness:
    stub_root = _make_stub_plugin(tmp_path)
    monkeypatch.setenv("CLAUDE_PLUGIN_ROOT", str(stub_root))
    harness = FakeHarness(review)
    monkeypatch.setattr(agent_voters.proc, "run", harness.run)
    monkeypatch.setattr(agent_voters.subprocess, "Popen", harness.popen)
    return harness


def test_happy_path_uses_stub_plugin_root_and_emits_clean_final_kvs(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> None:
    review = tmp_path / "review"
    ballot = tmp_path / "ballot.md"
    ballot.write_text("### FINDING_1: one\n", encoding="utf-8")
    harness = _install_harness(monkeypatch, tmp_path, review)

    assert agent_voters.dispatch_voters(_opts(ballot, review)) == 0

    out = capsys.readouterr().out
    assert "VOTER_1_PATH=" in out
    assert "VOTER_2_STATUS=launched" in out
    assert "VOTER_3_STATUS=launched" in out
    assert "DISPATCH_OK=true" in out
    assert "APPENDED=" not in out
    assert "\nSTATUS=" not in out
    paths_file = _kv(out, "VOTER_PATHS_FILE")
    assert Path(paths_file).is_file()
    assert Path(paths_file).read_text(encoding="utf-8").count("vote-output.txt") == 3
    cli_path = str(tmp_path / "stub-plugin" / "python" / "cli.py")
    for call in harness.run_calls:
        assert call[1] == cli_path
    assert harness.popen_calls[0][0][1] == cli_path
    assert harness.popen_calls[0][1] == subprocess.DEVNULL


def test_child_argv_parity_timeout_context_and_parse_rate_args(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    review = tmp_path / "review"
    ballot = tmp_path / "ballot.md"
    ballot.write_text("### FINDING_1: one\n", encoding="utf-8")
    diff = tmp_path / "diff.txt"
    plan = tmp_path / "plan.txt"
    diff.write_bytes(b"d" * 210000)
    plan.write_bytes(b"p" * 70000)
    harness = _install_harness(monkeypatch, tmp_path, review)
    monkeypatch.setenv("LARCH_VOTER_WAIT_TIMEOUT", "7")
    opts = agent_voters.Options(str(ballot), str(review), "true", "true", diff_file=str(diff), plan_file=str(plan))

    assert agent_voters.dispatch_voters(opts) == 0

    launch_argv = harness.popen_calls[0][0]
    assert _value_after(launch_argv, "--mode") == "description"
    assert _value_after(launch_argv, "--timeout") == "1200"
    assert Path(_value_after(launch_argv, "--diff-file")).stat().st_size == 200000
    assert Path(_value_after(launch_argv, "--plan-file")).stat().st_size == 60000
    waterfall = next(call for call in harness.run_calls if _verb(call) == ("agent", "dispatch-waterfall"))
    assert "--slots-file" in waterfall
    assert _value_after(waterfall, "--mode") == "description"
    assert _value_after(waterfall, "--timeout") == "1200"
    assert "--no-fallback" in waterfall
    waiter = next(call for call in harness.run_calls if _verb(call) == ("agent", "wait-reviewers"))
    assert _value_after(waiter, "--timeout") == "7"
    parse_call = next(call for call in harness.run_calls if _verb(call) == ("voting", "parse-rate-retry"))
    for flag in ("--ballot-file", "--id-grammar", "--review-tmpdir", "--plugin-root", "--dispatch-label", "--retry-prefix-kind", "--launch-mode", "--slot", "--voter-file", "--voter-tool", "--prompt-file"):
        assert flag in parse_call
    assert _value_after(parse_call, "--launch-mode") == "description"
    assert "--ctx=--diff-file" in parse_call
    assert "--ctx=--plan-file" in parse_call


def test_render_failure_aborts_before_launch(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    review = tmp_path / "review"
    ballot = tmp_path / "ballot.md"
    ballot.write_text("### FINDING_1: one\n", encoding="utf-8")
    harness = _install_harness(monkeypatch, tmp_path, review)
    harness.render_missing_pointer = True

    with pytest.raises(SystemExit) as excinfo:
        agent_voters.dispatch_voters(_opts(ballot, review))

    assert excinfo.value.code == 2
    assert not harness.popen_calls
    assert not any(_verb(call) == ("agent", "dispatch-waterfall") for call in harness.run_calls)


def test_both_externals_down_shrink_not_backfill(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> None:
    review = tmp_path / "review"
    ballot = tmp_path / "ballot.md"
    ballot.write_text("### FINDING_1: one\n", encoding="utf-8")
    harness = _install_harness(monkeypatch, tmp_path, review)
    harness.waterfall_mode = "none"

    assert agent_voters.dispatch_voters(_opts(ballot, review, codex="false", cursor="false")) == 0

    out = capsys.readouterr().out
    assert "VOTER_2_PATH=\n" in out
    assert "VOTER_2_STATUS=skipped" in out
    assert "VOTER_3_PATH=\n" in out
    assert "VOTER_3_STATUS=skipped" in out
    assert Path(_kv(out, "VOTER_PATHS_FILE")).read_text(encoding="utf-8").count("vote-output.txt") == 1


def test_cursor_only_maps_by_tool_name_and_degrades_available_codex(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> None:
    review = tmp_path / "review"
    ballot = tmp_path / "ballot.md"
    ballot.write_text("### FINDING_1: one\n", encoding="utf-8")
    harness = _install_harness(monkeypatch, tmp_path, review)
    harness.waterfall_mode = "cursor"

    assert agent_voters.dispatch_voters(_opts(ballot, review)) == 0

    out = capsys.readouterr().out
    assert "VOTER_2_PATH=\n" in out
    assert "VOTER_2_STATUS=failed" in out
    assert "VOTER_3_PATH=" in out
    assert "cursor-vote-output.txt" in _kv(out, "VOTER_3_PATH")
    assert "DEGRADED_PANEL_WARNING=" in out


def test_wait_timeout_blocks_voter1_late_sentinel(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> None:
    review = tmp_path / "review"
    ballot = tmp_path / "ballot.md"
    ballot.write_text("### FINDING_1: one\n", encoding="utf-8")
    harness = _install_harness(monkeypatch, tmp_path, review)
    harness.claude_write_done = False
    harness.wait_stdout = f"TIMEOUT 1 {review / 'claude-vote-output.txt.done'}\n"

    assert agent_voters.dispatch_voters(_opts(ballot, review)) == 0

    out = capsys.readouterr().out
    assert "VOTER_1_STATUS=failed" in out
    assert "DISPATCH_OK=false" in out
    assert not (review / "claude-vote-output.txt.done").exists()


def test_successful_voter1_without_launcher_done_gets_local_sentinel_after_wait(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> None:
    review = tmp_path / "review"
    ballot = tmp_path / "ballot.md"
    ballot.write_text("### FINDING_1: one\n", encoding="utf-8")
    harness = _install_harness(monkeypatch, tmp_path, review)
    harness.claude_write_done = False

    assert agent_voters.dispatch_voters(_opts(ballot, review)) == 0

    out = capsys.readouterr().out
    assert "VOTER_1_STATUS=launched" in out
    assert (review / "claude-vote-output.txt.done").read_text(encoding="utf-8") == "0\n"


def test_voter1_failure_appends_pinned_site_and_suppresses_helper_stdout(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> None:
    review = tmp_path / "review"
    ballot = tmp_path / "ballot.md"
    ballot.write_text("### FINDING_1: one\n", encoding="utf-8")
    harness = _install_harness(monkeypatch, tmp_path, review)
    harness.claude_rc = 1
    harness.claude_write_output = False
    harness.claude_write_done = False

    assert agent_voters.dispatch_voters(_opts(ballot, review)) == 0

    out = capsys.readouterr().out
    assert "APPENDED=" not in out
    assert "DISPATCH_OK=false" in out
    assert harness.append_calls
    assert _value_after(harness.append_calls[0], "--site") == "agent dispatch-voters voter1"


def test_default_round_num_cli_smoke_with_stub_plugin_root(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    root = _make_stub_plugin(tmp_path)
    stub = root / "python" / "cli.py"
    stub.write_text(
        "from pathlib import Path\n"
        "import sys\n"
        "args=sys.argv[1:]\n"
        "if args[:2] == ['render','voter']:\n"
        "    print('Read the ballot from this path: /tmp/ballot')\n"
        "elif args[:2] == ['agent','launch-claude-review']:\n"
        "    out=args[args.index('--output')+1]; Path(out).write_text('FINDING_1: YES CORRECTNESS=true SEVERITY=minor QUALITY=good UNCERTAIN=false\\n'); Path(out+'.done').write_text('0\\n')\n"
        "elif args[:2] == ['agent','dispatch-waterfall']:\n"
        "    print('ALL_OUTPUT_FILES=') ; print('ALL_OUTPUT_TOOLS=') ; print('DISPATCH_OK=true')\n"
        "elif args[:2] == ['agent','wait-reviewers']:\n"
        "    pass\n"
        "elif args[:2] == ['voting','parse-rate-retry']:\n"
        "    print('OK')\n"
        "else:\n"
        "    raise SystemExit(2)\n",
        encoding="utf-8",
    )
    ballot = tmp_path / "ballot.md"
    ballot.write_text("### FINDING_1: one\n", encoding="utf-8")
    review = tmp_path / "review"
    monkeypatch.setenv("CLAUDE_PLUGIN_ROOT", str(root))
    result = subprocess.run(
        [
            "python3",
            str(Path(__file__).with_name("cli.py")),
            "agent",
            "dispatch-voters",
            "--ballot-file",
            str(ballot),
            "--review-tmpdir",
            str(review),
            "--codex-available",
            "false",
            "--cursor-available",
            "false",
        ],
        text=True,
        capture_output=True,
        check=False,
        env={**os.environ, "CLAUDE_PLUGIN_ROOT": str(root), "LARCH_QUIET_DISABLE": "1"},
    )
    assert result.returncode == 0
    assert "VOTER_1_STATUS=launched" in result.stdout


def _kv(output: str, key: str) -> str:
    prefix = f"{key}="
    for line in output.splitlines():
        if line.startswith(prefix):
            return line[len(prefix) :]
    return ""
