# pyright: reportPrivateUsage=false, reportUnusedCallResult=false
# pyright: reportMissingParameterType=false, reportUnknownMemberType=false, reportUnknownArgumentType=false, reportArgumentType=false
from __future__ import annotations

import json
import os
import re
import subprocess
import sys
import textwrap
from pathlib import Path
from collections.abc import Sequence
from typing import Any

import pytest

from larch.agents import agent_voters
from larch.core import proc
from larch.report import tokens

REPO_ROOT = Path(__file__).resolve().parents[3]
CLI = REPO_ROOT / "python" / "cli.py"


class FakeHarness:
    def __init__(self, review_tmpdir: Path) -> None:
        self.review_tmpdir = review_tmpdir
        self.run_calls: list[list[str]] = []
        self.run_envs: list[dict[str, str] | None] = []
        self.append_calls: list[list[str]] = []
        self.render_missing_pointer = False
        self.render_rc = 0
        self.waterfall_rc = 0
        self.waterfall_mode = "both"
        self.parse_status: dict[str, str] = {}
        self.parse_rate_rc: dict[str, int] = {}

    def run(self, argv: Sequence[str], **_kwargs: Any) -> proc.CommandResult:
        args = [str(item) for item in argv]
        self.run_calls.append(args)
        self.run_envs.append(_kwargs.get("env"))
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
            return self._waterfall(args)
        if verb == ("voting", "parse-rate-retry"):
            tool = _value_after(args, "--voter-tool") or ""
            rc = self.parse_rate_rc.get(tool, 0)
            stdout = (self.parse_status.get(tool, "OK") + "\n") if rc == 0 else ""
            return _result(args, rc, stdout=stdout)
        if verb == ("voter-calibration", "snapshot"):
            out = _value_after(args, "--out")
            if out:
                Path(out).write_text("tool\tyes_votes\n", encoding="utf-8")
            return _result(args, 0)
        if verb == ("run-log", "append-failure"):
            self.append_calls.append(args)
            return _result(args, 0, stdout="APPENDED=true\nLOG=/tmp/log\n")
        return _result(args, 2, stderr=f"unexpected args: {args}\n")

    def _waterfall(self, args: list[str]) -> proc.CommandResult:
        slots_file = Path(_value_after(args, "--slots-file"))
        rows = [__import__("json").loads(line) for line in slots_file.read_text(encoding="utf-8").splitlines() if line]
        codex_present = _value_after(args, "--codex-present") == "true"
        cursor_present = _value_after(args, "--cursor-present") == "true"
        artifact_dir_raw = _value_after(args, "--panel-artifact-dir")
        artifact_path = Path(artifact_dir_raw) / tokens.PANEL_PROMPT_SIZE_BASENAME if artifact_dir_raw else None
        site = _value_after(args, "--site") or "implement Step 5"
        round_num: int | None = None
        if artifact_dir_raw and re.fullmatch(r"round-[0-9]+", Path(artifact_dir_raw).name):
            round_num = int(Path(artifact_dir_raw).name.removeprefix("round-"))

        def _final_tool(primary: str) -> str:
            present = {"codex": codex_present, "cursor": cursor_present}
            if present.get(primary, False):
                return primary
            other = "cursor" if primary == "codex" else "codex"
            if present.get(other, False):
                return other
            return "claude"

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
            tools.append(_final_tool(str(row.get("tool", "cursor"))))
            if artifact_path is not None:
                tokens.append_panel_prompt_size(
                    artifact_path=artifact_path,
                    output=out,
                    tool=tools[-1],
                    prompt="stub voter prompt",
                    slot=str(row.get("slot", "")),
                    slot_kind="voter",
                    site=site,
                    round_num=round_num,
                )
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
    return harness, stub_root


def _assert_stub_plugin_root_on_calls(harness: FakeHarness, stub_root: Path) -> None:
    cli_path = str(stub_root / "python" / "cli.py")
    for call in harness.run_calls:
        assert call[1] == cli_path
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

    render_calls = [call for call in harness.run_calls if _verb(call) == ("render", "voter")]
    # All three voters (voter-1 validity included) build prompts for every launchable
    # tier now that voter 1 flows through the shared waterfall manifest (issue #5837).
    assert sorted((_value_after(call, "--archetype"), _value_after(call, "--voter-tool")) for call in render_calls) == [
        ("plan-fidelity-completeness", "claude"),
        ("plan-fidelity-completeness", "codex"),
        ("plan-fidelity-completeness", "cursor"),
        ("pragmatism-cost", "claude"),
        ("pragmatism-cost", "codex"),
        ("pragmatism-cost", "cursor"),
        ("validity-correctness", "claude"),
        ("validity-correctness", "codex"),
        ("validity-correctness", "cursor"),
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
    # Voters grant the terminal Claude tier ballot read access (issue #5837).
    assert _value_after(waterfall, "--claude-read-tools-add-dir") == str(review)
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
    assert not any(_verb(call) == ("agent", "dispatch-waterfall") for call in harness.run_calls)


@pytest.mark.voter_happy
def test_both_externals_down_shrink_not_backfill(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> None:
    review = tmp_path / "review"
    ballot = tmp_path / "ballot.md"
    ballot.write_text("### FINDING_1: one\n", encoding="utf-8")
    _harness, _stub_root = _install_harness(monkeypatch, tmp_path, review)

    assert agent_voters.dispatch_voters(_opts(ballot, review, codex="false", cursor="false")) == 0

    out = capsys.readouterr().out
    # Voter 1 waterfalls through the shared manifest to the Claude floor and is the
    # single non-empty judge; voters 2/3 shrink away (no redundant Claude voters).
    assert "VOTER_1_TOOL=claude" in out
    assert "VOTER_1_STATUS=launched" in out
    assert "VOTER_1_PARSE_RATE_STATUS=OK" in out
    assert "VOTER_2_PATH=\n" in out
    assert "VOTER_2_TOOL=codex-plan-fidelity" in out
    assert "VOTER_2_STATUS=skipped" in out
    assert "VOTER_3_PATH=\n" in out
    assert "VOTER_3_TOOL=codex-pragmatism" in out
    assert "VOTER_3_STATUS=skipped" in out
    assert "DEGRADED_PANEL_WARNING=" not in out
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
def test_voter1_waterfalls_to_cursor_when_codex_unavailable(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> None:
    # Codex down but Cursor up -> voter 1 routes through the shared waterfall
    # manifest to its Cursor middle tier instead of dropping to Claude.
    review = tmp_path / "review"
    ballot = tmp_path / "ballot.md"
    ballot.write_text("### FINDING_1: one\n", encoding="utf-8")
    _harness, _stub_root = _install_harness(monkeypatch, tmp_path, review)

    assert agent_voters.dispatch_voters(_opts(ballot, review, codex="false", cursor="true")) == 0

    out = capsys.readouterr().out
    assert "VOTER_1_TOOL=cursor-validity" in out
    assert "VOTER_1_STATUS=launched" in out
    assert Path(_kv(out, "VOTER_1_PATH")).is_file()
    manifest = (review / "code-voter-slots.ndjson").read_text(encoding="utf-8")
    assert '"slot":"voter-1"' in manifest


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
        "    import json\n"
        "    sf=args[args.index('--slots-file')+1]\n"
        "    outs=[]\n"
        "    for row in [json.loads(line) for line in Path(sf).read_text().splitlines() if line]:\n"
        "        o=row['output']; Path(o).write_text('FINDING_1: YES CORRECTNESS=true SEVERITY=minor QUALITY=good UNCERTAIN=false\\n'); Path(o+'.done').write_text('0\\n'); outs.append(o)\n"
        "    print('ALL_OUTPUT_FILES='+' '.join(outs)); print('ALL_OUTPUT_TOOLS='+' '.join(['claude']*len(outs))); print('DISPATCH_OK=true')\n"
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
            str(Path(__file__).resolve().parents[2] / "cli.py"),
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
          fail)
            printf 'codex runtime failure: quota exhausted\\n' >&2
            exit 1 ;;
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
          fail)
            printf 'cursor runtime failure: unpaid invoice\\n' >&2
            exit 1 ;;
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
    # Voter 1 now shares the manifest with voters 2/3 (issue #5837).
    assert '"slot":"voter-1"' in text
    assert '"slot":"voter-2"' in text
    assert '"slot":"voter-3"' in text
    assert text.count('"tool":"codex"') == 3
    assert text.count('"tool":"cursor"') == 0


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


@pytest.mark.voter_happy
def test_voter1_runtime_codex_failure_redispatches_to_cursor(tmp_path: Path) -> None:
    # issue #5837 Mode A: Codex passes the static availability probe but fails at
    # runtime. Routing voter 1 through the shared waterfall re-dispatches it to
    # Cursor instead of dropping the slot.
    stub_bin = _make_voter_stub_bin(tmp_path)
    review = _harness_review_tmpdir(tmp_path, "voter1-runtime-codex-fail")
    ballot = _standard_ballot(tmp_path)
    result = _dispatch_via_cli(
        review,
        ballot,
        stub_bin=stub_bin,
        codex_available="true",
        cursor_available="true",
        env={"CODEX_STUB_MODE": "fail"},
    )
    assert result.returncode == 0, result.stderr
    assert "VOTER_1_TOOL=cursor-validity" in result.stdout
    assert "VOTER_1_STATUS=launched" in result.stdout
    manifest = (review / "code-voter-slots.ndjson").read_text(encoding="utf-8")
    assert '"slot":"voter-1"' in manifest


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
        codex_available="false",
        cursor_available="false",
        env={
            "CLAUDE_STUB_MODE": "parse_retry_fail",
            "CLAUDE_STUB_COUNT_FILE": str(count),
            "LARCH_EXECUTION_ISSUES_LOG": str(issues),
        },
    )
    assert result.returncode == 0, result.stderr
    assert "VOTER_1_PARSE_RATE_STATUS=NOT_SUBSTANTIVE" in result.stdout
    voter1 = Path(_kv(result.stdout, "VOTER_1_PATH"))
    assert voter1.with_name(voter1.stem + "-parse-rate-diag.txt").is_file()
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
        codex_available="false",
        cursor_available="false",
        env={"CLAUDE_STUB_MODE": "parse_retry_success", "CLAUDE_STUB_COUNT_FILE": str(count)},
    )
    assert result.returncode == 0, result.stderr
    assert "VOTER_1_PARSE_RATE_STATUS=NOT_SUBSTANTIVE" in result.stdout
    voter1 = Path(_kv(result.stdout, "VOTER_1_PATH"))
    assert "narrative instead of votes" in voter1.read_text(encoding="utf-8")
    assert not voter1.with_name(voter1.stem + "-first-pass.txt").exists()
    assert not voter1.with_name(voter1.stem + "-parse-retry.txt").exists()
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
        codex_available="false",
        cursor_available="false",
        env={"CLAUDE_STUB_MODE": "parse_retry_fail", "CLAUDE_STUB_COUNT_FILE": str(count)},
    )
    assert result.returncode == 0, result.stderr
    assert "VOTER_1_PARSE_RATE_STATUS=NOT_SUBSTANTIVE" in result.stdout
    voter1 = Path(_kv(result.stdout, "VOTER_1_PATH"))
    assert "narrative instead of votes" in voter1.read_text(encoding="utf-8")
    diag = voter1.with_name(voter1.stem + "-parse-rate-diag.txt")
    assert diag.is_file()
    assert f"voter_file={voter1}" in diag.read_text(encoding="utf-8")
    assert not voter1.with_name(voter1.stem + "-first-pass.txt").exists()


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
    for label in ("codex-validity", "codex-plan-fidelity", "codex-pragmatism"):
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
        codex_available="false",
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
        codex_available="false",
        cursor_available="false",
        env={
            "CLAUDE_STUB_MODE": "parse_retry_fail",
            "CLAUDE_STUB_COUNT_FILE": str(count),
            "LARCH_EXECUTION_ISSUES_LOG": str(parent_issues),
        },
    )
    assert result.returncode == 0, result.stderr
    voter1 = Path(_kv(result.stdout, "VOTER_1_PATH"))
    assert voter1.with_name(voter1.stem + "-parse-rate-diag.txt").is_file()
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
            "CODEX_STUB_MODE": "parse_retry_fail",
            "CODEX_STUB_COUNT_FILE": str(count),
            "LARCH_EXECUTION_ISSUES_LOG": str(issues),
        },
    )
    assert result.returncode == 0, result.stderr
    assert "VOTER_1_PARSE_RATE_STATUS=NOT_SUBSTANTIVE" in result.stdout
    assert (review / "codex-validity-vote-output-parse-rate-diag.txt").is_file()
    issues_text = issues.read_text(encoding="utf-8")
    assert "agent dispatch-voters codex-validity" in issues_text
    assert "agent launch-review --tool codex (voter parse-rate check; label codex-validity)" in issues_text


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


def test_dispatch_voters_skips_snapshot_when_feedback_disabled(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    review = tmp_path / "review"
    review.mkdir()
    monkeypatch.setenv("LARCH_VOTER_CALIBRATION_FEEDBACK", "0")
    assert agent_voters._fresh_calibration_stats_file(review_tmpdir=review) is None  # pyright: ignore[reportPrivateUsage]


def test_fresh_calibration_stats_file_passes_consumer_log_root(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    consumer = tmp_path / "consumer"
    (consumer / "larch-logs").mkdir(parents=True)
    implement = tmp_path / "implement"
    implement.mkdir()
    review = implement / "round-1"
    review.mkdir()
    (implement / "session-env.sh").write_text(f"REPO_CWD={consumer}\n", encoding="utf-8")
    captured: list[str] = []

    def _fake_run(argv: Sequence[str], **_kwargs: object) -> proc.CommandResult:
        args = [str(item) for item in argv]
        if _verb(args) == ("voter-calibration", "snapshot"):
            out = _value_after(args, "--out")
            captured.append(_value_after(args, "--log-root"))
            if out:
                Path(out).write_text("tool\tyes_votes\n", encoding="utf-8")
            return _result(args, 0)
        return _result(args, 2)

    monkeypatch.setenv("LARCH_VOTER_CALIBRATION_FEEDBACK", "1")
    monkeypatch.delenv("LARCH_CONSUMER_REPO", raising=False)
    monkeypatch.delenv("CLAUDE_PROJECT_DIR", raising=False)
    monkeypatch.setattr(agent_voters.proc, "run", _fake_run)
    result = agent_voters._fresh_calibration_stats_file(review_tmpdir=review)  # pyright: ignore[reportPrivateUsage]
    assert result == str(review / "voter-calibration-stats.tsv")
    assert captured == [str((consumer / "larch-logs").resolve())]


def test_dispatch_voters_invokes_snapshot_once_with_render_flags(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    consumer = tmp_path / "consumer"
    (consumer / "larch-logs").mkdir(parents=True)
    implement = tmp_path / "implement"
    implement.mkdir()
    review = implement / "round-1"
    review.mkdir()
    (implement / "session-env.sh").write_text(f"REPO_CWD={consumer}\n", encoding="utf-8")
    ballot = tmp_path / "ballot.md"
    ballot.write_text("### FINDING_1: one\n", encoding="utf-8")
    harness, _ = _install_harness(monkeypatch, tmp_path, review)
    snapshot_calls: list[Path] = []

    def _fake_fresh(*, review_tmpdir: Path) -> str:
        snapshot_calls.append(review_tmpdir)
        stats = review_tmpdir / "voter-calibration-stats.tsv"
        stats.write_text("tool\tyes_votes\n", encoding="utf-8")
        return str(stats)

    monkeypatch.setattr(agent_voters, "_fresh_calibration_stats_file", _fake_fresh)
    assert agent_voters.dispatch_voters(_opts(ballot, review)) == 0
    assert len(snapshot_calls) == 1
    render_calls = [call for call in harness.run_calls if _verb(call) == ("render", "voter")]
    assert render_calls
    assert all("--calibration-stats-file" in call for call in render_calls)
    assert all(_value_after(call, "--calibration-stats-file").endswith("voter-calibration-stats.tsv") for call in render_calls)
    waterfall = next(call for call in harness.run_calls if _verb(call) == ("agent", "dispatch-waterfall"))
    assert "--no-fallback" not in waterfall
    manifest_lines = Path(_value_after(waterfall, "--slots-file")).read_text(encoding="utf-8").splitlines()
    assert manifest_lines
    manifest = json.loads(manifest_lines[0])
    assert "prompt_files" in manifest


def test_dispatch_voters_codex_absent_uses_cursor_calibration(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    review = tmp_path / "review"
    ballot = tmp_path / "ballot.md"
    ballot.write_text("### FINDING_1: one\n", encoding="utf-8")
    harness, _ = _install_harness(monkeypatch, tmp_path, review)
    monkeypatch.setenv("LARCH_VOTER_CALIBRATION_FEEDBACK", "1")
    assert agent_voters.dispatch_voters(_opts(ballot, review, codex="false", cursor="true")) == 0
    render_calls = [call for call in harness.run_calls if _verb(call) == ("render", "voter")]
    voter_tools = {_value_after(call, "--voter-tool") for call in render_calls if "--voter-tool" in call}
    assert "cursor" in voter_tools
    assert "codex" not in voter_tools


def test_dispatch_voters_omits_calibration_after_snapshot_failure(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    implement = tmp_path / "implement"
    implement.mkdir()
    review = implement / "round-1"
    review.mkdir()
    ballot = tmp_path / "ballot.md"
    ballot.write_text("### FINDING_1: one\n", encoding="utf-8")
    harness, _ = _install_harness(monkeypatch, tmp_path, review)
    monkeypatch.setattr(agent_voters, "_fresh_calibration_stats_file", lambda **_k: None)  # type: ignore[arg-type]
    assert agent_voters.dispatch_voters(_opts(ballot, review)) == 0
    render_calls = [call for call in harness.run_calls if _verb(call) == ("render", "voter")]
    assert render_calls
    assert not any("--calibration-stats-file" in call for call in render_calls)


def test_dispatch_voters_keepalive_consumer_log_root(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    consumer = tmp_path / "consumer"
    (consumer / "larch-logs").mkdir(parents=True)
    plugin = tmp_path / "plugin"
    (plugin / "larch-logs").mkdir(parents=True)
    implement = tmp_path / "implement"
    implement.mkdir()
    review = implement / "round-1"
    review.mkdir()
    (implement / "session-env.sh").write_text("# no anchors\n", encoding="utf-8")
    (review / ".larch-keepalive").write_text(f"CLONE_PATH={consumer}\n", encoding="utf-8")
    captured: list[str] = []

    def _fake_run(argv: Sequence[str], **_kwargs: object) -> proc.CommandResult:
        args = [str(item) for item in argv]
        if _verb(args) == ("voter-calibration", "snapshot"):
            captured.append(_value_after(args, "--log-root"))
            out = _value_after(args, "--out")
            if out:
                Path(out).write_text("tool\tyes_votes\n", encoding="utf-8")
            return _result(args, 0)
        return _result(args, 2)

    monkeypatch.chdir(plugin)
    monkeypatch.delenv("LARCH_CONSUMER_REPO", raising=False)
    monkeypatch.delenv("CLAUDE_PROJECT_DIR", raising=False)
    monkeypatch.setenv("LARCH_VOTER_CALIBRATION_FEEDBACK", "1")
    monkeypatch.setattr(agent_voters.proc, "run", _fake_run)
    result = agent_voters._fresh_calibration_stats_file(review_tmpdir=review)  # pyright: ignore[reportPrivateUsage]
    assert result == str(review / "voter-calibration-stats.tsv")
    assert captured == [str((consumer / "larch-logs").resolve())]


def test_voter_dispatch_forwards_panel_artifact_dir(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    impl = tmp_path / "impl"
    review = impl / "round-4"
    review.mkdir(parents=True)
    ballot = tmp_path / "ballot.md"
    ballot.write_text("### FINDING_1: one\n", encoding="utf-8")
    harness, _stub_root = _install_harness(monkeypatch, tmp_path, review)

    assert agent_voters.dispatch_voters(_opts(ballot, review, round_num=4)) == 0

    waterfall = next(call for call in harness.run_calls if _verb(call) == ("agent", "dispatch-waterfall"))
    waterfall_env = harness.run_envs[harness.run_calls.index(waterfall)]
    assert _value_after(waterfall, "--panel-artifact-dir") == str(review)
    assert waterfall_env is not None
    assert waterfall_env["LARCH_PANEL_ARTIFACT_DIR"] == str(review)
    assert waterfall_env["LARCH_PANEL_SITE"] == "review Step 2"
    assert waterfall_env["LARCH_PANEL_ROUND_NUM"] == "4"


def test_voter_dispatch_materializes_panel_prompt_sizes(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    impl = tmp_path / "impl"
    review = impl / "round-4"
    review.mkdir(parents=True)
    ballot = tmp_path / "ballot.md"
    ballot.write_text("### FINDING_1: one\n", encoding="utf-8")
    _harness, _stub_root = _install_harness(monkeypatch, tmp_path, review)

    assert agent_voters.dispatch_voters(_opts(ballot, review, round_num=4)) == 0

    tsv = review / "panel-prompt-sizes.tsv"
    assert tsv.is_file()
    lines = [line for line in tsv.read_text(encoding="utf-8").splitlines() if line and not line.startswith("site\t")]
    assert len(lines) >= 1
    assert all(line.split("\t")[4] == "voter" for line in lines)
    waterfall = next(call for call in _harness.run_calls if _verb(call) == ("agent", "dispatch-waterfall"))
    manifest = json.loads(Path(_value_after(waterfall, "--slots-file")).read_text(encoding="utf-8").splitlines()[0])
    assert "payload_files" in manifest
    assert sorted(manifest["payload_files"]) == ["claude", "codex", "cursor"]


def test_build_voter_prompt_files_tracks_distinct_payload_counts(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    review = tmp_path / "review"
    review.mkdir()
    ballot = tmp_path / "ballot.md"
    ballot.write_text("### FINDING_1: one\n", encoding="utf-8")
    opts = _opts(ballot, review)
    payloads = {"codex": 7, "cursor": 11, "claude": 13}

    def fake_make_voter_prompt_file(
        *,
        voter_tool: str | None = None,
        label: str = "",
        **_kwargs: object,
    ) -> agent_voters.VoterPromptResult:
        tool = voter_tool or "claude"
        return agent_voters.VoterPromptResult(prompt_file=str(review / f"{label}-{tool}.txt"), payload_bytes=payloads[tool])

    monkeypatch.setattr(agent_voters, "_make_voter_prompt_file", fake_make_voter_prompt_file)

    prompt_files, payload_files = agent_voters._build_voter_prompt_files(  # pyright: ignore[reportPrivateUsage]
        opts=opts,
        review_tmpdir=review,
        policies=agent_voters.VOTER_SLOT_POLICIES[:2],
        availability=(True, True),
        calibration_stats_file=None,
    )

    assert payload_files[agent_voters.VOTER_SLOT_POLICIES[0].prompt_label]["codex"] == 7
    assert payload_files[agent_voters.VOTER_SLOT_POLICIES[0].prompt_label]["cursor"] == 11
    assert prompt_files[agent_voters.VOTER_SLOT_POLICIES[1].prompt_label]["codex"].endswith("codex.txt")


def test_voter_dispatch_resolves_round_subdir_for_panel_artifact(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    run_root = tmp_path / "impl"
    round_dir = run_root / "round-5"
    round_dir.mkdir(parents=True)
    ballot = tmp_path / "ballot.md"
    ballot.write_text("### FINDING_1: one\n", encoding="utf-8")
    harness, _stub_root = _install_harness(monkeypatch, tmp_path, run_root)

    assert agent_voters.dispatch_voters(_opts(ballot, run_root, round_num=5)) == 0

    waterfall = next(call for call in harness.run_calls if _verb(call) == ("agent", "dispatch-waterfall"))
    assert _value_after(waterfall, "--panel-artifact-dir") == str(round_dir)
    assert not (run_root / "panel-prompt-sizes.tsv").exists()
