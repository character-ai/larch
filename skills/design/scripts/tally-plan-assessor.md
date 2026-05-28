# tally-plan-assessor.sh

Strict-majority WORSE tally across three assessor outputs; writes compact verdict file and `.env` sidecar with `QUALIFICATIONS_SUMMARY`.

- Accepts `ASSESSMENT` / `REASONING` / `QUALIFICATIONS` headers with mixed case, optional markdown bold, and `:` or `=` separators.
- On duplicate `ASSESSMENT` blocks, resets accumulated reasoning/qualifications before honoring the last parseable verdict.
- Truncates `QUALIFICATIONS_SUMMARY` to a single-line excerpt for safe Step 3.6 display.
