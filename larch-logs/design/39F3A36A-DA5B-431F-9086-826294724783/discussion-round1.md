## Decision 1: Version filter date for --since-date
- **Question**: Should `--since-date` default to v51.3.19 (June 24, 2026, when new severity semantics landed) or v52.1.0 (June 26, 2026, when calibration-incentive landed)?
- **Resolution**: Default to v52.1.0 release date (2026-06-26). The issue explicitly says "the verdict should validate the incentivized signal, not today's flat one" — which requires post-calibration-incentive runs (v52.1.0+, not just v51.3.19+).
- **Source**: codebase (v52.1.0 = current release; v51.3.19+ has different but still un-incentivized severity signal)

## Decision 2: Verdict artifact location
- **Question**: New file or update existing docs?
- **Resolution**: New file `docs/ground-truth-verdict.md` committed to the repo.
- **Source**: user (Step 1c)

## Decision 3: CLI-enforced corpus gate
- **Question**: Should the code refuse to produce a verdict below the threshold?
- **Resolution**: Yes — `--min-runs N` (default 150) that exits non-zero when corpus has fewer than N qualifying runs.
- **Source**: user (Step 1c)

## Decision 4: Go/no-go threshold
- **Question**: Should the code encode a numeric alignment rate threshold for the go/no-go?
- **Resolution**: No — human judgment after seeing the rates. The command prints the report; the operator writes the decision into docs/ground-truth-verdict.md.
- **Source**: user (Step 1c)
