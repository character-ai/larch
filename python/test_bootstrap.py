# pyright: reportUnknownParameterType=false, reportMissingParameterType=false, reportUnknownMemberType=false, reportUnknownVariableType=false, reportUnknownArgumentType=false
from __future__ import annotations

import bootstrap


def test_filtered_envelope_allowlist_and_resume_empty_coder() -> None:
    text = "IMPLEMENT_TMPDIR=/tmp/x\nBAD=x\ncoder=\ncoder_fallback=true\nBRANCH_ACTION=create\n"
    out = bootstrap._filtered_envelope(text, resume=True)  # pyright: ignore[reportPrivateUsage]
    assert "IMPLEMENT_TMPDIR=/tmp/x" in out
    assert "BRANCH_ACTION=create" in out
    assert "BAD=" not in out
    assert "coder=\n" not in out


def test_parse_routing_file_first_stdout_fills_missing(tmp_path, capsys) -> None:
    tmpdir = tmp_path / "impl"
    tmpdir.mkdir()
    (tmpdir / "bootstrap-routing.env").write_text("IMPLEMENT_TMPDIR=/file\nBRANCH_NAME=file-branch\n", encoding="utf-8")
    stdout = tmp_path / "stdout.txt"
    stdout.write_text(f"IMPLEMENT_TMPDIR={tmpdir}\nBRANCH_NAME=stdout-branch\nRUN_ID=R1\n", encoding="utf-8")
    rc = bootstrap.parse_routing_main(["--stdout-file", str(stdout), "--tmpdir", str(tmpdir)])
    assert rc == 0
    out = capsys.readouterr().out
    assert "BRANCH_NAME=file-branch" in out
    assert "RUN_ID=R1" in out


def test_parse_routing_output_atomic(tmp_path) -> None:
    stdout = tmp_path / "stdout.txt"
    output = tmp_path / "out.env"
    stdout.write_text("IMPLEMENT_TMPDIR=/tmp/impl\nRUN_ID=abc\n", encoding="utf-8")
    assert bootstrap.parse_routing_main(["--stdout-file", str(stdout), "--output", str(output)]) == 0
    assert "RUN_ID=abc" in output.read_text(encoding="utf-8")
