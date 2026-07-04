### Warnings

- **Step design Step 3.5 Gate B — gate-b-dedup anomaly-recovered (exit 0)**:
  ```
gate-b-dedup mechanical sweep (design-step35-settle.sh --site gate-b) removed 7 lines from
plan.txt as "duplicate lines": it deduplicates by exact line text with no Markdown code-fence
awareness, so repeated bare ``` closing fences and repeated ```bash opening fences (legitimate,
required once per code block) were stripped as if they were duplicate content. This corrupted
plan.txt's structure (unclosed code fences from the CLI-registration snippet through the end of
the Testing strategy section). Manually restored the 4 missing fence lines via Edit immediately
after the settle wrapper returned, before continuing. Did not re-invoke the settle wrapper
(would likely re-trigger the same stripping on the restored fences); instead ran
`python/cli.py plan validate` directly against the corrected plan.txt.
Likely a real bug in the underlying dedup-plan-lines tool; worth a follow-up /larch:bug filing
against gate-b-dedup's mechanical sweep to make it fence-aware (skip lines inside/bounding a
fenced code block from cross-block dedup).
  ```

- **Step design Step 3.5 Gate B (round 2) — gate-b-dedup anomaly-recovered (exit 0)**:
  ```
Same gate-b-dedup fence-stripping anomaly recurred identically on the round-2 settle invocation
(design-step35-settle.sh --site gate-b --round-num 2): "removed 7 duplicate line(s)" again,
stripping the same 4 fence markers restored after round 1. Confirms the bug is deterministic/
systematic (triggers on every settle call against a plan with 2+ similar fenced code blocks),
not a one-off fluke. Restored the fences again via Edit and re-validated directly with
`plan validate` (VALIDATE_STATUS=ok both times) without re-invoking the settle wrapper a third
time. Reinforces the /larch:bug follow-up recommendation from the round-1 note.
  ```
