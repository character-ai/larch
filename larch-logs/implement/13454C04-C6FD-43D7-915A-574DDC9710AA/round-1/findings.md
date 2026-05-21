### FINDING_1: **architecture** `.claude/skills/audit-runs/SKILL.md:163-167` — After the branch, `### Title Format` defines `<ISO-timestamp>` as Pacific wall time with an explicit `-07:00`/`-08:00` offset, but the frontmatter example still uses the placeholder `audit_timestamp: <ISO-timestamp>` with no cross-reference, so the spec’s two visible “ISO” touchpoints are no longer obviously the same convention and an operator could still emit `Z`-suffixed UTC in YAML while matching the new title rules. **Suggested fix:** Tie the frontmatter field to the Title Format rule (rename the placeholder, e.g. to a Pacific-specific token, or add a short line immediately under `### Frontmatter` stating that `audit_timestamp` uses the same Pacific-offset minute precision as in `### Title Format`).
- **Reviewer**: dyn-impl-completeness-output.txt
- **Concern**: - **architecture** `.claude/skills/audit-runs/SKILL.md:163-167` — After the branch, `### Title Format` defines `<ISO-timestamp>` as Pacific wall time with an explicit `-07:00`/`-08:00` offset, but the frontmatter example still uses the placeholder `audit_timestamp: <ISO-timestamp>` with no cross-reference, so the spec’s two visible “ISO” touchpoints are no longer obviously the same convention and an operator could still emit `Z`-suffixed UTC in YAML while matching the new title rules. **Suggested fix:** Tie the frontmatter field to the Title Format rule (rename the placeholder, e.g. to a Pacific-specific token, or add a short line immediately under `### Frontmatter` stating that `audit_timestamp` uses the same Pacific-offset minute precision as in `### Title Format`).
- **Suggested revision**: Address the concern above.

### FINDING_2: [OUT_OF_SCOPE] Under `.claude/skills/audit-runs/`, the only runnable logic besides `SKILL.md` is [`scripts/test-audit-runs.sh`](.claude/skills/audit-runs/scripts/test-audit-runs.sh); there is no shell helper that writes `audit_timestamp` or builds the report title, so there is no stale `date … '…Z'` *producer* in this skill directory to update—the orchestration remains prompt-driven per the skill text. Concurrency `CUTOFF` examples correctly stay on `date -u` … `%SZ` for lexicographic comparison with GitHub’s `createdAt` ([`.claude/skills/audit-runs/SKILL.md:41-50`](.claude/skills/audit-runs/SKILL.md)).
- **Reviewer**: dyn-impl-completeness-output.txt
- **Concern**: - Under `.claude/skills/audit-runs/`, the only runnable logic besides `SKILL.md` is [`scripts/test-audit-runs.sh`](.claude/skills/audit-runs/scripts/test-audit-runs.sh); there is no shell helper that writes `audit_timestamp` or builds the report title, so there is no stale `date … '…Z'` *producer* in this skill directory to update—the orchestration remains prompt-driven per the skill text. Concurrency `CUTOFF` examples correctly stay on `date -u` … `%SZ` for lexicographic comparison with GitHub’s `createdAt` ([`.claude/skills/audit-runs/SKILL.md:41-50`](.claude/skills/audit-runs/SKILL.md)).
- **Suggested revision**: Address the concern above.

### FINDING_3: [OUT_OF_SCOPE] [`skills/fix-issue/scripts/test-find-lock-issue.sh`](skills/fix-issue/scripts/test-find-lock-issue.sh) still uses a mock title with `2026-05-20T19:30Z` (`~1306`); this file is outside the branch diff and `/fix-issue` exclusion is prefix-based, so it is example drift rather than a behavior regression relative to this change.
- **Reviewer**: dyn-impl-completeness-output.txt
- **Concern**: - [`skills/fix-issue/scripts/test-find-lock-issue.sh`](skills/fix-issue/scripts/test-find-lock-issue.sh) still uses a mock title with `2026-05-20T19:30Z` (`~1306`); this file is outside the branch diff and `/fix-issue` exclusion is prefix-based, so it is example drift rather than a behavior regression relative to this change.
- **Suggested revision**: Address the concern above.

### FINDING_4: [OUT_OF_SCOPE] code-quality: skills/fix-issue/scripts/test-find-lock-issue.sh:1306
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: [nit] Fixture audit title still uses UTC Z suffix Doc/test example drift vs new Pacific-offset reporting convention; no behavioral regression from prefix-based exclusion Optional align fixture to Pacific-offset title when touching fix-issue tests
- **Suggested revision**: Address the concern above.

### FINDING_5: [OUT_OF_SCOPE] code-quality: skills/fix-issue/scripts/test-find-lock-issue.sh:1306
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [nit] Fixture audit report title still uses 2026-05-20T19:30Z. Human readers see divergent examples from the updated audit-runs spec; tests remain valid. Update fixture to Pacific-offset example in a separate change.
- **Suggested revision**: Address the concern above.

### FINDING_6: code-quality: .claude/skills/audit-runs/SKILL.md:163-167
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [nit] audit_timestamp placeholder does not explicitly reference the Title Format Pacific-offset rule. Editors may assume audit_timestamp is still UTC Z or an unconstrained ISO string. Add one explicit cross-reference that audit_timestamp matches the Title Format Pacific-offset minute precision.
- **Suggested revision**: Address the concern above.

### FINDING_7: correctness: .claude/skills/audit-runs/SKILL.md:146
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [important] PDT/PST examples share date 2026-05-20 with -08:00 labeled PST; US Pacific is on DST in late May so PST is not in effect. An operator filing on a May date copies the PST example and writes -08:00 for a time that should be -07:00, misrepresenting the audit instant in the title/frontmatter. Use a winter-only date for the -08:00 PST example (or state explicitly that the PST line is format-only and not valid for May in Pacific).
- **Suggested revision**: Address the concern above.

### FINDING_8: risk-integration: .claude/skills/audit-runs/SKILL.md:23-27
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [important] Args still say since <ISO-timestamp> while Title Format defines ISO-timestamp as Pacific-only. Operator or implementer may apply the wrong timezone convention to since filters vs report titles or frontmatter. Qualify since as an ISO8601 instant comparable to mergedAt (Z or explicit offset) and state it is not tied to the Pacific title convention; or rename the title placeholder to avoid collision.
- **Suggested revision**: Address the concern above.

### FINDING_9: risk-integration: .claude/skills/audit-runs/scripts/test-audit-runs.sh:129-190
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [latent] No test locks 'since last audit' ignoring audit_timestamp Future SKILL/script change could compare audit_timestamp to mergedAt or parse the wrong field; CI would still pass Extend Test 7 (or add case) with valid last plus bogus audit_timestamp; assert last_pr unchanged
- **Suggested revision**: Address the concern above.

### FINDING_10: risk-integration: .claude/skills/audit-runs/scripts/test-audit-runs.sh:76-91
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [nit] since <ISO> tests only cover Z suffix Offset form accepted by regex is untested; regex regression could slip Add one parse_since_ts assertion for ...-07:00 input
- **Suggested revision**: Address the concern above.

