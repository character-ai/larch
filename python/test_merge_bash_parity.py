"""Bash parity for merge MERGE_RESULT classification."""

from __future__ import annotations

import os
import subprocess
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
MERGE_SH = REPO_ROOT / "scripts" / "merge-pr.sh"


@pytest.mark.skipif(not MERGE_SH.is_file(), reason="merge-pr.sh missing")
def test_behind_emits_main_advanced(tmp_path: Path) -> None:
    env = os.environ.copy()
    env.update(
        {
            "LARCH_QUIET_DISABLE": "1",
            "GH_MERGE_STATE": "BEHIND",
            "STUB_PR_HEAD_OID": "abc123",
        },
    )
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    gh_log = tmp_path / "gh.log"
    trace = tmp_path / "trace.log"
    env["GH_LOG_FILE"] = str(gh_log)
    env["TRACE_LOG_FILE"] = str(trace)
    # Minimal stub gh from test-merge-pr.sh pattern
    gh_stub = bin_dir / "gh"
    _ = gh_stub.write_text(
        '#!/usr/bin/env bash\n'
        'set -euo pipefail\n'
        'if [[ "$2" == "view" ]]; then\n'
        '  printf \'{"mergeStateStatus":"%s","headRefOid":"abc123"}\\n\' "${GH_MERGE_STATE:-CLEAN}"\n'
        '  exit 0\n'
        'fi\n'
        'exit 0\n',
        encoding="utf-8",
    )
    _ = gh_stub.chmod(0o755)
    git_stub = bin_dir / "git"
    _ = git_stub.write_text("#!/usr/bin/env bash\nexit 0\n", encoding="utf-8")
    _ = git_stub.chmod(0o755)
    env["PATH"] = f"{bin_dir}:{env['PATH']}"
    completed = subprocess.run(
        ["bash", str(MERGE_SH), "--pr", "1", "--repo", "o/r"],
        capture_output=True,
        text=True,
        check=False,
        env=env,
        cwd=REPO_ROOT,
    )
    assert completed.returncode == 0
    assert "MERGE_RESULT=main_advanced" in completed.stdout
