#!/usr/bin/env python3
"""Frozen stdlib reference for the pre-cutover execution-issue append path."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path


def chunks(body: str) -> list[str]:
    output: list[str] = []
    current: list[str] = []
    in_fence = False
    pending_break = False
    for line in body.splitlines():
        if not in_fence and not line.strip():
            pending_break = bool(current)
            continue
        candidate = line.lstrip()
        if candidate.startswith("- "):
            candidate = candidate[2:].lstrip()
        fence = candidate.startswith("```")
        if not in_fence and line.startswith("- ") and current and not fence:
            output.append("\n".join(current).strip() + "\n")
            current = []
            pending_break = False
        if pending_break and current:
            output.append("\n".join(current).strip() + "\n")
            current = []
        pending_break = False
        current.append(line)
        if fence:
            in_fence = not in_fence
    if current:
        output.append("\n".join(current).strip() + "\n")
    return output


def sections(markdown: str) -> list[tuple[str, str]]:
    output: list[tuple[str, str]] = []
    category = "Warnings"
    body: list[str] = []
    for line in markdown.splitlines():
        if line.startswith("### "):
            if body:
                output.append((category, "\n".join(body)))
            category = line[4:].strip()
            body = []
        else:
            body.append(line)
    if body:
        output.append((category, "\n".join(body)))
    return output


def identity(category: str, body: str) -> str:
    normalized = "\n".join(line for line in body.splitlines()).strip()
    return hashlib.sha256(f"{category}\0{normalized}".encode()).hexdigest()


def compose(existing: str, category: str, entry: str) -> str:
    heading = f"### {category}"
    lines = existing.splitlines()
    if heading not in lines:
        prefix = "\n\n" if existing.strip() else ""
        return existing.rstrip() + prefix + heading + "\n" + entry.rstrip("\n") + "\n"
    section = lines.index(heading)
    insert = next(
        (
            index
            for index, line in enumerate(lines[section + 1 :], section + 1)
            if line.startswith("### ")
        ),
        len(lines),
    )
    while insert > section + 1 and lines[insert - 1] == "":
        insert -= 1
    lines.insert(insert, entry.rstrip("\n"))
    return "\n".join(lines).rstrip() + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument("--log", required=True)
    parser.add_argument("--category", default="Tool Failures")
    parser.add_argument("--entry", required=True)
    parser.add_argument("--existing-batch", default="")
    args = parser.parse_args()
    log = Path(args.log)
    existing = (
        log.read_text(encoding="utf-8", errors="replace") if log.is_file() else ""
    )
    known = {
        identity(category, chunk)
        for category, body in sections(existing)
        for chunk in chunks(body)
    }
    if args.existing_batch:
        batch = Path(args.existing_batch)
        if batch.is_file():
            for raw in batch.read_text(encoding="utf-8", errors="replace").splitlines():
                try:
                    row = json.loads(raw)
                except json.JSONDecodeError:
                    continue
                if (
                    isinstance(row, dict)
                    and isinstance(row.get("category"), str)
                    and isinstance(row.get("body"), str)
                ):
                    known.add(identity(row["category"], row["body"]))
    kept: list[str] = []
    for chunk in chunks(args.entry):
        key = identity(args.category, chunk)
        if key in known:
            continue
        known.add(key)
        kept.append(chunk)
    if kept:
        log.parent.mkdir(parents=True, exist_ok=True)
        log.write_text(
            compose(existing, args.category, "\n".join(kept)), encoding="utf-8"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
