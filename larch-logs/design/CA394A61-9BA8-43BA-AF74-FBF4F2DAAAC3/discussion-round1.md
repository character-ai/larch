## Decision 1: Strategy for the organic-data precondition gap
- **Question**: Zero `.digest.txt` artifacts exist under `larch-logs/` today, and no existing committed batch persists digest-vs-full-log size data (confirmed by reading `docs/run-logs.md`'s batch list, `execution-issues.ndjson` writers, and `checks_run_relevant.py` — the digest file lives only in ephemeral `$IMPLEMENT_TMPDIR/relevant-checks/` and is deleted at cleanup). The issue's literal precondition ("5+ real digests from committed logs") can never be satisfied by waiting alone. How should this cycle proceed: instrument now and measure later, run a synthetic benchmark now to close the loop immediately, or hold the issue with no code change?
- **Resolution**: Instrument now, measure later. Add minimal instrumentation so each real checks-repair-loop digest use (in `/implement` and `/review`, at the shared digest-generation point in `checks_run_relevant.py`) records its byte-size delta into a committed batch, plus a `token measure-*`-style aggregator (matching the `measure-panel-cost` / `measure-references-heatmap` precedent) that reports insufficient-data until >=5 samples exist and computes the delta once they do. This PR does not close #6164's go/no-go acceptance criterion — it unblocks it.
- **Source**: user

## Decision 2: Issue-closure / done-criteria handling
- **Question**: Should the implementing PR auto-close #6164 (`Fixes #6164`), or leave it open pending the real measurement?
- **Resolution**: Leave #6164 open. Its acceptance criteria ("a committed measurement", "a go/no-go decision") are explicitly data-gated and remain unmet by an infrastructure-only change. The issue's own text ("Independent; waits on organic failure data, not on another issue") indicates it is meant to be the long-lived tracker for the eventual measurement — do not spawn a separate follow-up issue. The implementing PR should reference (not close) #6164 and a run of the new aggregator should comment progress once enough samples accrue.
- **Source**: codebase (issue body text + repo accept-criteria/issue-tracking conventions)

## Decision 3: Instrumentation must be best-effort and content-free
- **Question**: What failure-handling and content constraints apply to the new instrumentation?
- **Resolution**: The recorded fact must be non-blocking (best-effort; a write/lock failure must not fail the parent checks-repair-loop dispatch, matching the existing `panel-prompt-sizes.tsv` telemetry convention) and must record only sizes/counts, never digest or log text, consistent with `larch-logs/` redaction discipline.
- **Source**: codebase

Record 3 decisions resolved.
