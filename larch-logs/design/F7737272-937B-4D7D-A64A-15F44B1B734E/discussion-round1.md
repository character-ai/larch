## Decision 1: Round 1 demotion scope
- **Question**: Given thin design heatmap coverage (70 transcript runs / 9.5%) and unreliable implement read-attribution (max 4.6%, likely undercounted after the #6263 capture bug), how aggressive should this first evidence-gated demotion round be?
- **Resolution**: Design-focused. Demote only design eager references with strong never-read evidence and adequate design-side sample. Treat implement read-rates as not-yet-trustworthy and DEFER implement demotions to a later round once its capture/attribution is verified reliable. Round 1 may demote few — or zero — references if evidence is weak; do NOT force demotions to manufacture a change.
- **Source**: user

## Decision 2: Evidence requirement per demotion (hard constraint)
- **Question**: What evidence must justify each demotion?
- **Resolution**: Every demotion cites its `measure-references-heatmap` row (reads_observed / transcript_runs_observed). A reference qualifies only if it is (a) currently eager-loaded unconditionally on the normal/green path AND (b) never/rarely read per the heatmap. References already loaded conditionally (e.g. `validator-failure.md`, read only on validator defects → 1/70) are NOT candidates — their low read-rate is expected, not evidence of waste.
- **Source**: codebase + issue body

## Decision 3: Compaction-resilience preservation (hard constraint)
- **Question**: What must NOT be demoted regardless of read-rate?
- **Resolution**: Keep compaction-resilience duplication — anti-halt continuation blocks and NEVER blocks — eager per standing policy. Acceptance: no orchestrator halt-rate regression across the next 20 runs.
- **Source**: issue body

## Decision 4: Concrete demotion candidates (evidence, design skill)
- **Question**: Which design eager references qualify for demotion under the design-focused, evidence-gated scope?
- **Resolution**: Investigation of `skills/design/SKILL.md`'s eager closure (SKILL.md + 10 refs = the "11 eager files") against the 70-run heatmap found exactly TWO eager + genuinely never-read (~0/70) non-compaction-resilience candidates:
  1. `skills/shared/external-reviewers.md` — eager load site `skills/design/SKILL.md:112` (Step 0a degraded-tools gate) — ~0/70 reads — ~9,451 bytes (~2.4k eager tokens). The degraded-tools gate is Python-owned (`agent degraded-tools-gate`) and SKILL.md:113–122 already inlines all `STEP0_STATUS` branch handling; the wrapper itself prints the operator explanation block, so the agent never Reads the file on the green path. **Strongest candidate.**
  2. `skills/shared/session-setup-output.md` — eager load site `skills/design/SKILL.md:99` (Step 0a setup KVs) — ~0/70 reads — ~1,612 bytes (~430 tokens). The parse list is already inlined on the same SKILL.md line; the agent parses from wrapper stdout and never Reads the file.
- **Demotion mechanism**: reword/scope the SKILL.md:99 and :112 eager references so they are no longer eager-closure members per the closure scanner's directive detection (`scan_skill` in `python/larch/lint/lint_skill_closure_growth.py`) — convert to conditional-branch scoping (external-reviewers.md → the `needs-degraded-decision` branch) or a non-Read maintainer/contract pointer. Byte-preserve the referenced files themselves. Expected eager-closure drop ≈ 11,063 bytes (~2.8k tokens), zero behavioral change (files unread on green path). Verify the exact rewording actually drops closure membership and preserves any degraded-path contract before finalizing.
- **NOT candidates**: no eager ref is rarely-read (all measured ≥47%, floor `plan-review.md` 47%); `validator-failure.md` (1/70) is ALREADY conditional (loaded only under `VALIDATE_STATUS=defects-found` at SKILL.md:668).
- **Source**: codebase investigation + heatmap
