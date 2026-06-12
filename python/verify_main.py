# pyright: reportUnknownVariableType=false, reportUnknownMemberType=false, reportUnknownArgumentType=false, reportUnusedCallResult=false, reportOptionalSubscript=false, reportOptionalMemberAccess=false, reportPossiblyUnboundVariable=false, reportUnnecessaryComparison=false, reportUnknownLambdaType=false, reportArgumentType=false, reportUnknownParameterType=false, reportMissingParameterType=false, reportUnusedImport=false, reportUnusedFunction=false, reportPrivateUsage=false, reportUnusedVariable=false
# pylint: skip-file
"""Verify that main HEAD matches an expected squash-merge title."""

from __future__ import annotations

import argparse
import re
import proc


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="cli.py verify main")
    parser.add_argument("--expected-title", required=True)
    args = parser.parse_args(argv)
    expected = args.expected_title
    verified = "false"
    commit_hash = ""
    commit_message = ""
    res = proc.run(["git", "log", "-1", "--oneline"])
    line = res.stdout.strip()
    if not line:
        commit_message = "(no commits found)"
    else:
        if " " in line:
            commit_hash, commit_message = line.split(" ", 1)
        else:
            commit_hash, commit_message = line, ""
        if commit_message.startswith(expected):
            verified = "true"
        else:
            match = re.search(r"\(#[0-9]+\)$", expected)
            if match and commit_message.endswith(match.group(0)):
                verified = "true"
    print(f"VERIFIED={verified}")
    print(f"COMMIT_HASH={commit_hash}")
    print(f"COMMIT_MESSAGE={commit_message}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
