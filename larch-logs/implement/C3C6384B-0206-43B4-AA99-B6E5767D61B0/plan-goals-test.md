## Goal
Add behavioral rule suppressing grep-exit-1 transcript noise

## Implementation Plan
## Implementation Plan

### Goal
Suppress benign grep-exit-1 transcript noise by adding a behavioral rule
(Fix C) to KARPATHY_CLAUDE.md requiring that orchestrator-generated
grep/find probes use `|| true` or `|| echo 0`.

### Scope
The audit of local SKILL.md Bash blocks found only one grep call inside
a Bash fence (`if echo "$ERR" | grep -qiE ...`) and that is a legitimate
conditional where exit 1 IS the signal — no SKILL.md fix required. The
`grep -c . || echo 0` in `skills/implement/SKILL.md:1439` already has the
guard. Therefore only Fix C is needed.

### Files to modify
1. `KARPATHY_CLAUDE.md` — add new section "5. Exit-Code Safety for Bash
   Probes" citing the policy: orchestrator-generated grep-family and find
   probes must use `|| true` or `|| echo 0` to suppress false-positive
   Error rows in Bash() transcripts. Carve-out for `if grep -q ...`
   conditionals where exit 1 IS the signal.

### Implementation approach
- Append a concise new section to `KARPATHY_CLAUDE.md` after section 4.
- The section should: state the rule, give the pattern, give the
  carve-out, and cite the user goal ("no error messages in logs").
- Keep it terse (< 15 lines) consistent with the file's style.

### Verification
- Run `/relevant-checks` after the edit.
- Confirm `pre-commit` and `agent-lint` pass.
- The rule will take effect immediately for all future orchestrator runs.

### Edge cases
- `if grep -q PATTERN file; then` — exit 1 IS the branch condition;
  do NOT add `|| true` there. The rule applies only to probe-only
  invocations (e.g., `grep -c PAT FILE || echo 0`) where no-match is
  informational.
- `grep -q PAT FILE || echo "not found"` — acceptable; `echo` provides
  context without masking the condition.

## Test plan
(no test plan section in plan-file)
