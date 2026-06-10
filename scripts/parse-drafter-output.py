#!/usr/bin/env python3
"""Parse LARCH_PLAN_BEGIN/END and LARCH_SUMMARY_BEGIN/END sentinel blocks.

Usage: parse-drafter-output.py <raw-file> <plan-out> <summary-out>

Writes plan body to <plan-out> and (when present) summary body to <summary-out>.
Prints PLAN_LINES=N, DIFF_LINES=N, SUMMARY_WRITTEN=true|false to stdout.
Exits non-zero with a message on stderr on any validation failure.
"""
import re
import sys
from pathlib import Path

src = Path(sys.argv[1])
plan_tmp = Path(sys.argv[2])
summary_tmp = Path(sys.argv[3])
text = src.read_text(encoding='utf-8')
lines = text.splitlines()


def positions(marker):
    return [i for i, line in enumerate(lines) if line == marker]


pb = positions('LARCH_PLAN_BEGIN')
pe = positions('LARCH_PLAN_END')
sb = positions('LARCH_SUMMARY_BEGIN')
se = positions('LARCH_SUMMARY_END')
if len(pb) != 1 or len(pe) != 1:
    raise SystemExit('invalid plan sentinels: require exactly one LARCH_PLAN_BEGIN and LARCH_PLAN_END')
if pb[0] >= pe[0]:
    raise SystemExit('invalid plan sentinels: reversed or empty plan envelope')
if (len(sb) == 0) != (len(se) == 0) or len(sb) > 1 or len(se) > 1:
    raise SystemExit('invalid summary sentinels: require zero or one balanced pair')
if sb and sb[0] >= se[0]:
    raise SystemExit('invalid summary sentinels: reversed or empty summary envelope')
if sb and (pb[0] < sb[0] < pe[0] or pb[0] < se[0] < pe[0]):
    raise SystemExit('invalid sentinels: nested summary inside plan envelope')
if sb and sb[0] < pb[0] < pe[0] < se[0]:
    raise SystemExit('invalid sentinels: nested plan inside summary envelope')
plan_lines = lines[pb[0] + 1:pe[0]]
if not plan_lines or not ''.join(plan_lines).strip():
    raise SystemExit('empty extracted plan body')
while plan_lines and plan_lines[-1] == '':
    plan_lines.pop()
if not plan_lines or not re.match(r'^diff_lines: [0-9][0-9]*$', plan_lines[-1]):
    raise SystemExit('missing final diff_lines trailer')
plan_body = '\n'.join(plan_lines) + '\n'
plan_tmp.write_text(plan_body, encoding='utf-8')
summary_written = False
if sb:
    summary_lines = lines[sb[0] + 1:se[0]]
    if ''.join(summary_lines).strip():
        summary_tmp.write_text('\n'.join(summary_lines).rstrip('\n') + '\n', encoding='utf-8')
        summary_written = True
    else:
        raise SystemExit('empty extracted summary body')
print(f'PLAN_LINES={len(plan_lines)}')
print(f'DIFF_LINES={plan_lines[-1].split(": ", 1)[1]}')
print(f'SUMMARY_WRITTEN={str(summary_written).lower()}')
