## Decision 1: which corpora get neutral-rate
- **Question**: Should neutral-rate cover both implement and design corpora, or implement-only?
- **Resolution**: Both. Design records also carry `outcome="neutral"` from plan-review TSVs. Match the existing baseline table split.
- **Source**: codebase

## Decision 2: severity source for important-reject-rate
- **Question**: Should "reviewer-claimed-important" use `body_severity` (reviewer's own severity tag) or modal voter severity?
- **Resolution**: `body_severity` normalized to "important" tier (blocker/critical/major/important). Issue text says "reviewer-claimed-important".
- **Source**: issue text + codebase

## Decision 3: impact on existing baseline table
- **Question**: Should the new metrics change the existing baselines that lump neutral+rejected?
- **Resolution**: No. Leave existing baseline tables unchanged. Add new dedicated sections below them.
- **Source**: KARPATHY minimal-change principle

## Decision 4: voter-calibration.py neutral data path
- **Question**: Can voter-calibration.py use existing `voter_agreement_rows_from_tsv` for neutral findings?
- **Resolution**: No — `voter_agreement_row_from_panel` returns None for neutral rows (line 182-183 in voting.py). Need separate TSV read counting YES votes on neutral rows. Will add a new helper in voter-calibration.py reading the TSV directly via `_dict_rows_from_tsv`. No changes to voting.py.
- **Source**: codebase

## Decision 5: realized-outcome tie-in
- **Question**: Is the analyze-issues realized-outcome section in scope?
- **Resolution**: Yes, as optional/degraded section in voter-calibration.py. Skips silently when gh is unavailable or corpus gate fails. Follows existing era-boundary degraded pattern.
- **Source**: user

## Decision 6: test harness scope
- **Question**: Which harnesses need updating?
- **Resolution**: Both test-fluff-analysis.sh (new neutral-rate + important-reject-rate fixture rows and assertions) and test-voter-calibration.sh (new per-voter false-negative assertions).
- **Source**: issue text + codebase
