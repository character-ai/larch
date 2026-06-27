# pyright: reportPrivateUsage=false, reportUnusedCallResult=false
# pyright: reportMissingParameterType=false, reportUnknownMemberType=false, reportUnknownArgumentType=false, reportArgumentType=false
from __future__ import annotations

import os
import subprocess
import sys
import textwrap
import time
from pathlib import Path
from collections.abc import Sequence
from typing import Any

import pytest

from larch.agents import agent_voters
from larch.core import proc

REPO_ROOT = Path(__file__).resolve().parents[1]
CLI = REPO_ROOT / "python" / "cli.py"


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
        self.harness.events.append("claude_wait")
        return self.returncode


class FakeHarness:
    def __init__(self, review_tmpdir: Path) -> None:
        self.review_tmpdir = review_tmpdir
        self.run_calls: list[list[str]] = []
        self.popen_calls: list[tuple[list[str], object, object]] = []
        self.append_calls: list[list[str]] = []
        self.events: list[str] = []
        self.render_missing_pointer = False
        self.render_rc = 0
        self.waterfall_rc = 0
        self.waterfall_mode = "both"
        self.wait_stdout = ""
        self.wait_rc = 0
        self.parse_status: dict[str, str] = {}
        self.parse_rate_rc: dict[str, int] = {}
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
        if verb == ("agent", "launch-review"):
            output = _value_after(args, "--output")
            if output:
                Path(output).write_text("FINDING_1: YES CORRECTNESS=true SEVERITY=minor QUALITY=good UNCERTAIN=false\n", encoding="utf-8")
                Path(output + ".done").write_text("0\n", encoding="utf-8")
            return _result(args, 0)
        if verb == ("agent", "dispatch-waterfall"):
            self.events.append("waterfall")
            return self._waterfall(args)
        if verb == ("agent", "wait-reviewers"):
            stdout_fd = kwargs.get("stdout")
            if isinstance(stdout_fd, int):
                os.write(stdout_fd, self.wait_stdout.encode("utf-8"))
                return _result(args, self.wait_rc)
            return _result(args, self.wait_rc, stdout=self.wait_stdout)
        if verb == ("voting", "parse-rate-retry"):
            tool = _value_after(args, "--voter-tool") or ""
            rc = self.parse_rate_rc.get(tool, 0)
            stdout = (self.parse_status.get(tool, "OK") + "\n") if rc == 0 else ""
            return _result(args, rc, stdout=stdout)
        if verb == ("run-log", "append-failure"):
            self.append_calls.append(args)
            return _result(args, 0, stdout="APPENDED=true\nLOG=/tmp/log\n")
        return _result(args, 2, stderr=f"unexpected args: {args}\n")

    def _waterfall(self, args: list[str]) -> proc.CommandResult:
        slots_file = Path(_value_after(args, "--slots-file"))
        rows = [__import__("json").loads(line) for line in slots_file.read_text(encoding="utf-8").splitlines() if line]
        outputs: list[str] = []
        tools: list[str] = []
        for idx, row in enumerate(rows, start=1):
            if self.waterfall_mode == "none":
                continue
            if self.waterfall_mode == "slot2_failed" and row.get("slot") == "voter-2":
                continue
            out = Path(str(row["output"]))
            vote = "YES" if idx != 3 else "NO"
            out.write_text(f"FINDING_1: {vote} CORRECTNESS=true SEVERITY=minor QUALITY=good UNCERTAIN=false\n", encoding="utf-8")
            Path(str(out) + ".done").write_text("0\n", encoding="utf-8")
            outputs.append(str(out))
            tools.append(str(row.get("tool", "cursor")))
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


def _opts(ballot: Path, review: Path, *, codex: str = "true", cursor: str = "true", round_num: int = 1) -> agent_voters.Options:
    return agent_voters.Options(
        ballot_file=str(ballot),
        review_tmpdir=str(review),
        codex_available=codex,
        cursor_available=cursor,
        round_num=round_num,
    )


def _install_harness(monkeypatch: pytest.MonkeyPatch, tmp_path: Path, review: Path) -> tuple[FakeHarness, Path]:
    stub_root = _make_stub_plugin(tmp_path)
    monkeypatch.setenv("CLAUDE_PLUGIN_ROOT", str(stub_root))
    harness = FakeHarness(review)
    monkeypatch.setattr(agent_voters.proc, "run", harness.run)
    monkeypatch.setattr(agent_voters.subprocess, "Popen", harness.popen)
    return harness, stub_root


def _assert_stub_plugin_root_on_calls(harness: FakeHarness, stub_root: Path) -> None:
    cli_path = str(stub_root / "python" / "cli.py")
    for call in harness.run_calls:
        assert call[1] == cli_path
    for popen_argv, _, _ in harness.popen_calls:
        assert popen_argv[1] == cli_path
    parse_calls = [call for call in harness.run_calls if _verb(call) == ("voting", "parse-rate-retry")]
    for parse_call in parse_calls:
        assert _value_after(parse_call, "--plugin-root") == str(stub_root)


@pytest.mark.voter_happy
def test_happy_path_uses_stub_plugin_root_and_emits_clean_final_kvs(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> None:
    review = tmp_path / "review"
    ballot = tmp_path / "ballot.md"
    ballot.write_text("### FINDING_1: one\n", encoding="utf-8")
    harness, stub_root = _install_harness(monkeypatch, tmp_path, review)

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
    _assert_stub_plugin_root_on_calls(harness, stub_root)
    # Cursor voter 1 launches asynchronously via Popen so it runs in parallel
    # with the voters 2+3 waterfall (issue #5448).
    assert len(harness.popen_calls) == 1
    assert harness.popen_calls[0][0][2:4] == ["agent", "launch-review"]


@pytest.mark.voter_happy
def test_child_argv_parity_timeout_context_and_parse_rate_args(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    review = tmp_path / "review"
    ballot = tmp_path / "ballot.md"
    ballot.write_text("### FINDING_1: one\n", encoding="utf-8")
    diff = tmp_path / "diff.txt"
    plan = tmp_path / "plan.txt"
    diff.write_bytes(b"d" * 210000)
    plan.write_bytes(b"p" * 70000)
    harness, stub_root = _install_harness(monkeypatch, tmp_path, review)
    monkeypatch.setenv("LARCH_VOTER_WAIT_TIMEOUT", "7")
    opts = agent_voters.Options(str(ballot), str(review), "true", "true", diff_file=str(diff), plan_file=str(plan))

    assert agent_voters.dispatch_voters(opts) == 0

    # Cursor voter 1 launches asynchronously via Popen with the same launch-review
    # argv (tool, timing kind, timeout, site, bounded context) it carried when
    # blocking (issue #5448).
    assert len(harness.popen_calls) == 1
    voter1_argv = harness.popen_calls[0][0]
    assert voter1_argv[2:4] == ["agent", "launch-review"]
    assert _value_after(voter1_argv, "--tool") == "cursor"
    assert _value_after(voter1_argv, "--timing-task-kind") == "cursor-code-voter-validity"
    assert _value_after(voter1_argv, "--timeout") == "1200"
    assert _value_after(voter1_argv, "--site") == "review Step 2"
    assert Path(_value_after(voter1_argv, "--diff-file")).stat().st_size == 200000
    assert Path(_value_after(voter1_argv, "--plan-file")).stat().st_size == 60000
    render_calls = [call for call in harness.run_calls if _verb(call) == ("render", "voter")]
    assert [ _value_after(call, "--archetype") for call in render_calls ] == [
        "validity-correctness",
        "plan-fidelity-completeness",
        "pragmatism-cost",
    ]
    assert all(_value_after(call, "--findings-ledger-file") == str(review / "findings-ledger.tsv") for call in render_calls)
    waterfall = next(call for call in harness.run_calls if _verb(call) == ("agent", "dispatch-waterfall"))
    assert "--slots-file" in waterfall
    assert _value_after(waterfall, "--mode") == "description"
    assert _value_after(waterfall, "--timeout") == "1200"
    assert Path(_value_after(waterfall, "--diff-file")).stat().st_size == 200000
    assert Path(_value_after(waterfall, "--plan-file")).stat().st_size == 60000
    assert "--no-fallback" not in waterfall
    assert _value_after(waterfall, "--model-role") == "vote"
    waiter = next(call for call in harness.run_calls if _verb(call) == ("agent", "wait-reviewers"))
    assert _value_after(waiter, "--timeout") == "7"
    parse_call = next(call for call in harness.run_calls if _verb(call) == ("voting", "parse-rate-retry"))
    for flag in ("--ballot-file", "--id-grammar", "--review-tmpdir", "--plugin-root", "--dispatch-label", "--slot", "--voter-file", "--voter-tool"):
        assert flag in parse_call
    for flag in ("--prompt-file", "--retry-prefix-kind", "--launch-mode"):
        assert flag not in parse_call
    assert _value_after(parse_call, "--plugin-root") == str(stub_root)
    assert "--ctx=--diff-file" in parse_call
    assert "--ctx=--plan-file" in parse_call


@pytest.mark.voter_happy
def test_voter_prompts_use_nested_implement_ledger_root(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    impl = tmp_path / "impl"
    review = impl / "round-2"
    review.mkdir(parents=True)
    ballot = tmp_path / "ballot.md"
    ballot.write_text("### FINDING_1: one\n", encoding="utf-8")
    harness, _stub_root = _install_harness(monkeypatch, tmp_path, review)
    monkeypatch.setenv("IMPLEMENT_TMPDIR", str(impl))
    opts = agent_voters.Options(
        ballot_file=str(ballot),
        review_tmpdir=str(review),
        codex_available="true",
        cursor_available="true",
        session_env_path=str(impl / "session-env.sh"),
        round_num=2,
    )

    assert agent_voters.dispatch_voters(opts) == 0

    render_calls = [call for call in harness.run_calls if _verb(call) == ("render", "voter")]
    assert render_calls
    assert all(_value_after(call, "--findings-ledger-file") == str(impl / "findings-ledger.tsv") for call in render_calls)


@pytest.mark.voter_happy
def test_render_failure_aborts_before_launch(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    review = tmp_path / "review"
    ballot = tmp_path / "ballot.md"
    ballot.write_text("### FINDING_1: one\n", encoding="utf-8")
    harness, _stub_root = _install_harness(monkeypatch, tmp_path, review)
    harness.render_missing_pointer = True

    with pytest.raises(SystemExit) as excinfo:
        agent_voters.dispatch_voters(_opts(ballot, review))

    assert excinfo.value.code == 2
    assert not harness.popen_calls
    assert not any(_verb(call) == ("agent", "dispatch-waterfall") for call in harness.run_calls)


@pytest.mark.voter_happy
def test_render_nonzero_exit_aborts_before_launch(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    review = tmp_path / "review"
    ballot = tmp_path / "ballot.md"
    ballot.write_text("### FINDING_1: one\n", encoding="utf-8")
    harness, _stub_root = _install_harness(monkeypatch, tmp_path, review)
    harness.render_rc = 1

    with pytest.raises(SystemExit) as excinfo:
        agent_voters.dispatch_voters(_opts(ballot, review))

    assert excinfo.value.code == 2
    assert not harness.popen_calls
    assert not any(_verb(call) == ("agent", "dispatch-waterfall") for call in harness.run_calls)


@pytest.mark.voter_happy
def test_both_externals_down_shrink_not_backfill(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> None:
    review = tmp_path / "review"
    ballot = tmp_path / "ballot.md"
    ballot.write_text("### FINDING_1: one\n", encoding="utf-8")
    harness, _stub_root = _install_harness(monkeypatch, tmp_path, review)
    harness.waterfall_mode = "none"

    assert agent_voters.dispatch_voters(_opts(ballot, review, codex="false", cursor="false")) == 0

    out = capsys.readouterr().out
    assert "VOTER_1_TOOL=claude" in out
    assert "VOTER_2_PATH=\n" in out
    assert "VOTER_2_TOOL=codex-plan-fidelity" in out
    assert "VOTER_2_STATUS=skipped" in out
    assert "VOTER_3_PATH=\n" in out
    assert "VOTER_3_TOOL=codex-pragmatism" in out
    assert "VOTER_3_STATUS=skipped" in out
    assert Path(_kv(out, "VOTER_PATHS_FILE")).read_text(encoding="utf-8").count("vote-output.txt") == 1


@pytest.mark.voter_happy
def test_failed_middle_cursor_slot_degrades_without_backfill(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> None:
    review = tmp_path / "review"
    ballot = tmp_path / "ballot.md"
    ballot.write_text("### FINDING_1: one\n", encoding="utf-8")
    harness, _stub_root = _install_harness(monkeypatch, tmp_path, review)
    harness.waterfall_mode = "slot2_failed"

    assert agent_voters.dispatch_voters(_opts(ballot, review)) == 0

    out = capsys.readouterr().out
    assert _kv(out, "VOTER_2_PATH") == ""
    assert "VOTER_2_STATUS=failed" in out
    assert "VOTER_3_PATH=" in out
    assert "codex-pragmatism-vote-output.txt" in _kv(out, "VOTER_3_PATH")
    assert not (review / "codex-vote-output.txt").exists()
    assert "DEGRADED_PANEL_WARNING=" in out


@pytest.mark.voter_happy
def test_wait_timeout_blocks_voter1_late_sentinel(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> None:
    review = tmp_path / "review"
    ballot = tmp_path / "ballot.md"
    ballot.write_text("### FINDING_1: one\n", encoding="utf-8")
    harness, _stub_root = _install_harness(monkeypatch, tmp_path, review)
    harness.claude_write_done = False
    harness.wait_stdout = f"TIMEOUT 1 {review / 'claude-vote-output.txt.done'}\n"

    assert agent_voters.dispatch_voters(_opts(ballot, review, cursor="false")) == 0

    out = capsys.readouterr().out
    assert "VOTER_1_STATUS=failed" in out
    assert "DISPATCH_OK=false" in out
    assert not (review / "claude-vote-output.txt.done").exists()


@pytest.mark.voter_happy
def test_successful_voter1_without_launcher_done_gets_local_sentinel_after_wait(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> None:
    review = tmp_path / "review"
    ballot = tmp_path / "ballot.md"
    ballot.write_text("### FINDING_1: one\n", encoding="utf-8")
    harness, _stub_root = _install_harness(monkeypatch, tmp_path, review)
    harness.claude_write_done = False

    assert agent_voters.dispatch_voters(_opts(ballot, review, cursor="false")) == 0

    out = capsys.readouterr().out
    assert "VOTER_1_STATUS=launched" in out
    assert (review / "claude-vote-output.txt.done").read_text(encoding="utf-8") == "0\n"


@pytest.mark.voter_happy
def test_voter1_failure_appends_pinned_site_and_suppresses_helper_stdout(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> None:
    review = tmp_path / "review"
    ballot = tmp_path / "ballot.md"
    ballot.write_text("### FINDING_1: one\n", encoding="utf-8")
    harness, _stub_root = _install_harness(monkeypatch, tmp_path, review)
    harness.claude_rc = 1
    harness.claude_write_output = False
    harness.claude_write_done = False

    assert agent_voters.dispatch_voters(_opts(ballot, review, cursor="false")) == 0

    out = capsys.readouterr().out
    assert "APPENDED=" not in out
    assert "DISPATCH_OK=false" in out
    assert harness.append_calls
    assert _value_after(harness.append_calls[0], "--site") == "agent dispatch-voters voter1"


@pytest.mark.voter_happy
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


def _harness_review_tmpdir(tmp_path: Path, label: str = "review") -> Path:
    base = tmp_path / "test_agent_voters.tmp" / label
    base.mkdir(parents=True)
    return base


def _standard_ballot(tmp_path: Path) -> Path:
    ballot = tmp_path / "ballot.md"
    ballot.write_text("### FINDING_1: First\n- **Reviewer**: stub\n", encoding="utf-8")
    return ballot


def _make_voter_stub_bin(tmp_path: Path) -> Path:
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    claude = textwrap.dedent(
        """\
        #!/usr/bin/env bash
        cat >/dev/null
        case "${CLAUDE_STUB_MODE:-ok}" in
          empty) exit 0 ;;
          wait_for_marker)
            _i=0
            while [[ ! -f "${CLAUDE_STUB_WAIT_MARKER:?}" && "$_i" -lt 100 ]]; do
              sleep 0.05
              _i=$((_i + 1))
            done
            [[ -f "${CLAUDE_STUB_WAIT_MARKER}" ]] || exit 1
            printf '%s\\n' '{"result":"FINDING_1: YES\\n","usage":{"input_tokens":1,"output_tokens":1}}'
            exit 0 ;;
          fail_nonempty)
            printf '%s\\n' '{"result":"stub voter output for diag test\\n","usage":{"input_tokens":1,"output_tokens":1}}'
            exit 7 ;;
          fail)
            printf 'stub claude failure\\n' >&2
            exit 7 ;;
          parse_retry_success)
            count_file="${CLAUDE_STUB_COUNT_FILE:?CLAUDE_STUB_COUNT_FILE required}"
            count=0
            [[ -f "$count_file" ]] && count=$(cat "$count_file" 2>/dev/null || echo 0)
            count=$((count + 1))
            printf '%s\\n' "$count" > "$count_file"
            if [[ "$count" -eq 1 ]]; then
              printf '%s\\n' '{"result":"I reviewed the ballot and here is my narrative instead of votes.\\n","usage":{"input_tokens":1,"output_tokens":1}}'
            else
              printf '%s\\n' '{"result":"FINDING_1: YES CORRECTNESS=true SEVERITY=minor QUALITY=good UNCERTAIN=false\\n","usage":{"input_tokens":1,"output_tokens":1}}'
            fi
            exit 0 ;;
          parse_retry_fail)
            count_file="${CLAUDE_STUB_COUNT_FILE:?CLAUDE_STUB_COUNT_FILE required}"
            count=0
            [[ -f "$count_file" ]] && count=$(cat "$count_file" 2>/dev/null || echo 0)
            count=$((count + 1))
            printf '%s\\n' "$count" > "$count_file"
            printf '%s\\n' '{"result":"I reviewed the ballot and here is my narrative instead of votes.\\n","usage":{"input_tokens":1,"output_tokens":1}}'
            exit 0 ;;
        esac
        printf '%s\\n' '{"result":"FINDING_1: YES CORRECTNESS=true SEVERITY=minor QUALITY=good UNCERTAIN=false\\n","usage":{"input_tokens":1,"output_tokens":1}}'
        """
    )
    codex = textwrap.dedent(
        """\
        #!/usr/bin/env bash
        out=""; last=""
        for arg in "$@"; do [[ "$last" == "--output-last-message" ]] && out="$arg"; last="$arg"; done
        [[ -n "$out" ]] || exit 9
        case "${CODEX_STUB_MODE:-ok}" in
          parse_retry_success)
            count_file="${CODEX_STUB_COUNT_FILE:?CODEX_STUB_COUNT_FILE required}"
            count=0
            [[ -f "$count_file" ]] && count=$(cat "$count_file" 2>/dev/null || echo 0)
            count=$((count + 1))
            printf '%s\\n' "$count" > "$count_file"
            if [[ "$count" -eq 1 ]]; then
              printf 'Narrative codex output without structured votes.\\n' > "$out"
            else
              printf 'FINDING_1: YES CORRECTNESS=true SEVERITY=minor QUALITY=good UNCERTAIN=false\\n' > "$out"
            fi ;;
          parse_retry_fail)
            count_file="${CODEX_STUB_COUNT_FILE:?CODEX_STUB_COUNT_FILE required}"
            count=0
            [[ -f "$count_file" ]] && count=$(cat "$count_file" 2>/dev/null || echo 0)
            count=$((count + 1))
            printf '%s\\n' "$count" > "$count_file"
            printf 'Narrative codex output without structured votes.\\n' > "$out" ;;
          *)
            printf 'FINDING_1: YES CORRECTNESS=true SEVERITY=minor QUALITY=good UNCERTAIN=false\\n' > "$out" ;;
        esac
        """
    )
    cursor = textwrap.dedent(
        """\
        #!/usr/bin/env bash
        case "${CURSOR_STUB_MODE:-ok}" in
          parse_retry_success)
            count_file="${CURSOR_STUB_COUNT_FILE:?CURSOR_STUB_COUNT_FILE required}"
            count=0
            [[ -f "$count_file" ]] && count=$(cat "$count_file" 2>/dev/null || echo 0)
            count=$((count + 1))
            printf '%s\\n' "$count" > "$count_file"
            if [[ "$count" -eq 1 ]]; then
              printf '{"result":"Narrative cursor output without structured votes.","usage":{"inputTokens":1,"outputTokens":1,"cacheReadTokens":0,"cacheWriteTokens":0}}\\n'
            else
              printf '{"result":"FINDING_1: NO CORRECTNESS=true SEVERITY=minor QUALITY=good UNCERTAIN=false -- cursor","usage":{"inputTokens":1,"outputTokens":1,"cacheReadTokens":0,"cacheWriteTokens":0}}\\n'
            fi ;;
          parse_retry_fail)
            count_file="${CURSOR_STUB_COUNT_FILE:?CURSOR_STUB_COUNT_FILE required}"
            count=0
            [[ -f "$count_file" ]] && count=$(cat "$count_file" 2>/dev/null || echo 0)
            count=$((count + 1))
            printf '%s\\n' "$count" > "$count_file"
            printf '{"result":"Narrative cursor output without structured votes.","usage":{"inputTokens":1,"outputTokens":1,"cacheReadTokens":0,"cacheWriteTokens":0}}\\n' ;;
          *)
            printf '{"result":"FINDING_1: NO CORRECTNESS=true SEVERITY=minor QUALITY=good UNCERTAIN=false -- cursor","usage":{"inputTokens":1,"outputTokens":1,"cacheReadTokens":0,"cacheWriteTokens":0}}\\n' ;;
        esac
        """
    )
    for name, body in (("claude", claude), ("codex", codex), ("cursor", cursor)):
        path = bin_dir / name
        path.write_text(body, encoding="utf-8")
        path.chmod(0o755)
    return bin_dir


def _write_wait_barrier_stub_plugin(root: Path, real_cli: Path) -> None:
    (root / "python").mkdir(parents=True)
    script = textwrap.dedent(
        f"""\
        import os
        import sys
        import time
        from pathlib import Path
        REAL_CLI = {str(real_cli)!r}
        if sys.argv[1:3] == ["agent", "wait-reviewers"]:
            if os.environ.get("LARCH_FORCE_WAIT_USAGE_ERROR") == "1":
                print("usage: forced test wait failure", file=sys.stderr)
                raise SystemExit(1)
            os.execv(sys.executable, [sys.executable, REAL_CLI, *sys.argv[1:]])
        if sys.argv[1:2] == ["voting"]:
            os.execv(sys.executable, [sys.executable, REAL_CLI, *sys.argv[1:]])
        if sys.argv[1:3] == ["agent", "launch-review"]:
            output = ""
            args = sys.argv[3:]
            i = 0
            while i < len(args):
                if args[i] == "--output":
                    output = args[i + 1]
                    i += 2
                elif args[i].startswith("--") and i + 1 < len(args):
                    i += 2
                else:
                    i += 1
            if not output:
                raise SystemExit(2)
            Path(output).write_text("FINDING_1: YES CORRECTNESS=true SEVERITY=minor QUALITY=good UNCERTAIN=false\\n", encoding="utf-8")
            Path(output + ".done").write_text("0\\n", encoding="utf-8")
            raise SystemExit(0)
        if sys.argv[1:3] == ["agent", "launch-claude-review"]:
            output = ""
            args = sys.argv[3:]
            i = 0
            while i < len(args):
                if args[i] in ("--output", "--output-file"):
                    output = args[i + 1]
                    i += 2
                elif args[i] in ("--prompt-file", "--mode", "--role", "--timeout", "--timing-task-kind", "--diff-file", "--plan-file"):
                    i += 2
                else:
                    i += 1
            if not output:
                raise SystemExit(2)
            if os.environ.get("CLAUDE_STUB_MODE") == "wait_for_marker":
                marker = os.environ["CLAUDE_STUB_WAIT_MARKER"]
                for _ in range(100):
                    if Path(marker).is_file():
                        break
                    time.sleep(0.05)
                if not Path(marker).is_file():
                    raise SystemExit(1)
                Path(output).write_text("FINDING_1: YES\\nOOS_1: NO -- claude parallel ok\\n", encoding="utf-8")
            else:
                Path(output).write_text("FINDING_1: YES CORRECTNESS=true SEVERITY=minor QUALITY=good UNCERTAIN=false\\n", encoding="utf-8")
            Path(output + ".done").write_text("0\\n", encoding="utf-8")
            raise SystemExit(0)
        if sys.argv[1:3] == ["agent", "dispatch-waterfall"]:
            import json
            args = sys.argv[3:]
            slots_file = args[args.index("--slots-file") + 1]
            rows = [json.loads(line) for line in Path(slots_file).read_text(encoding="utf-8").splitlines() if line]
            review_tmpdir = str(Path(rows[0]["output"]).parent)
            mode = os.environ.get("LARCH_WAIT_BARRIER_MODE", "delayed")
            delay = float(os.environ.get("LARCH_WAIT_BARRIER_DELAY", "0.2"))
            if mode == "concurrent":
                Path(os.environ["LARCH_WAIT_BARRIER_MARKER"]).write_text("", encoding="utf-8")
            if mode == "timeout":
                Path(review_tmpdir, "timeout-mode-observed").write_text("", encoding="utf-8")
            outputs = []
            for index, row in enumerate(rows, start=1):
                out = row["output"]
                outputs.append(out)
                if mode == "timeout":
                    continue
                vote = "NO" if index == 3 else "YES"
                Path(out).write_text("FINDING_1: " + vote + "\\n", encoding="utf-8")
                if mode == "nonzero_done":
                    Path(out + ".done").write_text(str(index + 6) + "\\n", encoding="utf-8")
                elif mode == "delayed":
                    pass
                else:
                    Path(out + ".done").write_text("0\\n", encoding="utf-8")
            if mode == "delayed":
                time.sleep(delay)
                for out in outputs:
                    Path(out + ".done").write_text("0\\n", encoding="utf-8")
            print("ALL_OUTPUT_FILES=" + " ".join(outputs))
            print("ALL_OUTPUT_TOOLS=" + " ".join(["cursor"] * len(outputs)))
            print("DISPATCH_OK=true")
            raise SystemExit(0)
        if sys.argv[1:3] == ["render", "voter"]:
            print("stub voter prompt")
            print("Read the ballot from this path: /stub/ballot")
            raise SystemExit(0)
        if sys.argv[1:3] == ["run-log", "append-failure"]:
            os.execv(sys.executable, [sys.executable, REAL_CLI, *sys.argv[1:]])
        print(f"unexpected cli args: {{sys.argv[1:]}}", file=sys.stderr)
        raise SystemExit(2)
        """
    )
    (root / "python" / "cli.py").write_text(script.lstrip(), encoding="utf-8")
    (root / "python" / "cli.py").chmod(0o755)


def _write_voter1_delayed_done_stub_plugin(root: Path, real_cli: Path) -> None:
    (root / "python").mkdir(parents=True)
    script = textwrap.dedent(
        f"""\
        import os
        import subprocess
        import sys
        from pathlib import Path
        REAL_CLI = {str(real_cli)!r}
        log_file = os.environ.get("LARCH_STUB_CLI_LOG", "")
        if log_file:
            Path(log_file).parent.mkdir(parents=True, exist_ok=True)
            with open(log_file, "a", encoding="utf-8") as handle:
                handle.write(" ".join(sys.argv) + "\\n")
        if sys.argv[1:3] == ["agent", "wait-reviewers"]:
            os.execv(sys.executable, [sys.executable, REAL_CLI, *sys.argv[1:]])
        if sys.argv[1:2] == ["voting"]:
            os.execv(sys.executable, [sys.executable, REAL_CLI, *sys.argv[1:]])
        if sys.argv[1:3] == ["agent", "launch-review"]:
            output = ""
            args = sys.argv[3:]
            i = 0
            while i < len(args):
                if args[i] == "--output":
                    output = args[i + 1]
                    i += 2
                elif args[i].startswith("--") and i + 1 < len(args):
                    i += 2
                else:
                    i += 1
            if not output:
                raise SystemExit(2)
            Path(output).write_text("FINDING_1: YES CORRECTNESS=true SEVERITY=minor QUALITY=good UNCERTAIN=false\\n", encoding="utf-8")
            Path(output + ".done").write_text("0\\n", encoding="utf-8")
            raise SystemExit(0)
        if sys.argv[1:3] == ["agent", "launch-claude-review"]:
            output = ""
            args = sys.argv[3:]
            i = 0
            while i < len(args):
                if args[i] in ("--output", "--output-file"):
                    output = args[i + 1]
                    i += 2
                elif args[i] in ("--prompt-file", "--mode", "--role", "--timeout", "--timing-task-kind", "--diff-file", "--plan-file"):
                    i += 2
                else:
                    i += 1
            if not output:
                raise SystemExit(2)
            Path(output).write_text("FINDING_1: YES CORRECTNESS=true SEVERITY=minor QUALITY=good UNCERTAIN=false\\n", encoding="utf-8")
            if os.environ.get("LARCH_VOTER1_DONE_MODE", "delayed") != "missing":
                delay = os.environ.get("LARCH_VOTER1_DONE_DELAY", "1")
                subprocess.Popen([
                    sys.executable,
                    "-c",
                    "import pathlib,sys,time; time.sleep(float(sys.argv[1])); pathlib.Path(sys.argv[2]).write_text('0\\\\n', encoding='utf-8')",
                    delay,
                    output + ".done",
                ])
            raise SystemExit(0)
        if sys.argv[1:3] == ["agent", "dispatch-waterfall"]:
            import json
            slots_file = ""
            args = sys.argv[3:]
            i = 0
            while i < len(args):
                if args[i] == "--slots-file":
                    slots_file = args[i + 1]
                    i += 2
                elif args[i] in ("--codex-present", "--cursor-present", "--mode", "--timeout", "--model-role", "--site", "--diff-file", "--plan-file", "--feature-file", "--require-result-pattern", "--require-first-line-pattern", "--paths-file"):
                    i += 2
                else:
                    i += 1
            if not slots_file:
                raise SystemExit(2)
            rows = [json.loads(line) for line in Path(slots_file).read_text(encoding="utf-8").splitlines() if line]
            outputs = []
            tools = []
            for index, row in enumerate(rows, start=1):
                out = row["output"]
                vote = "NO" if index == 2 else "YES"
                Path(out).write_text("FINDING_1: " + vote + " CORRECTNESS=true SEVERITY=minor QUALITY=good UNCERTAIN=false\\n", encoding="utf-8")
                Path(out + ".done").write_text("0\\n", encoding="utf-8")
                outputs.append(out)
                tools.append(row.get("tool", "codex"))
            print("ALL_OUTPUT_FILES=" + " ".join(outputs))
            print("ALL_OUTPUT_TOOLS=" + " ".join(tools))
            print("DISPATCH_OK=true")
            raise SystemExit(0)
        if sys.argv[1:3] == ["render", "voter"]:
            print("stub voter prompt")
            print("Read the ballot from this path: /stub/ballot")
            raise SystemExit(0)
        print(f"unexpected cli args: {{sys.argv[1:]}}", file=sys.stderr)
        raise SystemExit(2)
        """
    )
    (root / "python" / "cli.py").write_text(script, encoding="utf-8")
    (root / "python" / "cli.py").chmod(0o755)


def _dispatch_via_cli(
    review: Path,
    ballot: Path,
    *,
    stub_bin: Path,
    plugin_root: Path | None = None,
    env: dict[str, str] | None = None,
    codex_available: str = "true",
    cursor_available: str = "true",
    round_num: str = "1",
    diff_file: str = "",
    plan_file: str = "",
) -> subprocess.CompletedProcess[str]:
    merged = os.environ.copy()
    merged.update(
        {
            "LARCH_QUIET_DISABLE": "1",
            "RUN_EXTERNAL_AGENT_POLL_INTERVAL": "0.05",
            "WAIT_FOR_REVIEWERS_POLL_INTERVAL": "0.05",
            "LARCH_EXTERNAL_HEALTH_CHECK_TIMEOUT": "0",
            "PATH": f"{stub_bin}:{merged.get('PATH', '')}",
        }
    )
    merged.pop("LARCH_EXECUTION_ISSUES_LOG", None)
    merged.pop("SESSION_ENV_PATH", None)
    merged.pop("IMPLEMENT_TMPDIR", None)
    if plugin_root is not None:
        merged["CLAUDE_PLUGIN_ROOT"] = str(plugin_root)
    else:
        merged.pop("CLAUDE_PLUGIN_ROOT", None)
    if env:
        merged.update(env)
    args = [
        sys.executable,
        str(CLI),
        "agent",
        "dispatch-voters",
        "--ballot-file",
        str(ballot),
        "--review-tmpdir",
        str(review),
        "--codex-available",
        codex_available,
        "--cursor-available",
        cursor_available,
        "--round-num",
        round_num,
    ]
    if diff_file:
        args.extend(["--diff-file", diff_file])
    if plan_file:
        args.extend(["--plan-file", plan_file])
    return subprocess.run(args, text=True, capture_output=True, env=merged, check=False, cwd=REPO_ROOT)


@pytest.mark.voter_happy
def test_waterfall_dispatch_runs_before_claude_wait(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    review = tmp_path / "review"
    ballot = _standard_ballot(tmp_path)
    harness, _stub_root = _install_harness(monkeypatch, tmp_path, review)

    assert agent_voters.dispatch_voters(_opts(ballot, review)) == 0

    # Cursor voter 1 launches asynchronously, so the voters 2+3 waterfall is
    # dispatched while voter 1 is still in flight; the voter-1 wait barrier
    # (recorded by the fake Popen as "claude_wait") resolves only afterward
    # (issue #5448).
    assert harness.events.index("waterfall") < harness.events.index("claude_wait")
    assert len(harness.popen_calls) == 1
    assert harness.popen_calls[0][0][2:4] == ["agent", "launch-review"]


@pytest.mark.voter_happy
def test_one_external_down_shrink_without_degraded_warning(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> None:
    review = tmp_path / "review"
    ballot = _standard_ballot(tmp_path)
    harness, _stub_root = _install_harness(monkeypatch, tmp_path, review)
    harness.waterfall_mode = "cursor"

    assert agent_voters.dispatch_voters(_opts(ballot, review, codex="false", cursor="true")) == 0

    out = capsys.readouterr().out
    assert "VOTER_1_TOOL=cursor-validity" in out
    assert "VOTER_2_STATUS=launched" in out
    assert "VOTER_3_STATUS=launched" in out
    assert "DEGRADED_PANEL_WARNING=" not in out
    assert Path(_kv(out, "VOTER_PATHS_FILE")).read_text(encoding="utf-8").count("vote-output.txt") == 3


@pytest.mark.voter_happy
def test_round2_three_judge_parity(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> None:
    review = tmp_path / "review"
    ballot = _standard_ballot(tmp_path)
    _harness, _stub_root = _install_harness(monkeypatch, tmp_path, review)

    assert agent_voters.dispatch_voters(_opts(ballot, review, round_num=2)) == 0

    out = capsys.readouterr().out
    assert "VOTER_2_STATUS=launched" in out
    assert "VOTER_3_STATUS=launched" in out
    assert "DEGRADED_PANEL_WARNING=" not in out
    manifest = review / "code-voter-slots.ndjson"
    assert manifest.is_file()
    text = manifest.read_text(encoding="utf-8")
    assert '"slot":"voter-1"' not in text
    assert '"slot":"voter-2"' in text
    assert '"slot":"voter-3"' in text
    assert text.count('"tool":"codex"') == 2


@pytest.mark.voter_happy
def test_parallel_dispatch_concurrent_waterfall_and_claude(tmp_path: Path) -> None:
    stub_bin = _make_voter_stub_bin(tmp_path)
    plugin = tmp_path / "wait-plugin"
    _write_wait_barrier_stub_plugin(plugin, CLI)
    review = tmp_path / "parallel-dispatch"
    review.mkdir()
    ballot = _standard_ballot(tmp_path)
    marker = review / "waterfall-started"
    result = _dispatch_via_cli(
        review,
        ballot,
        stub_bin=stub_bin,
        plugin_root=plugin,
        env={
            "CLAUDE_STUB_MODE": "wait_for_marker",
            "CLAUDE_STUB_WAIT_MARKER": str(marker),
            "LARCH_WAIT_BARRIER_MODE": "concurrent",
            "LARCH_WAIT_BARRIER_MARKER": str(marker),
            "LARCH_WAIT_BARRIER_VOTER2": str(review / "codex-vote-output.txt"),
            "LARCH_WAIT_BARRIER_VOTER3": str(review / "cursor-vote-output.txt"),
            "LARCH_VOTER_WAIT_TIMEOUT": "2",
        },
    )
    assert result.returncode == 0, result.stderr
    assert "VOTER_1_STATUS=launched" in result.stdout
    assert "VOTER_2_STATUS=launched" in result.stdout
    assert "VOTER_3_STATUS=launched" in result.stdout
    assert "DISPATCH_OK=true" in result.stdout


@pytest.mark.voter_happy
def test_wait_usage_error_proceeds_with_existing_output(tmp_path: Path) -> None:
    stub_bin = _make_voter_stub_bin(tmp_path)
    plugin = tmp_path / "wait-usage-plugin"
    _write_wait_barrier_stub_plugin(plugin, CLI)
    review = tmp_path / "wait-usage-error"
    review.mkdir()
    ballot = _standard_ballot(tmp_path)
    result = _dispatch_via_cli(
        review,
        ballot,
        stub_bin=stub_bin,
        plugin_root=plugin,
        env={
            "LARCH_FORCE_WAIT_USAGE_ERROR": "1",
            "LARCH_WAIT_BARRIER_MODE": "immediate",
            "LARCH_WAIT_BARRIER_VOTER2": str(review / "codex-vote-output.txt"),
            "LARCH_WAIT_BARRIER_VOTER3": str(review / "cursor-vote-output.txt"),
        },
    )
    assert result.returncode == 0, result.stderr
    assert "VOTER_2_STATUS=launched" in result.stdout
    assert "VOTER_3_STATUS=launched" in result.stdout
    assert "wait-reviewers exited 1" in result.stderr


@pytest.mark.voter_happy
def test_wait_barrier_delayed_external_done(tmp_path: Path) -> None:
    stub_bin = _make_voter_stub_bin(tmp_path)
    plugin = tmp_path / "wait-delayed-plugin"
    _write_wait_barrier_stub_plugin(plugin, CLI)
    review = tmp_path / "wait-delayed"
    review.mkdir()
    ballot = _standard_ballot(tmp_path)
    start = time.time()
    result = _dispatch_via_cli(
        review,
        ballot,
        stub_bin=stub_bin,
        plugin_root=plugin,
        env={
            "LARCH_WAIT_BARRIER_MODE": "delayed",
            "LARCH_WAIT_BARRIER_DELAY": "1",
            "LARCH_WAIT_BARRIER_VOTER2": str(review / "codex-vote-output.txt"),
            "LARCH_WAIT_BARRIER_VOTER3": str(review / "cursor-vote-output.txt"),
            "LARCH_VOTER_WAIT_TIMEOUT": "2",
        },
    )
    elapsed = time.time() - start
    assert result.returncode == 0, result.stderr
    assert "VOTER_2_STATUS=launched" in result.stdout
    assert "VOTER_3_STATUS=launched" in result.stdout
    assert elapsed >= 1.0


@pytest.mark.voter_happy
def test_wait_barrier_nonzero_done_fails_externals(tmp_path: Path) -> None:
    stub_bin = _make_voter_stub_bin(tmp_path)
    plugin = tmp_path / "wait-nonzero-plugin"
    _write_wait_barrier_stub_plugin(plugin, CLI)
    review = tmp_path / "wait-nonzero-done"
    review.mkdir()
    ballot = _standard_ballot(tmp_path)
    result = _dispatch_via_cli(
        review,
        ballot,
        stub_bin=stub_bin,
        plugin_root=plugin,
        env={
            "LARCH_WAIT_BARRIER_MODE": "nonzero_done",
            "LARCH_WAIT_BARRIER_VOTER2": str(review / "codex-vote-output.txt"),
            "LARCH_WAIT_BARRIER_VOTER3": str(review / "cursor-vote-output.txt"),
            "LARCH_VOTER_WAIT_TIMEOUT": "2",
        },
    )
    assert result.returncode == 0, result.stderr
    assert "VOTER_1_STATUS=launched" in result.stdout
    assert "VOTER_2_STATUS=failed" in result.stdout
    assert "VOTER_3_STATUS=failed" in result.stdout
    assert "1/3 effective judges" in result.stdout


@pytest.mark.voter_happy
def test_wait_barrier_external_timeout_degrades_panel(tmp_path: Path) -> None:
    stub_bin = _make_voter_stub_bin(tmp_path)
    plugin = tmp_path / "wait-timeout-plugin"
    _write_wait_barrier_stub_plugin(plugin, CLI)
    review = tmp_path / "wait-timeout"
    review.mkdir()
    ballot = _standard_ballot(tmp_path)
    result = _dispatch_via_cli(
        review,
        ballot,
        stub_bin=stub_bin,
        plugin_root=plugin,
        env={
            "LARCH_WAIT_BARRIER_MODE": "timeout",
            "LARCH_WAIT_BARRIER_VOTER2": str(review / "codex-vote-output.txt"),
            "LARCH_WAIT_BARRIER_VOTER3": str(review / "cursor-vote-output.txt"),
            "LARCH_VOTER_WAIT_TIMEOUT": "1",
        },
    )
    assert result.returncode == 0, result.stderr
    assert "VOTER_1_STATUS=launched" in result.stdout
    assert "VOTER_2_STATUS=failed" in result.stdout
    assert "VOTER_3_STATUS=failed" in result.stdout
    assert "1/3 effective judges" in result.stdout


@pytest.mark.voter_happy
def test_voter1_delayed_done_subprocess_uses_stub_plugin_root(tmp_path: Path) -> None:
    stub_bin = _make_voter_stub_bin(tmp_path)
    plugin = tmp_path / "voter1-delayed-plugin"
    log_path = tmp_path / "stub-cli.log"
    _write_voter1_delayed_done_stub_plugin(plugin, CLI)
    review = tmp_path / "voter1-delayed-done"
    review.mkdir()
    ballot = _standard_ballot(tmp_path)
    stub_cli = str(plugin / "python" / "cli.py")
    start = time.time()
    result = _dispatch_via_cli(
        review,
        ballot,
        stub_bin=stub_bin,
        plugin_root=plugin,
        cursor_available="false",
        env={
            "LARCH_VOTER1_DONE_DELAY": "1",
            "LARCH_STUB_CLI_LOG": str(log_path),
        },
    )
    elapsed = time.time() - start
    assert result.returncode == 0, result.stderr
    assert "VOTER_1_STATUS=launched" in result.stdout
    assert "VOTER_1_PARSE_RATE_STATUS=OK" in result.stdout
    assert (review / "claude-vote-output.txt.done").is_file()
    assert elapsed >= 1.0
    log_lines = [line for line in log_path.read_text(encoding="utf-8").splitlines() if line.strip()]
    assert log_lines
    for line in log_lines:
        parts = line.split()
        assert stub_cli in parts


@pytest.mark.voter_happy
def test_parse_rate_retry_nonzero_rc_counts_as_not_substantive(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    review = tmp_path / "review"
    ballot = tmp_path / "ballot.md"
    ballot.write_text("### FINDING_1: one\n", encoding="utf-8")
    harness, _stub_root = _install_harness(monkeypatch, tmp_path, review)
    harness.parse_rate_rc = {"cursor-validity": 1}

    assert agent_voters.dispatch_voters(_opts(ballot, review, codex="false", cursor="true")) == 0

    out = capsys.readouterr().out
    assert "VOTER_1_PARSE_RATE_STATUS=NOT_SUBSTANTIVE" in out
    assert "DEGRADED_PANEL_WARNING=" in out


@pytest.mark.voter_edge_and_r3_claude
def test_symlink_diff_bounded_copy(tmp_path: Path) -> None:
    stub_bin = _make_voter_stub_bin(tmp_path)
    review = _harness_review_tmpdir(tmp_path, "sym-diff")
    ballot = _standard_ballot(tmp_path)
    diff = tmp_path / "diff.txt"
    diff.write_text("diff\n", encoding="utf-8")
    sym = tmp_path / "diff-symlink.patch"
    sym.symlink_to(diff)
    result = _dispatch_via_cli(review, ballot, stub_bin=stub_bin, diff_file=str(sym))
    assert result.returncode == 0, result.stderr
    assert "VOTER_1_STATUS=launched" in result.stdout
    assert (review / "diff-context.txt").is_file()


@pytest.mark.voter_edge_and_r3_claude
def test_big_diff_bounded_copy(tmp_path: Path) -> None:
    stub_bin = _make_voter_stub_bin(tmp_path)
    review = _harness_review_tmpdir(tmp_path, "big-diff")
    ballot = _standard_ballot(tmp_path)
    big_diff = tmp_path / "big-diff.txt"
    big_diff.write_bytes(b"x" * (2048 * 1024))
    plan = tmp_path / "plan.txt"
    plan.write_text("plan\n", encoding="utf-8")
    result = _dispatch_via_cli(review, ballot, stub_bin=stub_bin, diff_file=str(big_diff), plan_file=str(plan))
    assert result.returncode == 0, result.stderr
    assert (review / "diff-context.txt").stat().st_size == 200000


@pytest.mark.voter_edge_and_r3_claude
def test_bounded_copy_does_not_read_entire_file(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    review = tmp_path / "review"
    review.mkdir()
    src = tmp_path / "big-diff.txt"
    src.write_bytes(b"x" * (2048 * 1024))

    def _no_whole_file_read(self: Path) -> bytes:
        raise AssertionError(f"_make_bounded_context_copy must not read all of {self} into memory")

    monkeypatch.setattr(agent_voters.Path, "read_bytes", _no_whole_file_read)  # type: ignore[arg-type]

    dest = agent_voters._make_bounded_context_copy(review_tmpdir=review, label="diff", src=str(src), max_bytes=200000)  # pyright: ignore[reportPrivateUsage]
    assert dest, "expected a bounded context copy path"
    dest_path = Path(dest)
    assert dest_path.stat().st_size == 200000
    with dest_path.open("rb") as handle:
        assert handle.read() == b"x" * 200000


@pytest.mark.voter_edge_and_r3_claude
def test_oos_only_ballot_triggers_parse_retry(tmp_path: Path) -> None:
    stub_bin = _make_voter_stub_bin(tmp_path)
    review = _harness_review_tmpdir(tmp_path, "oos-retry")
    ballot = tmp_path / "oos-only-ballot.md"
    ballot.write_text("### OOS_1: OOS-only observation\n", encoding="utf-8")
    count = tmp_path / "oos-retry-count.txt"
    result = _dispatch_via_cli(
        review,
        ballot,
        stub_bin=stub_bin,
        cursor_available="false",
        env={"CLAUDE_STUB_MODE": "parse_retry_success", "CLAUDE_STUB_COUNT_FILE": str(count)},
    )
    assert result.returncode == 0, result.stderr
    assert "VOTER_1_PARSE_RATE_STATUS=NOT_SUBSTANTIVE" in result.stdout
    assert not (review / "claude-vote-prompt-retry.txt").exists()


@pytest.mark.voter_edge_and_r3_claude
def test_prod_shape_claude_parse_retry_appends_issues_log(tmp_path: Path) -> None:
    stub_bin = _make_voter_stub_bin(tmp_path)
    prod_tmp = tmp_path / "review-prod-shape-claude"
    review = prod_tmp / "review"
    review.mkdir(parents=True)
    ballot = _standard_ballot(tmp_path)
    issues = prod_tmp / "prod-issues.md"
    count = tmp_path / "prod-shape-count.txt"
    result = _dispatch_via_cli(
        review,
        ballot,
        stub_bin=stub_bin,
        cursor_available="false",
        env={
            "CLAUDE_STUB_MODE": "parse_retry_fail",
            "CLAUDE_STUB_COUNT_FILE": str(count),
            "LARCH_EXECUTION_ISSUES_LOG": str(issues),
        },
    )
    assert result.returncode == 0, result.stderr
    assert "VOTER_1_PARSE_RATE_STATUS=NOT_SUBSTANTIVE" in result.stdout
    assert (review / "claude-vote-output-parse-rate-diag.txt").is_file()
    issues_text = issues.read_text(encoding="utf-8")
    assert "agent dispatch-voters claude" in issues_text
    assert "agent launch-claude-review (voter parse-rate check)" in issues_text


@pytest.mark.voter_retry_claude
def test_retry_success_claude_preserves_first_pass_sidecar(tmp_path: Path) -> None:
    stub_bin = _make_voter_stub_bin(tmp_path)
    review = _harness_review_tmpdir(tmp_path, "retry-success")
    ballot = _standard_ballot(tmp_path)
    count = tmp_path / "retry-success-count.txt"
    result = _dispatch_via_cli(
        review,
        ballot,
        stub_bin=stub_bin,
        cursor_available="false",
        env={"CLAUDE_STUB_MODE": "parse_retry_success", "CLAUDE_STUB_COUNT_FILE": str(count)},
    )
    assert result.returncode == 0, result.stderr
    assert "VOTER_1_PARSE_RATE_STATUS=NOT_SUBSTANTIVE" in result.stdout
    final = review / "claude-vote-output.txt"
    assert "narrative instead of votes" in final.read_text(encoding="utf-8")
    assert not (review / "claude-vote-output-first-pass.txt").exists()
    assert not (review / "claude-vote-output-parse-retry.txt").exists()
    assert count.read_text(encoding="utf-8").strip() == "1"


@pytest.mark.voter_retry_claude
def test_retry_fail_claude_preserves_narrative_and_diag(tmp_path: Path) -> None:
    stub_bin = _make_voter_stub_bin(tmp_path)
    review = _harness_review_tmpdir(tmp_path, "retry-fail")
    ballot = _standard_ballot(tmp_path)
    count = tmp_path / "retry-fail-count.txt"
    result = _dispatch_via_cli(
        review,
        ballot,
        stub_bin=stub_bin,
        cursor_available="false",
        env={"CLAUDE_STUB_MODE": "parse_retry_fail", "CLAUDE_STUB_COUNT_FILE": str(count)},
    )
    assert result.returncode == 0, result.stderr
    assert "VOTER_1_PARSE_RATE_STATUS=NOT_SUBSTANTIVE" in result.stdout
    assert "narrative instead of votes" in (review / "claude-vote-output.txt").read_text(encoding="utf-8")
    diag = review / "claude-vote-output-parse-rate-diag.txt"
    assert diag.is_file()
    assert f"voter_file={review / 'claude-vote-output.txt'}" in diag.read_text(encoding="utf-8")
    assert not (review / "claude-vote-output-first-pass.txt").exists()


@pytest.mark.voter_retry_codex_success
def test_retry_success_codex_preserves_first_pass_sidecar(tmp_path: Path) -> None:
    stub_bin = _make_voter_stub_bin(tmp_path)
    review = _harness_review_tmpdir(tmp_path, "retry-success-codex")
    ballot = _standard_ballot(tmp_path)
    count = tmp_path / "retry-success-codex-count.txt"
    result = _dispatch_via_cli(
        review,
        ballot,
        stub_bin=stub_bin,
        env={"CODEX_STUB_MODE": "parse_retry_success", "CODEX_STUB_COUNT_FILE": str(count)},
    )
    assert result.returncode == 0, result.stderr
    # Parse-rate retry was removed (main #4547): a narrative voter degrades the
    # panel and leaves no retry/first-pass sidecars on any archetype slot. Which
    # slot races to the narrative output is non-deterministic, so assert panel
    # degradation rather than a specific voter index.
    assert "DEGRADED_PANEL_WARNING=" in result.stdout
    for label in ("cursor-validity", "codex-plan-fidelity", "codex-pragmatism"):
        assert not (review / f"{label}-vote-output-first-pass.txt").exists()
        assert not (review / f"{label}-vote-output-parse-retry.txt").exists()


@pytest.mark.voter_retry_cursor
def test_retry_success_cursor_preserves_first_pass_sidecar(tmp_path: Path) -> None:
    stub_bin = _make_voter_stub_bin(tmp_path)
    review = _harness_review_tmpdir(tmp_path, "retry-success-cursor")
    ballot = _standard_ballot(tmp_path)
    count = tmp_path / "retry-success-cursor-count.txt"
    result = _dispatch_via_cli(
        review,
        ballot,
        stub_bin=stub_bin,
        codex_available="false",
        env={"CURSOR_STUB_MODE": "parse_retry_success", "CURSOR_STUB_COUNT_FILE": str(count)},
    )
    assert result.returncode == 0, result.stderr
    # Parse-rate retry was removed (main #4547): a narrative voter degrades the
    # panel and leaves no retry/first-pass sidecars on any archetype slot.
    assert "DEGRADED_PANEL_WARNING=" in result.stdout
    for label in ("cursor-validity", "cursor-plan-fidelity", "cursor-pragmatism"):
        assert not (review / f"{label}-vote-output-first-pass.txt").exists()
        assert not (review / f"{label}-vote-output-parse-retry.txt").exists()


@pytest.mark.voter_retry_codex_fail_and_fallback
def test_retry_fail_codex_degrades_panel(tmp_path: Path) -> None:
    stub_bin = _make_voter_stub_bin(tmp_path)
    review = _harness_review_tmpdir(tmp_path, "retry-fail-codex")
    ballot = _standard_ballot(tmp_path)
    count = tmp_path / "retry-fail-codex-count.txt"
    result = _dispatch_via_cli(
        review,
        ballot,
        stub_bin=stub_bin,
        env={"CODEX_STUB_MODE": "parse_retry_fail", "CODEX_STUB_COUNT_FILE": str(count)},
    )
    assert result.returncode == 0, result.stderr
    assert "VOTER_2_PARSE_RATE_STATUS=NOT_SUBSTANTIVE" in result.stdout
    assert "VOTER_3_PARSE_RATE_STATUS=NOT_SUBSTANTIVE" in result.stdout
    assert "DEGRADED_PANEL_WARNING=" in result.stdout
    assert (review / "codex-plan-fidelity-vote-output-parse-rate-diag.txt").is_file()
    assert not (review / "codex-plan-fidelity-vote-output-first-pass.txt").exists()


@pytest.mark.voter_retry_codex_fail_and_fallback
def test_retry_fail_fallback_both_down_degrades_to_zero_effective(tmp_path: Path) -> None:
    stub_bin = _make_voter_stub_bin(tmp_path)
    review = _harness_review_tmpdir(tmp_path, "retry-fail-fallback")
    ballot = _standard_ballot(tmp_path)
    count = tmp_path / "retry-fail-fallback-count.txt"
    result = _dispatch_via_cli(
        review,
        ballot,
        stub_bin=stub_bin,
        codex_available="false",
        cursor_available="false",
        env={"CLAUDE_STUB_MODE": "parse_retry_fail", "CLAUDE_STUB_COUNT_FILE": str(count)},
    )
    assert result.returncode == 0, result.stderr
    assert "VOTER_2_STATUS=skipped" in result.stdout
    assert "VOTER_3_STATUS=skipped" in result.stdout
    assert "VOTER_1_PARSE_RATE_STATUS=NOT_SUBSTANTIVE" in result.stdout
    assert "0/1 effective judges" in result.stdout


@pytest.mark.voter_regressions_r1_r2
def test_env_isolation_suppresses_parent_issues_log(tmp_path: Path) -> None:
    stub_bin = _make_voter_stub_bin(tmp_path)
    review = _harness_review_tmpdir(tmp_path, "env-isolation-review")
    ballot = _standard_ballot(tmp_path)
    parent_issues = tmp_path / "env-isolation-parent.md"
    count = tmp_path / "env-isolation-count.txt"
    result = _dispatch_via_cli(
        review,
        ballot,
        stub_bin=stub_bin,
        cursor_available="false",
        env={
            "CLAUDE_STUB_MODE": "parse_retry_fail",
            "CLAUDE_STUB_COUNT_FILE": str(count),
            "LARCH_EXECUTION_ISSUES_LOG": str(parent_issues),
        },
    )
    assert result.returncode == 0, result.stderr
    assert "VOTER_1_PARSE_RATE_STATUS=NOT_SUBSTANTIVE" in result.stdout
    assert not parent_issues.exists() or parent_issues.stat().st_size == 0


@pytest.mark.voter_regressions_r1_r2
def test_harness_path_guard_writes_local_diag_only(tmp_path: Path) -> None:
    stub_bin = _make_voter_stub_bin(tmp_path)
    review = _harness_review_tmpdir(tmp_path, "path-guard-review")
    ballot = _standard_ballot(tmp_path)
    parent_issues = tmp_path / "path-guard-issues.md"
    count = tmp_path / "path-guard-count.txt"
    result = _dispatch_via_cli(
        review,
        ballot,
        stub_bin=stub_bin,
        cursor_available="false",
        env={
            "CLAUDE_STUB_MODE": "parse_retry_fail",
            "CLAUDE_STUB_COUNT_FILE": str(count),
            "LARCH_EXECUTION_ISSUES_LOG": str(parent_issues),
        },
    )
    assert result.returncode == 0, result.stderr
    assert (review / "claude-vote-output-parse-rate-diag.txt").is_file()
    assert not parent_issues.exists() or parent_issues.stat().st_size == 0


@pytest.mark.voter_regressions_r3_codex
def test_prod_shape_codex_parse_retry_appends_issues_log(tmp_path: Path) -> None:
    stub_bin = _make_voter_stub_bin(tmp_path)
    prod_tmp = tmp_path / "review-prod-shape-codex"
    review = prod_tmp / "review-codex"
    review.mkdir(parents=True)
    ballot = _standard_ballot(tmp_path)
    issues = prod_tmp / "prod-codex-issues.md"
    count = tmp_path / "prod-shape-codex-count.txt"
    result = _dispatch_via_cli(
        review,
        ballot,
        stub_bin=stub_bin,
        env={
            "CURSOR_STUB_MODE": "parse_retry_fail",
            "CURSOR_STUB_COUNT_FILE": str(count),
            "LARCH_EXECUTION_ISSUES_LOG": str(issues),
        },
    )
    assert result.returncode == 0, result.stderr
    assert "VOTER_1_PARSE_RATE_STATUS=NOT_SUBSTANTIVE" in result.stdout
    assert (review / "cursor-validity-vote-output-parse-rate-diag.txt").is_file()
    issues_text = issues.read_text(encoding="utf-8")
    assert "agent dispatch-voters cursor-validity" in issues_text
    assert "agent launch-review --tool cursor (voter parse-rate check; label cursor-validity)" in issues_text


def test_append_voter1_failure_uses_bounded_prefix_reads(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    review = tmp_path / "review"
    review.mkdir()
    output = review / "voter1.txt"
    _ = output.write_text("A" * 1000, encoding="utf-8")
    _ = Path(f"{output}.diag").write_text("B" * 1000, encoding="utf-8")
    _ = Path(f"{output}.launcher-stderr").write_text("C" * 1000, encoding="utf-8")

    def forbidden_read_bytes(_path: Path) -> bytes:
        raise AssertionError("read_bytes should not be used for diagnostic snippets")

    def fake_run(_argv: Sequence[str], **_kwargs: Any) -> proc.CommandResult:
        return _result(["run-log", "append-failure"], 0)

    monkeypatch.setattr(Path, "read_bytes", forbidden_read_bytes)
    monkeypatch.setattr(agent_voters.proc, "run", fake_run)
    opts = agent_voters.Options(
        ballot_file=str(tmp_path / "ballot.tsv"),
        review_tmpdir=str(review),
        codex_available="false",
        cursor_available="false",
    )
    agent_voters._append_voter1_failure(opts=opts, review_tmpdir=review, voter_1_path=str(output), voter1_rc=7)  # pylint: disable=protected-access
    diag = (review / "voter1-diag.txt").read_text(encoding="utf-8")
    assert "--- first 200 bytes of voter output ---\n" + ("A" * 200) in diag
    assert "--- first 200 bytes of .diag ---\n" + ("B" * 200) in diag
    assert "--- launcher stderr (first 500 bytes) ---\n" + ("C" * 500) in diag
    assert "A" * 201 not in diag
    assert "B" * 201 not in diag
    assert "C" * 501 not in diag


def test_dispatch_voters_accepts_neutralized_reviewer_ballot(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    ballot = tmp_path / "ballot.md"
    _ = ballot.write_text(
        "### FINDING_1: Bug\n- **Reviewer**: anonymous\n- **Concern**: issue\n",
        encoding="utf-8",
    )
    review = tmp_path / "review"
    review.mkdir()
    _install_harness(monkeypatch, tmp_path, review)
    assert agent_voters.dispatch_voters(_opts(ballot, review)) == 0


def _kv(output: str, key: str) -> str:
    prefix = f"{key}="
    for line in output.splitlines():
        if line.startswith(prefix):
            return line[len(prefix) :]
    return ""


def test_parse_args_site_default_and_explicit() -> None:
    base = ["--ballot-file", "/x", "--review-tmpdir", "/y", "--codex-available", "true", "--cursor-available", "true"]
    default_opts = agent_voters._parse_args(argv=base)
    assert isinstance(default_opts, agent_voters.Options)
    assert default_opts.site == "review Step 2"
    explicit_opts = agent_voters._parse_args(argv=[*base, "--site", "implement Step 5"])
    assert isinstance(explicit_opts, agent_voters.Options)
    assert explicit_opts.site == "implement Step 5"


@pytest.mark.voter_happy
def test_dispatch_voters_forwards_site_to_waterfall(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    review = tmp_path / "review"
    ballot = tmp_path / "ballot.md"
    ballot.write_text("### FINDING_1: one\n", encoding="utf-8")
    harness, _ = _install_harness(monkeypatch, tmp_path, review)
    opts = agent_voters.Options(str(ballot), str(review), "true", "true", site="implement Step 5")
    assert agent_voters.dispatch_voters(opts) == 0
    waterfall = next(call for call in harness.run_calls if _verb(call) == ("agent", "dispatch-waterfall"))
    assert _value_after(waterfall, "--site") == "implement Step 5"
