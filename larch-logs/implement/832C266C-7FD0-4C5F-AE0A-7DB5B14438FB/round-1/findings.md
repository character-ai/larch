Here is the normalized aggregator output. Same behavioral risks merged: **FINDING_2+3** (weak pins in check (17)), **FINDING_6+8** (banner/`/larch:issue` ordering and pin soundness), **FINDING_9+10** (committed `larch-logs` run tree; merged heading keeps **`[OUT_OF_SCOPE]`** per your rule). **FINDING_11** kept separate as an observational out-of-scope note, distinct from the run-artifact scope finding.

---

### FINDING_1: Step 5c vs Gate C continuation banner punctuation mismatch
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: Step 5c continuation banner punctuation differs from the Step 5 Gate C continuation banner in the same file. This is low impact (operator-facing visual consistency only, not behavior). Match Continue-banner punctuation to the existing Gate C pattern, or normalize both.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.

### FINDING_2: Check (17) leaves key anti-halt / orchestrator-never prose unpinned in the Step 5b–5c window
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-testing-output.txt
- **Severity**: nit
- **Concern**: Check (17) does not pin ISSUES_* / sentinel / summary wording inside the Step 5b–5c window (structure reviewer), and does not pin **Why** / **How to apply** / **CI-backed** for orchestrator-never item 2 (testing reviewer). A shortened banner or deleted rationale could pass while weakening the regression signal the incident called for.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt, cursor-specialist-testing-output.txt: Address the concern above.

### FINDING_3: Anti-halt parenthetical skips intermediate Step 5c sub-steps (5c.2–5c.5)
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: Anti-halt parenthetical lists 5c.1→5c.6→5c.7 and omits 5c.2–5c.5. An orchestrator may still treat outputs after compose redact or plan-block-write as a natural stop because those sub-steps are not named in the enumerated chain, risking another summary-halt before publish/rename.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.

### FINDING_4: Check (15b) redundant with check (17) for overlapping substring
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: nit
- **Concern**: Check (15b) greps for 5c.7→6 on SKILL.md while check (17) already requires the full intra-Step-5 token that contains the same substring. That yields redundant CI signal: a future edit could satisfy (15b) with a stray 5c.7→6 mention outside the anti-halt line while breaking (17), or maintainers may think both checks guard distinct invariants.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.

### FINDING_5: Check (17) does not enforce continuation-banner vs `/larch:issue` ordering or tie `/larch:issue` to the banner line
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt, dyn-test-pin-soundness-output.txt
- **Severity**: important
- **Concern**: Check (17) only requires the banner and `/larch:issue` anywhere strictly between the `### 5b` and `### 5c` headings, so the banner could sit above the `/larch:issue` instructions and still pass, encouraging the wrong execution order relative to written Step 5b flow. Separately, `grep -Fq '/larch:issue'` over the whole window does not tie `/larch:issue` to the continuation banner because Step 5b prose already mentions `/larch:issue` multiple times anywhere in that window, so the banner could drop the `/larch:issue` call-out while the check still passes—contradicting the failure message that the banner window must name `/larch:issue`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.
  - From dyn-test-pin-soundness-output.txt: Pin a single literal that appears only on the banner line (for example `grep -Fq 'Continue to Step 5c IMMEDIATELY.** The \`/larch:issue\` Skill tool' "$SKILL_MD"` after a line-number guard, or `grep -F` a full one-line substring joining the banner prefix and `` `/larch:issue` ``), or split the file at the banner line with `grep -n` and assert `/larch:issue` on that same line.

### FINDING_6: Post-edit shell checks not provable from diff-only review
- **Reviewer(s)**: cursor-specialist-plan-fidelity-output.txt
- **Severity**: latent
- **Concern**: Plan acceptance requires three post-edit shell checks to pass; diff-only review cannot confirm `scripts/test-design-structure.sh`, `scripts/test-anti-improvised-wakeup.sh`, and `scripts/relevant-checks.sh` were run and succeeded on the final commit.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-plan-fidelity-output.txt: Address the concern above.

*(The source text also said to await or inspect CI, or attach command transcripts, showing those scripts pass before treating the plan as fully satisfied; that sentence lived only under **Concern**, not under **Suggested revision**, so it is not duplicated as a separate verbatim bullet.)*

### FINDING_7: [OUT_OF_SCOPE] Committed `/implement` run artifacts under `larch-logs/implement/832C266C-7FD0-4C5F-AE0A-7DB5B14438FB/`
- **Reviewer(s)**: dyn-test-pin-soundness-output.txt, dyn-scope-boundary-output.txt
- **Severity**: important
- **Concern**: The branch diff adds a full committed `/implement` run record (e.g. `manifest.json`, `parent-issue.md`, embedded plan copy, `plan-review-tally.json`) under `larch-logs/implement/`, which is outside a “three files / surgical documentation + pins only” surface and couples operator/run metadata to the same change set as the `/design` anti-halt edits; dyn-test-pin notes the same paths as unrelated to test-pin mechanics and possibly unintended to ship on `main`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-test-pin-soundness-output.txt: Address the concern above.
  - From dyn-scope-boundary-output.txt: Unless issue #2681 or `docs/run-logs.md` explicitly requires this run id to be committed with the fix, drop the entire `larch-logs/implement/832C266C-7FD0-4C5F-AE0A-7DB5B14438FB/` tree from the branch so the PR stays scoped to `skills/design/SKILL.md`, `skills/shared/orchestrator-never.md`, and `scripts/test-design-structure.sh`.

### FINDING_8: [OUT_OF_SCOPE] Observed limited change surface in core hunks (5b/5c flow aside from anti-halt pins)
- **Reviewer(s)**: dyn-scope-boundary-output.txt
- **Severity**: nit
- **Concern**: In the hunks for `skills/design/SKILL.md`, `skills/shared/orchestrator-never.md`, and `scripts/test-design-structure.sh`, Step **5c** items **1–7** (compose → redact → `plan-block-write.sh` → `REPO` resolution → `design-log-publish.sh` → rename) and Step **5b** `/larch:issue` + annotate sequencing are unchanged aside from the anti-halt paragraph, the new blockquote (prose and inline backticks only, no new fenced bash), the new `orchestrator-never.md` entry **2.** (documentation only), and check **(15b)** / **(17)** updates in `scripts/test-design-structure.sh` with no other check logic touched in the shown diff.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-scope-boundary-output.txt: Address the concern above.

---

**Merge log (for traceability, not raw transcripts):** FINDING_2+3 → **FINDING_2**; FINDING_6+8 → **FINDING_5**; FINDING_9+10 → **FINDING_7** (`[OUT_OF_SCOPE]` preserved on merged first line). **Severity** for **FINDING_5**: `important` > `latent` from latent (F6) + correctness-class (F8). **FINDING_1** and **FINDING_4** unmerged. **FINDING_11** kept as **FINDING_8** (distinct from FINDING_7: attestation vs artifact drop). Because one or more `### FINDING_N:` blocks exist, **`LARCH_AGGREGATOR_EMPTY_MERGE_ATTESTED` is not included.**
