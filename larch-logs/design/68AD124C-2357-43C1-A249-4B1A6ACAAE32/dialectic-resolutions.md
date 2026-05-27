## Dialectic Resolutions

Note on protocol: full external dialectic debate was abbreviated due to issue #2995 (Cursor narration-only outputs). With 5 of 10 debater slots structurally unable to produce substantive content, the orchestrator opted for a focused, evidence-based main-agent resolution that draws on the 4 sketch outputs already on file (Codex-Innovation, Codex-Pragmatic, Claude-Arch fallback, Claude-Edge fallback) plus the user's Round 1 settled decisions. Per user direction at Step 2a.5 entry: "Run dialectic on the 2 truly-contested decisions only" — D1/D3/D4 marked bucket-skipped (user-settled), D2/D5 resolved via fallback-to-synthesis with rationale.

---

### DECISION_1 — Verdict file location

- **Resolution**: top-level — `$DESIGN_TMPDIR/assessor-verdict-round-<N>.txt`
- **Disposition**: bucket-skipped
- **Why skipped**: User's Round 1 D2 explicitly says the verdict file must "flush with logs". `scripts/design-log-publish.sh` uses `find $DESIGN_TMPDIR -maxdepth 1 -type f` to harvest top-level files (verified at `scripts/design-log-publish.sh:274`). Subdirectory location would require concurrent changes to design-log-publish; top-level is the smaller-blast-radius choice. User decision is binding.

### DECISION_2 — Combine entry + dispatcher vs split

- **Resolution**: split — `assess-plan-round.sh` (entry orchestrator) + `dispatch-plan-assessors.sh` (cross-model panel launcher) + `tally-plan-assessor.sh` (verdict tally) + `snapshot-plan-round.sh` (snapshot + cursor I/O)
- **Disposition**: fallback-to-synthesis
- **Why fallback**: External adversarial debate skipped due to #2995. Main-agent resolution from sketch evidence: Codex-Pragmatic favors combine ("minimize"), but Claude-Arch and Claude-Edge both lean toward split, citing the existing `dispatch-plan-voters.sh` / `plan-review-loop.sh` / `tally-plan-review.sh` precedent and per-script offline harness convention. Anti-pattern #6 (no mechanical conflation of voter and assessor tally) reinforces tally-as-separate. Single-responsibility per script wins on testability and clarity; the file-count overhead is modest.
- **Thesis summary**: Combine — fewer files, less testing infra, simpler maintenance.
- **Antithesis summary**: Split — matches repo precedent (single-responsibility scripts), each script's offline harness can target one concern, future #2871 auto-loop integration has clean seams.

### DECISION_3 — Best-so-far guard vs prev-vs-current only

- **Resolution**: prev-vs-current only (with `plan.txt-original` as the third input to give assessors implicit cumulative-drift context)
- **Disposition**: bucket-skipped
- **Why skipped**: User's original problem statement specifies "previous round's plan" as the comparison anchor. The best-so-far insight (Codex-Innovation) is preserved as a noted alternative in the synthesis but does not override the user's explicit scope. The original-plan snapshot (`plan.txt-original`, also used by the user-specified 3-input scheme) gives assessors enough signal to detect cumulative drift without adding a separate "best" file.

### DECISION_4 — Verdict file format strictness

- **Resolution**: user-specified compact body — `NOT_WORSE` on line 1, or `WORSE: <brief justification — a few sentences>` (line 1 carries semantics)
- **Disposition**: bucket-skipped
- **Why skipped**: User's Round 1 D2 specifies this byte-for-byte. Tally parser tolerance (case-insensitive, markdown-strip per `lib-vote-tally.sh` precedent) is applied at INPUT parsing (raw assessor outputs), not OUTPUT formatting. Format strictness in the OUTPUT file is a contract for #2871 consumers and human readability; user's chosen format meets both.

### DECISION_5 — Render prompt: extend `render-voter-prompt.sh` vs new `render-assessor-prompt.sh`

- **Resolution**: new `skills/shared/scripts/render-assessor-prompt.sh` (separate script with its own grammar, sibling to `render-voter-prompt.sh`)
- **Disposition**: fallback-to-synthesis
- **Why fallback**: External adversarial debate skipped due to #2995. Main-agent resolution from sketch evidence: Claude-Arch leans toward extending `render-voter-prompt.sh` for reuse; Codex-Pragmatic and Claude-Edge implicitly favor a separate script. Anti-pattern #6 (different units of measurement — per-finding YES/NO/EXONERATE vs whole-plan binary) plus the existing voter renderer's coupling to `lib-vote-tally.sh`-shaped outputs tip the balance toward separation. A separate script keeps the voter renderer single-purpose and avoids "what does this prompt produce" mode-flag confusion. The small duplication is worth the clarity.
- **Thesis summary**: Extend render-voter-prompt — reuses vendor-neutral prompt synthesis machinery, less code duplication.
- **Antithesis summary**: New render-assessor-prompt — preserves single-responsibility, voter renderer not weighed down by assessor concerns, future maintainers see one script per output grammar.
