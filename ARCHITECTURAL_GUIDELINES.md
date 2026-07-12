# Architectural Guidelines

These guidelines are aspirational. Surface meaningful deviations in design or implementation reviews. Move deterministic requirements into lints, hooks, or tests instead of relying on this file.

## Fix discipline

### G-Fix-1: Fix the class, not the instance
- Why: one-site fixes produced the largest recurring family in the closed bug backlog; the aggregator-retry, guideline-pin, fast-fail-lane, and `NO_OPEN_BROWSER` chains each took four to nine follow-up bugs to converge (#4881, #5222, #5969, #6021, #5971, #6022, #6264).
- Guidance: when the defect you are fixing has the same shape at sibling sites (launch lanes, step wrappers, retry classes, tally writers, sentinel cases, grace windows), enumerate the siblings by grep in the same change, and fix each one or file a tracking issue for it in the same run; never leave a conscious descope untracked.
- Deviate when: a sibling is provably unreachable or intentionally different; say so, with the sibling list, in the PR description.

### G-Fix-2: A recovery-path bug fix ships with an executable reproduction
- Why: 82% of 2026-07 bugs were found only by live runs; CI-green carries no signal for this class, and unreproduced fixes repeatedly shipped incomplete (#6610, #6882, #6931 chains).
- Guidance: when fixing a bug in recovery or orchestration machinery (implement steps, ship and postmerge routing, bgjob, design publish and resume, CI fixer, stall classifiers), add or extend an offline harness or test case that replays the failure and passes with the fix. Close criteria is reproduced-then-passed, not merged or CI-green.
- Deviate when: the failure requires live vendor or GitHub state that no harness can replay; say so in the PR and name the manual verification performed.

## Python coding practices

### G-Py-1: Pass composite data as frozen dataclasses
- Why: immutability, plus named, refactor-safe fields across boundaries.
- Deviate when: scalar returns; genuine builders; an external dict or JSON parsed into a frozen dataclass at the edge. Aspirational today; `frozen=True` appears in a minority of files.

### G-Py-2: Annotate types beyond signatures, including locals
- Why: annotations document intent and catch what inference will not demand.
- Deviate when: for locals, see G-Py-9; only scalar literals and loop targets may stay unannotated. Note: ruff `ANN` is ignored today, so presence is unenforced; `ANN001`/`ANN201` would mechanize signatures and leave local annotation as the residue.

### G-Py-3: Prefer domain types over stringly-typed primitives
- Why: illegal states become unrepresentable, and call sites self-document.
- Deviate when: a one-call-site private helper, or a signature fixed by an external API or protocol. Note: ruff `FBT001`/`FBT003` already flag this and are widely `# noqa`'d today.

### G-Py-4: Fail loudly and fail closed; never silently swallow
- Why: loud failure preserves auditability and the codebase's fail-closed parity. Catch narrow, named exceptions; a bare `except:` or a blind `except Exception` that swallows hides real bugs like a misspelled name, `KeyboardInterrupt`, or `SystemExit`.
- Deviate when: a documented, narrow degraded path the caller handles, or an outermost thread or process handler that logs and re-raises.

### G-Py-5: Isolate side effects behind injectable seams
- Why: injectable seams keep logic unit-testable offline.
- Deviate when: thin CLI dispatch glue with nothing to test.

### G-Py-6: Pythonic judgment (PEP 20) is the scope; PEP 8 mechanics are not
- Why: ruff, pylint, and pyright own the deterministic style layer.
- Deviate when: n/a; this is what "adhere to official Python guidelines" reduces to once the linters take their half.

### G-Py-7: Wrap external CLIs (git, gh) as typed functions over the injected Runner; read helpers raise ShipError, mutating helpers return CommandResult
- Why: call sites get refactor-safe typed results and one uniform failure mode, not ad-hoc returncode checks.
- Deviate when: a one-shot internal probe with nothing to type, or a parser that needs the raw `CommandResult` (use the `*_read` variant).

### G-Py-8: After a security- or integrity-critical mutation, re-verify the postcondition and raise if the invariant did not hold
- Why: a redaction or cleanup that silently leaves the bad state is worse than a loud failure; re-checking turns "probably scrubbed" into a proven invariant.
- Deviate when: the operation is cheap to retry and carries no security weight.

### G-Py-9: Strongly type every local declaration; use the most-specific type and never `Any`
- Why: a local whose inferred type is absent, imprecise, or `Any` (`payload = json.loads(raw)`, `client = make_client()`) hides bugs; name the narrowest provable type.
- Deviate when: the type is obvious from the RHS (scalar literals like `count = 0`, loop targets); a union the checker cannot narrow even with a cast (say why); or a boundary that forces `Any` (narrow to a protocol or typed alias at the first safe site).

### G-Py-10: Make loop totality explicit when a bounded loop must always return, instead of relying on fall-through
- Why: an impossible loop exit should be loud; otherwise a later edit to the bound returns `None` or `""` silently.
- Deviate when: the function legitimately returns a default after the loop, and that default is intended.

### G-Py-11: Give every lint or type suppression an inline reason and the narrowest scope that works
- Why: the reason lets a reviewer, and the `/design` and `/implement` assessments, tell a deliberate carve-out from a silenced defect. Use `# noqa: CODE - reason`, `# pylint: disable=check  # reason`, or `# type: ignore[code]  # reason`. This codebase annotates suppressions densely, so a bare one reads as unexplained debt.
- Deviate when: n/a for having a reason (a ratchet candidate); a file-level suppression is fine when the condition is genuinely file-wide and carries its reason.

### G-Py-12: Break an import cycle at the call site with a documented function-level import, not by collapsing the leaf/domain layering
- Why: `larch.core` leaf modules must not import domain modules at top level; a local import with a `# lint-layering: ok <reason>` note keeps the graph acyclic without merging modules or hoisting logic to the wrong layer.
- Deviate when: the cycle signals real mislayering; move the code to the correct module instead of importing through the seam.

### G-Py-13: Acquire every external resource through a context manager so cleanup runs on every path
- Why: a manual `open()`/`close()` or acquire/release leaks the handle when an exception fires between them. A `with` block, or `contextlib.closing`, releases the file, lock, descriptor, or subprocess deterministically. This is the standard Python pattern.
- Deviate when: a resource whose lifetime outlives the enclosing scope; return it, or wrap it in its own context-manager type.

### G-Py-14: Prefer typed helper functions for monkeypatched callables with parameters
- Why: pyright strict mode can flag untyped lambda parameters in `monkeypatch.setattr` callables, and helper functions make the fake contract reviewable.
- Deviate when: the callable has no parameters or a narrow inline pyright suppression is clearer; preserve existing suppressions and keep any new suppression on the smallest possible line.

### G-Py-15: Partition status values into terminal and non-terminal sets; never branch on truthiness
- Why: `/analyze-bugs` short-circuited on any truthy mechanical verdict, so the routing value `NEEDS_DEEP` masked already-ingested deep verdicts (#6153); resume hydration coerced any unrecognized merge result, including empty, to already-merged, and the reconciler collapsed every refresh skip into a spurious terminal STALLED (#6018).
- Guidance: when a status, verdict, or result type has routing or in-progress members, define the terminal subset once, next to the type, and route every "is this final?" decision through that membership test; make validators reject unknown values instead of coercing them to a member; never gate on the presence or truthiness of a status value.
- Deviate when: the status never crosses a function boundary and has no special members; a local boolean is fine.

## Configuration and protocol literals

### G-Cfg-1: Define every exit code, env-var name, tunable, and wire literal once in config.py as a Final; build token sets from prior sets rather than re-listing
- Mechanized: `python3 python/cli.py lint env-via-config-constant` covers env-var literals only; exit codes, tunables, and other wire literals remain review-guided.
- Why: one edit point for protocol literals; aggregated sets cannot drift out of sync with their members.
- Deviate when: a module-private constant used at one call site with no cross-module contract.

### G-Cfg-2: Release-owned version bumps use the release flow
- Why: plugin version changes carry release automation and a reserved commit-message shape; manually reusing `Bump version to X.Y.Z` makes provenance ambiguous.
- Deviate when: n/a for release-owned version fields. Use the release flow or leave the version unchanged.

### G-Cfg-3: A convention's writer and its selectors share one constant
- Why: `/analyze-bugs` selected bugs with a hand-written `[BUG]` prefix test while the retitle convention had grown `[DONE]` and case variants, so the audit silently skipped most of its population (#6604); the /design pause snapshot allowlist lagged the sentinel layout its resume guard read, so resume false-refused a complete review (#6548).
- Guidance: when code writes a convention that other code later selects on, such as a title lifecycle prefix, a marker line, or an artifact filename pattern, define the token once and make the writer, every selector, and every normalizer consume that same constant; a selector that re-derives the convention by hand drifts when the convention gains a new case.
- Deviate when: the convention belongs to an external system you cannot import; then test the selector against live samples of that system's output.

## Wire-file I/O

### G-IO-1: Route reads and writes of larch wire files through larch.io helpers with explicit policy flags, instead of re-implementing KEY=value parsing or bare tmp+replace
- Why: one audited implementation of the on-disk grammar (duplicate keys, CR, symlinks, atomicity) keeps every envelope byte-compatible and centralizes fail-closed temp cleanup.
- Deviate when: a throwaway internal file with no wire contract, or stdin/stdout streaming.

### G-IO-2: Reject or escape embedded newlines and carriage returns before writing a value into a line-oriented `KEY=value` wire file
- Why: a value with a raw newline forges an extra `KEY=value` line, so an untrusted title, URL, or diagnostic could spoof a state key a later reader trusts. The ship driver and note writers already reject or `_env_escape` newlines.
- Deviate when: the value is a controlled constant with no newline path, or a `larch.io` helper already enforces this.

### G-IO-3: Return an existing absolute path unchanged from a path-rebase helper
- Why: a path-rebase helper re-anchored a valid, existing absolute path from the system `$TMPDIR` into a non-existent path, which broke session-transcript capture on every run after the migration because a same-host absolute path was treated as foreign (#6263).
- Guidance: a path-rebase helper returns an existing absolute path unchanged instead of re-anchoring it under a different root; when the input is absolute and the file exists, or the input already lies under the real system `$TMPDIR`, return it as-is.
- Deviate when: the helper documents that it deliberately relocates paths into a sandbox root, and the relocation target is guaranteed to exist before the call.

## Wire and protocol compatibility

### G-Wire-1: A change to a machine-consumed grammar is a multi-consumer change: preserve byte-compatibility for existing readers, or update every consumer in the same change
- Why: `KEY=value` stdout, manifest JSON, machine footers, plan markers, and sentinel names are parsed by prompts, hooks, and scripts with no type system to catch a renamed or widened field. A producer that runs ahead of its readers fails silently.
- Deviate when: the field has no consumer yet (module-private, single call site). This complements AGENTS.md Output Style, which forbids rewording machine structure, with the consumer-atomicity half.

### G-Wire-2: Evolve a committed-artifact schema additively; keep readers tolerant of prior shapes and never backfill historical logs
- Why: committed run-log TSV and JSONL files mix schema versions across runs forever, so a reader that assumes the latest columns misreads old rows. larch keeps new writes backward-compatible and detects the shape by column count, `schema_version`, or header.
- Deviate when: an unreleased artifact with no committed history yet.

### G-Wire-3: Sweep every consumer of shared machinery, not only the consumer that surfaced the bug
- Why: a feature or fix that changes a shared renderer, a shared status converter, or a shared committed-artifact writer was repeatedly completed for one consumer while a sibling consumer sharing the same machinery was left unswept, so the fix silently no-op'd or misbehaved on the unswept surface (#5940, #6578, #6668, #6632, #6027).
- Guidance: when a change touches a renderer, status converter, parser, or artifact writer that more than one consumer shares, enumerate the sibling consumers by grep in the same change, update each one, and add a regression test for at least one consumer other than the one that surfaced the bug.
- Deviate when: a sibling consumer is provably unreachable for this change because it is guarded behind a flag that is off; record that fact, with the sibling list, in the PR description.

## CLI surface

### G-CLI-1: Expose each runtime entry as a module-level main(argv)->int returning a typed exit code, registered by (domain, verb) in the cli.py table; no per-script shim
- Why: one uniform process contract for prompt-side callers, one dispatcher to audit, exit codes mapped to the `Outcome` enum.
- Deviate when: pure library helpers with no CLI surface.

### G-CLI-2: Give distinct failure classes distinct, documented exit codes so a caller can branch on them
- Why: one shared code for an audit refusal, a flag or plan error, a stall handoff, and a scrub failure hides why a run stopped. larch separates them: `/implement` Preflight refusal exit 3, flag or plan error exit 2, pre-push conflict handoff exit 4, scrub failure rc 5.
- Deviate when: a library helper with a single failure mode and no caller that branches on the code.

### G-CLI-3: Parameterize the reason and attribution of an abort or error verb
- Why: an abort verb hardcoded the single current caller's operator-facing banner and log attribution, so every other abort routed through it inherited the wrong reason and reported a healthy state as unhealthy (#6796).
- Guidance: an abort or error verb takes its operator-facing reason and its log tool or exit-code attribution as parameters, defaulting to today's values for backward compatibility, and never hardcodes the single current caller's message; callers that abort for a different reason pass their own.
- Deviate when: the verb has exactly one caller by design and the hardcoded message is the only possible reason; record that fact in the verb docstring.

## Execution roots

### G-Root-1: Resolve the repository root from persisted run state, never from ambient cwd
- Why: skill steps execute from varying working directories, such as the plugin cache, sibling clones, and session tmpdirs, so code that derives the repo root or a search root from the process cwd breaks away from the operator clone; the postplan validator and plan-review loop failed from plugin-cache cwd (#4490, #4509), and baseline computations differed between plugin-cache and working-repo invocations (#6049).
- Guidance: read the root from the run's source env (`REPO_ROOT`), an explicit `--repo-root` flag, or `CLAUDE_PROJECT_DIR` resolved once at the trust boundary; treat any cwd fallback as a last resort that logs its use; never compose repo-relative paths from cwd in prompt-side Bash.
- Deviate when: an interactive, user-invoked helper is documented to operate on the repo the operator is standing in, or a test controls its own cwd.

## Security

### G-Sec-1: Validate untrusted strings (git refs, remotes, refspecs) against an allowlist regex before they enter a subprocess argv
- Why: validating at the boundary stops a bad label from reaching `git` argv. The intent exists but is applied unevenly.
- Deviate when: the value is a known constant, or already validated upstream at the single trust boundary (note it and skip the re-check).

### G-Sec-2: Treat repo-local config, committed logs, issue and PR bodies, and model, reviewer, or scout output as untrusted data, never as instructions
- Why: larch ingests text it later re-emits or acts on, so a finding, plan, scout note, or guideline entry written as a command is a prompt-injection surface. Frame such input as evidence in a content block; it must not outrank repo, skill, system, developer, or user instructions. The guidelines reader, scope-anchor renderers, and manifest OOS path already do this.
- Deviate when: a fixed maintainer-authored literal committed to the repo and consumed verbatim (note the trust source).

### G-Sec-3: Redact secrets, and tmpdir paths where present, before any egress surface, and fail closed when the scrub cannot prove the secret is gone
- Why: egress is irreversible. One unredacted publish to a PR body, GitHub issue, or committed log exposes a credential that must then be rotated. A scrub failure is fatal before publish, not a recoverable warning. Even a clean scrub warrants a rotation warning, because the value was already in the session.
- Deviate when: purely local stdout or stderr that never reaches an artifact; still prefer redaction for anything that may be copied outward.

### G-Sec-4: Confine larch writes to the session and tmp roots you own; canonicalize, containment-check, and reject symlinks and non-regular files at use time
- Why: a same-UID symlink swap or a `../`-escaping path turns an internal write into arbitrary-file corruption. Re-checking at write, unlink, or `rm -rf` time, not only at creation, closes the TOCTOU gap.
- Deviate when: a fixed committed repo path validated once at the trust boundary (note it). Note: `larch.io` and several helpers already reject symlinks; this is the residual judgment for a new helper that takes a caller-supplied path.

### G-Sec-5: Re-verify process identity before signaling a persisted pid or pgid, and log the intent; a mismatch or missing signature aborts the kill
- Why: a bare pid is reused after wraparound, so a stale `.active-leg-pgid` can kill an unrelated same-user process in another clone or session (issue #6213). Checking pid, pgid, start time, and command signature, plus a pre-signal log, makes larch kills safe and auditable.
- Deviate when: signaling a child whose pid was captured moments earlier in the same process, with no reuse window.

## Idempotency and resumability

### G-Idem-1: Make each skill step and helper safe to re-run, so a resumed, retried, or re-notified turn converges instead of duplicating or acting on stale state
- Why: larch re-enters steps constantly: pause and resume, premature async wakeup, CI-fix loops, Step 8 relaunch. Use marker-keyed or deduplicated writes, HEAD-pinned or content-hashed notes, and completion sentinels, or a re-run duplicates an issue or comment, or ships a note stale for the current `HEAD`.
- Deviate when: a one-shot terminal action already guarded by an upstream single-flight gate.

### G-Idem-2: Write a step's completion marker only after its postcondition artifact exists and verifies; a marker without its evidence is corrupt and must fail audit
- Why: a provisional marker written before the checkpoint succeeds lets a crashed or partial run look complete. larch fails audit when `step9a1=true` lacks `run-statistics.md`, and treats disposition evidence like `oos-issues.ndjson` as separate from the completion signal.
- Deviate when: a step whose only effect is the marker itself, with no separate postcondition artifact.

### G-Idem-3: On resume or reseed, persisted run state outranks caller-supplied defaults
- Why: a hardcoded `--merge false` reseed permanently erased operator intent after a stall (#5308), and a persisted dispatcher-committed flag skipped committing later lint-fix edits, leaving a dirty tree at rebase (#6199, #5922, #4487).
- Guidance: read the prior state file before seeding; never reseed with hardcoded constants, and never let a sticky completion flag suppress handling of new work performed after the flag was set.
- Deviate when: only on an explicit operator override, and record the override next to the overwritten value.

### G-Idem-4: At a ship gate, distinguish a transient assessment failure from a genuine defect by its reason token, and route the transient case to operator-bail rather than a hard-stall the reship will replay byte-identically
- Why: the Step 8 invariant/guideline ship gate mapped a transient `unavailable` assessor result to the same `outcome=dropped` hard-stall as a real violation, and the stall classifier read the transient-failure detail in the evidence as `transient-infra`, so `/implement --merge` reshipped, re-ran the assessment, failed again, and restalled until the attempt cap with no operator path (#7022). `unavailable` is a documented non-violation fallback (`docs/run-logs.md`), not a code defect.
- Guidance: when a gate acts on an outcome that has both a value and a reason, branch on the reason before stalling; reserve the hard-stall for reasons that denote a genuine defect (`compose-materialization-failed`, `unknown`, read/redaction failures) and route transient reasons (`unavailable`) to `Outcome.NEEDS_USER_INPUT` so the dispatcher maps them to `NEXT_ACTION=operator-bail` and the operator decides from the run-log assessment receipt. The assessor already retried before declaring `unavailable`, so an automated reship is not a useful recovery there.
- Deviate when: a transient failure has a bounded, idempotent in-process retry that the gate itself owns and that converges before any stall is written.

## Determinism and identity

### G-Det-1: Derive a stable cross-run identity (hash, dedup key) only from durable content, excluding run ids, paths, line hints, timestamps, and filesystem state
- Why: an identity that mixes in run-local state changes every run, so the same finding never matches across runs or clones and dedup and idempotency break. larch's `finding_hash` uses normalized file plus concern only, and public dedup signatures exclude run ids, paths, and raw state.
- Deviate when: a within-run-only key that never needs to match across runs (say so).

## Orchestration and panels

### G-Orch-1: Keep parallel reviewer and voter agents isolated with no shared state; deduplicate and synthesize in the orchestrator, not by letting agents see each other
- Why: independent perspectives are the point of a panel, so cross-agent visibility invites groupthink. larch runs agents in isolated contexts and does aggregation and dedup as deterministic orchestrator code, not as another agent that reads the others.
- Deviate when: a genuinely sequential refinement, where a later agent is meant to build on an earlier one (make the dependency explicit).

### G-Orch-2: Bound agent fan-out with an explicit cap and a fixed panel shape, and pick a deterministic degradation policy per surface, never a silent reviewer substitution
- Why: unbounded fan-out is a cost and latency risk, and a silent cross-vendor substitution corrupts attribution and independence. larch caps review rounds and panel size, drops missing vendor rows where attribution matters (`--no-fallback`), and uses a shape-preserving Claude fallback only where the panel shape must hold (`/research`).
- Deviate when: n/a for having a cap; the degradation policy itself is the judgment to state per surface.

### G-Orch-3: Treat zero findings as a first-class result
- Why: empty-versus-failed ambiguity silently degraded panels, retried guaranteed-empty ballots, and reported completed reviews as N/A (#3402, #5032, #6026, #4885, #4618).
- Guidance: at every agent-output boundary (reviewer, voter, aggregator, validator, tally, self-review), represent empty-success with an explicit typed sentinel or status distinct from failure, and never let a consumer infer health or failure from emptiness alone.
- Deviate when: the boundary already returns a machine-typed status that separates the two; never deviate by adding a new emptiness heuristic.

### G-Orch-5: Key destructive watchers to structured error events, not aggregated output
- Why: the codex policy-rejection watcher regex-scanned the raw events tail, matched historical design-log text quoted by a successful grep, and killed a healthy voter (#6577).
- Guidance: a watcher that kills, retries, or fails over an agent must match the stream's structured error events or a dedicated error channel, never raw aggregated output that can quote arbitrary bytes such as grep results over committed logs; before acting destructively, record the matched evidence and its provenance to the run diagnostics.
- Deviate when: the vendor emits no structured error framing; then anchor the match to the vendor's own event delimiters and keep the kill path non-silent so a false positive stays diagnosable.

### G-Orch-6: Size inlined agent payloads from the owning cap constants, not from an observed run
- Why: an inlining design that worked on one small observed run failed at the configured worst case near 700KB per batch, and the toolless agent downstream fabricated verdicts instead of failing (#6671).
- Guidance: when a skill or dispatcher inlines payloads into an agent prompt, compute the worst case from the cap constants that own the payload (diff cap, body cap, batch size) and check that it fits the transport; when it cannot, pass paths and grant the agent a Read tool.
- Deviate when: the payload is bounded small by construction, such as a fixed-format single record; note the bound where the dispatch is defined.

## Observability and telemetry

### G-Obs-1: Keep telemetry writes best-effort, count-only, and fail-soft; a write failure skips the metric without failing the parent, and telemetry never stores prompt or payload text
- Why: an operation must not fail because a metric could not be recorded, and a panel-size or digest-size row that captured prompt text would leak it into committed logs. larch's panel and checks telemetry store byte and token counts only, behind best-effort flock writers.
- Deviate when: a security or integrity postcondition, which fails closed per G-Py-8 and is not telemetry.

### G-Obs-2: Keep the committed artifact authoritative and the human-facing surface a slim, marker-keyed pointer to it, not a second copy of the payload
- Why: copying bulky payloads into an issue or PR body bloats them and drifts from the source of truth. larch commits full run content under `larch-logs/` and keeps tracking-issue comments as marker-keyed summaries that reference the files.
- Deviate when: a payload small and stable enough that a pointer costs more than the copy, like the embedded `larch:diagrams` Mermaid bodies.

### G-Obs-3: Record every skill-execution error or noteworthy failure to the run's category-keyed execution-issues log, so it flushes into the committed run logs for later analysis
- Why: a failure that lives only in the session tmpdir vanishes at cleanup, so audits, calibration skills, and follow-up filing never see it. larch appends tool failures, reviewer issues, CI issues, and warnings to `execution-issues.ndjson` as the durable audit trail.
- Deviate when: a run that produces no committed logs at all, like `repo_unavailable`, where the tmpdir `execution-issues.md` is the only possible trail.

### G-Obs-5: Give report renderers a golden test with hostile-width and fallback-shaped fixtures
- Why: the /design Gantt corrupted alignment on long slot names twice (#5587, #5753), and the round timing chart silently omitted the vendor-fallback runs that did the round's actual work (#6578).
- Guidance: a renderer that aligns columns, truncates labels, or selects rows for a human-facing report gets a golden test whose fixture includes labels wider than the layout budget and rows produced by retry, phase2, or vendor-fallback paths.
- Deviate when: the output is a throwaway diagnostic that no operator decision consumes.

### G-Obs-6: Compute report column widths and bar offsets from the global maximum, not a per-row constant
- Why: a report renderer that aligned rows started each bar at a fixed offset instead of the longest row label plus one, which misaligned every row in the chart (#5587, #5753).
- Guidance: a renderer that aligns multiple rows computes column widths, bar start offsets, and bar lengths from the maximum across all rows in the render pass, not from a per-row value or a hardcoded constant; compute the maximum in a first pass, then render.
- Deviate when: the renderer draws a single row, so there is no cross-row maximum to compute.

## Skill authoring and context economy

### G-Skill-1: Load phase-local skill content lazily, at the point of need
- Why: a lean active prompt, with instructions next to their use.
- Deviate when: cross-cutting safety or NEVER constraints and Step-0-governing rules load eagerly; or blocks too small to justify a separate Read.

### G-Skill-2: Keep logic in Python behind `cli.py`; SKILL.md and Bash stay thin
- Why: the judgment residue is "is this logic that belongs in Python?".
- Deviate when: n/a; the mechanical parts (no consecutive Bash blocks, the residual-bash allowlist) are lints, not this guideline.

### G-Skill-3: Use the correct runtime root for skill paths
- Why: public skills run from an installed plugin tree, while dev-only skills run from the checkout. Public `skills/*/SKILL.md` should point at `${CLAUDE_PLUGIN_ROOT}/...`; dev-only `.claude/skills/*/SKILL.md` may use `$PWD/...`.
- Deviate when: the path is explicitly user-supplied or a local scratch path, not a plugin resource.

### G-Skill-4: Trace skill edits from the skill prompt through local scripts and shared helpers
- Why: skill behavior is split across `SKILL.md`, local `scripts/`, root `scripts/`, and `skills/shared/`; changing one without reading the others misses the real contract. When `skills/implement/SKILL.md` Bash fences change, inspect `scripts/test-implement-fence-shape.sh` because it pins the old/new fence shape.
- Deviate when: a purely typographic edit cannot affect behavior and has no local helper references.

## Bash authoring

### G-Bash-1: For assistant-authored Bash with three or more nested quote or escape levels, use a file-backed script or a quoted heredoc; on a parse error, switch shapes rather than re-patch escapes
- Why: multi-level escaping is where assistant-authored Bash silently corrupts argv before the command runs (BASH_AUTHORING.md §2). A file-backed script or quoted heredoc is auditable and quoting-stable.
- Deviate when: a one- or two-level composition that is obviously correct at a glance.

### G-Bash-2: Keep orchestrator-facing Bash probes bounded and exit-code-safe; prefer a bounded CLI over a discovery grep, pass an explicit path, and guard expected no-match with `|| true`
- Why: a bare top-level `grep` in a Claude Code Bash block can abort the block, and a pathless grep-family probe can hang on open stdin (BASH_AUTHORING.md §1). A bounded `cli.py … --help` often answers the question with no scan at all.
- Deviate when: a rare reviewed fixture, tagged on that line with `# lint-bare-grep-probe: ok <reason>`.

### G-Bash-3: Keep committed shell scripts compatible with macOS system Bash 3.2 unless the script documents a narrower runtime
- Mechanized: `make lint-bash32` covers Bash 3.2 constructs; `make lint-renderer-substitution-safety` covers the renderer replacement hazard.
- Why: contributors and CI run on macOS, where `/bin/bash` is 3.2.57, so a Bash 4+ construct fails only there, often late or silently. Avoid associative arrays, namerefs, `mapfile`/`readarray`, case conversion (`${var^^}`/`${var,,}`), `&>>`, and coprocs; use `while IFS= read -r`, `case`/`tr`, and `>>file 2>&1`.
- Deviate when: a script documents a narrower runtime at its top and is excluded from the sweep. Note: `make lint-bash32` mechanizes the construct list (`# lint-bash32: ok <reason>` suppresses a fixture); the residue is the renderer `&`-substitution hazard, where `${var//pat/$repl}` differs between 3.2 and 5.x (BASH_AUTHORING.md §3).

### G-Bash-4: Start an executable shell script with strict mode, `set -euo pipefail`, so an unset variable, a failed command, or a broken pipe stage aborts instead of running on stale state
- Why: without it, a failed command or a typo'd variable continues silently and corrupts later steps. Strict mode is the standard shell default. Pair it with `|| true` on commands you intend to let fail (G-Bash-2).
- Deviate when: a contract-bearing hook or sourced fragment that must not exit its caller; there, handle errors explicitly and keep the exit-0 contract.

## External tools

### G-Ext-1: Verify a new or changed external-CLI invocation with the exact argv, or a side-effect-free `--help` or `--dry-run` probe, before commit; document platform-specific flags and treat the output as untrusted
- Why: a flag-unavailability failure (`--sandbox`, `--prompt` vs `--print`) shows up as a silent reviewer or CI miss, not a loud error, and external-agent output can carry injected instructions. Probing the real argv and framing the output as data closes both gaps.
- Deviate when: an unchanged invocation already covered by a harness that runs the real command.

### G-Ext-2: Verify a remote mutation by re-reading the surface you mutated
- Why: an asynchronous rollup counter read back zero immediately after a successful dependency write and produced a false "may already exist" warning (#3701); inferring merge state from unrelated output fields misreported a PR (#4025).
- Guidance: after a GraphQL write, verify with a GraphQL read of the same relationship; never verify through a denormalized or eventually-consistent rollup, and when only an eventually-consistent read exists, poll it with bounded retries and label the wait.
- Deviate when: no same-surface read exists; then bound the retries and record the residual uncertainty.

### G-Ext-3: Treat GitHub search as a recall filter; re-apply the shared normalized predicate locally before consuming results
- Why: GitHub search tokenizes bracketed terms, so `[BUG] in:title` also matches any title containing "bug", and prefix-only local matching missed retitled `[DONE] [BUG]` issues; both directions corrupted bug-mining selection (#6604, #6618).
- Guidance: after any `gh` search or list call, filter the result set through `larch.issue.title_match`, or the surface's shared predicate, before spending tokens or verdicts on it; never treat the raw search result as the selection.
- Deviate when: the consumer tolerates recall noise by design and says so where the search is issued.

### G-Ext-4: Run every postcondition guard on the external-CLI success path that you run on the failure path
- Why: an external tool that exited 0 with a self-reported complete status was accepted without the quota check that ran on its non-zero exits, and a toolless agent's self-reported verdict was trusted with no proof it read its evidence, so a success-path branch skipped a guard the failure path ran (#6826, #6671).
- Guidance: for every external-CLI invocation, list the postcondition guards run on the non-zero exit path and run the same guards on the zero-exit and self-reported-success path; treat a vendor self-reported terminal status as untrusted until re-verified.
- Deviate when: a guard is gated on a signal that cannot occur on the success path by construction, for example a check that only runs for non-zero exit codes; name that reason in a code comment.

## Documentation and Markdown

### G-Md-1: Keep drift-prone facts out of prose; derive counts from a single source, refer to code by symbol not line number, and use repo-relative or `${CLAUDE_PLUGIN_ROOT}` paths
- Why: prose in Markdown and YAML goes stale silently. A hardcoded count, a `file.py:198` reference, or a `/Users/<name>/...` path is wrong on the next edit. Source counts and panel sizes from `skills/shared/topology.tsv` or the harness.
- Deviate when: a literal that must appear inline is tagged for grep, so its source of truth stays discoverable.

### G-Md-2: A rename of a script, step, flag, or enum value is not done until its prose consumers are swept in the same change
- Why: stale prose pointing at a renamed entity is the top recurring OOS source, and a green test suite does not catch it. Grep `docs/`, `skills/**/SKILL.md`, `README.md`, `SECURITY.md`, and `.github/workflows/` for the old token.
- Deviate when: n/a; the sweep is cheap and the failure mode is silent.

### G-Md-3: Track fenced-code-block state when parsing Markdown headings from splitlines
- Why: a parser that matched heading regular expressions over Markdown splitlines, with no fence state, split items on `###` lines that appeared inside fenced code blocks, because heading-like text inside a fence was indistinguishable from a real heading (#6676).
- Guidance: any parser that matches a `^#{1,6}\s` heading regular expression over `text.splitlines()` first computes the set of line indices inside balanced fenced code blocks and skips heading matches on those lines; reuse the `_balanced_fence_line_indices` helper in `python/larch/issue/issue_create.py` rather than re-deriving fence state.
- Deviate when: the parser documents that it intentionally reads headings inside fenced code blocks, which no current parser does.

### G-Md-4: File a bug report with structured Summary, Root cause analysis, and Suggested fix(es) sections
- Why: title-only and pasted-run-summary bug reports carry no root-cause statement, so /analyze-bugs cannot verify their fixes and /learn-from-bugs cannot cluster them (#6115, #6192, #5753); in the 2026-07-11 mining window, the structured minority of reports drove every recurring-cluster identification.
- Guidance: state what broke, why it broke, and the suggested fix under those three headings; paste evidence such as run summaries or transcripts below the headings, not instead of them. When the reporter cannot yet explain the root cause, say so explicitly under Root cause analysis rather than omitting the section.
- Deviate when: capturing a live failure before evidence evaporates; file the stub immediately, then backfill the sections before the issue closes.

## Migration discipline

### G-Mig-1: Inventory environmental assumptions before a platform migration
- Why: two platform migrations broke distant features that depended on properties the migration changed rather than on any code it edited; the Python flush port moved rendered files into the system `$TMPDIR` and corrupted every subsequent transcript capture (#6263), and the bgjob transport removed the idle prompt that the typed `p`/`progress` surface required to fire at all (#6624), and neither victim surface appeared in the migration diffs, so review could not catch them.
- Guidance: before landing a migration that changes an execution-environment property, such as temp-file location, process lifetime, turn or idle structure, working directory, or notification timing, enumerate the features keyed on that property by searching for its consumers (env-var reads, hook trigger channels, path derivations), and verify or migrate each consumer in the same change or a linked tracking issue.
- Deviate when: the changed property provably has no consumer outside the migration's edit surface; say so in the PR description and name the search you ran.

## Enforcement philosophy

### G-Enf-1: Prefer mechanical enforcement
- Why: when a judgment call recurs, promote it to a lint, hook, or structural test. This governs the file itself: entries graduate to lints over time.
- Deviate when: n/a.

### G-Enf-2: When a recurring defect graduates to a mechanical ratchet, grandfather existing violations in a reason-bearing baseline that only shrinks
- Why: a ratchet stops new violations while the baseline documents and drains the old ones. Widening the baseline, or suppressing without a reason, silently re-admits the defect and defeats the ratchet.
- Deviate when: n/a; a first-run baseline is expected, but every row and suppression carries a reason (G-Py-11).

## Fail-closed gates

### G-Gate-1: Land a fail-closed gate with or after every producer that satisfies it
- Why: gates that land before their producers or author guidance stall valid runs or turn routine changes into failures (#6880, #6882, #6875).
- Guidance: land a fail-closed gate in the same change or release as every producer that satisfies it, or later, never earlier. Update author guidance in the same change or release as every new ship-blocking contract, or in an earlier change or release, never later. Before a gate reads persisted state, verify every live writer path persists it and test the producer and gate together.
- Deviate when: a separate migration completes the producer and gate wire-up only when it lands in the same change as the gate or in an earlier same-release change already released before the gate becomes consumer-visible. A gate and its producer in one artifact are already atomic.
