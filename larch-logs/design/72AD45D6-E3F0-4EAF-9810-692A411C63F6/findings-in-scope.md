### FINDING_1: Section 5 lint rows lack section 4 lint-field parity
- **Reviewer(s)**: Cursor-Arch
- **Severity**: major
- **Concern**: Section 5 lint-classified invariants still lack section 4 lint-field parity. When an invariant is classified `lint`, section 5 can include only normative invariant bullets while omitting the mechanical lint contract fields section 4 requires (what it flags, scan surface, backing issues, false-positive risk, suppression policy, baseline policy). An operator approving a lint-classified invariant from section 5 would get paste-ready normative text but not a paste-ready lint spec, repeating the original operator-must-expand-cryptic-output failure mode on a different artifact.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: When rewriting section 5 bullets, require lint-classified rows to carry the same lint contract fields as section 4 (what it flags, surface, backing issues, false-positive risk, suppression policy, baseline policy) in addition to the normative statement, boundary, always/never rule, and evidence check
  - From Cursor-Arch: Require lint-classified section 5 rows to include the same lint metadata bullets as section 4, plus the normative invariant content.

### FINDING_2: Carve-out should explicitly override readability-style.md Brevity axis
- **Reviewer(s)**: Cursor-Arch
- **Severity**: minor
- **Concern**: The proposal carve-out does not explicitly override `skills/shared/readability-style.md`. Line 10 still mandates reading that file before all user-facing prose, and its Brevity axis says to go shorter when unsure. The planned carve-out only says exactness beats brevity without naming the shared authority, so agents can still compress sections 4–6 after loading global brevity guidance.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: In the Step 4 carve-out near sections 4-6, add one sentence that proposal wording in those sections overrides the Brevity axis of skills/shared/readability-style.md while the rest of the report and chat narration stay under the existing brevity rules
  - From Cursor-Arch: In the Step 4 carve-out, state that sections 4-6 proposal wording overrides the Brevity axis of `skills/shared/readability-style.md`; keep sections 1-3 and 7 on the existing brevity rules.

---

**Merge notes (for voters, not machine output):**
- Both structured `FINDING_1`/`FINDING_2` blocks and the duplicate `## Findings` entries describe the same two behavioral risks; merged into two blocks.
- `Cursor-Arch` appears in both blocks (inventory satisfied).
- No `[OUT_OF_SCOPE]` items; no `LARCH_AGGREGATOR_EMPTY_MERGE_ATTESTED` token (findings present).
- Rejected/subsumed items (`invariants-file` append-ready text, FINDING_4, FINDING_5, OOS_1) were not promoted into new findings.
