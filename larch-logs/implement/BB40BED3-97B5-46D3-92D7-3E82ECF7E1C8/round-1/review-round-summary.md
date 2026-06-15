# Review Round 1

- Mode: `diff`
- 4 accepted, 8 rejected (2 neutral)

## Accepted Findings

### FINDING_12: **security** `skills/bug/SKILL.md:17,119-123` — `/bug` always turns a bug report into a public `/issue` call, but it has no guard for reports or investigation results that indicate a security vulnerability. This conflicts with `SECURITY.md:14-18` and `SECURITY.md:24`, which say security vulnerabilities must not be opened as public GitHub issues or filed via `/issue`. **Suggested fix:** Add a Step 1 or pre-Step-5 security triage. If the report or root-cause evidence is security-sensitive, abort public issue filing and direct the operator to the private SECURITY.md disclosure flow.
- **Reviewer**: codex-specialist-edge-cases-output.txt
- **Concern**: - **security** `skills/bug/SKILL.md:17,119-123` — `/bug` always turns a bug report into a public `/issue` call, but it has no guard for reports or investigation results that indicate a security vulnerability. This conflicts with `SECURITY.md:14-18` and `SECURITY.md:24`, which say security vulnerabilities must not be opened as public GitHub issues or filed via `/issue`. **Suggested fix:** Add a Step 1 or pre-Step-5 security triage. If the report or root-cause evidence is security-sensitive, abort public issue filing and direct the operator to the private SECURITY.md disclosure flow.
- **Suggested revision**: Address the concern above.


### FINDING_15: **correctness** `skills/bug/SKILL.md:153-164` — Step 6 ends with “surface the failure and **stop** without claiming an issue was filed,” but Step 7 is an unconditional numbered step that always runs `rm -rf "$BUG_TMPDIR"` and tells the agent to “Report the issue URL selected in Step 6.” That conflicts with the anti-halt banner (line 19), which pushes continuation after `/issue` returns, and with no explicit carve-out such as “skip Step 7 on failure.” An agent can reach Step 7 after a failed `/issue` or `VERIFIED=false`, delete the scratch dir, and still try to report a URL that was never bound. **Suggested fix:** Add an explicit failure branch in Step 6 (e.g. “on failure, stop; do not run Step 7”) or a Step 7 entry guard (“only when Step 6 bound a report URL or dedup URL”). Optionally keep `$BUG_TMPDIR` on failure for debugging.
- **Reviewer**: dyn-bug-flow-output.txt
- **Concern**: - **correctness** `skills/bug/SKILL.md:153-164` — Step 6 ends with “surface the failure and **stop** without claiming an issue was filed,” but Step 7 is an unconditional numbered step that always runs `rm -rf "$BUG_TMPDIR"` and tells the agent to “Report the issue URL selected in Step 6.” That conflicts with the anti-halt banner (line 19), which pushes continuation after `/issue` returns, and with no explicit carve-out such as “skip Step 7 on failure.” An agent can reach Step 7 after a failed `/issue` or `VERIFIED=false`, delete the scratch dir, and still try to report a URL that was never bound. **Suggested fix:** Add an explicit failure branch in Step 6 (e.g. “on failure, stop; do not run Step 7”) or a Step 7 entry guard (“only when Step 6 bound a report URL or dedup URL”). Optionally keep `$BUG_TMPDIR` on failure for debugging.
- **Suggested revision**: Address the concern above.


### FINDING_2: correctness: skills/bug/SKILL.md:75-77
- **Reviewer**: codex-specialist-correctness-output.txt
- **Concern**: [important] /bug preserves user report text without neutralizing larch control markers. A report containing raw larch plan start/end markers can make /design route to already-planned via python/design_lifecycle.py:262. Escape larch marker comments in user-controlled issue-body sections before writing the body.
- **Suggested revision**: Address the concern above.


### FINDING_3: correctness: skills/bug/SKILL.md:117-121
- **Reviewer**: codex-specialist-correctness-output.txt
- **Concern**: [important] Derived issue titles can start with -- even though /bug treats all args as prose. A report beginning with --no-dedup can produce a title parsed by /issue as a flag or rejected option. Force option-safe titles, such as prefixing Bug: when the title would start with a hyphen.
- **Suggested revision**: Address the concern above.


