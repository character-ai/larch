#!/usr/bin/env python3
"""Offline verified-entrypoint stand-in for the Step 5c Gate C parity case."""
from __future__ import annotations

import os
import sys
from pathlib import Path


def value(flag: str) -> str:
    index = sys.argv.index(flag)
    return sys.argv[index + 1]


if sys.argv[1:3] == ["plan", "check-size"]:
    print("PLAN_SIZE_STATUS=ok")
    print("SIZE_TRIGGER_FIRED=false")
    raise SystemExit(0)
if sys.argv[1:3] == ["design", "publish"]:
    mode = os.environ.get("DESIGN_FINALIZE_FAKE_MODE", "")
    rows = [
        f"PUBLISH_ATTEMPT_ID={os.environ.get('LARCH_DESIGN_PUBLISH_ATTEMPT_ID', '')}",
        "PUBLISH_RC_SOURCE=returned",
        "LATEST_PHASE=publish" if mode == "success" else "LATEST_PHASE=plan-write",
        f"PLAN_WRITE_OK={'true' if mode == 'success' else 'false'}",
        f"PUBLISH_OK={'true' if mode == 'success' else 'false'}",
        "LOG_PUBLISH_ATTEMPTED=false",
        "LOG_PUBLISH_COMPLETED=false",
        "RENAMED=false",
        "VALIDATE_STATUS=ok",
    ]
    body = "\n".join(rows) + "\n"
    if mode == "success":
        Path(value("--design-tmpdir"), ".design-publish-result.env").write_text(
            body, encoding="utf-8"
        )
    sys.stdout.write(body)
    raise SystemExit(0 if mode == "success" else 5)
if sys.argv[1:3] == ["design", "read-result-env"]:
    primary = Path(value("--input"))
    fallback = Path(value("--fallback-input"))
    source = primary if primary.is_file() and not primary.is_symlink() else fallback
    if not source.is_file() or source.is_symlink():
        raise SystemExit(1)
    allowed = {
        sys.argv[index + 1]
        for index, item in enumerate(sys.argv[:-1])
        if item == "--allow"
    }
    rows = []
    for line in source.read_text(encoding="utf-8").splitlines():
        key, separator, row_value = line.partition("=")
        if separator and key in allowed:
            rows.append(f"{key}={row_value}")
    Path(value("--output")).write_text("\n".join(rows) + "\n", encoding="utf-8")
    raise SystemExit(0)
if sys.argv[1:3] == ["design", "stage-terminal-state"]:
    print("STAGED=true")
    raise SystemExit(0)
if sys.argv[1:3] == ["design", "render-final-summary"]:
    Path(value("--design-tmpdir"), "final-summary.md").write_text(
        "offline final summary\n", encoding="utf-8"
    )
    raise SystemExit(0)
print(f"design-finalize-fake-plugin: unsupported command: {sys.argv[1:]!r}", file=sys.stderr)
raise SystemExit(2)
