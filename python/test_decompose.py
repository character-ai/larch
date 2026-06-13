# pyright: reportUnusedCallResult=false, reportUnknownParameterType=false, reportMissingParameterType=false, reportUnknownMemberType=false
from __future__ import annotations

import json
import os
from pathlib import Path

import decompose


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
        "### Piece 1: Base\n- Scope: base\n- Dependencies: none\n\n"
        "### Piece 2: API\n- Scope: api\n- Dependencies: blocked-by Piece 1\n\n"
        "### Piece 3: UI\n- Scope: ui\n- Dependencies: blocked-by Piece 1, Piece 2 and Piece 2\n",
        encoding="utf-8",
    )
    status, witness = decompose.prepare_partition_issues(design_tmpdir=d, partition_file=partition, issue_number="123")
    assert (status, witness) == ("ok", "")
    deps = (d / "decompose" / "partition-deps.tsv").read_text(encoding="utf-8")
    assert deps.splitlines() == ["1\t2", "1\t3", "2\t3"]
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
        "## Pieces\n\n### Piece 1: A\n- Dependencies: blocked-by Piece 2\n\n### Piece 2: B\n- Dependencies: blocked-by Piece 1\n",
        encoding="utf-8",
    )
    status, witness = decompose.prepare_partition_issues(design_tmpdir=d, partition_file=cycle)
    assert status == "cycle-detected"
    assert "Piece 2→Piece 1" in witness


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
