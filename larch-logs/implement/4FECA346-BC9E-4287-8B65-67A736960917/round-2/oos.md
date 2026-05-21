### FINDING_6: [OUT_OF_SCOPE] Historical CHANGELOG prose still references GO / auto-pick / old lock flows
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-security-output.txt
- **Concern**: Older changelog sections still describe GO tails, auto-pick, and related removed behavior; readers scanning only the changelog may infer current semantics incorrectly, and one note flags CHANGELOG as unchanged in the provided diff (release-time follow-up).
- **Suggested revision**: When cutting a release, add an explicit new changelog entry reflecting the contract change; optional broader editorial pass on historical entries is out-of-band for the code diff itself.
```

```text

Vote tally: YES=1 NO=0 EXON=1 JUDGE_ERROR=0 Result=exonerated

### FINDING_7: [OUT_OF_SCOPE] Stale comments in test-find-lock-issue.sh about eligibility scan / auto-pick-era fixtures
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-testing-output.txt
- **Concern**: Harness/fixture comment blocks (including around ~584–595) still reference an “eligibility scan” / auto-pick-era framing, causing doc drift for future readers triaging what production path is under test (assertions not implicated).
- **Suggested revision**: Reword comments to explicit-target eligibility language in a future cleanup PR.
```

```text

Vote tally: YES=1 NO=0 EXON=1 JUDGE_ERROR=0 Result=exonerated

