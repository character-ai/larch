## Implementation Plan

**Goal**: Add mean (average) per-run cost to the "Cost by workflow" section in the `/report-tokens` skill.

**File to modify**: `skills/report-tokens/scripts/run-analysis.sh`
The Python analyzer is embedded as a heredoc. The relevant section is `print_analysis()`, specifically the per-workflow loop (around line 800-815).

**Change**: In the `for workflow in ("SIMPLE", "HARD", "unknown"):` loop inside `print_analysis`, the current output line is:
```python
print(
    f"- {workflow}: {len(rows)} run(s), total {dollars(sum(values))}, "
    f"median {dollars(statistics.median(values))}, max {dollars(max(values))}"
)
```

Add `mean {dollars(statistics.mean(values))},` between median and max:
```python
print(
    f"- {workflow}: {len(rows)} run(s), total {dollars(sum(values))}, "
    f"median {dollars(statistics.median(values))}, mean {dollars(statistics.mean(values))}, max {dollars(max(values))}"
)
```

`statistics.mean` is already imported at the top of the Python script.

**Also update the sibling `.md`**: The `run-analysis.md` sibling contract describes the output; update it to mention that per-workflow stats now include mean.

**Verification**: Run `/relevant-checks` on modified files.
