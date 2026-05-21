### FINDING_6: [OUT_OF_SCOPE] Historical CHANGELOG prose still references GO / auto-pick / old lock flows
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-security-output.txt
- **Concern**: Older changelog sections still describe GO tails, auto-pick, and related removed behavior; readers scanning only the changelog may infer current semantics incorrectly, and one note flags CHANGELOG as unchanged in the provided diff (release-time follow-up).
- **Suggested revision**: When cutting a release, add an explicit new changelog entry reflecting the contract change; optional broader editorial pass on historical entries is out-of-band for the code diff itself.
```

```text

Vote tally: YES=1 NO=0 EXON=1 JUDGE_ERROR=0 Result=exonerated


