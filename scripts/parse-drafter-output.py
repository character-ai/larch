#!/usr/bin/env python3
"""Parse drafter sentinel blocks.

Usage: parse-drafter-output.py <raw-file> <plan-out> <summary-out> [scout-out]

Writes plan body to <plan-out> and (when present) summary body to <summary-out>.
When scout-out is provided, writes valid post-plan scout JSON to that path.
Prints PLAN_LINES=N, DIFF_LINES=N, SUMMARY_WRITTEN=true|false,
SCOUT_CANDIDATE_WRITTEN=true|false, and optional SCOUT_FAIL_REASON=<reason>
to stdout.
Exits non-zero with a message on stderr on any validation failure.
"""
import json
import re
import sys
from pathlib import Path

if len(sys.argv) not in (4, 5):
    raise SystemExit('usage: parse-drafter-output.py <raw-file> <plan-out> <summary-out> [scout-out]')

src = Path(sys.argv[1])
plan_tmp = Path(sys.argv[2])
summary_tmp = Path(sys.argv[3])
scout_tmp = Path(sys.argv[4]) if len(sys.argv) == 5 else None
text = src.read_text(encoding='utf-8')
lines = text.splitlines()


def positions(marker):
    return [i for i, line in enumerate(lines) if line == marker]


pb = positions('LARCH_PLAN_BEGIN')
pe = positions('LARCH_PLAN_END')
sb = positions('LARCH_SUMMARY_BEGIN')
se = positions('LARCH_SUMMARY_END')
scb = positions('LARCH_SCOUT_BEGIN')
sce = positions('LARCH_SCOUT_END')


def fail(message):
    if scout_tmp is not None:
        try:
            scout_tmp.unlink()
        except FileNotFoundError:
            pass
    raise SystemExit(message)


def write_scout_candidate(payload):
    if scout_tmp is None:
        return
    tmp = scout_tmp.with_name(f'{scout_tmp.name}.tmp')
    tmp.write_text(json.dumps(payload, separators=(',', ':')) + '\n', encoding='utf-8')
    tmp.replace(scout_tmp)


def remove_scout_candidate():
    if scout_tmp is None:
        return
    try:
        scout_tmp.unlink()
    except FileNotFoundError:
        pass


def plan_contains_standalone_scout_manifest(plan_text):
    in_fence = False
    candidate = []
    depth = 0
    capture = False
    for line in plan_text.splitlines():
        if re.match(r'^\s*```', line):
            in_fence = not in_fence
            continue
        if in_fence:
            continue
        stripped = line.strip()
        if not capture:
            if not stripped.startswith('{'):
                continue
            candidate = [line]
            depth = stripped.count('{') - stripped.count('}')
            capture = True
            if depth > 0:
                continue
        else:
            candidate.append(line)
            depth += stripped.count('{') - stripped.count('}')
            if depth > 0:
                continue
        blob = '\n'.join(candidate).strip()
        capture = False
        candidate = []
        depth = 0
        try:
            parsed = json.loads(blob)
        except json.JSONDecodeError:
            continue
        if isinstance(parsed, dict) and isinstance(parsed.get('archetypes'), list):
            return True
    return False
if len(pb) != 1 or len(pe) != 1:
    fail('invalid plan sentinels: require exactly one LARCH_PLAN_BEGIN and LARCH_PLAN_END')
if pb[0] >= pe[0]:
    fail('invalid plan sentinels: reversed or empty plan envelope')
if (len(sb) == 0) != (len(se) == 0) or len(sb) > 1 or len(se) > 1:
    fail('invalid summary sentinels: require zero or one balanced pair')
if sb and sb[0] >= se[0]:
    fail('invalid summary sentinels: reversed or empty summary envelope')
if sb and (pb[0] < sb[0] < pe[0] or pb[0] < se[0] < pe[0]):
    fail('invalid sentinels: nested summary inside plan envelope')
if sb and sb[0] < pb[0] < pe[0] < se[0]:
    fail('invalid sentinels: nested plan inside summary envelope')
if sb and not (se[0] < pb[0]):
    fail('invalid summary sentinels: summary must appear before plan envelope')
if any(i < pe[0] for i in scb + sce):
    fail('invalid scout sentinels: scout block may appear only after LARCH_PLAN_END')
plan_lines = lines[pb[0] + 1:pe[0]]
if not plan_lines or not ''.join(plan_lines).strip():
    fail('empty extracted plan body')
while plan_lines and plan_lines[-1] == '':
    plan_lines.pop()
if not plan_lines or not re.match(r'^diff_lines: [0-9][0-9]*$', plan_lines[-1]):
    fail('missing final diff_lines trailer')
plan_body = '\n'.join(plan_lines) + '\n'
if plan_contains_standalone_scout_manifest(plan_body):
    fail('invalid plan body: standalone scout manifest JSON is not allowed inside plan')
plan_tmp.write_text(plan_body, encoding='utf-8')
summary_written = False
if sb:
    summary_lines = lines[sb[0] + 1:se[0]]
    if ''.join(summary_lines).strip():
        summary_tmp.write_text('\n'.join(summary_lines).rstrip('\n') + '\n', encoding='utf-8')
        summary_written = True
    else:
        fail('empty extracted summary body')

scout_written = False
scout_fail_reason = ''
remove_scout_candidate()
if scout_tmp is not None:
    if not scb and not sce:
        scout_fail_reason = 'absent'
    elif len(scb) != 1 or len(sce) != 1:
        scout_fail_reason = 'invalid_scout_sentinels'
    elif scb[0] >= sce[0]:
        scout_fail_reason = 'invalid_scout_sentinels'
    else:
        scout_lines = lines[scb[0] + 1:sce[0]]
        scout_text = '\n'.join(scout_lines).strip()
        if not scout_text:
            scout_fail_reason = 'empty_scout_json'
        else:
            try:
                scout_payload = json.loads(scout_text)
            except json.JSONDecodeError:
                scout_fail_reason = 'json_parse'
            else:
                if isinstance(scout_payload, dict) and isinstance(scout_payload.get('archetypes'), list):
                    write_scout_candidate(scout_payload)
                    scout_written = True
                else:
                    scout_fail_reason = 'invalid_archetypes_shape'
print(f'PLAN_LINES={len(plan_lines)}')
print(f'DIFF_LINES={plan_lines[-1].split(": ", 1)[1]}')
print(f'SUMMARY_WRITTEN={str(summary_written).lower()}')
if scout_tmp is not None:
    print(f'SCOUT_CANDIDATE_WRITTEN={str(scout_written).lower()}')
    if not scout_written:
        print(f'SCOUT_FAIL_REASON={scout_fail_reason or "invalid_scout"}')
