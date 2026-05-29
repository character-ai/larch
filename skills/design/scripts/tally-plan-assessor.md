# tally-plan-assessor.sh

Strict-majority WORSE tally across three assessor outputs; writes compact verdict file and `.env` sidecar with `QUALIFICATIONS_SUMMARY`.

- Accepts `ASSESSMENT` / `REASONING` / `QUALIFICATIONS` headers with mixed case, optional markdown bold, and `:` or `=` separators.
- On duplicate `ASSESSMENT` blocks, resets accumulated reasoning/qualifications before honoring the last parseable verdict.
- Normalizes `QUALIFICATIONS_SUMMARY` and WORSE justification to single-line, control-character-free excerpts before writing the `.env` sidecar.

## Majority rule

Let `(better, tie, worse)` count only parseable assessor outputs. `TIE` contributes to `EFFECTIVE_ASSESSORS` but never to the WORSE count.

- `WORSE` when `(0,0,3)`, `(0,1,2)`, `(1,0,2)`, `(0,0,2)`, or `(0,0,1)`.
- `NOT_WORSE` when `(2,1,0)`, `(0,2,1)`, `(1,1,1)`, `(0,2,0)`, `(0,1,1)`, `(0,1,0)`, or zero assessors parse successfully.

This is the strict-majority contract referenced by Step 3.6 and the offline harness.
