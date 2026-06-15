# Review Round 2

- Mode: `diff`
- 3 accepted, 4 rejected (2 neutral)

## Accepted Findings

### FINDING_3: `$BUG_TMPDIR` path is not machine-readable across Bash tool calls
- **Reviewer(s)**: dyn-bug-flow-output.txt
- **Severity**: important
- **Concern**: Step 2 creates `$BUG_TMPDIR` inside a Bash assignment but never emits a parseable `BUG_TMPDIR=<path>` KV line. Claude Code Bash fences do not preserve shell variables across calls, while Steps 4–7 depend on `$BUG_TMPDIR` for `Write`, `/issue` `--body-file` / `--sentinel-file`, `verify skill-called`, and `rm -rf`. An assignment-only fence returns empty stdout, so the orchestrator cannot reliably bind the random `mktemp` path before later steps.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-bug-flow-output.txt: After `mktemp`, print a KV line the orchestrator must parse and retain, e.g. `printf 'BUG_TMPDIR=%s\n' "$BUG_TMPDIR"`, and add an explicit Step 2 instruction to bind that path for all later steps (mirror `/research` Step 0 parsing of `SESSION_TMPDIR`).


### FINDING_7: Security triage runs after detailed body is written to world-readable `/tmp`
- **Reviewer(s)**: dyn-tmp-hook-output.txt
- **Severity**: important
- **Concern**: Security triage runs in Step 5, after Step 4 writes a full `bug-issue-body.md` (including **Root cause analysis** and **Evidence**) under `$BUG_TMPDIR` in world-readable `/tmp`. For security-sensitive reports, detailed exploit/weakness prose can sit on disk before the triage gate decides to abort; cleanup only happens if the agent follows Step 5 afterward.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-tmp-hook-output.txt: Move security triage to Step 1 (immediately after validating `$ARGUMENTS`) or early Step 3, before composing a detailed public-facing body; keep Step 5 as a fail-closed re-check immediately before the `/issue` Skill-tool call.


### FINDING_8: Step 4 lacks compose-time sanitization for public issue filing
- **Reviewer(s)**: dyn-tmp-hook-output.txt
- **Severity**: important
- **Concern**: **Evidence** and **Original report** instruct copying investigation output and user text into a body filed as a **public** GitHub issue. The skill does not require prompt-level sanitization of internal URLs, hostnames, or PII. `/issue`’s `redact secrets` backstop covers token-shaped secrets only (`SECURITY.md` documents non-coverage for internal URLs/PII); `skills/implement/references/execution-issues-tracking.md` requires dual-write sanitization before public filing.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-tmp-hook-output.txt: Add explicit compose-time rules in Step 4 (e.g., redact secrets, replace internal URLs with `<INTERNAL-URL>`, redact PII per `execution-issues-tracking.md`) and note that `/issue` redaction is defense-in-depth, not sufficient alone.


