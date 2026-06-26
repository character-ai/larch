## Proposed Design Outline

### Goals
- Add `analyze-issues verdict` CLI subcommand that filters ground-truth runs by `--since-date` and enforces a `--min-runs` corpus gate.
- Produce a committed `docs/ground-truth-verdict.md` file with the filtered report so operators can make the go/no-go call on token allocation (#4771).
- Document the new subcommand in `.claude/skills/analyze-issues/SKILL.md` and reference the verdict in `docs/point-competition.md`.

### Non-goals
- No automatic go/no-go decision in code; the operator writes the verdict judgment after reading the report.
- No changes to the ground-truth algorithm itself; only date-based corpus filtering is added.
- No pre-generating the verdict now; the corpus (v52.1.0+ runs) will accumulate before the operator runs the command.

### Approach sketch
- Add `since_date: datetime | None` parameter to `ground_truth_voter_calibration()` in `analyze_issues.py`; filter rows where `started_at < since_date` before outcome computation.
- Count unique qualifying run directories (not rows) for the `--min-runs` gate; exit non-zero below threshold.
- Add `verdict_main()` in `analyze_issues.py` wired to a new `analyze-issues verdict` dispatch in `python/cli.py`.
- The command accepts `--since-date YYYY-MM-DD` (default `2026-06-26`), `--min-runs N` (default 150), `--log-root PATH`, and `--out PATH` (optional; defaults to stdout).
- Operator runs the command, inspects output, writes the judgment, and commits `docs/ground-truth-verdict.md`.

### Surfaces in scope
- `python/analyze_issues.py` (ground_truth_voter_calibration, new verdict_main)
- `python/cli.py` (new `analyze-issues verdict` dispatch)
- `.claude/skills/analyze-issues/SKILL.md` (document new subcommand)
- `docs/point-competition.md` (brief reference to verdict gate)
- `python/test_analyze_issues.py` (corpus-gate and since-date filter tests)

### Open questions
- None.
