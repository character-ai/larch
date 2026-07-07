### FINDING_1: correctness: python/larch/design/plan_quality.py:577-585
- **Reviewer**: codex-specialist-correctness-output.txt
- **Concern**: [major] Trusted override authority hashes the whole plan, but several trusted rewrite paths can preserve oversize_override: operator without refreshing that hash. Operator overrides an oversized plan, a Gate B or discussion rewrite changes another line while preserving the trailer, and Step 5c publish sees SIZE_TRIGGER_FIRED=true because _trusted_oversize_override returns None. Sync authority after every trusted rewrite that preserves a previously trusted override, or store override authority independently from unrelated plan text bytes.
- **Suggested revision**: Address the concern above.


Vote tally: YES=1 NO=2 JUDGE_ERROR=0 Result=neutral Fileable=false

