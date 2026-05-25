Quick mode — Claude-only plan review.

- FINDING_1 (accepted): Plan must update `SECURITY.md` aggregator description — sentence at line 68 documents the current "attestation as guardrail when input had findings" behavior that this fix changes; AGENTS.md requires SECURITY.md updates on security-relevant behavior changes.
- FINDING_2 (accepted): Plan must decide whether `empty_merge_from_nonempty_input` progresses the outer Cursor → Codex → Claude waterfall (currently only `preamble_finding_substring` does); bug report's observation that Codex succeeded where Cursor failed is the recovery case.
- OOS_1 (filed): Future cleanup of `_attempt_attestation_repair` synthesis path that becomes dead code for input-nonempty after this fix.

No rejected findings.
