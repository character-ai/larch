# Architectural Guidelines

These guidelines are aspirational. Surface meaningful deviations in design or implementation reviews. Move deterministic requirements into lints, hooks, or tests instead of relying on this file.

## Python coding practices

### G-Py-1: Pass composite data as frozen dataclasses
- Why: immutability plus named, refactor-safe fields across boundaries.
- Deviate when: scalar returns; genuine builders; an external dict/JSON parsed into a frozen dataclass at the edge. Aspirational today (`frozen=True` in a minority of files).

### G-Py-2: Annotate types beyond signatures, including locals
- Why: documents intent and catches what inference will not demand.
- Deviate when: for local declarations, see G-Py-9 (only scalar literals and loop targets may remain unannotated). Note: ruff `ANN` is currently ignored, so annotation presence is unenforced; enabling `ANN001`/`ANN201` would mechanize signatures, leaving local-variable annotation as the judgment residue.

### G-Py-3: Prefer domain types over stringly-typed primitives
- Why: illegal states unrepresentable; self-documenting call sites.
- Deviate when: one-call-site private helper; signature fixed by an external API/protocol. Note: ruff `FBT001`/`FBT003` already flag this and are widely `# noqa`'d today.

### G-Py-4: Fail loudly and fail closed; never silently swallow
- Why: auditability and the codebase's fail-closed parity. Catch narrow, named exceptions and handle or re-raise them deliberately; a bare `except:` or a blind `except Exception` that swallows hides real bugs (misspelled names, `KeyboardInterrupt`, `SystemExit`).
- Deviate when: a documented, narrow degraded path the caller explicitly handles, or the outermost handler of a thread or process that logs and re-raises.

### G-Py-5: Isolate side effects behind injectable seams
- Why: keeps logic unit-testable offline.
- Deviate when: thin CLI dispatch glue with nothing to test.

### G-Py-6: Pythonic judgment (PEP 20) is the scope; PEP 8 mechanics are not
- Why: the deterministic style layer is owned by ruff + pylint + pyright.
- Deviate when: n/a; this is what "adhere to official Python guidelines" reduces to once the linters take their half.

### G-Py-7: Wrap external CLIs (git/gh) as typed functions over the injected Runner; read helpers raise the ShipError hierarchy, mutating helpers return CommandResult
- Why: call sites get refactor-safe typed results and one uniform failure mode instead of ad-hoc returncode checks per caller.
- Deviate when: a one-shot internal probe with nothing to type, or a parser that needs the raw `CommandResult` (use the `*_read` variant).

### G-Py-8: After a security-or-integrity-critical mutation, re-verify the postcondition and raise if the invariant did not hold
- Why: a redaction or cleanup that silently leaves the bad state is worse than a loud failure; re-checking turns "probably scrubbed" into a proven invariant.
- Deviate when: the operation is cheap-to-retry and non-security-bearing.

### G-Py-9: Strongly type every local declaration; use the most-specific type and never `Any`
- Why: a local whose inferred type would be absent, imprecise, or `Any` (`payload = json.loads(raw)`, `client = make_client()`) hides bugs; an explicit annotation must name the narrowest provable type.
- Deviate when: the type is obvious from the RHS (scalar literals like `count = 0`, loop targets); a union the type-checker cannot narrow even with a cast (document why); an interoperability boundary that forces `Any` (narrow to a protocol or typed alias at the first safe site).

### G-Py-10: Make loop totality explicit when a bounded loop must always return, instead of relying on fall-through
- Why: an impossible loop exit should be loud; otherwise a future edit that changes the bound returns `None` or `""` silently.
- Deviate when: the function legitimately returns a default after the loop and that default is intended.

### G-Py-11: Give every lint or type suppression an inline reason and the narrowest scope that works — `# noqa: CODE - reason`, `# pylint: disable=check  # reason`, `# type: ignore[code]  # reason`
- Why: the reason lets a reviewer and the `/design` and `/implement` guideline assessments separate a deliberate carve-out from a silenced real defect; this codebase already annotates suppressions densely (`# lint-layering: ok …`), so a bare or blanket suppression reads as unexplained debt.
- Deviate when: n/a for the presence of a reason (ratchet candidate for a lint); a file-level suppression is acceptable when the condition is genuinely file-wide and carries that reason.

### G-Py-12: Break an import cycle at the call site with a documented function-level import, not by collapsing the leaf/domain layering
- Why: `larch.core` leaf modules must not import domain modules at top level; when a leaf function genuinely needs a domain helper, a local import with a `# lint-layering: ok <reason>` note keeps the graph acyclic without merging modules or hoisting logic to the wrong layer.
- Deviate when: the cycle is a symptom of real mislayering — move the code to the correct module instead of importing through the seam.

### G-Py-13: Acquire every external resource (file, lock, file descriptor, subprocess) through a context manager so cleanup runs on every path, success or exception
- Why: a manual `open()`/`close()` or acquire/release leaks the handle when an exception fires between them; a `with` block (or `contextlib.closing`) releases deterministically, which is the universally recommended Python pattern.
- Deviate when: a resource whose lifetime genuinely outlives the enclosing scope — return it, or manage it behind its own context-manager type.

## Configuration and protocol literals

### G-Cfg-1: Define every exit code, env-var name, tunable, and wire-literal once in config.py as a Final; aggregate token sets from prior sets rather than re-listing
- Why: a single edit point for protocol literals; aggregated sets cannot drift out of sync with their members.
- Deviate when: a module-private constant used at one call site with no cross-module contract.

## Wire-file I/O

### G-IO-1: Route reads/writes of larch wire files through larch.io helpers with explicit caller-selected policy flags, instead of re-implementing KEY=value parsing or bare tmp+replace
- Why: one audited implementation of the on-disk grammar (duplicate-key, CR, symlink, atomicity) keeps every envelope byte-compatible and centralizes fail-closed temp cleanup.
- Deviate when: a throwaway internal file with no wire contract, or stdin/stdout streaming.

### G-IO-2: Reject or escape embedded newlines and carriage returns in any value before writing it into a line-oriented `KEY=value` wire file
- Why: a value carrying a raw newline forges an extra `KEY=value` line, so an untrusted title, URL, or diagnostic could spoof a state key a later reader trusts; the ship driver and note writers already reject or `_env_escape` newlines for exactly this reason.
- Deviate when: the value is a controlled constant with no newline path, or it is written through a `larch.io` helper that already enforces this.

## Wire and protocol compatibility

### G-Wire-1: A change to a machine-consumed grammar is a multi-consumer change — preserve byte-compatibility for existing readers, or update every prompt-side and script consumer in the same change
- Why: `KEY=value` stdout, manifest JSON, machine footers, plan markers, and sentinel names are parsed by prompts, hooks, and scripts with no type system to catch a renamed or widened field; a producer that gets ahead of its readers fails silently.
- Deviate when: the field has no consumer yet (module-private, single call site). Complements AGENTS.md Output Style, which forbids rewording machine-parsed structure, with the consumer-atomicity half.

### G-Wire-2: Evolve a committed-artifact schema additively — keep every reader tolerant of prior shapes (version or header detection), and never backfill historical logs
- Why: committed run-log TSV and JSONL files mix schema versions across runs forever, so a reader that assumes the latest columns silently misreads old rows; larch keeps new writes backward-compatible and detects the shape by column count, `schema_version`, or header.
- Deviate when: an unreleased artifact with no committed history yet.

## CLI surface

### G-CLI-1: Expose each runtime entry as a module-level main(argv)->int returning a typed exit code, registered by (domain, verb) in the cli.py table; no per-script shim
- Why: uniform process contract for prompt-side callers, one dispatcher to audit, exit codes mapped to the `Outcome` enum.
- Deviate when: pure library helpers with no CLI surface.

### G-CLI-2: Give distinct failure classes distinct, documented exit codes so a caller can branch on them
- Why: collapsing an audit refusal, a flag or plan error, a stall handoff, and a scrub failure into one code hides why a run stopped; larch already separates them (`/implement` Preflight refusal exit 3, flag/plan error exit 2, pre-push conflict handoff exit 4, scrub failure rc 5).
- Deviate when: a library helper with a single failure mode and no caller that branches on the code.

## Security

### G-Sec-1: Validate untrusted strings (git refs/remotes/refspecs) against an allowlist regex before they enter a subprocess argv
- Why: validating at the boundary prevents a bad label reaching `git` argv; the intent already exists but is applied unevenly.
- Deviate when: the value is a known constant or already validated upstream at the single trust boundary (note it and skip the redundant re-check).

### G-Sec-2: Treat repo-local config, committed run logs, issue and PR bodies, and model, reviewer, or scout output as untrusted data — frame it as evidence in a content block, never as instructions that can outrank repo, skill, system, developer, or user priority
- Why: larch continuously ingests text it later re-emits or acts on, so a finding, plan, scout note, or guideline entry written as a command is a prompt-injection surface; the guidelines reader, scope-anchor renderers, and manifest OOS path already wrap their input this way.
- Deviate when: the value is a fixed maintainer-authored literal committed to the repo and consumed verbatim (note the trust source).

### G-Sec-3: Redact secrets, and tmpdir paths where present, before any egress surface — PR body, GitHub issue or comment, committed run log — and fail closed when the scrub cannot prove the secret is gone
- Why: egress is irreversible, so one unredacted publish exposes a credential that must then be rotated; a scrub failure is fatal-before-publish, not a recoverable warning, and even successful redaction warrants a rotation warning because the value was already in the session.
- Deviate when: purely local stdout or stderr that never reaches an artifact — still prefer redaction for anything that may be copied outward. Note: `.claude/rules/gh-body-file.md` reminds but does not mechanically enforce this at new call sites.

### G-Sec-4: Confine larch writes to the session and tmp roots you own — canonicalize and containment-check the path, and reject symlinks and non-regular files at read and write time, before any write, unlink, or `rm -rf`
- Why: a same-UID symlink swap or a `../`-escaping path turns an internal write into arbitrary-file corruption, and re-checking at use time rather than only at creation closes the TOCTOU gap.
- Deviate when: a fixed committed repo path validated once at the trust boundary (note it). Note: `larch.io` and several helpers already reject symlinks; this is the residual judgment for a new helper that accepts a caller-supplied path.

### G-Sec-5: Before signaling a persisted pid or pgid, re-verify process identity — pid, pgid, start time, and command signature — and log the intent; a mismatch or missing signature aborts the kill
- Why: a bare pid is reused after wraparound, so a stale `.active-leg-pgid` can kill an unrelated same-user process in another clone or session (issue #6213); identity re-verification plus a pre-signal log makes larch-initiated kills auditable and safe.
- Deviate when: signaling a child whose pid was captured moments earlier in the same process, with no reuse window.

## Idempotency and resumability

### G-Idem-1: Make each skill step and helper safe to re-run — marker-keyed or deduplicated writes, HEAD-pinned or content-hashed notes, and completion sentinels — so a resumed, retried, or re-notified turn converges instead of duplicating or acting on stale state
- Why: larch steps are re-entered constantly (pause and resume, premature `<task-notification>`, CI-fix loops, Step 8 relaunch), so a non-idempotent write duplicates an issue or comment, or ships a note stale for the current `HEAD`.
- Deviate when: a genuinely one-shot terminal action already guarded by an upstream single-flight gate.

### G-Idem-2: Write a step's completion marker only after its postcondition artifact exists and verifies — a marker without its evidence is corrupt and must fail audit, not read as done
- Why: a provisional marker written before the checkpoint succeeds lets a crashed or partial run look complete; larch fails audit when `step9a1=true` lacks `run-statistics.md`, and treats disposition evidence (`oos-issues.ndjson`) as separate from the completion signal.
- Deviate when: a step whose only effect is the marker itself, with no separate postcondition artifact.

## Determinism and identity

### G-Det-1: Derive a stable cross-run identity (hash, dedup key) only from durable content, excluding run ids, paths, line hints, timestamps, and filesystem state
- Why: an identity that mixes in run-local state changes every run, so the same finding never matches across runs or clones and dedup and idempotency break; larch's `finding_hash` uses normalized file plus concern only, and public dedup signatures exclude run ids, paths, and raw state.
- Deviate when: a within-run-only key that never needs to match across runs (say so).

## Orchestration and panels

### G-Orch-1: Keep parallel reviewer and voter agents isolated with no shared state, and deduplicate or synthesize in the orchestrator rather than letting agents see each other
- Why: independent perspectives are the point of a panel, so cross-agent visibility invites groupthink; larch runs agents in isolated contexts and does aggregation and dedup as deterministic orchestrator code, not as another agent that reads the others.
- Deviate when: a genuinely sequential refinement where a later agent is meant to build on an earlier one (make the dependency explicit).

### G-Orch-2: Bound agent fan-out with an explicit cap and a fixed panel shape, and choose a deterministic degradation policy per surface — drop the row, or a shape-preserving fallback — never a silent reviewer substitution
- Why: unbounded fan-out is a cost and latency risk, and a silent cross-vendor substitution corrupts attribution and independence; larch caps review rounds and panel size, drops missing vendor rows where attribution matters (`--no-fallback`), and uses a shape-preserving Claude fallback only where the panel shape must hold (`/research`).
- Deviate when: n/a for having a cap; the degradation policy itself is the judgment to state per surface.

## Observability and telemetry

### G-Obs-1: Telemetry and observability writes are best-effort, count-only, and fail-soft — a lock or write failure skips the metric without failing the parent, and telemetry never stores prompt or payload text
- Why: an operation must not fail because a metric could not be recorded, and a panel-size or digest-size row that captured prompt text would leak it into committed logs; larch's panel and checks telemetry store byte and token counts only, behind best-effort flock writers.
- Deviate when: a security or integrity postcondition, which fails closed per G-Py-8 and is not telemetry.

### G-Obs-2: Keep the durable committed artifact authoritative and the human-facing surface a slim, marker-keyed projection that points at it, not a second copy of the payload
- Why: duplicating bulky payloads into an issue or PR body bloats them and drifts from the source of truth; larch commits full run content under `larch-logs/` and keeps tracking-issue comments as marker-keyed summaries that reference the committed files.
- Deviate when: a payload small and stable enough that a pointer costs more than the copy (for example the embedded `larch:diagrams` Mermaid bodies).

### G-Obs-3: Record every skill-execution error or noteworthy failure to the run's category-keyed execution-issues log so it flushes into the committed run logs for later analysis
- Why: a failure that lives only in the session tmpdir vanishes at cleanup, so audits, calibration skills, and follow-up filing never see it; larch appends tool failures, reviewer issues, CI issues, and warnings to `execution-issues.ndjson` as the durable audit trail.
- Deviate when: a run that produces no committed logs at all (for example `repo_unavailable`), where the tmpdir `execution-issues.md` is the only possible trail.

## Skill authoring and context economy

### G-Skill-1: Load phase-local skill content lazily, at the point of need
- Why: lean active prompt; instructions adjacent to use.
- Deviate when: cross-cutting safety/NEVER constraints and Step-0-governing rules load eagerly; blocks too small to justify a separate Read.

### G-Skill-2: Logic lives in Python behind `cli.py`; SKILL.md and Bash stay thin
- Why: the judgment residue is "is this logic that belongs in Python?".
- Deviate when: n/a; mechanical parts (no consecutive Bash blocks; residual-bash allowlist) are lints, not this guideline.

## Bash authoring

### G-Bash-1: For assistant-authored Bash with three or more nested quote or escape levels, use a file-backed script or a quoted heredoc instead of inline composition, and on a parse error switch shapes rather than re-patching escapes
- Why: multi-level escaping is where assistant-authored Bash silently corrupts argv before the command runs (see BASH_AUTHORING.md §2); a file-backed script or quoted heredoc is auditable and quoting-stable.
- Deviate when: a one- or two-level composition that is obviously correct at a glance.

### G-Bash-2: Keep orchestrator-facing Bash probes bounded and exit-code-safe — prefer a bounded CLI over a discovery grep, pass an explicit path operand, and guard expected no-match with `|| true` so a probe never aborts its block or emits a false error row
- Why: a bare top-level `grep` in a Claude Code Bash block can abort the whole block, and a pathless grep-family probe can hang on open stdin (see BASH_AUTHORING.md §1); a bounded `cli.py … --help` answers most questions without a discovery scan at all.
- Deviate when: a rare reviewed fixture, tagged on that line with the `# lint-bare-grep-probe: ok <reason>` pragma.

### G-Bash-3: Keep committed shell scripts compatible with macOS system Bash 3.2 unless the script documents a narrower runtime — no associative arrays, namerefs, `mapfile`/`readarray`, case conversion (`${var^^}`/`${var,,}`), `&>>`, or coprocs
- Why: contributors and CI run on macOS, where `/bin/bash` is 3.2.57, so a Bash 4+ construct fails only on those machines, often silently or with a late error; reach for the 3.2 alternatives (newline-delimited temp files, `while IFS= read -r`, `case`/`tr`, `>>file 2>&1`).
- Deviate when: a script documents a narrower runtime at its top and is excluded from the sweep. Note: `make lint-bash32` mechanizes the forbidden-construct list (suppress a reviewed fixture on-line with `# lint-bash32: ok <reason>`); the residual judgment is the renderer `&`-substitution hazard (`${var//pat/$repl}` differs between 3.2 and 5.x — see BASH_AUTHORING.md §3) and any new Bash-4+ idiom not yet on the lint's list.

### G-Bash-4: Start an executable shell script with strict mode — `set -euo pipefail` — so an unset variable, a failed command, or a broken pipe stage aborts instead of continuing on stale state
- Why: without it a failed command or a typo'd variable silently continues and corrupts later steps; strict mode is the universally recommended shell default. Pair it with `|| true` on commands you intentionally let fail (see G-Bash-2).
- Deviate when: a contract-bearing hook or sourced fragment that must not exit its caller — there, handle errors explicitly and keep the hook's exit-0 contract.

## External tools

### G-Ext-1: Verify a new or changed external-CLI invocation with the exact argv (or a side-effect-free `--help`/`--dry-run` probe) before commit, document any platform-specific flag, and treat the tool's output as untrusted
- Why: a flag-unavailability failure (`--sandbox`, `--prompt` vs `--print`) surfaces as a silent reviewer or CI miss, not a loud error, and external-agent output can carry injected instructions; probing the real argv and framing the output as data closes both gaps.
- Deviate when: an unchanged invocation already covered by a harness that runs the real command.

## Documentation and Markdown

### G-Md-1: Keep drift-prone facts out of prose — derive counts and panel sizes from a single source (`skills/shared/topology.tsv`, the harness), refer to code by symbol rather than line number, and use repo-relative or `${CLAUDE_PLUGIN_ROOT}` paths, never machine-local absolute paths
- Why: prose in Markdown and YAML goes stale silently with no test to catch it (see `.claude/rules/drift-prone-prose-in-docs.md`); a hardcoded count, a `file.py:198` reference, or a `/Users/<name>/...` path is wrong on the next edit.
- Deviate when: a literal that must appear inline is tagged for grep so its source of truth stays discoverable.

### G-Md-2: A rename of a script, step, flag, or enum value is not complete until its prose consumers are swept in the same change — grep `docs/`, `skills/**/SKILL.md`, `README.md`, `SECURITY.md`, and `.github/workflows/` for the old token
- Why: stale prose pointing at a deleted or renamed entity is the top recurring OOS source; a green test suite does not catch a doc that still names the old step, flag, or enum value.
- Deviate when: n/a — the sweep is cheap and the failure mode is silent.

## Enforcement philosophy

### G-Enf-1: Prefer mechanical enforcement
- Why: when a judgment call recurs, promote it to a lint, hook, or structural test. Governs this file too: entries graduate to lints over time.
- Deviate when: n/a.

### G-Enf-2: When a recurring defect graduates to a mechanical ratchet, grandfather existing violations in a reason-bearing baseline that only shrinks — never widen a baseline or add a bare suppression to pass
- Why: a ratchet stops new violations while the baseline documents and drains the old ones; widening it, or suppressing without a reason, silently re-admits the defect and defeats the ratchet.
- Deviate when: n/a; a first-run baseline is expected, but every baseline row and suppression carries a reason (see G-Py-11).
