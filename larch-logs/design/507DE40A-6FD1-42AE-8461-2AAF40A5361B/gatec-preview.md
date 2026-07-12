## Final Design Plan

The plan is very large. Showing the full plan body below.

## Plan

## Approach

Create a standalone pre-`/design` `/triage` stateful orchestrator that investigates an existing issue, produces bounded evidence, and updates only an eligible non-security issue after fail-closed checks.

Keep model-led diagnosis in `skills/triage/SKILL.md`. Put deterministic GitHub mutation, freshness and lifecycle checks, immutable-ref evidence inspection, outbound sanitation, probe execution, and postcondition verification behind typed Python CLI helpers.

`--report-only` is a hard no-mutation path: render evidence, diagnosis, verdict, missing evidence, and fix outline before terminal machine keys, but never invoke mutation, dependency, or follow-up filing paths. `/triage` never edits repository files or authors a `/design` plan.

### NEW: skills/triage/SKILL.md

- Define `/triage <issue-number> [--repo OWNER/REPO] [--report-only]`.
- Add the canonical stateful-orchestrator anti-halt banner near the top. After every child `Skill` call and numbered Bash helper, continue to the explicitly named next step unless this file directs non-sequential control flow.
- Validate one positive issue number, the optional repository slug, and known flags before scratch allocation.
- Fetch the target issue’s title, body, comments, state, URL, labels, `updatedAt`, and pull-request discriminator using read-only GitHub calls. Wrap issue payloads, content-bearing evidence, Git output, and probe output using `python/cli.py untrusted file-block` before model inspection.
- Add mandatory security gates immediately after initial issue fetch and immediately before every mutation, dependency operation, or `/issue` invocation. If the issue or gathered evidence is security-sensitive, or classification is uncertain, disarm the Write hook, print the existing `SECURITY.md` responsible-disclosure guidance, emit `TRIAGE_VERDICT=inconclusive`, `ISSUE_UPDATED=false`, and `TRIAGE_FAILURE=security-sensitive`, then stop without public mutation.
- Resolve the checkout origin slug and immutable `main` snapshot before investigation. Use a deterministic helper to resolve the fixed remote’s exact `refs/heads/main` commit, record that SHA in the report, and fail closed with inconclusive results if the exact main ref or object cannot be verified.
- When `--repo` differs from the checkout origin, do not inspect local `main`, the worktree, local logs, or local code. Do not create a temporary checkout or fetch arbitrary repositories. Restrict analysis to issue-linked GitHub metadata and explicitly validated cited refs, mark repository-code conclusions unverified, and end inconclusive without mutation, dependencies, or follow-ups.
- Create the canonical `/tmp` scratch directory only after the first security, repository-target, and main-snapshot gates pass. Add a token-scoped `Write` hook using the `triage` activation token; permit scratch artifacts only there and remove the activation sentinel on every terminal path.
- Treat the checkout as untrusted for evidence purposes: read current-main cited files, symbols, and line context only through the recorded immutable main commit, never through a feature branch or dirty worktree.
- Before proposing a mutable verdict, reject active protected lifecycle state:
  - Call `python3 python/cli.py issue title-eligibility`.
  - Refuse all mutations for clarify labels or valid/malformed `larch:plan`, pause, design, implement, or other protected lifecycle control blocks.
  - Permit replacement only of a syntactically validated helper-owned triage block; treat any other or malformed `<!-- larch:` marker as protected.
  - A title-only stale lifecycle prefix with no protected label or block is not an active lifecycle state: permit it only for an `already-fixed`, `invalid`, or `duplicate` close verdict, where title restoration is required. Do not use that exception for valid updates or dependency writes.
  - Render refusal in report-only output and otherwise emit inconclusive, `ISSUE_UPDATED=false`, and `TRIAGE_FAILURE=protected-state`.
- Investigate inline with a bounded evidence budget:
  - Prioritize explicitly cited run logs and files.
  - Inspect `execution-issues.ndjson`, `final-summary.md`, `manifest.json`, outcome, handoff, and cited code only when relevant.
  - Read current-main code through `triage inspect` and the recorded main SHA.
  - Read cited unmerged-branch evidence only through `triage inspect`, using the fixed checkout remote, a validated full commit SHA or `refs/pull/<positive-number>/head`, argument-vector execution, validated repo-relative or canonical `larch-logs/` paths, and capped output.
  - Record missing refs, unavailable objects, rejected paths, truncated output, omitted sources, and unflushed logs as evidence gaps rather than inferring contents.
- Verify whether behavior remains on the recorded main commit, whether a later cited change fixed it, and whether cited paths, symbols, and line references resolve. Label each conclusion as an observation or inference.
- Never execute issue-supplied reproduction commands verbatim. Route feasible reproduction through `triage probe`:
  - Allow fixed named local probes with validated argv, no shell, and bounded output.
  - Allow only explicitly named, fixed-destination, read-only external-tool probes through existing credential-safe launch paths. Forbid issue-supplied credentials, arbitrary commands, arguments, destinations, shell syntax, redirects, expansions, destructive operations, repository writes, and externally mutating calls.
  - Otherwise report the proposed reproduction as unexecuted evidence.
- Snapshot open issues, shortlist bounded plausible overlaps, inspect only bounded candidates, and classify dependencies as near-certain or uncertain.
- Compose a design-ready triage section for `valid` findings. Preserve the original report and all non-triage body content byte-for-byte; replace only a validated helper-owned triage section. Include summary, verified behavior, corrected root cause, immutable-main evidence, reproduction, scope split, missing evidence, and fix outline. Do not create a `larch:plan` block.
- Sanitize copied and generated outbound content before scratch write and again in mutation helpers: redact secrets, internal URLs, PII, and temporary paths; neutralize user-controlled `<!-- larch:` markers; permit only a separately synthesized validated triage marker.
- Map verdicts as follows:
  - `valid`: append or replace the helper-owned sanitized triage section and leave title and state unchanged.
  - `already-fixed` or `invalid`: add a sanitized verification comment, restore only permitted stale shared lifecycle title prefixes, and close as `NOT_PLANNED`.
  - `duplicate`: add a sanitized comment naming a verified different canonical issue, restore permitted stale lifecycle prefixes, and close as `NOT_PLANNED`.
  - `inconclusive`: make no GitHub mutation and state the evidence gap or safety gate.
- Outside `--report-only`, invoke `python3 python/cli.py triage apply --operator-invoked` with fetched `updatedAt` and required artifact paths. Never call it for `inconclusive`.
- Apply only near-certain dependencies after primary-update verification. Pass the latest verified issue `updatedAt` to `/block-issue` with `--operator-invoked` and triage-controlled freshness options; require the helper to recheck target freshness and protected state immediately before GraphQL mutation and to return a fresh verified timestamp after exact relation read-back. Process edges serially, advancing the expected timestamp only from verified read-back. Keep uncertain edges as recommendations only.
- Invoke `/block-issue` and `/issue` with canonical per-call anti-halt micro-reminders. For `/block-issue`, parse its verified machine result and require the exact blocked-by relation plus fresh timestamp. For `/issue`, parse `ISSUES_CREATED`, `ISSUES_FAILED`, and per-issue result keys; pass a caller sentinel path and run `python3 python/cli.py verify skill-called --sentinel-file <path>`. Abort follow-up processing if either check fails.
- File follow-up issues only through `/issue ... --operator-invoked`, never for public security findings.
- Emit rendered analysis before terminal machine keys. Use exactly:
  - `TRIAGE_VERDICT=<valid|already-fixed|duplicate|invalid|inconclusive>`
  - `ISSUE_UPDATED=<true|false>`
  - `TRIAGE_FAILURE=<none|security-sensitive|protected-state|foreign-repository|insufficient-evidence|validation|authorization|stale-snapshot|redaction|mutation|postcondition|dependency-postcondition>`
- Avoid success claims when mutation, child-skill verification, cleanup, freshness checks, or dependency read-back fails.

### NEW: python/larch/issue/triage.py

- Add typed `main(argv) -> int` entry points for `triage apply`, `triage probe`, and `triage inspect`.
- Validate issue numbers, repository slugs, verdicts, required body/comment inputs, canonical duplicate numbers, expected `updatedAt` timestamps, helper-owned triage block syntax, `--operator-invoked`, ref formats, and bounded paths.
- Implement `triage inspect` as the sole validated Git evidence surface:
  - Resolve `origin` and `refs/heads/main` to a full immutable SHA without using the worktree as evidence.
  - Fetch only the fixed origin’s validated main or cited full-SHA/`refs/pull/<N>/head` ref when necessary; never check out, reset, merge, or update a working branch.
  - Read requested paths only through `git show <immutable-sha>:<path>` after repo-relative or canonical-log path validation.
  - Cap returned content and emit machine-safe evidence-gap results for missing, unavailable, rejected, or truncated evidence.
- Require `--operator-invoked` for every non-dry mutation and call `check_live_mutation_auth(..., operator_mode=True)` before any GitHub call when that boundary is absent. Refuse absent authorization with zero GitHub calls.
- Read input artifacts only as regular, non-symlink files below the canonical triage temp root.
- Implement shared outbound sanitation modeled on `deps_audit._sanitize_outbound_body`: redact secrets, internal URLs, PII, and temporary paths; neutralize user-controlled larch markers; reject malformed or unauthorized helper markers; fail closed on sanitation failure.
- Re-read the issue immediately before every mutation and compare `updatedAt` exactly with the expected version. Reject missing, closed, pull-request, repository-mismatched, concurrently updated, active-lifecycle-protected, or security-classified targets.
- Classify title-only stale lifecycle prefixes separately from active protected lifecycle state. Permit them only in the close-verdict title-restoration sequence after confirming no protected label or block remains.
- Advance expected `updatedAt` only from each verified read-back. Apply compare-and-swap checks before body edit, comment creation, title restoration, and close operations.
- Implement idempotent verdict application:
  - For `valid`, preserve original content, replace only a validated triage section, and skip an identical result.
  - For close verdicts, avoid duplicate marker-keyed comments, restore only permitted lifecycle prefixes, and close with `NOT_PLANNED`.
  - For `duplicate`, require a different open-or-resolvable canonical issue in the selected repository before posting or closing.
- Re-read every mutated surface. Verify exact sanitized body or triage section, comment marker/content, title restoration, state, close reason where exposed, and fresh snapshot timestamp.
- Keep probes separate from mutation. Use no shell; scrub credentials and proxy variables for local probes; permit external probes only from a fixed definition table with fixed destinations and credential-safe launcher seams; cap and sanitize output; return a machine-safe rejected-probe result for unsafe input.
- Emit newline-free result keys and distinct nonzero codes for usage, authorization, stale snapshot, protected state, redaction, mutation, and postcondition failures.
- Use injected `Runner` seams for all `gh`, `git`, and probe subprocess calls.

### UPDATED: python/larch/issue/issue_block.py

- Require `--operator-invoked` and the live-mutation authorization boundary for blocked-by mutations.
- Add triage-controlled `--expected-updated-at` validation and a shared target precondition read that verifies repository, issue type/state, security classification, active protected lifecycle state, and exact timestamp before GraphQL mutation. Refuse title-only stale-prefix targets for dependency writes.
- Make malformed mutation payloads, absent requested edges, and missing relationship data fail closed.
- Re-read the exact blocked-by relation and target issue after mutation. Return nonzero unless the requested edge and fresh timestamp verify; emit the fresh verified timestamp only on success.
- Preserve existing machine-readable success behavior only after authorization, pre-mutation freshness checks, and exact read-back.

### UPDATED: skills/block-issue/SKILL.md

- Accept and forward `/triage`’s `--operator-invoked`, expected-timestamp, and triage-controlled dependency options without weakening ordinary `/block-issue` validation.
- Document that triage dependency writes require live authorization, immediate freshness/protected-state recheck, and exact edge read-back.

### UPDATED: python/larch/cli.py

- Register `("triage", "apply")`, `("triage", "probe")`, and `("triage", "inspect")` under the existing dispatcher.
- Keep the public process contract behind `python3 python/cli.py` with no script shim.

### NEW: python/tests/issue/test_triage.py

Cover:

- Argument, repository, verdict, artifact-path, helper-marker, canonical-duplicate, ref, and path validation.
- Missing `--operator-invoked` and authorization refusal with zero GitHub calls.
- Immutable-main resolution, fixed-remote fetch/show success, unavailable-main failure, rejected refs/paths, output caps, and proof that code evidence never reads the worktree.
- Initial and per-mutation `updatedAt` mismatch refusal, expected-version advancement after read-back, and no later mutation after mismatch.
- Security, protected-title, clarify-label, valid/malformed plan-block, pause/control-marker, foreign-repository, and title-only stale-prefix close paths.
- Secret, internal URL, PII, temporary-path, and user-supplied larch-marker sanitation; valid helper marker preservation; sanitation failure.
- Valid insertion, replacement, original-body preservation, idempotency, and read-back failure.
- Already-fixed and invalid comments, stale lifecycle-title restoration, `NOT_PLANNED` close, and postcondition checks.
- Duplicate canonical validation, marker-keyed comment deduplication, and close behavior.
- Local safe-probe allowlists, argv validation, shell-syntax rejection, bounded output, and fixed-destination external-probe acceptance/rejection through credential-safe launcher seams.
- Failure ordering, stable stdout grammar, inconclusive no-mutation output, and distinct exit codes.

### UPDATED: python/tests/issue/test_issue_block.py

- Cover missing operator authorization with zero GitHub calls.
- Cover dependency expected-timestamp mismatch and protected/security precondition failure before GraphQL mutation.
- Cover malformed mutation payloads, absent requested edges, failed read-backs, fresh timestamp output, and verified success.

### NEW: scripts/test-triage-structure.sh

Pin the prompt contract:

- Exact public arguments, five-value verdict grammar, rendered report-only analysis, and terminal failure grammar.
- Canonical anti-halt banner, per-child-call continuation reminders, `/issue` counter-plus-sentinel verification, and `/block-issue` verified-result continuation.
- Both security gates, `SECURITY.md` routing, and no public mutation for security-sensitive or uncertain reports.
- Untrusted-content wrapping for issue data, logs, Git output, code excerpts, and probe output.
- Immutable-main snapshot resolution, `triage inspect` fixed-remote fetch/show boundary, evidence caps, missing-evidence language, foreign-repository restriction, and inconclusive no-mutation handling.
- Validated ref/path handling, local safe probes, and fixed-destination credential-safe external probes.
- `--report-only` mutation prohibition, no code edits, and no plan authoring.
- Protected lifecycle title, label, and machine-block refusals, plus the narrow stale-prefix close restoration exception.
- Outbound redaction, control-marker neutralization, per-mutation snapshot comparison, and read-back verification.
- Verdict routing, dependency confidence split, latest timestamp forwarding to `/block-issue`, live dependency authorization, strict dependency verification, and follow-up filing through `/issue --operator-invoked`.
- Triage activation-sentinel creation and cleanup.

### NEW: scripts/test-triage-structure.md

- Document the structural harness, protected prompt contracts, direct invocation, and Makefile integration.

### UPDATED: skills/shared/subskill-invocation.md

- Add `skills/triage/SKILL.md` to the stateful-orchestrator anti-halt scope list.
- Document `/triage`’s mandatory `/block-issue` result parsing and `/issue` stdout-counter plus sentinel verification as concrete post-invocation checks.

### UPDATED: scripts/test-anti-halt-banners.sh

- Add `/triage` to the required orchestrator banner scope.
- Assert its canonical banner and child-skill continuation reminders.

### UPDATED: scripts/residual-bash-paths.txt

- Add the new structural harness to the residual Bash inventory with other test harnesses.

### UPDATED: Makefile

- Add `test-triage-structure`, place it in exactly one harness shard, and keep shard coverage valid.
- Keep the existing anti-halt target wired so its expanded scope runs in lint.

### UPDATED: agent-lint.toml

- Add `scripts/test-triage-structure.sh` and its Markdown sibling to the appropriate dead-script exclusions, using the established Makefile-only structural-harness comment pattern.

### UPDATED: scripts/deny-edit-write.sh

- Recognize the `triage` activation token.
- Preserve the fail-closed canonical `/tmp` policy and token isolation.

### UPDATED: scripts/deny-edit-write.md

- Document `/triage` as a consumer, its matcher, activation token, and scratch-only write boundary.

### UPDATED: scripts/test-deny-edit-write.sh

- Add triage-token activation, cross-token isolation, inactive, stale, repository-denial, and canonical `/tmp` allowance cases.

### UPDATED: README.md

- Add `/triage` to the primary workflow and issue-management feature summary.
- Add its invocation and concise behavior to the public skill catalog.
- State that it verifies and updates an eligible non-security issue before `/design`, while `--report-only` and `inconclusive` do not mutate GitHub.

### UPDATED: docs/skills.md

- Add the public skill index entry and reference section.
- Document verdicts, immutable-main evidence, evidence limits, security gates, foreign-repository limits, safe local and external reproduction boundaries, preserved-body triage sections, protected lifecycle-state refusal, stale-prefix close restoration, dependency freshness, child-skill verification, and machine output.
- Distinguish `/triage` from `/bug`, `/research`, and `/design`.

### UPDATED: AGENTS.md

- Add `skills/triage/SKILL.md`, triage inspect/probe/apply helpers, and the immutable-main evidence contract to the canonical-source list.

### UPDATED: SECURITY.md

- Extend the untrusted GitHub issue-content section to `/triage`.
- Document both security gates, private responsible-disclosure routing, prompt wrapping, protected-state refusal, immutable-main snapshots, outbound sanitation, and residual prompt-injection risk.
- Document the reproduction boundary: deterministic local probes plus narrowly named, fixed-destination, read-only external probes through credential-safe launchers; no issue-supplied shell commands, credentials, arbitrary destinations, destructive operations, repository writes, or externally mutating commands.
- Add triage body edits, comments, closes, title restoration, and dependency wiring to the scoped live-mutation authorization boundary.
- Document per-mutation and dependency freshness checks, fail-closed post-mutation verification, and the `--report-only` no-mutation guarantee.

## Edge cases

- The issue changes between fetch, body edit, comment, title restoration, close, dependency application, or dependency read-back.
- The issue is closed, deleted, transferred, or is a pull request.
- `--repo` differs from checkout origin.
- The fixed remote’s main ref is unavailable, stale, missing locally, or cannot resolve to the fetched immutable object.
- The report is security-sensitive or classification is uncertain.
- Cited logs exist only on an unmerged branch, are missing, truncated, rejected by validation, or were never flushed.
- A cited line moved while its symbol still exists.
- A reproduction suggestion contains shell syntax, unapproved authentication, an arbitrary network destination, or an unallowlisted executable.
- Multiple plausible duplicates exist without one canonical match.
- A dependency is plausible but not near-certain.
- The body contains a valid or malformed lifecycle machine block, untrusted larch marker, or prior helper-owned triage section.
- A title has only a stale lifecycle prefix versus an active lifecycle label or block.
- The body already contains the proposed triage section or a prior triage comment exists.
- The canonical duplicate equals the triaged issue.
- Redaction or marker neutralization changes proposed content.
- A GitHub mutation succeeds but read-back, timestamp, close reason, title, or dependency edge does not confirm the postcondition.

## Failure modes

- Fail before mutation when validation, authorization, security, repository-target, immutable-main, lifecycle-state, snapshot freshness, redaction, ref/path validation, or safe-probe checks fail.
- Stop the mutation sequence after any failed command, timestamp mismatch, child-skill verification failure, or failed read-back.
- Preserve scratch artifacts for actionable mutation diagnostics, but disarm the Write hook.
- Do not claim design readiness when evidence is insufficient, main cannot be verified, the target repository cannot be verified, or a valid triage-section update cannot be verified.
- Do not close an issue when verification comment, title restoration, canonical duplicate check, or pre-mutation snapshot check fails.
- Treat a missing, stale, or unverifiable dependency edge as failure without a success summary.
- Report missing evidence and residual uncertainty without inventing a root cause.

## Testing strategy

- Run `python3 -m pytest python/tests/issue/test_triage.py python/tests/issue/test_issue_block.py`.
- Run `bash scripts/test-triage-structure.sh`.
- Run `bash scripts/test-anti-halt-banners.sh`.
- Run `bash scripts/test-deny-edit-write.sh`.
- Run `make test-harness-shards-coverage`.
- Run changed-file lint and type checks for Python, Markdown, TOML, and Bash surfaces.
- Manually exercise `--report-only` against a test issue and confirm rendered analysis with zero mutation.
- In a disposable test repository, exercise immutable-main inspection, valid unmerged-ref evidence inspection, each mutable verdict, and verified dependency wiring.
- Exercise security-sensitive, protected-lifecycle, stale-prefix close, foreign-`--repo`, stale-dependency-timestamp, unavailable-main, and rejected-external-probe cases; confirm no unauthorized public mutation occurs.

Confidence: high. Existing untrusted wrappers, redaction patterns, mutation authorization, title eligibility, GitHub adapters, dependency helpers, token-scoped scratch-write guards, and anti-halt contracts provide the required foundations. The main added risk is correctly separating active lifecycle state from stale close-only prefixes, resolving immutable main evidence without trusting the worktree, enforcing post-child continuation, and preserving freshness across dependency writes.

difficulty: HARD
diff_added: 1720
diff_deleted: 30
mechanical_churn: false
oversize_override: operator
diff_lines: 1750
