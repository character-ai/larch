# pyright: reportUnusedCallResult=false, reportUnknownParameterType=false, reportMissingParameterType=false, reportUnknownMemberType=false
from __future__ import annotations

import json
import os
import subprocess
import sys
from collections.abc import Sequence
from pathlib import Path
from typing import TYPE_CHECKING

from larch.design import decompose

if TYPE_CHECKING:
    import pytest


def _design_tmp(tmp_path: Path) -> Path:
    d = tmp_path / "design"
    d.mkdir()
    (d / "feature-description.txt").write_text("Feature\n### embedded heading\n", encoding="utf-8")
    return d


def test_prepare_happy_path_multi_blocker_and_neutralizes_feature(tmp_path: Path) -> None:
    d = _design_tmp(tmp_path)
    partition = d / "partition.md"
    partition.write_text(
        "## Pieces\n\n"
        "### Piece 1: Base\n- Scope: base\n- Firm-headings: base/file.py\n- Acceptance: verify base\n- Dependencies: none\n\n"
        "### Piece 2: API\n- Scope: api\n- Firm-headings: api/file.py\n- Acceptance: verify api\n- Dependencies: blocked-by Piece 1\n\n"
        "### Piece 3: UI\n- Scope: ui\n- Firm-headings: ui/file.py\n- Acceptance: verify ui\n- Dependencies: blocked-by Piece 1, Piece 2 and Piece 2\n",
        encoding="utf-8",
    )
    status, witness = decompose.prepare_partition_issues(design_tmpdir=d, partition_file=partition, issue_number="123")
    assert (status, witness) == ("ok", "")
    deps = (d / "decompose" / "partition-deps.tsv").read_text(encoding="utf-8")
    assert deps.splitlines() == ["1\t2", "2\t3", "1\t3"]
    batch = (d / "decompose" / "partition-input.txt").read_text(encoding="utf-8")
    assert "#123" in batch
    assert "\u200b### embedded heading" in batch


def test_prepare_bad_dependency_and_cycle(tmp_path: Path) -> None:
    d = _design_tmp(tmp_path)
    bad = d / "bad.md"
    bad.write_text("## Pieces\n\n### Piece 1: A\n- Dependencies: blocked-by Piece 2\n", encoding="utf-8")
    assert decompose.prepare_partition_issues(design_tmpdir=d, partition_file=bad)[0] == "bad-dependency-ref"
    cycle = d / "cycle.md"
    cycle.write_text(
        "## Pieces\n\n"
        "### Piece 1: A\n- Firm-headings: a.py\n- Acceptance: verify a\n- Dependencies: blocked-by Piece 2\n\n"
        "### Piece 2: B\n- Firm-headings: b.py\n- Acceptance: verify b\n- Dependencies: blocked-by Piece 1\n",
        encoding="utf-8",
    )
    status, witness = decompose.prepare_partition_issues(design_tmpdir=d, partition_file=cycle)
    assert (status, witness) == ("ok", "")
    deps = (d / "decompose" / "partition-deps.tsv").read_text(encoding="utf-8")
    assert deps.splitlines() == ["1\t2"]


def test_prepare_skips_cyclic_panel_dependency_but_keeps_serial_chain(tmp_path: Path) -> None:
    d = _design_tmp(tmp_path)
    (d / "plan.txt").write_text(
        "## Files to modify\n\n"
        "### UPDATED: `python/larch/design/a.py`\n"
        "### UPDATED: `python/larch/design/b.py`\n"
        "### UPDATED: `python/larch/design/c.py`\n"
        "\n## Testing strategy\n\n"
        "- Cover python/larch/design/a.py behavior.\n"
        "- Cover python/larch/design/b.py behavior.\n"
        "- Cover python/larch/design/c.py behavior.\n"
        "diff_lines: 10\n",
        encoding="utf-8",
    )
    partition = d / "partition.md"
    partition.write_text(
        "## Pieces\n\n"
        "### Piece 1: A\n- Scope: python/larch/design/a.py\n- Firm-headings: python/larch/design/a.py\n- Acceptance: cover a\n- Dependencies: none\n\n"
        "### Piece 2: B\n- Scope: python/larch/design/b.py\n- Firm-headings: python/larch/design/b.py\n- Acceptance: cover b\n- Dependencies: blocked-by Piece 3\n\n"
        "### Piece 3: C\n- Scope: python/larch/design/c.py\n- Firm-headings: python/larch/design/c.py\n- Acceptance: cover c\n- Dependencies: none\n",
        encoding="utf-8",
    )

    status, witness = decompose.prepare_partition_issues(design_tmpdir=d, partition_file=partition, issue_number="123")

    assert (status, witness) == ("ok", "")
    deps = (d / "decompose" / "partition-deps.tsv").read_text(encoding="utf-8")
    assert deps.splitlines() == ["1\t2", "2\t3"]


def test_prepare_derives_piece_metadata_and_serial_edges(tmp_path: Path) -> None:
    d = _design_tmp(tmp_path)
    (d / "plan.txt").write_text(
        "## Files to modify\n\n"
        "### UPDATED: `python/larch/design/a.py`\n"
        "### UPDATED: `python/larch/design/b.py`\n\n"
        "## Testing strategy\n\n"
        "- Cover python/larch/design/a.py behavior.\n"
        "- Cover python/larch/design/b.py behavior.\n"
        "diff_lines: 10\n",
        encoding="utf-8",
    )
    partition = d / "partition.md"
    partition.write_text(
        "## Pieces\n\n"
        "### Piece 1: A\n- Scope: python/larch/design/a.py\n- Dependencies: none\n\n"
        "### Piece 2: B\n- Scope: python/larch/design/b.py\n- Dependencies: none\n",
        encoding="utf-8",
    )

    status, witness = decompose.prepare_partition_issues(design_tmpdir=d, partition_file=partition, issue_number="123")

    assert (status, witness) == ("ok", "")
    deps = (d / "decompose" / "partition-deps.tsv").read_text(encoding="utf-8")
    assert deps.splitlines() == ["1\t2"]
    batch = (d / "decompose" / "partition-input.txt").read_text(encoding="utf-8")
    assert "**Firm headings**: python/larch/design/a.py" in batch
    assert "Cover python/larch/design/b.py behavior." in batch
    assert "Gate C approval before `[DESIGNED]` or `/implement`" in batch


def test_prepare_missing_piece_metadata_when_fallback_cannot_match(tmp_path: Path) -> None:
    d = _design_tmp(tmp_path)
    (d / "plan.txt").write_text("## Files to modify\n\n### UPDATED: `python/larch/design/a.py`\ndiff_lines: 10\n", encoding="utf-8")
    partition = d / "partition.md"
    partition.write_text("## Pieces\n\n### Piece 1: A\n- Scope: docs/other.md\n- Dependencies: none\n", encoding="utf-8")

    assert decompose.prepare_partition_issues(design_tmpdir=d, partition_file=partition)[0] == "missing-piece-metadata"


def test_annotate_success_partial_and_idempotent(tmp_path: Path) -> None:
    d = _design_tmp(tmp_path)
    out = d / "issue.out"
    out.write_text("ISSUES_CREATED=2\nISSUES_FAILED=0\nISSUE_1_URL=https://x/1\nISSUE_2_URL=https://x/2\n", encoding="utf-8")
    decompose.annotate_partition_issues(design_tmpdir=d, issue_stdout_file=out)
    sentinel = d / ".decompose-issues-filed"
    assert "PARTITION_FILE_MAP\t1\thttps://x/1" in sentinel.read_text(encoding="utf-8")
    before = (d / "decompose" / "partition-filed.md").read_text(encoding="utf-8")
    decompose.annotate_partition_issues(design_tmpdir=d, issue_stdout_file=out)
    assert (d / "decompose" / "partition-filed.md").read_text(encoding="utf-8") == before
    partial = d / "partial.out"
    partial.write_text("ISSUES_CREATED=1\nISSUES_FAILED=1\nISSUE_1_URL=https://x/1\n", encoding="utf-8")
    decompose.annotate_partition_issues(design_tmpdir=d, issue_stdout_file=partial)
    assert not sentinel.exists()


def test_close_original_redacts_and_preserves_comment_sentinel_on_close_failure(tmp_path: Path, monkeypatch) -> None:
    d = _design_tmp(tmp_path)
    dec = d / "decompose"
    dec.mkdir(exist_ok=True)
    (dec / "partition-filed.md").write_text("## Piece 1\n- **Filed URL**: https://x/1\n", encoding="utf-8")
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    gh = bin_dir / "gh"
    log = tmp_path / "gh.log"
    gh.write_text(
        "#!/usr/bin/env bash\n"
        "printf '%s\\n' \"$*\" >> \"$GH_LOG\"\n"
        'if [[ "$*" == issue\\ close* ]]; then exit 9; fi\n',
        encoding="utf-8",
    )
    gh.chmod(0o755)
    monkeypatch.setenv("PATH", f"{bin_dir}:{os.environ['PATH']}")
    monkeypatch.setenv("GH_LOG", str(log))
    status = decompose.close_original_issue(design_tmpdir=d, original_issue="99", repo="o/r")
    assert status == "failed"
    assert (dec / ".decompose-close-comment-posted").exists()
    assert "--body-file" in log.read_text(encoding="utf-8")


def test_dispatch_panel_and_aggregate_with_stub_waterfall(tmp_path: Path, monkeypatch) -> None:
    d = _design_tmp(tmp_path)
    plan = d / "plan.txt"
    plan.write_text("## Plan\n", encoding="utf-8")
    stub = tmp_path / "waterfall.sh"
    stub.write_text(
        "#!/usr/bin/env bash\n"
        'slots=""\nwhile [[ $# -gt 0 ]]; do if [[ $1 == --slots-file ]]; then slots=$2; shift 2; else shift; fi; done\n'
        "paths=$(mktemp)\nwhile IFS= read -r row; do out=$(python3 -c 'import json,sys; print(json.loads(sys.stdin.read())[\"output\"])' <<<\"$row\"); printf '## Recommendation\\nsplit\\n' >\"$out\"; printf '%s\\n' \"$out\" >>\"$paths\"; done <\"$slots\"\n"
        "printf 'DISPATCH_OK=true\\nFALLBACK_COUNT=0\\nCOMBINED_FALLBACK_COUNT=0\\nSTATIC_DISPATCH_OK=true\\nALL_OUTPUT_FILES_PATH=%s\\n' \"$paths\"\n",
        encoding="utf-8",
    )
    stub.chmod(0o755)
    monkeypatch.setenv("DECOMPOSE_PANEL_WATERFALL_SH", str(stub))
    monkeypatch.setenv("DECOMPOSE_AGGREGATE_WATERFALL_SH", str(stub))
    decompose.dispatch_panel(design_tmpdir=d, codex_present=True, cursor_present=True, mode="plan", plan_file=plan)
    rows = [json.loads(line) for line in (d / "decompose" / "panel-outputs.ndjson").read_text(encoding="utf-8").splitlines()]
    assert len(rows) == 8
    assert all(row["status"] == "ok" for row in rows)
    status = decompose.aggregate_partition(design_tmpdir=d, panel_outputs_file=d / "decompose" / "panel-outputs.ndjson", codex_present=True, cursor_present=True, output=d / "partition.md")
    assert status == "ok"
    assert (d / "partition.md").is_file()
    assert not list(d.rglob("panel-prompt-sizes.tsv"))


def _panel_stub(tmp_path: Path, *, mode: str = "ok", static_ok: str = "true", exit_code: int = 0, partial_first: bool = False, path_limit: int = 0) -> Path:
    stub = tmp_path / "waterfall.sh"
    if partial_first:
        body = (
            "#!/usr/bin/env bash\n"
            'slots=""\nwhile [[ $# -gt 0 ]]; do if [[ $1 == --slots-file ]]; then slots=$2; shift 2; else shift; fi; done\n'
            "paths=$(mktemp)\nfirst=true\nwhile IFS= read -r row; do out=$(python3 -c 'import json,sys; print(json.loads(sys.stdin.read())[\"output\"])' <<<\"$row\"); "
            'if [[ "$first" == true ]]; then printf "narration only\\n" >"$out"; first=false; else printf "## Recommendation\\nsplit\\n" >"$out"; printf "%s\\n" "$out" >>"$paths"; fi; done <"$slots"\n'
            'printf "DISPATCH_OK=true\\nFALLBACK_COUNT=0\\nCOMBINED_FALLBACK_COUNT=0\\nSTATIC_DISPATCH_OK=true\\nALL_OUTPUT_FILES_PATH=%s\\n" "$paths"\n'
        )
    elif path_limit > 0:
        body = (
            "#!/usr/bin/env bash\n"
            'slots=""\nwhile [[ $# -gt 0 ]]; do if [[ $1 == --slots-file ]]; then slots=$2; shift 2; else shift; fi; done\n'
            "paths=$(mktemp)\nn=0\nwhile IFS= read -r row; do out=$(python3 -c 'import json,sys; print(json.loads(sys.stdin.read())[\"output\"])' <<<\"$row\"); "
            'printf "## Recommendation\\nsplit\\n" >"$out"; n=$((n+1)); '
            f"if (( n <= {path_limit} )); then printf '%s\\n' \"$out\" >>\"$paths\"; fi; done <\"$slots\"\n"
            'printf "DISPATCH_OK=true\\nSTATIC_DISPATCH_OK=true\\nALL_OUTPUT_FILES_PATH=%s\\n" "$paths"\n'
        )
    else:
        rec = "## Recommendation\\nsplit\\n" if mode == "ok" else "no heading\\n"
        body = (
            "#!/usr/bin/env bash\n"
            'slots=""\nwhile [[ $# -gt 0 ]]; do if [[ $1 == --slots-file ]]; then slots=$2; shift 2; else shift; fi; done\n'
            "paths=$(mktemp)\nwhile IFS= read -r row; do out=$(python3 -c 'import json,sys; print(json.loads(sys.stdin.read())[\"output\"])' <<<\"$row\"); "
            f"printf '{rec}' >\"$out\"; printf '%s\\n' \"$out\" >>\"$paths\"; done <\"$slots\"\n"
            f'printf "DISPATCH_OK=true\\nFALLBACK_COUNT=0\\nCOMBINED_FALLBACK_COUNT=0\\nSTATIC_DISPATCH_OK={static_ok}\\nALL_OUTPUT_FILES_PATH=%s\\n" "$paths"\n'
            f"exit {exit_code}\n"
        )
    stub.write_text(body, encoding="utf-8")
    stub.chmod(0o755)
    return stub


def test_panel_degraded_when_static_dispatch_false(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> None:
    d = _design_tmp(tmp_path)
    (d / "plan.txt").write_text("## Plan\n", encoding="utf-8")
    stub = _panel_stub(tmp_path, static_ok="false")
    monkeypatch.setenv("DECOMPOSE_PANEL_WATERFALL_SH", str(stub))
    decompose.panel_dispatch_main(["--design-tmpdir", str(d), "--codex-binary-found", "true", "--cursor-binary-found", "true", "--mode", "plan", "--plan-file", str(d / "plan.txt"), "--timeout", "30"])
    out = capsys.readouterr().out
    assert "DEGRADED_PANEL=true" in out
    assert "PANEL_STATUS=degraded" in out


def test_panel_partial_paths_file_marks_degraded(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> None:
    d = _design_tmp(tmp_path)
    (d / "plan.txt").write_text("## Plan\n", encoding="utf-8")
    stub = _panel_stub(tmp_path, path_limit=4)
    monkeypatch.setenv("DECOMPOSE_PANEL_WATERFALL_SH", str(stub))
    decompose.panel_dispatch_main(["--design-tmpdir", str(d), "--codex-binary-found", "true", "--cursor-binary-found", "true", "--mode", "plan", "--plan-file", str(d / "plan.txt"), "--timeout", "30"])
    out = capsys.readouterr().out
    assert "DEGRADED_PANEL=true" in out
    rows = [json.loads(line) for line in (d / "decompose" / "panel-outputs.ndjson").read_text(encoding="utf-8").splitlines()]
    assert len(rows) == 8
    assert sum(1 for row in rows if row["status"] == "ok") == 4
    assert sum(1 for row in rows if row["status"] == "missing") == 4


def test_panel_both_tools_absent_generic_claude(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> None:
    d = _design_tmp(tmp_path)
    (d / "plan.txt").write_text("## Plan\n", encoding="utf-8")
    claude = tmp_path / "claude.sh"
    claude.write_text("#!/usr/bin/env bash\nwhile [[ $# -gt 0 ]]; do if [[ $1 == --output ]]; then out=$2; shift 2; else shift; fi; done\nprintf '## Recommendation\\nGeneric\\n' >\"$out\"\nprintf '0\\n' >\"${out}.done\"\n", encoding="utf-8")
    claude.chmod(0o755)
    monkeypatch.setenv("LARCH_TEST_LAUNCH_CLAUDE_REVIEW", str(claude))
    decompose.panel_dispatch_main(["--design-tmpdir", str(d), "--codex-binary-found", "false", "--cursor-binary-found", "false", "--mode", "plan", "--plan-file", str(d / "plan.txt"), "--timeout", "30"])
    rows = [json.loads(line) for line in (d / "decompose" / "panel-outputs.ndjson").read_text(encoding="utf-8").splitlines()]
    assert len(rows) == 1
    assert rows[0]["archetype"] == "generic"
    assert "PANEL_STATUS=ok" in capsys.readouterr().out


def test_aggregate_failed_when_dispatch_broken(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> None:
    d = _design_tmp(tmp_path)
    panel = d / "panel.ndjson"
    panel.write_text('{"archetype":"decomposition-specialist","vendor":"cursor","output":"OUT1","status":"ok"}\n', encoding="utf-8")
    (d / "OUT1").write_text("## Recommendation\nsplit\n", encoding="utf-8")
    stub = tmp_path / "agg.sh"
    stub.write_text("#!/usr/bin/env bash\nprintf 'DISPATCH_OK=false\\nALL_OUTPUT_FILES_PATH=/dev/null\\n'\n", encoding="utf-8")
    stub.chmod(0o755)
    monkeypatch.setenv("DECOMPOSE_AGGREGATE_WATERFALL_SH", str(stub))
    decompose.aggregate_main(["--design-tmpdir", str(d), "--panel-outputs-file", str(panel), "--codex-binary-found", "true", "--cursor-binary-found", "true", "--output", str(d / "merged.md"), "--timeout", "30"])
    assert "AGGREGATOR_STATUS=failed" in capsys.readouterr().out


def test_panel_replays_waterfall_kvs_on_contract_stream(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> None:
    d = _design_tmp(tmp_path)
    (d / "plan.txt").write_text("## Plan\n", encoding="utf-8")
    stub = _panel_stub(tmp_path)
    monkeypatch.setenv("DECOMPOSE_PANEL_WATERFALL_SH", str(stub))
    decompose.panel_dispatch_main(["--design-tmpdir", str(d), "--codex-binary-found", "true", "--cursor-binary-found", "true", "--mode", "plan", "--plan-file", str(d / "plan.txt"), "--timeout", "30"])
    out = capsys.readouterr().out
    assert "DISPATCH_OK=true" in out
    assert "ALL_OUTPUT_FILES_PATH=" in out


def test_close_original_idempotent_when_already_closed(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    d = _design_tmp(tmp_path)
    (d / ".decompose-original-closed").touch()
    dec = d / "decompose"
    dec.mkdir(exist_ok=True)
    (dec / "partition-filed.md").write_text("## Piece 1\n- **Filed URL**: https://x/1\n", encoding="utf-8")
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    gh = bin_dir / "gh"
    gh.write_text("#!/usr/bin/env bash\nexit 99\n", encoding="utf-8")
    gh.chmod(0o755)
    monkeypatch.setenv("PATH", f"{bin_dir}:{os.environ['PATH']}")
    status = decompose.close_original_issue(design_tmpdir=d, original_issue="99", repo="o/r")
    assert status == "ok"


def test_panel_dispatch_malformed_slots_ndjson(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> None:
    d = _design_tmp(tmp_path)
    (d / "plan.txt").write_text("## Plan\n", encoding="utf-8")
    stub = tmp_path / "waterfall.sh"
    stub.write_text(
        "#!/usr/bin/env bash\n"
        'slots=""\nwhile [[ $# -gt 0 ]]; do if [[ $1 == --slots-file ]]; then slots=$2; shift 2; else shift; fi; done\n'
        'printf "not-json\\n" >"$slots"\n'
        "printf 'DISPATCH_OK=true\\nSTATIC_DISPATCH_OK=true\\nALL_OUTPUT_FILES_PATH=/dev/null\\n'\n",
        encoding="utf-8",
    )
    stub.chmod(0o755)
    monkeypatch.setenv("DECOMPOSE_PANEL_WATERFALL_SH", str(stub))
    rc = decompose.panel_dispatch_main(
        ["--design-tmpdir", str(d), "--codex-binary-found", "true", "--cursor-binary-found", "true", "--mode", "plan", "--plan-file", str(d / "plan.txt"), "--timeout", "30"],
    )
    out = capsys.readouterr().out
    assert rc == 2
    assert "PANEL_STATUS=panel-failed" in out


def test_aggregate_malformed_panel_ndjson(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    d = _design_tmp(tmp_path)
    panel = d / "panel.ndjson"
    panel.write_text("not-json\n", encoding="utf-8")
    rc = decompose.aggregate_main(
        ["--design-tmpdir", str(d), "--panel-outputs-file", str(panel), "--codex-binary-found", "true", "--cursor-binary-found", "true", "--output", str(d / "merged.md"), "--timeout", "30"],
    )
    out = capsys.readouterr().out
    assert rc == 2
    assert "AGGREGATOR_STATUS=failed" in out


def test_dispatch_panel_defaults_to_agent_dispatch_waterfall(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    d = _design_tmp(tmp_path)
    plan = d / "plan.txt"
    plan.write_text("## Plan\n", encoding="utf-8")
    seen: list[list[str]] = []

    def fake_run(cmd: Sequence[str], **_kwargs: object) -> subprocess.CompletedProcess[str]:
        seen.append(list(cmd))
        slots = Path(cmd[cmd.index("--slots-file") + 1])
        paths = tmp_path / "panel.paths"
        with paths.open("w", encoding="utf-8") as handle:
            for row in slots.read_text(encoding="utf-8").splitlines():
                data = json.loads(row)
                out = Path(data["output"])
                out.write_text("## Recommendation\nsplit\n", encoding="utf-8")
                handle.write(str(out) + "\n")
        return subprocess.CompletedProcess(cmd, 0, stdout=f"DISPATCH_OK=true\nFALLBACK_COUNT=0\nCOMBINED_FALLBACK_COUNT=0\nSTATIC_DISPATCH_OK=true\nALL_OUTPUT_FILES_PATH={paths}\n", stderr="")

    monkeypatch.delenv("DECOMPOSE_PANEL_WATERFALL_SH", raising=False)
    monkeypatch.setattr(decompose.subprocess, "run", fake_run)  # type: ignore[arg-type]
    decompose.dispatch_panel(design_tmpdir=d, codex_present=True, cursor_present=True, mode="plan", plan_file=plan)
    assert seen
    assert seen[0][:4] == [sys.executable, str(decompose.PLUGIN_ROOT / "python" / "cli.py"), "agent", "dispatch-waterfall"]


def test_aggregate_partition_defaults_to_agent_dispatch_waterfall(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    d = _design_tmp(tmp_path)
    source = d / "panel-output.txt"
    source.write_text("## Recommendation\nsplit\n", encoding="utf-8")
    panel = d / "panel.ndjson"
    panel.write_text(json.dumps({"archetype": "a", "vendor": "codex", "output": str(source), "status": "ok"}) + "\n", encoding="utf-8")
    seen: list[list[str]] = []

    def fake_run(cmd: Sequence[str], **_kwargs: object) -> subprocess.CompletedProcess[str]:
        seen.append(list(cmd))
        out = d / "aggregate-final.txt"
        out.write_text("## Recommendation\nsplit\n", encoding="utf-8")
        paths = d / "aggregate.paths"
        paths.write_text(str(out) + "\n", encoding="utf-8")
        return subprocess.CompletedProcess(cmd, 0, stdout=f"DISPATCH_OK=true\nALL_OUTPUT_FILES_PATH={paths}\n", stderr="")

    monkeypatch.delenv("DECOMPOSE_AGGREGATE_WATERFALL_SH", raising=False)
    monkeypatch.setattr(decompose.subprocess, "run", fake_run)  # type: ignore[arg-type]
    status = decompose.aggregate_partition(design_tmpdir=d, panel_outputs_file=panel, codex_present=True, cursor_present=True, output=d / "merged.md")
    assert status == "ok"
    assert seen
    assert seen[0][:4] == [sys.executable, str(decompose.PLUGIN_ROOT / "python" / "cli.py"), "agent", "dispatch-waterfall"]
