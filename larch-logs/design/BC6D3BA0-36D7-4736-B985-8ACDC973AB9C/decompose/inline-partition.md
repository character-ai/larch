## Pieces

### Piece 1: Core runtime stage
- Scope: python/larch/core/config.py, python/larch/cli.py, python/larch/issue/analyze_bugs.py
- Firm-headings: python/larch/core/config.py, python/larch/cli.py, python/larch/issue/analyze_bugs.py
- Acceptance: `python3 -m pytest python/tests/issue/test_analyze_bugs.py -q` passes; `python3 python/cli.py analyze-bugs runtime --help` exits 0.
- Dependencies: none
- Size estimate: ~520 lines

### Piece 2: Tests and SKILL.md
- Scope: python/tests/issue/test_analyze_bugs_runtime.py, .claude/skills/analyze-bugs/SKILL.md
- Firm-headings: python/tests/issue/test_analyze_bugs_runtime.py, .claude/skills/analyze-bugs/SKILL.md
- Acceptance: `python3 -m pytest python/tests/issue/test_analyze_bugs_runtime.py -q` passes; SKILL.md contains `--runtime-max` and `RUNTIME` tier.
- Dependencies: blocked-by Piece 1
- Size estimate: ~200 lines
