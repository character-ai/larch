## Decision 1: Body-text scrubbing
- **Question**: Should anonymization scrub vendor/model substrings from the finding body text (mirror the dialectic protocol), or only remove the attribution line?
- **Resolution**: Strip the attribution line ONLY. Do NOT scrub body text. Legitimate `Codex`, `Cursor`, and `Claude` references inside finding/OOS bodies must survive unchanged. No vendor/model substring scrub.
- **Source**: user

## Decision 2: Attribution-line replacement
- **Question**: When removing voter-facing attribution, omit the `- **Reviewer**:` line entirely or replace it with a neutral placeholder token?
- **Resolution**: Replace with a neutral placeholder token. Keep a `- **Reviewer**:` line present in the voter-facing ballot, but set its value to a neutral, non-vendor-identifying token so block structure stays stable for parsers and fixtures. (Differs from the prior plan, which omitted the line.)
- **Source**: user

## Decision 3: Skills in scope
- **Question**: Which skills must be updated?
- **Resolution**: All three finding-adjudication voting paths: `/design` plan review, `/review` code review, and `/implement` Step 5 code review. Single shared change in `python/voting.py` plus per-skill ballot builders/tallies and the affected docs/references.
- **Source**: issue (explicit "across all three skills")

## Decision 4: Empirical measurement pass
- **Question**: Is the empirical self-vs-other YES-rate measurement over committed run logs part of this change?
- **Resolution**: Out of scope. The issue states it is "underway and may be attached as a follow-up comment." This design implements the structural mitigation only.
- **Source**: issue

## Decision 5: Scoring and competition must be unaffected
- **Question**: What must not break?
- **Resolution**: Proposer attribution must be retained out of band (a `proposer-map.tsv` sidecar) so `findings-classification.tsv`, the Reviewer Competition Scoreboard, and accepted/rejected/OOS audit/issue-filing artifacts keep correct proposer labels. Scores must match pre-change expectations for equivalent votes. Tallies must fall back to `voting.reviewer_for_block` when the sidecar is absent so legacy ballots and direct CLI callers still work.
- **Source**: issue + codebase (`python/voting.py`, `skills/shared/voting-protocol.md`)

## Decision 6: MAV and OOS coverage
- **Question**: Which ballot read paths must see the stripped ballot?
- **Resolution**: The main-agent-vote (MAV) fallback reads the same on-disk `ballot.txt` / `findings.md`, so the canonical file must be stripped on disk before any MAV branch can read it. Out-of-scope (`### OOS_N:`) rows carry the same attribution field and get identical neutral-token treatment.
- **Source**: issue

Record: 6 decisions resolved (2 user, 4 issue/codebase).
