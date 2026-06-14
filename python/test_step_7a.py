from pathlib import Path

import step_7a


def test_step7a_emits_terminal_kvs(tmp_path: Path, capsys) -> None:
    (tmp_path / "session-id").write_text("run-1\n", encoding="utf-8")

    rc = step_7a.run_step7a(tmp_path)

    assert rc == 0
    out = capsys.readouterr().out
    assert "DIAGRAM_STATUS=ok" in out
    assert "LOG_FLUSH_STATUS=skip" in out
    assert (tmp_path / "code-flow-diagram.md").is_file()
