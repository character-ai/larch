Reviewing the cited locations to normalize overlapping findings accurately.
### FINDING_1: Over-scoped `safe_step_value` allowlist rewrite
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: nit
- **Concern**: The plan’s full-string `safe_step_value` allowlist rewrite duplicates `resume_hint_for` logic and is not required to fix silent `ITEMS_TOTAL=0` filing. The root failure is piping a heading-less `stall-recovery-bug-body.md` into `/issue`; existing case globs already require full-string match (e.g. `8a<script>` becomes `unknown`). A large allowlist rewrite plus two sanitizer harness cases roughly doubles test surface for secondary hardening without demonstrating a concrete bypass.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Innovation: Minimum-change path: wire `issue-input-file` in `stall-recovery.md` and add only the proven production gap (`bump-branch-guard`) to the existing case arm; defer full-string grammar rewrite unless a concrete bypass is demonstrated

### FINDING_2: Brittle negative grep on `stall-recovery-bug-body.md`
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Concern**: A proposed negative grep asserting that `stall-recovery-bug-body.md` does not appear on the same physical line as `/larch:issue --input-file` is fragile. Step 4 prose that legitimately warns not to use `stall-recovery-bug-body.md` on the filing line—a natural documentation pattern—would fail the harness even when wiring is correct.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Innovation: Drop the negative grep; keep the positive same-line `stall-recovery-issue-input.md` pin only

### FINDING_3: Wrong authority cited for `/issue` stdout → env normalization
- **Reviewer(s)**: Cursor-Innovation, Cursor-dyn-env-contract
- **Severity**: nit
- **Concern**: The plan cites `oos-pipeline.md` as the mirror for create-or-dedup normalization (`ISSUE_1_*` → `ISSUE_NUMBER` / `ISSUE_URL` in `stall-recovery-issue.env`), but that file only documents parsing indexed batch stdout keys and treating duplicate-of URLs as valid disposition evidence—it has no `ISSUE_NUMBER`/`ISSUE_URL` env-file mapping example and no `stall-recovery-issue.env` pattern. An implementer following the plan will search the wrong authority and may miss dedup fallback rules that live in `skills/issue/SKILL.md` batch stdout emission.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Innovation: Point normalization prose at `skills/issue/SKILL.md` batch output keys (`ISSUE_1_NUMBER`, `ISSUE_1_DUPLICATE_OF_*`) instead of `oos-pipeline.md`
  - From Cursor-dyn-env-contract: Cite `skills/issue/SKILL.md:332-344` for indexed batch stdout keys and `oos-pipeline.md:49` only for duplicate-of URL validity; describe `stall-recovery-issue.env` mapping as a new single-item consumer convention

### FINDING_4: `bump-branch-guard` omitted from production-token regression asserts
- **Reviewer(s)**: Cursor-dyn-subcommand-existence
- **Severity**: important
- **Concern**: Proposed production-token regression coverage omits `bump-branch-guard` even though plan grammar and ship-pr inventory include it. Today `safe_step_value` maps `bump-branch-guard` to `unknown` while `resume_hint_for` accepts it at `stall-recovery-report.sh:465`. After the planned grammar adds the token, case 2 only pins `10-max-retries`, `12d`, and `10-detached-head`, so `bump-branch-guard` can regress to `unknown` stall titles without failing CI.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-dyn-subcommand-existence: Add `bump-branch-guard` to production-token preservation asserts (direct `safe_step_value` or `issue-input-file` heading) alongside the listed hyphenated/suffixed tokens
