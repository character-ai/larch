### [rejected] FINDING_12

### FINDING_12: **`risk-integration` (plan)** — **Latent** — [`skills/review-and-fix/scripts/review-and-fix.sh`](skills/review-and-fix/scripts/review-and-fix.sh) (`write_rejected_findings_aggregate`, ~397–451): The plan Part C text says concatenate each round’s **`rejected-findings-full.md`** when any round has full detail, and fall back to the bare ledger only when **no** round has a non-empty full file. The implementation, as documented in [`skills/review-and-fix/scripts/review-and-fix.md`](skills/review-and-fix/scripts/review-and-fix.md), uses **per-round** choice: full file if non-empty, else that round’s compact `rejected-findings.md`, whenever **any** round contributed to the aggregate. **Scenario:** A consumer that assumed “all sections are full prose once any full exists” may see a `## Round N` section that is still the compact ledger. **Suggested fix:** If strict plan fidelity matters, gate compact inclusion on the global “any full exists?” rule; if the mixed behavior is desired, align the written issue/plan with the implemented contract (already partly done in `review-and-fix.md`).
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: 2. **`risk-integration` (plan)** — **Latent** — [`skills/review-and-fix/scripts/review-and-fix.sh`](skills/review-and-fix/scripts/review-and-fix.sh) (`write_rejected_findings_aggregate`, ~397–451): The plan Part C text says concatenate each round’s **`rejected-findings-full.md`** when any round has full detail, and fall back to the bare ledger only when **no** round has a non-empty full file. The implementation, as documented in [`skills/review-and-fix/scripts/review-and-fix.md`](skills/review-and-fix/scripts/review-and-fix.md), uses **per-round** choice: full file if non-empty, else that round’s compact `rejected-findings.md`, whenever **any** round contributed to the aggregate. **Scenario:** A consumer that assumed “all sections are full prose once any full exists” may see a `## Round N` section that is still the compact ledger. **Suggested fix:** If strict plan fidelity matters, gate compact inclusion on the global “any full exists?” rule; if the mixed behavior is desired, align the written issue/plan with the implemented contract (already partly done in `review-and-fix.md`).
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=1 EXON=1 NEUTRAL=1

### [rejected] FINDING_13

### FINDING_13: **`risk-integration`** — **Nit** — [`skills/review/scripts/test-review-core.sh`](skills/review/scripts/test-review-core.sh): Default harness stubs `REVIEW_CORE_EMIT_TALLY_SH` (`write_stubs` / `emit.sh`), so this suite never asserts that the **real** `review-core.sh → emit-tally.sh` path passes `--scout-status`, `--dynamic-slots`, and `--static-slot-count`. **Mitigation in-branch:** [`skills/review/scripts/test-dispatch-panel.sh`](skills/review/scripts/test-dispatch-panel.sh) and [`skills/review/scripts/test-emit-tally.sh`](skills/review/scripts/test-emit-tally.sh) cover the new flags and JSON shape. **Suggested fix:** Optional integration assertion with the real `emit-tally.sh` or a contract test on `review-summary.json` from an unst stubbed `review-core` slice.
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: 3. **`risk-integration`** — **Nit** — [`skills/review/scripts/test-review-core.sh`](skills/review/scripts/test-review-core.sh): Default harness stubs `REVIEW_CORE_EMIT_TALLY_SH` (`write_stubs` / `emit.sh`), so this suite never asserts that the **real** `review-core.sh → emit-tally.sh` path passes `--scout-status`, `--dynamic-slots`, and `--static-slot-count`. **Mitigation in-branch:** [`skills/review/scripts/test-dispatch-panel.sh`](skills/review/scripts/test-dispatch-panel.sh) and [`skills/review/scripts/test-emit-tally.sh`](skills/review/scripts/test-emit-tally.sh) cover the new flags and JSON shape. **Suggested fix:** Optional integration assertion with the real `emit-tally.sh` or a contract test on `review-summary.json` from an unst stubbed `review-core` slice.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=0 EXON=2 NEUTRAL=1

### [rejected] FINDING_16

### FINDING_16: code-quality: skills/review-and-fix/scripts/review-and-fix.sh:442-453
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [nit] render_rejected_findings_for_tally strips ## from Round headers in tally batch body. code-review-tally markdown loses explicit ## Round N markers vs prior cat of full files. Preserve markdown headings or use a dedicated plain-text label without rewriting ## lines.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=0 EXON=2 NEUTRAL=1

### [rejected] FINDING_6

### FINDING_6: **Latent** (`correctness`) — [`skills/review-and-fix/scripts/review-and-fix.sh:442-453`](skills/review-and-fix/scripts/review-and-fix.sh) — `render_rejected_findings_for_tally` only strips the top title when **line 1 exactly** matches `# Rejected Findings`. A leading BOM, blank line, or wrapper text leaves the heading duplicated inside the `code-review-tally` batch body and can break downstream “strip first heading” assumptions. **Suggested fix:** strip UTF-8 BOM and/or relax the header gate (e.g., skip until first `# Rejected Findings` before processing `## Round` lines).
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: 3. **Latent** (`correctness`) — [`skills/review-and-fix/scripts/review-and-fix.sh:442-453`](skills/review-and-fix/scripts/review-and-fix.sh) — `render_rejected_findings_for_tally` only strips the top title when **line 1 exactly** matches `# Rejected Findings`. A leading BOM, blank line, or wrapper text leaves the heading duplicated inside the `code-review-tally` batch body and can break downstream “strip first heading” assumptions. **Suggested fix:** strip UTF-8 BOM and/or relax the header gate (e.g., skip until first `# Rejected Findings` before processing `## Round` lines).
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=0 EXON=2 NEUTRAL=1

