Quick mode — Claude-only plan review.

- FINDING_1 (Medium): Impure-attestation lines may leak into `findings.md` after collapse — strip step matches only exact token; old repair path called `drop_impure_empty_merge_attestation_lines` on the file unconditionally.
- FINDING_2 (Low): `mv -f "$cand" "$agg_dest"` is a self-move (no-op on Linux mv, error on BSD mv); drop the line on the success path.

OOS:
- OOS_1: Doc-code mismatch — `aggregate-findings.md` documents narrow-trigger retry as keying only on `preamble_finding_substring`, but the regex in `_agg_pipeline_for_candidate` also matches `empty_merge_from_nonempty_input`. Cleanup affects which validator branches emit which tokens; doc-code alignment is a useful follow-up but out of scope here.
