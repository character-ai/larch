### FINDING_3: [OUT_OF_SCOPE] Allowlist still permits multi-segment `*` paths vs “single asterisk segment” contract
- **Reviewer(s)**: cursor-specialist-correctness-output.txt
- **Concern**: Contract text implies a single `*` segment, but the allowlist/glob behavior can still admit rows with multiple `*` segments (e.g. `a*b*c.txt`), with broader glob expansion than a strict single-`*` grammar; treated as latent / pre-existing, not introduced by the hardening alone.
- **Suggested revision**: Optional follow-up only: enforce single-`*` shape or stricter path grammar if product intent requires it.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0 Result=exonerated

### FINDING_5: [OUT_OF_SCOPE] Reviewer clarifications (harness mechanics, fixtures, diff scope)
- **Reviewer(s)**: dyn-test-isolation-output.txt
- **Concern**: Out-of-scope notes from the same source: test 14’s `LARCH_VERIFY_MANIFEST=… cmd` form does not persist in the parent shell and is not the cross-case leakage mechanism when the variable is not exported from outside; `bad_manifest` / `run_bad_chars` live under `mktemp` `$TMP` with the same `EXIT` cleanup pattern as other cases; synthetic manifest header/column order matches `docs/run-logs-required-files.tsv:1`; branch diff also carries orthogonal `larch-logs/implement/...` metadata noise relative to verifier-focused review.
- **Suggested revision**: No in-scope change required from these observations alone; optionally keep diff hygiene separate from verifier changes if maintaining review signal.
```

Vote tally: YES=0 NO=3 EXON=0 JUDGE_ERROR=0 Result=rejected

