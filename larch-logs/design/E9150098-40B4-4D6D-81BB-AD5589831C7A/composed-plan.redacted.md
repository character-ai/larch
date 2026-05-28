## Plan

## Summary

Reconcile larch reference docs and contracts with the now-landed multi-round design plan-review loop (PR #3142 / INT-2871). Scope is narrowed to gaps that survived the integration: surface the structured `- **Severity**: important|latent|nit` field in Gate B presentation prose, document the patch-apply security surface introduced by `revise-plan-with-waterfall.sh`, enumerate per-round artifacts under `larch-logs/design/<RUN_ID>/plan-review/round-<N>/` in `docs/run-logs.md`, document the new env vars to match actual script validation, register a missing test harness, and add two prose-presence structure-test assertions. Pure documentation/configuration; no behavior changes.

## Files to modify/create

### UPDATED: `skills/design/references/plan-review.md`

- Replace the **Accepted FINDING_N template** byte-preserved block so it matches the actual emission in `skills/design/scripts/plan-review-loop.sh::emit_finding`. The template gains `- **Reviewer(s)**:`, `- **Severity**: important|latent|nit`, `- **Focus area**:`, and `- **Location**:` lines between `### FINDING_N:` and `- **Concern**:`. Keep the existing `- **Concern**:` and `- **Proposed resolution**:` lines and append a brief note that `- **Severity**:` defaults to `nit` when missing (mirrors the existing "Severity default" bullet under Multi-round loop).
- Replace the **Accepted OOS format** byte-preserved block so it matches `emit_oos`: `### OOS_N:`, `- **Description**:`, `- **Reviewer**:`, `- **Severity**:`, `- **Focus area**:`, `- **Location**:`, `- **Phase**: design`. Drop the obsolete `- **Vote tally**:` line (the loop does not emit it).
- Under **Multi-round loop**, add one bullet: `oos-accepted-design.md` accumulates across rounds within the loop via the in-script `_accumulate_round_oos` helper; it is overwritten when Step 3 re-enters from Gate C(c) per `approval-gates.md` State Invariant about no preserved findings across review runs.
- Add a one-line cross-reference under the Multi-round loop section: see `approval-gates.md` for the **Severity precedence rule** used by Gate B presentation.

### UPDATED: `skills/design/references/approval-gates.md`

- Extend **Severity classification rubric** with a normative precedence rule using an **all-or-nothing** policy: when every accepted in-scope finding block carries a `- **Severity**:` line, map `important → High`, `latent → Medium`, `nit → Low` for Gate B presentation. When any accepted finding lacks the `- **Severity**:` line, fall back to the existing Critical/High/Medium/Low rubric sourced from `- **Concern**:` text for **all** findings (no per-finding hybrid). Document both the all-or-nothing precedence and the legacy fallback explicitly so readers know which rule applies in which case.
- Update the Gate B `AskUserQuestion` question text to use the structured-severity bucket counts only when the structured field is present on every accepted finding, and to fall back to the Concern-text rubric counts otherwise. Header stays `"Plan findings"`. New text when structured: `"Plan review returned N findings (H high / M medium / L low). How would you like to handle them?"` (mapped from important/latent/nit). When falling back: keep the existing C critical / H high / M medium / L low format. The `Critical` bucket has no structured equivalent, so when structured-severity counts are used the question header drops the `C` column.
- Add a carve-out to **State invariants** Invariant about "No preserved findings across review runs": clarify that the invariant covers cross-Gate-C-re-run behavior only — within a single multi-round loop, `oos-accepted-design.md` accumulates across rounds and per-round forensics under `plan-review/round-<N>/` accumulate across rounds; Gate C re-entry overwrites both.
- Add a carve-out to **State invariants** Invariant about Gate B apply contract: the existing prose says Gate A/Gate C never auto-revise `plan.txt`. Add a sentence noting that the multi-round loop itself auto-applies accepted findings between rounds via `revise-plan-with-waterfall.sh`, bounded by `LARCH_DESIGN_ROUND_CAP` and `LARCH_DESIGN_CONVERGENCE_THRESHOLD`, and that this loop-internal mechanical revision is distinct from Gate B's user-driven apply contract.

### UPDATED: `skills/design/references/discussion-rounds.md`

- Under the post-plan discussion sub-round body **Inputs** section, augment the `accepted-plan-findings.md` bullet to note it is the **final-round** artifact of the multi-round loop. Cross-reference `plan-review.md` Multi-round loop section for full semantics. No other discussion-round behavior changes.

### UPDATED: `skills/design/references/flags.md`

- Add a new sub-section under **Plan-size thresholds (Step 2b.5)** (or as a peer section, whichever placement preserves the table-of-contents order) titled `## Multi-round loop env vars` with two normative rows, documenting **actual** `plan-review-loop.sh` argv validation behavior (no fallback-on-invalid, no clamping):
  - `LARCH_DESIGN_ROUND_CAP` — default `5`. When unset or empty, the SKILL.md launch line expands to `5`. Non-numeric or non-positive explicit values cause `plan-review-loop.sh` argv validation to exit `2`. The Step 3 review-round counter (tier-derived cap: SIMPLE = `3`, HARD = `5`) is a **separate** layer that limits Gate C re-entries — `LARCH_DESIGN_ROUND_CAP` is **not** clamped against the tier cap; the two layers compose.
  - `LARCH_DESIGN_CONVERGENCE_THRESHOLD` — default `3`. When unset or empty, the SKILL.md launch line expands to `3`. Non-numeric or negative explicit values cause argv validation to exit `2`. Bounds the per-round `ACCEPTED_COUNT` that, combined with zero `IMPORTANT_ACCEPTED_COUNT` across two consecutive non-degraded rounds, triggers convergence.
- Cross-reference `docs/configuration-and-permissions.md` Environment Variables section.

### UPDATED: `docs/configuration-and-permissions.md`

- Under the existing **Environment Variables** section, add two peers to the existing `LARCH_DESIGN_PLAN_SUMMARY_THRESHOLD` sub-section: `LARCH_DESIGN_ROUND_CAP` and `LARCH_DESIGN_CONVERGENCE_THRESHOLD`. Each sub-section documents the **default** value applied via shell expansion when the env var is unset or empty, the **fail-closed** behavior on invalid explicit values (`plan-review-loop.sh` argv validation exits 2; no silent fallback), and a one-line cross-reference to `skills/design/references/flags.md` and `skills/design/references/plan-review.md` Multi-round loop section. Note: `LARCH_DESIGN_PLAN_SUMMARY_THRESHOLD` normalizes invalid values silently (per its existing contract); the loop env vars do **not** share that normalization.

### UPDATED: `SECURITY.md`

- Add a paragraph documenting the patch-apply security surface introduced by `skills/design/scripts/revise-plan-with-waterfall.sh`. Cover:
  - LLM-authored unified diffs or `file-replacement` candidates applied byte-level to `$DESIGN_TMPDIR/plan.txt`.
  - Plan-file canonical-path constraint: `--plan-file` must resolve to `$DESIGN_TMPDIR/plan.txt` (basename `plan.txt`). Mismatch exits 2 before any launcher fires.
  - Pre-revision snapshot at `<plan-file>.before-revise` is created before any patch attempt. The snapshot intentionally lives **outside** the `plan-review/round-<N>/revise/` subtree — adjacent to the plan file — so revert remains a single-file rename. The snapshot is removed only on `REVISE_STATUS=ok`. On failure (`failed-no-patch`, `failed-validation`, `failed-apply`), the snapshot stays in place so the operator or loop driver can roll back.
  - Per-tier launcher timeout is bounded by `--timeout` (default 1800s) and forwarded uniformly to Codex, Cursor, and Claude launchers.
  - Launcher outputs, prompts, and candidate patches are confined to `$DESIGN_TMPDIR/plan-review/round-<N>/revise/`. Both the revise outputs and the adjacent rollback snapshot are allowlisted at design-log publish time per the existing publish-allowlist paragraph.

### UPDATED: `docs/run-logs.md`

- Under **design plan-review findings-classification.tsv**, add a new sibling sub-section **design plan-review per-round artifacts** that lists **representative** artifacts produced under `larch-logs/design/<RUN_ID>/plan-review/round-<N>/`. State explicitly that this enumeration is a representative selection — `scripts/lib-design-round-artifacts.md` is the **authoritative** allowlist for the complete file set, and `SECURITY.md` publish-allowlist paragraph covers the design-log publish enforcement.
- Group representative artifacts by producer:
  - Findings: `findings.md`, `findings-in-scope.md`, `findings-oos.md`, `findings-classification.tsv`.
  - Voting: `accepted-plan-findings.md`, `rejected-findings.md`, `oos.md`, `oos-accepted-design.md`, `ballot.txt`, `voting-tally.md`.
  - Manifests & voter diagnostics: `plan-review-slots.ndjson`, `plan-voter-slots.ndjson`, `scout-plan-manifest.json`, `*-vote-output.txt`, `voter*-diag.txt`, `plan.txt` snapshot.
  - Loop forensics: `round-summary.env`.
  - Revise sub-tree (`round-<N>/revise/`): `codex-output.txt`, `cursor-output.txt`, `claude-output.txt`, `revise.env`, `prompt.txt`, `*-candidate.patch`.

### UPDATED: `docs/installation-and-setup.md`

- Add a short note (`### SIMPLE-tier `/design` cost` or equivalent sub-section under existing installation/setup prose) explaining that with the multi-round loop landed, `/design --simple` now runs the full plan-review panel and up to `LARCH_DESIGN_ROUND_CAP`-bounded inner rounds with the plan-revision waterfall. Real-world runs therefore take roughly tens of minutes (panel size and number of inner rounds are operator-tunable via the env vars; the Step 3 review-run counter caps Gate C re-entries separately at the tier-derived cap of `3` for SIMPLE). Cross-reference `docs/configuration-and-permissions.md` for the env var contracts.

### UPDATED: `agent-lint.toml`

- Add `scripts/test-revise-plan-with-waterfall.sh` and its sibling `scripts/test-revise-plan-with-waterfall.md` to the same registration block that already covers `scripts/test-design-multi-round-integration.sh` and `scripts/test-dispatch-plan-voters.sh`. Use the same Makefile-only or default category as the sibling rows so the comment block stays accurate.

### UPDATED: `scripts/test-design-structure.sh`

- Add one structure-test assertion: `approval-gates.md` Severity classification rubric block contains the literal substrings `important → High`, `latent → Medium`, `nit → Low` AND a sentence indicating Concern-text fallback applies under the all-or-nothing precedence rule when the structured `- **Severity**:` line is absent on any accepted finding.
- Add one structure-test assertion: `plan-review.md` Accepted FINDING_N template block contains **all six** required field labels: `- **Reviewer(s)**:`, `- **Severity**:`, `- **Focus area**:`, `- **Location**:`, `- **Concern**:`, and `- **Proposed resolution**:`. This catches removals or renames of any field that Gate B presentation depends on.
- Use unique check identifiers consistent with the existing numbering style in the file (e.g., a `# Check FINDING_2667` or `# Check 22 (#2667)` token); do not renumber existing checks.

## Approach

1. Pure documentation/configuration changes. No behavior changes. No new scripts.
2. Each `### UPDATED:` surface is grounded in inspection of the currently landed code (`plan-review-loop.sh::emit_finding` / `emit_oos`, `lib-design-round-artifacts.sh`, `revise-plan-with-waterfall.sh`, existing `approval-gates.md` and `plan-review.md` content). Env-var docs describe the **actual** argv validation contract (exit 2 on invalid; empty/unset takes the default; no clamping); no behavior-implying fallback claims.
3. Drift mitigation: the two new structure-test assertions catch future regressions of the severity-precedence prose and the FINDING_N template field set. CI's existing structure-test framework runs these on every PR.
4. Stylistic constraints honored: no hardcoded counts in prose (e.g., do not hardcode "5 Cursor reviewers" — defer to `skills/shared/topology.tsv`); no line-number references in prose; refer by section header or symbol; no machine-local absolute paths.
5. Topology TSV is **not** modified. Inspection confirms `skills/shared/topology.tsv` carries panel-composition counts, not a script catalog; adding rows for `plan-review-loop.sh` or `revise-plan-with-waterfall.sh` would not fit the existing row schema. Original #2667 plan's directive on this is moot.

## Edge cases

- Severity field absent on **any** accepted finding in a round: Gate B uses the all-or-nothing rule and falls back to the existing Concern-text rubric (Critical/High/Medium/Low) for the entire findings set. No per-finding hybrid is documented. The precedence rule documents this explicitly so operators understand which rubric drives the question header text.
- `LARCH_DESIGN_ROUND_CAP` or `LARCH_DESIGN_CONVERGENCE_THRESHOLD` set to invalid values (non-numeric, non-positive for round-cap, negative for convergence-threshold): `plan-review-loop.sh` argv validation exits 2 and Step 3 short-circuits to Step 3b. Document this as fail-closed; the docs do not claim silent normalization.
- `LARCH_DESIGN_ROUND_CAP` set above the tier cap by the operator (e.g., `--simple` with `LARCH_DESIGN_ROUND_CAP=10`): both layers apply. The inner loop iterates up to `10`. The Step 3 review-run counter independently caps Gate C re-entries at `3` for SIMPLE. The two limits compose; neither clamps the other.
- `oos-accepted-design.md` cumulative artifact behavior on legacy single-pass plan-review runs (callers that omit `--round-cap`): the loop runs one round and writes a non-cumulative `oos-accepted-design.md`; the within-loop cumulation prose remains correct because one-round = trivially-cumulative.

## Failure modes

1. **Doc-prose drift between the two reference files.** `approval-gates.md` and `plan-review.md` both touch the Severity field semantics. Even with the new structure-test assertion, the human-readable prose can diverge over time. **Earliest signal**: operator confusion in Gate B paths; CI structure-test still green. **Mitigation**: the new severity-precedence assertion pins the precedence terms in `approval-gates.md`; the new FINDING_N template assertion pins the full six-field set in `plan-review.md`. Together they catch most renames or precedence inversions.
2. **`docs/run-logs.md` representative list drifts from `scripts/lib-design-round-artifacts.sh` allowlist.** Future allowlist changes (new patterns or removed basenames) are not auto-reflected. **Earliest signal**: post-merge operator notices a committed log artifact that the doc does not mention. **Mitigation**: the prose explicitly states the enumeration is representative and cross-references `scripts/lib-design-round-artifacts.md` as authoritative; future contributors editing the allowlist see the doc-cross-link contract in `.claude/rules/drift-prone-prose-in-docs.md`.
3. **`SECURITY.md` patch-apply paragraph drifts from `revise-plan-with-waterfall.sh` behavior.** Future patch-format or snapshot-path changes can invalidate the prose. **Earliest signal**: a follow-up PR adds a new patch format or relocates `.before-revise`. **Mitigation**: keep the paragraph narrow (canonical-plan-file check, snapshot lifecycle including the adjacent-snapshot rationale, allowlisted output directory) and rely on the existing structure-test patterns for `revise-plan-with-waterfall.md` sibling-doc invariants.

## Testing strategy

- **Mechanical**: `scripts/test-design-structure.sh` gains two new prose-presence assertions; the existing harness invocation in CI exercises them on every PR.
- **Manual smoke check after merge**: run `/design --simple` on a synthetic issue, confirm Gate B presents the structured severity buckets when accepted findings carry the `- **Severity**:` field, and confirm the question header text matches the documented form.
- **Cross-doc grep checks** (one-time, performed by the implementer before merging):
  - `command grep -n 'important → High' skills/design/references/approval-gates.md` returns a hit.
  - `command grep -n 'Reviewer(s)' skills/design/references/plan-review.md` returns a hit inside the FINDING_N template block.
  - `command grep -E 'codex-output.txt|revise.env' docs/run-logs.md` returns hits inside the new per-round artifact section.
- **No new behavioral tests**. The loop / waterfall / Gate B presentation code is already covered by the landed Piece 2 harnesses.

## Acceptance

- `skills/design/references/plan-review.md` FINDING_N template lists `- **Reviewer(s)**:`, `- **Severity**:`, `- **Focus area**:`, `- **Location**:` plus the existing Concern and Proposed resolution lines.
- `skills/design/references/plan-review.md` OOS_N template matches the actual `emit_oos` output (Description / Reviewer / Severity / Focus area / Location / Phase).
- `skills/design/references/plan-review.md` Multi-round loop section documents `oos-accepted-design.md` within-loop cumulation and the Gate C re-run overwrite behavior, with a cross-reference to `approval-gates.md` State invariants.
- `skills/design/references/approval-gates.md` Severity classification rubric documents both the all-or-nothing structured-field precedence (`important → High`, `latent → Medium`, `nit → Low`) and the Concern-text legacy fallback (applied to the entire findings set when any accepted finding lacks the structured field).
- `skills/design/references/approval-gates.md` Gate B `AskUserQuestion` text uses structured-severity bucket counts only when the field is present on every accepted finding and falls back to Concern-text rubric otherwise.
- `skills/design/references/approval-gates.md` State invariants carve out within-loop cumulation and loop-internal mechanical revision.
- `skills/design/references/flags.md` documents `LARCH_DESIGN_ROUND_CAP` and `LARCH_DESIGN_CONVERGENCE_THRESHOLD` with the actual argv-validation contract (defaults via empty/unset; invalid values exit 2; no clamping; Step 3 review-run counter is a separate layer).
- `docs/configuration-and-permissions.md` Environment Variables section gains sibling entries for the same two env vars with the same fail-closed contract.
- `SECURITY.md` includes the new patch-apply paragraph for `revise-plan-with-waterfall.sh`, with explicit prose for the adjacent `<plan-file>.before-revise` snapshot location outside the revise/ subtree.
- `docs/run-logs.md` lists representative per-round artifacts and points at `scripts/lib-design-round-artifacts.md` as the authoritative allowlist.
- `docs/installation-and-setup.md` notes the SIMPLE-tier cost change.
- `agent-lint.toml` registers `scripts/test-revise-plan-with-waterfall.sh` and its sibling `.md`.
- `scripts/test-design-structure.sh` gains the two new structure-test assertions: severity-precedence prose in `approval-gates.md`, and the full six-field FINDING_N template label set in `plan-review.md`.
- `make lint` passes; `bash scripts/test-design-structure.sh` exits 0.

diff_lines: 235
