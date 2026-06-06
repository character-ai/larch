## Decision 1: Auth wiring location
- **Question**: Where should the Codex auth wiring live for the uncovered call sites?
- **Resolution**: New shared launcher script (launch-codex-research.sh-style helper encapsulating ephemeral CODEX_HOME prep + auth config args); route research fences and lint-fix-loop through it. run-negotiation-round.sh routing (launcher vs per-site) is an implementation decision for the plan.
- **Source**: user

## Decision 2: Sweep breadth
- **Question**: Is the in-scope call-site list exactly the four uncovered sites (codex-only)?
- **Resolution**: Broaden the sweep — wire the four uncovered sites AND add a lint/CI guard that flags new `codex exec` call sites lacking auth wiring (plus audit other surfaces, e.g. doc examples in run-external-agent.sh header). Codex-only; no Cursor changes.
- **Source**: user

## Decision 3: Lint-guard mechanics
- **Question**: Should the guard hard-fail or warn, and does it scan markdown fences?
- **Resolution**: Follow the established lint-bare-grep-probe.sh convention: static scan over shell scripts and orchestrator-facing markdown fences, wired into pre-commit + make lint, hard fail, inline `# lint-<name>: ok <reason>` suppression comments.
- **Source**: codebase

## Decision 4: Covered sites are out of scope
- **Question**: Should the 5 already-covered sites (launch-review.sh, launch-codex-ci.sh, launch-codex-implement.sh, check-reviewers.sh, review-and-fix.sh) be refactored onto the new launcher?
- **Resolution**: No. Non-goal — issue targets uncovered paths only; leave covered sites untouched to minimize regression risk.
- **Source**: codebase

## Decision 5: Hard constraints
- **Question**: What must not break?
- **Resolution**: (a) When OPENAI_API_KEY is unset/empty, every wired site must keep working via the ~/.codex/auth.json symlink path (current default behavior). (b) Bash 3.2 portability for all new/edited scripts. (c) lib-quiet.md FD-3 contract for any new script. (d) Existing covered sites' behavior unchanged. (e) run-negotiation-round.sh exit-code contract (3 = cursor auth preflight) preserved.
- **Source**: codebase
