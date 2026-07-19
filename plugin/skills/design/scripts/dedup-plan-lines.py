#!/usr/bin/env python3
"""Section-aware plan-line dedup for plan-review post-apply.

Fence model: two-pass balanced opener/closer pairing; only lines strictly
between a matched fence pair are in-fence for heading and Constraints-section
state; a failed closer leaves the stack unchanged (plain-text semantics);
duplicate-line collapse still applies inside fenced blocks;
Constraints-section duplicates are protected only outside fences.

This model intentionally differs from parse-plan-commands.awk (simple
bash/sh fence toggle); see dedup-plan-lines.md.
"""
import re
import sys

src, dest = sys.argv[1:3]
heading_re = re.compile(r"^(#{1,6})\s+(.+?)\s*$")
fence_re = re.compile(r"^(\x60{3,})(.*)$")
removed = 0
prev_key = None
inside_constraints = False
constraints_level = None
out = []


def norm_key(line: str) -> str:
    return " ".join(line.strip().split())


def is_fence_marker(line: str) -> bool:
    return fence_re.match(line.strip()) is not None


def update_heading_state(line: str) -> None:
    global inside_constraints, constraints_level
    m = heading_re.match(line)
    if not m:
        return
    level = len(m.group(1))
    text = m.group(2).strip().lower()
    if text == "constraints":
        if inside_constraints:
            constraints_level = min(constraints_level, level)
        else:
            inside_constraints = True
            constraints_level = level
    elif inside_constraints and level <= constraints_level:
        inside_constraints = False
        constraints_level = None


with open(src, encoding="utf-8", errors="replace") as fh:
    lines = fh.readlines()

# Pass 1: balanced opener/closer pairs only; indices strictly between mark in-fence.
in_fence_lines: set[int] = set()
stack: list[tuple[int, int]] = []
for i, line in enumerate(lines):
    stripped = line.strip()
    m = fence_re.match(stripped)
    if not m:
        continue
    ticks = len(m.group(1))
    suffix = m.group(2)
    if not stack:
        stack.append((i, ticks))
    else:
        top_i, top_ticks = stack[-1]
        if ticks >= top_ticks and suffix.strip() == "":
            stack.pop()
            for j in range(top_i + 1, i):
                in_fence_lines.add(j)
        # failed closer: stack unchanged (plain text semantics)

for i, line in enumerate(lines):
    in_fence = i in in_fence_lines
    if not in_fence and not is_fence_marker(line):
        update_heading_state(line)
    m = heading_re.match(line)
    if m and not in_fence:
        prev_key = None
    key = norm_key(line)
    protected = inside_constraints and not in_fence
    if key and prev_key == key and not protected:
        removed += 1
        continue
    out.append(line)
    prev_key = key

with open(dest, "w", encoding="utf-8") as fh:
    fh.writelines(out)
print(removed)
