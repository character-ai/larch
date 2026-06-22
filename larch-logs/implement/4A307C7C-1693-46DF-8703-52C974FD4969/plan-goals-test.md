## Goal
Implement issue #5022: [IMPLEMENTING] [BUG] Findings aggregator drops merge to un-deduped fallback on reviewer-slot mismatch.

## Implementation Plan
## Summary

The shared findings aggregator (`python/review_aggregate.py`, `review aggregate-findings`) discards an entire round's merge and degrades to **un-deduplicated reviewer findings** whenever the aggregator's merged output attributes a finding to a reviewer-slot name that does not byte-match the validator's `input_slot_set`. In a real `/implement` code-review run the merged output named slot `cursor-specialist-correctness` while the input attribution used the `-output`-suffixed spelling `cursor-specialist-correctness-output`; `_validate_aggregate_output` returned rc=2 (`unknown reviewer slot in merge output`). Because issue #4881 scoped the bounded validation-retry to the OOS-attribution class only (`_OOS_ATTRIBUTION_RC=5`), an rc=2 slot-name mismatch is **not** retried or self-repaired — it falls straight through to the un-deduped fallback with only a warning. Dedup/merge is silently lost for that round; duplicate findings reach the ballot un-merged. This is a robustness gap in the **same class** as #4994 (a vendor agent emitting a plausible-but-non-exact token that a strict validator rejects), but in the aggregator's reviewer-slot check rather than the structured-TSV field check.

This is **distinct from #5021** (which is about Step 18a `record-escalation` being called with an invalid trigger token in stall recovery — `python/stall_recovery.py` / `stall-recovery.md` / `SKILL.md`). This issue is in `python/review_aggregate.py`'s slot-name validation and the #4868/#4881 retry-scope interaction. Different file, different failure mode, different fix surface.

## Original report

Surfaced during `/implement --merge --emergency 4994` (run `595C1826-4CC7-450E-B7C4-2DE843A86F78`, which merged as PR #5013). Round 1 of the code-review panel logged one execution issue under **External Reviewer Issues**:

> **findings aggregator**: merged output failed validation; leaving `<TMPDIR>/round-1/findings.md` unchanged. See `round-1/aggregator-validate.stderr` in the committed run log.

The committed `round-1/aggregator-validate.stderr` contained exactly:

```
unknown reviewer slot in merge output: 'cursor-specialist-correctness'
```

The run still succeeded (review completed across 3 rounds, 9/15 findings accepted, CI passed, merged), so the impact was benign for this run, but the round-1 dedup/merge was discarded and the raw un-deduped findings were used instead. Issue #4994 itself flagged this aggregator-validation-failure-to-un-deduped-fallback as a separate, untracked sibling exec issue; this files the specific occurrence with a concrete root cause.

## Reproduction scenario

Not deterministically reproducible on demand because it depends on the aggregator agent (Cursor here) emitting a reviewer-slot spelling that differs from the input attribution. Observed scenario:

1. Run `/implement --merge <issue>` so the code-review panel dispatches specialist reviewer slots (e.g. `cursor-specialist-correctness`, surfaced in artifacts as `cursor-specialist-correctness-output`).
2. The round-1 aggregator (`review aggregate-findings`) merges the per-reviewer findings and emits a merged finding whose `Reviewer(s):` line names `cursor-specialist-correctness` (the bare slot, **without** the `-output` suffix that the input attribution carries).
3. `_validate_aggregate_output` builds `input_slot_set` from the input findings' reviewer-lines, normalizes each via `_normalize_slot`, and checks every output slot against it.
4. `_normalize_slot` only strips a trailing `(...)` parenthetical — it does not reconcile the `-output` suffix — so `cursor-specialist-correctness` is absent from `input_slot_set`.
5. The validator returns `2, "unknown reviewer slot in merge output: 'cursor-specialist-correctness'"`.
6. rc=2 is not `_OOS_ATTRIBUTION_RC` (=5), so per #4881 it is not retried; the aggregator degrades single-shot to the un-deduplicated input findings and appends the warning.

A focused unit reproduction: feed `_validate_aggregate_output` an input whose reviewer-line is `cursor-specialist-correctness-output` and a merged output whose reviewer-line is `cursor-specialist-correctness`; it returns rc=2.

## Expected behavior

A merged finding that attributes to a reviewer slot which is the **same slot** as an input reviewer (differing only by a known suffix like `-output` or other vendor-introduced elaboration) should be accepted, so the round's dedup/merge is preserved. At minimum, a slot-name mismatch should be **recoverable** (bounded retry with targeted "use the exact input slot names" repair feedback, or normalization that reconciles the known suffix), rather than silently dropping the whole merge to un-deduped findings.

## Observed behavior

- `_validate_aggregate_output` returns rc=2 with `unknown reviewer slot in merge output: 'cursor-specialist-correctness'`.
- rc=2 is not retried (only `_OOS_ATTRIBUTION_RC=5` is), so the merge is discarded.
- The round falls back to **un-deduplicated** reviewer findings; only an `execution-issues` warning records the loss.
- Net: duplicate findings across reviewers reach the ballot un-merged for that round; the operator sees only the warning, not which findings were affected.

## Root cause analysis

**Primary (high confidence): reviewer-slot name inconsistency the normalizer does not reconcile.**

- The validator (`python/review_aggregate.py:556-559`) requires every slot in the merged output, after `_normalize_slot`, to be present in `input_slot_set`.
- `_normalize_slot` (`python/review_aggregate.py:227-228`) is `re.sub(r"\s*\([^)]*\)\s*$", "", slot).strip()` — it only removes a trailing parenthetical. It does **not** strip a `-output` suffix or otherwise canonicalize vendor-elaborated slot names.
- `input_slot_set` (`python/review_aggregate.py:513-525`) is derived from the **input** findings' `Reviewer(s):` lines. Round-1 artifacts show both spellings coexisting: `cursor-specialist-correctness-output` (the suffixed form) and the bare `cursor-specialist-correctness`. The aggregator's merge output used the bare form; the input attribution carried `-output`; the two do not match after normalization.

**Secondary (high confidence): no recovery path for this failure class.**

- Issue #4881 (PR following #4868) deliberately scoped the bounded validation-retry to the OOS-attribution class only. The in-code comment at `python/review_aggregate.py:27-31` states: "the OOS-attribution failure class (#4868) is the only semantically retryable [class] ... [every other] semantic failure degrades single-shot (pre-#4868 behavior)."
- The retry is gated on `if validate_rc == _OOS_ATTRIBUTION_RC` (`python/review_aggregate.py:607`). An rc=2 unknown-slot failure therefore never retries and never gets repair feedback.
- The aggregator prompt already instructs the agent to "preserve every input reviewer slot in the merged output" (`python/review_aggregate.py:679,685`), so this is a vendor (Cursor) conformance gap — the agent renamed/abbreviated the slot despite the instruction, exactly the #4994 pattern.

**Uncertainty:** the exact input-vs-output provenance of the two spellings could not be fully reconstructed because the per-round aggregator tmpdir intermediates were cleaned at run end; the committed evidence shows both spellings present and the validator error naming the bare form. The fix direction (reconcile the suffix and/or make the failure recoverable) holds regardless of which producer introduced `-output`.

**Version note:** the failing slot-validation block is **byte-identical** between the active plugin cache `51.3.4` and current `origin/main` (verified by diff; the only `review_aggregate.py` delta between them is the #4996/#5004 forensics-pointer change, which is unrelated). So this is unfixed on current main, not a stale-cache artifact.

## Evidence

- `python/review_aggregate.py:556-559` — per-slot guard: `norm = _normalize_slot(slot); if norm not in input_slot_set: return 2, f"unknown reviewer slot in merge output: {slot!r}\n"`.
- `python/review_aggregate.py:227-228` — `_normalize_slot` strips only a trailing `(...)` parenthetical; no `-output`/suffix canonicalization.
- `python/review_aggregate.py:513-525` — `input_slot_set` built from input reviewer-lines via `_reviewer_line_slots` + `_normalize_slot`.
- `python/review_aggregate.py:27-31` — comment: OOS-attribution (#4868) is the only retryable class; all other semantic failures degrade single-shot (#4881).
- `python/review_aggregate.py:607` — retry gated on `validate_rc == _OOS_ATTRIBUTION_RC` (=5); rc=2 not retried.
- `python/review_aggregate.py:679,685` — aggregator prompt instructs "preserving every input reviewer slot in the merged output".
- Run log `larch-logs/implement/595C1826-4CC7-450E-B7C4-2DE843A86F78/round-1/aggregator-validate.stderr` — `unknown reviewer slot in merge output: 'cursor-specialist-correctness'`.
- Same run, round-1 artifacts: `cursor-specialist-correctness-output` (5 occurrences) and bare `cursor-specialist-correctness` (2 occurrences) both present, confirming the dual spelling.
- Related-but-distinct closed work: #4868 (OOS-attribution retry), #4881 (scoped that retry to OOS-attribution only — explicitly names "unknown reviewer slots" among the non-retried structural failures), #4890 (panel/retry follow-ups), #4996/#5004 (forensics-pointer round-stamping, not validation).

## Affected files

- `python/review_aggregate.py` — `_validate_aggregate_output` slot-name check (lines ~556-559), `_normalize_slot` (lines 227-228), and the retry-scope gate (lines 27-31, 607). Primary fix surface.
- `python/test_review_aggregate.py` — regression coverage for the chosen behavior (slot-name reconciliation and/or recoverable retry).
- Possibly the aggregator prompt scaffold in `python/review_aggregate.py` (lines ~673-690) if the fix includes enumerating exact input slot names / forbidding renaming, mirroring #4994 item 1.

## Suggested fix(es)

Mirror the #4994 tolerance approach. Options to weigh in `/design`:

1. **(Primary, low-risk) Reconcile the slot name in `_normalize_slot`.** Strip a trailing `-output` suffix (and apply the same normalization when building `input_slot_set` and when checking output slots) so `cursor-specialist-correctness` and `cursor-specialist-correctness-output` canonicalize to the same key. This recovers the merge without weakening the "every input reviewer must appear" invariant. Verify the upstream producer of the `-output` suffix so normalization is applied symmetrically on both input and output sides.
2. **(Defense-in-depth) Make the unknown-slot class recoverable.** Re-include the slot-name-mismatch failure in the bounded retry with a targeted repair prompt ("attribute findings using these exact input slot names: ..."), without reopening the broad retry that #4881 deliberately closed (scope the retry strictly to slot-name mismatches, not to all rc=2 structural failures).
3. **(Prompt hardening) Enumerate exact input slot names** in the aggregator prompt and forbid renaming/abbreviating them, the way #4994 item 1 hardened the reviewer TSV prompt.
4. **(Visibility) Surface which findings were lost.** When falling back to un-deduped findings, the warning should note that dedup was skipped for the round so the impact is not invisible.

Whatever is chosen must preserve the post-#4881 guarantee that arbitrary semantic failures do not burn the full retry budget, and must keep `python/test_review_aggregate.py` coverage intact.

## Open questions

- Which producer introduces the `-output` suffix, and is the canonical reviewer-slot identity the bare form (`cursor-specialist-correctness`) or the suffixed form? The fix should normalize toward the canonical one on both input and output sides.
- Should the recovery be normalization-only (accept the variant) or a targeted bounded retry (ask the agent to re-attribute with exact names), or both?
- Are there other vendor-introduced slot-name variants beyond the `-output` suffix (e.g., `-vote`, `-vote-output` seen in voter slots) that the same normalization should cover, and do any of those legitimately denote distinct slots that must NOT be collapsed?
- Should the un-deduped fallback emit a louder/aggregated signal (not just an `execution-issues` warning) so silent dedup loss is visible during a run?

## Test plan
(no test plan section in plan-file)
