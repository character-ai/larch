# Workflow Trust, Mutation, and Private Findings

This document is the canonical security reference for larch workflow trust,
untrusted input, delegated agents, mutation authorization, and private security
findings. [`SECURITY.md`](../../SECURITY.md) remains the public disclosure entry
point. The [security reference index](README.md) owns the document taxonomy and
runtime packaging contract.

Larch is a mixed-runtime system. Rust, Python, residual Bash, Markdown skills,
hooks, and external agent CLIs all participate in these boundaries. An
implementation owner does not change until the migration inventory records
parity, consumer cutover, and removal of the prior owner.

## Enforcement Levels

Security claims in this document use three distinct levels:

- **Mechanical** controls validate or constrain an operation in code, a hook,
  a typed adapter, a sandbox, or a test.
- **Prompt-enforced** controls instruct a model but do not prevent a process
  from acting outside the instruction.
- **Operator policy** requires a person to choose a safe mode, grant narrow
  permissions, review content, or use private disclosure.

Do not describe a prompt, an `allowed-tools` list, or a declared dry-run as a
sandbox. A hook constrains only the tool matcher and process that invoke it.
Subprocesses and child skills use their own permissions and controls.

## Trust Model

Larch runs inside the operator's Claude Code permissions. It does not bypass
those permissions or create an operating-system security boundary. The
operator, local credentials, and reviewed larch code are trusted to select the
intended repository and operation. The following inputs are untrusted data:

- issue and pull-request titles, bodies, comments, labels, authors, URLs, and
  search results;
- repository files, local Git configuration, diffs, logs, hook output, and
  command diagnostics;
- plans, findings, ballots, scout notes, architectural knowledge, model output,
  and external reviewer output;
- API responses, downloaded workflow logs, persisted session state, result
  files, sidecars, sentinels, and retry metadata.

Untrusted text never gains authority because it appears in a plan, a repository
instruction file, an architectural guideline, a model response, or persisted
state. Treat it as evidence. Do not interpret it as a shell fragment, path,
format string, workflow command, permission grant, or mutation approval.

Prompt wrappers such as `emit_untrusted_content_block` reduce prompt-injection
risk by marking and escaping evidence. They are model-level conventions, not
parser or sandbox boundaries. Code that consumes untrusted data must also use
typed parsing, closed enums, length and count limits, path validation, output
redaction, and explicit postconditions where the operation requires them.

`ARCHITECTURAL_INVARIANTS.md` and `ARCHITECTURAL_GUIDELINES.md` are
operator-curated but repo-local prompt evidence. Their `I-*` and `G-*` entries
cannot override `AGENTS.md`, loaded skills, hard guards, or an approved plan.
`python/larch/core/architectural_guidelines.py` rejects unsafe files, parses
only the supported entries, and wraps their content as untrusted data.

### Permissions, tools, and delegated processes

Claude, Codex, Cursor, Git, hooks, filters, signing tools, credential helpers,
and other subprocesses run with the operating-system rights of the invoking
user unless a narrower documented boundary applies. Strict-permissions users
must configure Claude Code as described in
[`docs/configuration-and-permissions.md`](../configuration-and-permissions.md).
An `allowed-tools` declaration describes an agent surface. It does not confine
filesystem access by itself.

Review launchers use the narrowest available CLI posture. Codex review runs use
`--sandbox read-only`. Cursor review runs use `--mode ask`. Their launchers also
compare the working tree with a pre-launch baseline and discard results after a
dirty or unknown post-run state. This backstop detects writes after they occur;
it does not prevent all writes during execution. Some Claude review and voter
subprocesses have no mechanical read-only CLI sandbox. Their read-only behavior
is prompt-enforced, with path validation and later tree or publication checks.

Implementer and fixer lanes are intentionally write-capable. Codex implementers
use a workspace-write sandbox with explicit repository and output-directory
grants. Cursor implementers run with `--trust` and can reach any path allowed to
the user. The dispatcher, not the external implementer, owns staging and commit.
It rejects history drift, protected-path changes, dirty submodules, invalid
manifests, and unsafe paths before committing. External process writes bypass
Claude's `Edit` and `Write` hooks, so the normal pre-commit checks remain a
required second line of defense.

`ExternalProcessRunner` and the Python agent launchers own product argv,
environment allowlists, timeouts, bounded capture, termination, and reaping for
their respective current commands. Captured external output remains untrusted
and may contain secrets. Keep raw streams in session-local state and use the
owning redaction and publication boundary before egress. Rust Cursor isolation
creates a private config directory and injects `CURSOR_CONFIG_DIR` only into the
child `ProcessRequest` environment; it does not mutate the parent process
environment, so parallel tests and parallel clones stay isolated.

`analyze-bugs runtime` uses closed `HostUtilityProgram` cases: `python3 -m
pytest` only for Gix-discovered, live, repository-relative `python/tests/`
changes, plus two fixed Make harness targets selected from touched-path
prefixes. It accepts no generic executable or target, has a 300-second deadline,
five-second shutdown grace, and 64 KiB capture cap, and caps normalized failure
evidence before it reaches private artifacts. `analyze-bugs report` is local
only: it may render a follow-up issue body, but never mutates GitHub.

Rust Codex-home preparation likewise creates a fresh confined directory below
the caller's private root. It strips inherited API settings and prior trusted
instructions from copied configuration, accepts a trusted-instructions file
only when it is a regular non-symlink, and copies a regular `auth.json` into
the private home when environment-key auth is absent. It never places a
symlink in the prepared home or points `CODEX_HOME` outside that root; the
typed `CODEX_HOME` override reaches only the vendor child request.

Rust owns the `agent launch-review` lifecycle for Codex and Cursor reviewers.
It preserves cap, preflight, execution, retry, and postprocessing order while
the shared process runner remains the only Rust product-spawn and live
process-group owner. On cancellation or timeout, a final group kill follows a
gracefully exited leader so a surviving descendant cannot escape cleanup.
Darwin startup locking uses a caller-selected temporary root, a bounded retry
budget, a confined lock directory, and an owned delayed-release handle. Stall
writers reuse `LauncherArtifactPaths` for the `.stall.json` path, bound and
redact captured transcript and Git status text, and publish through the shared
confined atomic writer. A detailed Cursor compatibility sidecar remains
best-effort and cannot turn a successfully published primary artifact into a
launch failure.

### Same-user state and sandbox limits

Session directories, cache files, startup locks, `.meta` files, result envs,
sentinels, and PID or process-group records are not authentication boundaries.
Their readers validate shape, ownership assumptions, containment, file type,
identity, and freshness before use. Writers use the owning guarded and atomic
helpers. Do not `source`, `eval`, or execute a persisted data file unless its
specific contract defines a closed sourceable format and validates every key.

These controls do not defend against a hostile process running as the same
operating-system user. Such a process may inspect environments, alter writable
session state, race pathname checks, or modify plugin cache data. Temporary
directories are private workflow state, not a confidentiality boundary against
the same user. `/tmp` is shared scratch and provides no cross-skill secrecy.

Rust filesystem adapters require explicit absolute roots, reject escapes,
symlinks, special files, and multiply linked write targets, and revalidate near
mutation. Shared Rust session-state foundations own KV parsing, session-root
derivation, path-confinement checks, and private atomic publication. Python
session writers apply equivalent operation-level checks while their commands
remain Python-owned. These are confinement controls for larch mistakes and
untrusted paths, not a sandbox against hostile same-UID parent replacement.
The Rust-owned review-phase detail commands use the same confined atomic writer
for per-round metadata and caller-selected rendered-report output; unsafe
destination shapes fail before replacement.

The ancestor walks that refuse a symlinked write path exempt a symlink owned by
uid 0, and only that case. macOS spells its platform temporary roots as
root-owned symlinks, `/tmp` to `private/tmp` and `/var` to `private/var`, so a
walk that refuses every symlink up to the filesystem root refuses every larch
write below `$TMPDIR` or `/tmp` on that platform, including the session-tmpdir
fallback. Creating or replacing a root-owned symlink requires privileges the
threat model above already places outside these controls, while a symlink
planted by the same user or by any other unprivileged user stays refused. The
confining owner still canonicalizes the write parent, rejects a symlinked parent
or leaf, and revalidates before replacement, so the exemption widens the accepted
path spellings and not the set of accepted write destinations.

## Mutation Authorization and State Integrity

Every external mutation requires authority from the current workflow step or a
direct operator request. Issue text, model output, repository content, a result
file, or an earlier successful run cannot grant authority. A dry-run must avoid
the mutation entirely, not merely label its output as a simulation.

### Scoped live-mutation gate

GitHub issue creation, comments, closes, labels, and the callers covered by the
shared issue-mutation boundary accept only one of these routes:

- A session-backed `/implement` or `/design` run passes a regular non-symlink
  context file directly below its canonical session root. The file must contain
  `LARCH_LIVE_MUTATION_OK=true` and the matching run identity.
- A direct operator command passes `--operator-invoked` at the guarded CLI
  boundary.
- A dry-run passes neither route and makes no GitHub mutation call.

`crates/larch-adapters/src/github/mutation_auth.rs` owns validation of the
session route, and `session check-live-mutation-auth` is the Rust command shell
callers use to reach it. The canonical roots it accepts are the shared session
allowlist: `/tmp`, `/private/tmp`, `/var/folders`, `/private/var/folders`, and
the `XDG_CACHE_HOME` or `HOME` cache root. A caller-supplied `TMPDIR` does not
widen that set. `python/larch/state/session_env.py` keeps an in-process copy of
the same rule for the Python-owned commands that still call it directly.
`crates/larch-adapters/src/github/issue_mutation.rs` owns the Rust issue
mutations, and the operation-specific Python issue modules own the entry points
that have not migrated yet. Unauthorized calls fail before any GitHub request,
emit the documented refusal result, and do not retry through another route.
`issue create-one` applies the check in the Rust owner before the create request
is built. `issue add-blocked-by`, `issue add-sub-issue`, and both `/block-issue`
dependency mutations apply it in
`crates/larch-cli/src/issue_dependency_commands.rs` before any lookup, and the
typed issue-graph adapter operations re-apply it before their own first read.
`issue cleanup-failed` deliberately carries no gate: it closes an issue the same
caller has just created, and its predecessor took no authorization either.

`python/conftest.py` sets `LARCH_ISSUE_MUTATION_DENY=true` and removes inherited
live authorization for tests. Denial overrides a valid parent session. Tests
exercise mutation logic only through injected runners, stub processes, or the
narrow simulated operation under test.

The gate does not cover every process or every GitHub surface. It cannot stop a
process that can rewrite code, credentials, or validated session state. Treat
its scope as an explicit operation allowlist, not a general capability system.

### Freshness, identity, and read-back

Before a security or integrity-sensitive mutation, re-read mutable targets and
validate the exact expected repository, issue or pull request, state, revision,
head SHA, timestamp, lease, and input fingerprint required by that operation.
Persisted results carry the identity of the inputs that produced them. Consumers
reject or recompute stale results as required by I-Stale-1.

After mutation, read back the owning surface and verify the requested
postcondition. An uncertain mutation is not blindly retried. Idempotent writes
may reconcile and retry only after proving absence. Creates without a stable
collision key return an ambiguous outcome instead of risking a duplicate.

Protected issue-body updates require an expected `updatedAt`, the expected
state, a matching lease, one named block, redaction, and a strictly newer exact
read-back. Named-block writers resolve the lease identity from `RUN_ID`, then
the rehydrated `LARCH_RUN_ID` and `SESSION_ID`; missing all three still fails
closed. Dependency and migration-governance paths bind blocker, owner, plan,
base, and lease evidence. `/implement` evaluates receipt base-scope freshness
between the receipt base and the current base target (`origin/main`, or
`upstream/main` for a fork run), never the implementation-branch `HEAD`.
Plan, owner, and blocker hashes remain live checks, and in-scope base-target
drift fails closed. Unavailable or stale evidence fails closed.

`crates/larch-adapters/src/github/issue_mutation.rs` is the single Rust owner
for issue title, body, label, comment, and close writes. Tracking comment
creation, replacement, and deletion pass through this owner, which verifies the
returned comment identity and body, then verifies create and replacement with a
same-surface comment-list read-back; deletion is verified by absence from that
list. Issue creation accepts a canonical create response only after a same-issue
GET proves its title, body, labels, identity, and open state; a failed proof
names the orphan for best-effort closure.
Tracking lease activation also applies the lease body and `[IMPLEMENTING]`
title together, bound to the preflight title, body, and admission-relevant
label hashes, timestamp lower bound, and current base-target SHA. Metadata-only
timestamp advancement is accepted only while those admission-relevant issue
fields remain exact; pre- and post-mutation governance checks consume a fresh
Rust-materialized post-mutation body and retain blocker and owner race
detection. Python tracking workflows reach those
operations through `scripts/larch.sh`; former in-process Python consumers use
typed `rust_runtime` calls, and external command consumers keep the same
verified entrypoint. `final-report write` calls the same Rust tracking owner in
process to preserve its own output envelope. Later Rust callers use
`larch_adapters::github::IssueMutationOwner`, which applies the shared
live-mutation gate before its first read, serializes through the shared GitHub
runtime lock, redacts outbound titles, bodies, and comments, and proves a
fresh exact read-back without a blind retry. The Rust-owned `/combine-issues`
apply path reads every source's native blockers before creation, re-adds those
blockers to the combined issue, and verifies the full set before it can
close a source. A partial transfer leaves sources open and reports the durable
combined issue URL. Deferred source closure re-reads the combined host and each
source's active blockers; missing or unverifiable inherited edges leave that
source open. If a source-close batch becomes partial after the combined issue
is durable, it also reports that URL and its exact closure tally. A close
comment is published before the close while holding the same mutation lock;
comment, close, or closed-state failure is never reported
as a successful close. Python remains responsible only for issue callers that
have not reached an explicit atomic cutover.

`audit-runs close-priors` first performs a bounded labeled issue read and
refuses without commenting or closing when more than one matching prior report
is present. Its one permitted close goes through that same owner and emits a
verified close result only after the comment and closed-state read-backs. The
related backlog advisory is read-only and never posts a comment.

### Local mutation safety

Wire files use closed key sets, single-line values, explicit size limits,
non-symlink regular files, and atomic publication. The Rust CLI owns `kv get`,
`session read-key`, and `session read-keys`; their parsing and filesystem
primitives live in `larch-core` and `larch-adapters`. Session writer commands in
`python/larch/state/session_env.py` still own approved destinations and key
allowlists. Prompt-side orchestration must not write or repair trusted result or
session files directly.

Destructive cleanup or synchronization validates the exact root and target,
rechecks mutable identity immediately before acting, and limits deletion to an
operation-owned allowlist. A persisted PID or process group is signaled only
after process identity is re-verified. The Rust runtime owns process-identity
capture, validated process-group termination, and
`session kill-background-processes` (`crates/larch-core/src/process_identity.rs`,
`crates/larch-adapters/src/process_identity.rs`,
`crates/larch-cli/src/kill_background.rs`). Rust-owned stall-state clearing
consumes the Rust bgjob registry and process-identity validation directly.
Python still owns the shared `process_identity` helpers consumed by the Python
bgjob runtime and the plan-review / review-and-fix loop-identity commands until
later #7677 leaves cut those callers over. Rust-owned stall classification also
consumes the Rust bgjob registry directly. Classification and attempt artifacts
are published atomically below the validated temporary root, and attempt values
reject line breaks. Escalation rows are appended under an exclusive lock through
a non-symlink file descriptor; unsafe detail filenames cannot forge TSV fields,
and the append repairs a missing terminal newline before writing one complete row.
Unsafe canonical or fallback paths fail closed, while a genuine canonical write
failure may use the existing bounded fallback artifacts. A fixed-string
comparison, field equality, or closed parser must handle
interpolated labels, markers, refs, and identifiers. Do not interpolate
untrusted data into a regular expression or shell program.

Rust owns every bgjob command: durable registry records, `bgjob adapt`, and the
daemon `start`, `wait`, `status`, and `reap` surfaces
(`crates/larch-core/src/bgjob.rs`, `crates/larch-core/src/bgjob_daemon.rs`,
`crates/larch-cli/src/bgjob_adapt.rs`, and
`crates/larch-cli/src/bgjob_commands.rs`). The adapter confines its state files
and holds a pinned decision lock before it reattaches or launches. `start`
detaches the daemon by re-executing the same verified binary in a daemon role,
and the daemon binds the owner's recorded process identity, never a bare pid, so
a reused pid never keeps an orphaned job alive (#6604). The daemon terminates a
timed-out or orphaned child only through validated process-group termination.
A child may legitimately replace its wrapper through `exec`; that transition
retains its recorded PID, process group, and start time, which are revalidated
before signaling. Other persisted identities retain exact command validation.
Legacy background-job rows use the same transition policy because they predate
the explicit registry marker.
If the recorded group leader has disappeared while a numeric group remains,
larch cannot prove that a recycled group is still its child and retains the
record instead of signaling it.

When a daemon dies, `wait` and `reap` share an exclusive, process-identity-bound
recovery lease for its durable registry row. The lease holder validates the
recorded child group, logs each intended signal, and proves that the full group
is absent before it removes the row. A signal attempt, bounded child reap, or
missing leader alone is not proof of teardown. If that proof fails, larch keeps
the registry state and an actionable teardown diagnostic; it does not publish a
`BGJOB_RC` result envelope or claim `DONE`. `wait` reports the non-success
`DEAD` diagnostic instead. This fail-closed retention is an explicit safety
difference from the retired Python behavior, which could discard the row after
an unverified timeout or orphan cleanup.

## Workflow Boundaries

### CI cache trust

The [CI tool bootstrap and caches](supply-chain-credentials-and-services.md#ci-tool-bootstrap-and-caches)
section is the canonical cache-class and publication contract. Pull-request and
merge-group workflows may consume only the explicitly scoped default-branch
cache classes; they do not gain authority to publish a compiler-output cache or
trusted policy cache. A coverage target cache is dependency-only, bound at a
measured 1,350,000,000 bytes, and enabled only after independent end-to-end
measurements prove it helps. Neither a cache restore nor its diagnostic metadata
waives the coverage, artifact, executable, repository-policy, or
plugin-validation gates.

The manual target-cache benchmark is isolated from that production cache
contract. Its fixed workflow condition requires a direct `workflow_dispatch`
of `refs/heads/main`, its benchmark-only key cannot be restored by the normal
coverage lane, and its decimal size input is capped before the shared action
can save. During that exact dispatch, `rust-full` stays cache-off as the paired
control. The benchmark exists only to collect the independent warm-cache
comparison; it does not authorize a pull request or normal manual run to
publish compiler output.

### CI Rust selection trust

The pull-request `rust-selection` job has read-only workflow permissions. The
checkout action supplies GitHub's tested merge candidate with full history, and
a separate checkout supplies the pull-request base. The job builds that base's
`larch` executable and invokes its `ci rust-select` command through
`scripts/larch.sh`. The command proves the base commit, candidate commit, and
base ancestry before it reads the candidate diff. An invalid identity,
unavailable history proof, missing trusted base executable, or selector failure
selects `full`. Candidate code can supply the tree being classified, but cannot
author the classifier that authorizes a non-full lane. Selector, workflow,
coverage-action, and selector-redaction/workspace-metadata changes are explicit
global `full` triggers.

The selector validates commit identity, checked-out state, and base ancestry
before it inspects a diff. Missing history, a malformed or empty diff, unknown
path, metadata failure, unsupported workspace shape, and selector failure all
become `full`. The partial decision is a strict Rust-source package closure
derived from locked offline Cargo metadata. It includes normal, build, and dev
reverse dependency edges; it must contain `larch-cli` and be smaller than the
workspace. The selected lane builds that candidate executable, runs repository
policy and plugin validation, and supplies the Python artifact, so it does not
mistake an all-workspace closure for a partial path.

Skip ownership is explicit rather than extension-based. Each root or path
family in the allowlist names the normal lint, agent, Python, plugin, and/or
trusted-main repository-policy job that continues to validate it. The
`trusted-main-rust-policy` cache trust contract is canonical in
[Supply Chain, Credentials, and Services](supply-chain-credentials-and-services.md#ci-tool-bootstrap-and-caches).
The selection job and skip job both verify that content-derived identity before
they execute it. A cache miss or failed verification selects `full`; no
pull-request-provided Rust binary is accepted for `skip`.

`RUST_CI_PARTIAL_ENFORCEMENT` remains `false` while the partial class is under
observation. `RUST_CI_SKIP_ENFORCEMENT` is `true` only because its durable live
record has three independent non-full proposals, successful full backstops, and
zero false-safe results. A proposed `partial` is recorded with an
observation-window effective `full` mode; an enforced `skip` still falls back
to `full` if trusted-main policy validation fails. Only a reviewed workflow
update may set a class-specific value to `true`. A candidate checkout, selector
output, cache result, or pull-request label cannot promote a class.

Every dynamic JSON and summary string passes through the Rust core redaction
boundary and a residual-secret rescan; redaction failure emits a static `full`
result without changed-path data. The step summary HTML-escapes those redacted
fields. The structured result preserves the classifier proposal and adds the
effective execution mode, reason, rollout state, and observation flag after
cache validation and any safe override; it is an artifact for audit, not an
authorization token. The stable required `rust-coverage` status accepts only
one successful producer (`rust-full`, `rust-partial`, or `rust-skip`). An
unavailable selector requires the full producer, which must succeed before the
stable status can pass. Main, manual, scheduled, merge-queue, and unknown
events continue to run the full lane. The `full-rust-ci` label is a
safe pull-request override because it can only force that same full path.

### Design

Issue text, feature text, plan text, findings, ballots, scout output,
architectural guidance, and operator refinement text are untrusted evidence.
Inline prompt renderers redact and escape these blocks. Path-only handoffs pass
validated paths and never relay file bytes through `KEY=value` output.
`python/larch/rendering/rendering.py` and
`python/larch/issue/issue_wire.py` own these render and wrapper boundaries.

The Step 1d.7 outline is binding only after operator approval. `--skip-approve`
removes that human review for the outline and final plan. Use it only when issue
and refinement input are trusted or generated by a controlled pipeline. It does
not disable size, validation, finding-apply, or persistence gates.

`validate_design_tmpdir` in `python/larch/state/session_env.py` confines design
state before any quiet-log, result, pause, or publish write. Pause markers bind
the issue, repository, run, snapshot, and allowed recovery branch. Restore uses
a staged tree, validates every path and required artifact, and installs only
after the complete snapshot verifies. GitHub issue markers remain editable by
collaborators and are not an authenticity proof.

Dialectic drafter, debater, judge, and assessor output is advisory model data.
It cannot edit `plan.txt` or clear a gate by declaring itself safe. Compact
digests reach approval surfaces through untrusted framing. Operator text uses a
file-backed request and never enters shell argv through interpolation.

### Implementation and shipping

The approved plan limits scope but remains untrusted text. `/implement` passes
it to coders and reviewers as evidence. The dispatcher validates the manifest,
branch, history, changed paths, submodules, and worktree before it stages or
commits. Model-authored commit text passes through secret redaction before Git
receives it.

Preflight rejects closed or managed issues, audit reports, live blockers, and
missing design state before session setup. A `[DESIGNED]` title is mutable
GitHub metadata, not proof of plan identity. `--force` may skip semantic plan
review and the designed-prefix check. It cannot admit a missing or malformed
`larch:plan`, suppress later branch or worktree gates, or turn issue prose into
an execution plan. Every admitted bypass is recorded. Blocker lookup still has
its documented fail-open behavior when GitHub dependency reads fail, so an API
outage can produce a false negative.

`python/larch/implement/ship.py` owns the active post-review pull-request, CI,
merge, and teardown state machine. It consumes typed, bounded, redacted result
envelopes. Pull-request creation and updates require current scope and coverage
artifacts. CI fixes receive a bounded redacted digest, not raw failed logs.
Conflict fixers receive validated repository-relative paths and may edit only
the named conflict files. The driver owns staging, rebase continuation, push,
and merge.

Recovery never applies pre-merge mutations to a merged or closed pull request.
Manual reconciliation first proves the repository and merged pull request, then
writes only its closed state allowlist and verifies that stall and bail overlays
are clear. Assessment waivers and state artifacts stay inside the validated run
root and bind to the current run identity.

### Review

Plans, diffs, findings, reviewer prose, votes, and dynamic scout notes are
untrusted. Review prompts use fixed trusted templates. Scout output can supply
file or aspect hints but cannot add commands, tools, scope, or output grammar.
Accepted findings still pass through the fix-coder contract. Unsafe or
out-of-scope instructions in finding prose are ignored.

The code-reviewer security lane covers injection, authorization, secret
handling, cryptography, deserialization, SSRF, path traversal, and dependency
risk. Namespaced context tags and a data-not-instructions preamble reduce prompt
injection but remain model-level conventions. Dynamic prompt bodies with
reserved slugs, unsupported focus areas, unsafe closers, or standalone YAML
fences are rejected before reviewer dispatch.

Review retry metadata is parsed as JSON arrays and closed typed fields, never
with `eval`. Tool-specific argv shapes, timeouts, prompt paths, workdirs, output
containment, and sentinels are validated before replay. Invalid outer-launcher
metadata cannot fall back to an inner command that skips launcher-owned checks.

Review and plan-coverage snapshots are untrusted local state. Readers require
a contained non-symlink root, regular no-follow files, complete artifact sets,
and identity matching the live plan, diff, and run. A partial, stale, malformed,
or unsafe present set fails closed. Snapshot creation and cleanup never rewrite
an unsafe pre-existing tree.

### Research

`/research` is best-effort read-only for the repository. Its skill-scoped
`scripts/deny-edit-write.sh research` hook mechanically confines only Claude's
matched `Edit`, `Write`, and `NotebookEdit` calls to canonical `/tmp` and the
larch cache sessions root (`~/.cache/larch/sessions`, the larch-owned session
scratch tree, so a nested `/issue` can write its session-setup tmpdir body
files) while a fresh activation sentinel exists. It does not cover `Bash`, child `Skill`
invocations, or external subprocesses. `allowed-tools` does not add confinement.

Research Cursor and Codex lanes run against the working tree with write-capable
user privileges. Their non-modification rule is prompt-enforced. Synthesis and
revision subagents have their own permissions, and the parent hook does not
propagate. Operators who require a stronger read-only posture must constrain
Claude Code permissions and external tool visibility or avoid those lanes.

Successful research publishes the full report to GitHub unless `--no-issue` is
set. Reports can contain internal architecture, private infrastructure, or
security-sensitive analysis. Use `--no-issue` for sensitive work. Outbound
secret redaction is a backstop, not a classifier for internal URLs, PII, or
domain-specific sensitive content.

### Triage and issue filing

`/triage` treats issue content, repository content, Git output, probe output,
and model verdicts as untrusted. It activates scratch writes only after the
security, repository-target, and immutable-main gates pass. Reproduction uses
the named fixed probes from the triage contract. Issue-supplied commands,
credentials, destinations, and mutations are forbidden.

Before every public mutation, triage rechecks security classification and
freshness. Uncertain security classification routes to private disclosure and
no public issue mutation. Allowed edits and closes pass the expected
`updated_at`, current state, redaction, operator authorization, and exact
read-back contracts in `crates/larch-cli/src/triage_commands.rs`, over the
grammar in `crates/larch-core/src/issue/triage.rs`. The typed Rust
issue-dependency adapter applies the same security terms and exact security
labels across the target title, body, and every bounded comment page before a
triage-controlled public dependency mutation. The service transport and
pagination contract is canonical in
[`supply-chain-credentials-and-services.md`](supply-chain-credentials-and-services.md#pull-request-review-and-dependency-operations).

`/issue` treats fetched issue content as an untrusted corpus. Its delimiter
wrappers are prompt-level defenses. Its candidate snapshot splits the query so
the data contract holds within the reviewed transport bound: open issues are
fetched exhaustively, so an over-bound open corpus fails closed rather than
dropping blockers, while recent closed issues fill the remaining budget as a
bounded-partial snapshot whose omitted older tail is reported instead of
silently narrowing deduplication. A refused fetch names its real class,
including the transport-limit case, and never mislabels the transport bound as a
network, authentication, or rate-limit failure. Deduplication runs through a
read-only verdict agent that cannot mutate the repository or GitHub. Issue
creation uses the scoped live-mutation gate and outbound redaction. Public issue
text still requires prompt-level removal of internal URLs, PII, and sensitive
context that token-pattern redaction does not cover.

`/deps` applies the same untrusted-corpus treatment to open issue titles,
bodies, and comments. It validates rewrite, close, and dependency targets
against the fetched snapshot, requires operator approval before mutation, and
revalidates issue state during apply. Delimiter wrapping and endpoint checks
reduce prompt-injection risk but do not create a parser-enforced sandbox.

### Rejected analysis

`/rejected-analysis` treats published findings and run-log prose as untrusted.
Verifier prompts wrap the candidate, pin the expected file location, and demand
the closed verdict format. Launchers use their read-only posture and dirty-tree
backstop. Replies must bind to the candidate path. Ledger, sidecar, and issue
batch fields are TSV-sanitized before persistence.

Confirmed non-security findings are filed only through `/issue`, preserving
redaction, deduplication, and dependency handling. Finalization reruns the
security classifier. Confirmed or uncertain security findings never enter the
public filing batch.

### Architectural assessment

Architectural knowledge, materialized diffs, assessor output, route detail, and
diagnostics are untrusted evidence. `architectural-assessment materialize` owns
deterministic diff filtering, input fingerprints, durable state, coverage
reuse, and reassessment requests. The read-only `larch:arch-assessor` reads only
the supplied paths and authors every requested assessment kind.

`architectural-assessment submit` revalidates HEAD and diff identity, parses the
closed state and note grammar, redacts the note, reapplies its size cap, and
publishes atomically. A first-submission guideline deviation cannot inject an
`Exception:` block. Only the documented decline path may add a validated block
with rationale, author tier, and date.

The main workflow does not author, repair, or inspect assessment prose on this
path. Stale, malformed, incomplete, unavailable, or mismatched results do not
clear the gate. A fresh assessor judges every repair. An invariant violation
hard-stops after the bounded fix ladder; no waiver or operator override accepts
it. `python/larch/core/architectural_guidelines.py` and the Step 8 ship route
own the current mixed-runtime implementation.

### Destructive and background workflows

`/set-up-forked-open-source-repo` verifies the fork parent, prints exact branch
identities, requires explicit confirmation, and reprobes immediately before its
destructive mirror push. A confirmed sync can delete or overwrite fork refs.
URL overrides remain operator-supplied trust inputs.

Rust-owned `/cleanup` and SessionStart cleanup use fixed roots, name
allowlists, age gates, bounded nested-activity checks, and symlink rejection.
The sweep collects session directories named by live environment state and
current pointers before it considers deletion; those live directories remain
protected regardless of age. An unreadable current pointer makes the
age-based sweep fail closed. Retention is not a lock for an unknown or
unreferenced stale session. Stale private session state can be deleted
permanently when it passes those gates.

SessionStart maintenance hooks are fail-soft and non-blocking. They must not
turn local paths, logs, or subprocess diagnostics into advisory instructions.
Automated merge remains gated on validated pull-request state and green
required checks. Immediately before mutation, the Python pull-request owner
reads the active default-branch rules. An enabled merge queue receives a plain
queue submission without an admin bypass or branch-deletion request. Durable
state records queue acceptance only after bounded GraphQL read-back observes a
queue entry, auto-merge request, or completed merge. It distinguishes that
acceptance from completion, and post-merge work waits for an observed `MERGED`
state. A policy-read failure stops before mutation. Direct admin merge remains
the no-queue fallback. The development-only
release command has a narrow queue bypass that requires both merge-commit mode
and a version-bump commit so the already-tagged candidate remains an ancestor
of `main`. If that direct admin merge is rejected on a queue-enabled branch,
the release stops without a plain merge or queue fallback.

## Security Findings in OOS Workflows

Security-sensitive or uncertain findings are private. Never file them through
`/issue`, copy them into a public issue or pull request, include them in
published run logs, or fold them into an unrelated implementation. Follow the
responsible disclosure instructions in [`SECURITY.md`](../../SECURITY.md).

Review and design tally paths route security-tagged OOS blocks to the
session-local `security-oos-observations.md` sidecar. The sidecar never merges
into `oos-accepted-design.md`, `oos-accepted-review.md`, `oos.md`, or a public
issue batch. A non-empty sidecar keeps `OOS_PENDING=true` and blocks pull-request
creation until private disposition completes.

Public-boundary classifiers recognize these structured security signals:

- an unfenced canonical `focus-area=security` token;
- a dedicated line-start `focus-area` field whose value begins with `security`,
  including values such as `security-hardening` and supported markup or
  separator variants;
- a block-opening heading that begins with `[security]` or `<security>`,
  optionally after `[OUT_OF_SCOPE]` or `[OOS]`.

Canonical tokens that appear only inside inline code or triple-backtick fences
are meta-discussion, not a security route. A later prose heading that merely
contains `[security]` is not an opening tag. External implementer manifests use
the same dedicated-field predicate after sanitization. A security-looking title
alone does not route a manifest item.

Classifier failure is private by default. It must never fall back to the public
OOS path. Manifest materialization and private-sidecar routing are Rust-owned by
`crates/larch-cli/src/oos_commands.rs` and
`crates/larch-core/src/issue/oos_batch.rs` behind
`scripts/larch.sh oos materialize-manifest`. Rust checkpoint enforcement is
owned by `oos_commands.rs` and `larch_core::issue::oos_disposition` behind
`scripts/larch.sh oos disposition-checkpoint`; the Rust filing driver in
`crates/larch-cli/src/oos_file_commands.rs` refuses post-checkpoint completion
while the sidecar remains.

Review and design tally/aggregation modules retain their distinct source-side
classification responsibilities. Under receiving umbrella #7681,
`python/larch/implement/dispatch_ship.py` retains Step 8 routing and
post-checkpoint bookkeeping. The surviving
`python/larch/issue/file_oos.py` callers use in-process block parsing/counting,
title normalization, and run-id resolution under receiving umbrella #7680; the
module is not an OOS command owner or fallback. Rust tests in `oos_commands.rs`,
`oos_file_commands.rs`, `oos_batch.rs`, `oos_disposition.rs`, and
`oos_record.rs` cover manifest materialization, field variants, private
routing, and checkpoint refusal.

## Major Residual Risks

- A hostile same-UID process can inspect credentials in child environments,
  tamper with writable state, race path checks, and alter plugin data.
- Prompt wrappers reduce but do not eliminate prompt injection. A model can
  still misunderstand or disobey evidence framing.
- Some Claude, Cursor, Codex, Git, hook, and helper paths retain user-level
  filesystem access. Prompt-only read-only rules are not sandboxes.
- Pattern redaction does not cover every credential, internal hostname, PII,
  partial token, or domain-specific secret. Minimize captured and published
  text even when a redactor runs.
- GitHub collaborators can edit issue bodies and workflow markers. Freshness,
  leases, hashes, and read-back reduce risk but do not prove authorship.
- Dry-run, mutation authorization, and test-deny controls apply only to their
  documented entry points. They do not restrict arbitrary code with the same
  credentials.

## Umbrella

`/umbrella` treats input issue text, draft records, agent output, and child `/issue` output as untrusted. It applies one explicit approval gate; `--skip-approve` changes only that presentation wait. The skill persists immutable leaf identities and in-flight state before filing, confirms the child sentinel and machine counters, performs live authorization and freshness checks for every mutation, redacts outbound public content, and reads back the final native graph. Ambiguous recovery, incomplete dependency analysis, failed redaction, or missing verification stops the run without a replacement create.

Nested `/design` and `/implement` partitions use a narrower prepared-artifact path. The child accepts it only with immutable parent lifecycle context, one numeric managed issue, `--skip-approve`, and the complete internal flag group. Input and dependency files must be contained regular files under the declared parent scratch root. `/umbrella` parses and bounds the exact generic batch, rejects malformed or cyclic dependency graphs, persists deterministic leaf identities and an atomic child-local dependency copy before any create, and keeps `/issue` duplicate detection enabled. Filing consumes that copy instead of rereading the parent TSV. The parent approval covers only those exact leaves and edges; the child cannot re-decompose them or ask a broader second question.

Final conversion is one centralized issue-mutation operation. It accepts only an open `[DESIGNING]` or `[IMPLEMENTING]` source, requires the target title to preserve the complete source title after replacing its lifecycle prefix with `[UMBRELLA]`, requires the complete prior body to survive inside the new body, redacts before write, and verifies a fresh read-back. The child compares the live prepared-artifact hashes and deterministic leaf/edge shape to the persisted proposal, then writes a repository-, issue-, artifact-, and graph-SHA-256-bound parent completion sentinel atomically only after leaf and graph verification. The parent rehashes both live artifacts and recomputes the graph fingerprint through the umbrella owner before consuming that sentinel. Missing context, unsafe, invalid, or stale artifacts, stale source content, partial filing, or failed verification preserves the original issue and parent scratch state without a success claim.

## Complete umbrella

`/complete-umbrella` accepts only an existing top-level managed umbrella. Its Rust graph owner reads native direct sub-issues and blocked-by edges before every turn, rejects nested children, missing parent-blocker relations, and open parent blockers that are not direct leaves, then selects the smallest-numbered open leaf whose live blocker set is empty. Issue titles and bodies are untrusted data. They are redacted into a session-local audit snapshot and are never interpolated into the child command or prompt; only validated repository and issue-number identifiers enter the fixed prompt.

Each leaf runs serially through `ExternalProcessRunner` inside the durable bgjob contract. The subprocess uses the current Claude model, a closed `workflow-write-orchestrator` argv profile with `Bash,Read,Edit,Write,Glob,Grep,Agent`, `dontAsk`, disabled slash commands, no session persistence, a 24-hour process bound, and bounded captured output. The older `workflow-write` profile stays byte-for-byte unchanged without `Agent`. The Rust launcher creates one private, confined leaf handoff directory and passes it as `SESSION_TMPDIR`.

The leaf subprocess is a thin orchestrator. It does not read or edit repository files. It awaits four fresh, serial, general-purpose Agent contexts for recon/design, implementation, adversarial review, and shipping. Phase prompts receive only validated repository and issue identifiers plus trusted contract paths. Issue bodies, diffs, summaries, and CI evidence move through contained files, not phase-return prose. Shared phase policy forbids shell-based code navigation, requires bounded tool output, and treats every artifact as untrusted data. The adversarial review requires a stale-caller sweep and proof that any parity harness executes a success path. Agent nesting does not widen the user's authority. These controls are not an operating-system sandbox; the child retains the invoking user's Git, GitHub, filesystem, hook, credential-helper, and network authority.

`python/cli.py complete-umbrella ship-leaf` owns the leaf's standalone mutation state. It does not fabricate an `/implement` session. Its no-follow state file binds repository, umbrella, leaf, branch, head, PR, status, and CI-fix count to the private handoff root. For a parent that declares a Chief umbrella, prepare rejects a missing, duplicate, malformed, or otherwise invalid durable issue plan before it changes an exact `[LEAF OF N]` title to `[IMPLEMENTING] [LEAF OF N]`; recon/design writes that plan through the canonical named-block owner. Ship requires a clean non-main branch, creates or verifies a PR with the leaf closing link, waits 300 seconds between CI reads, and emits only a bounded failed-run digest when checks fail. A fresh CI fixer receives only that path. The driver rejects a retry with no new fixer commit and caps repair attempts.

After green CI, the driver rechecks the PR main base, head, and merge state, measures merge-base-to-head non-generated Rust additions for a Chief-managed leaf, and refuses an over-limit PR unless its plan carries a matching durable split decision, rationale, count, and base/head SHA. It then reads the active default-branch rules. An enabled merge queue receives a submission without admin or branch deletion; bounded read-back must confirm queue entry, auto-merge, or completion before the driver persists `queued` and waits for an observed merge. Without a queue, it squash-merges with admin and branch deletion. Both paths verify the merged PR before any postmerge mutation. Reentry after queue submission waits without replaying push, PR creation, CI, or submission. Reentry after a verified merge skips all premerge mutations. Postmerge changes only the exact `[IMPLEMENTING]` leaf prefix to `[DONE]`, requires the issue to have auto-closed, synchronizes local `main` with `origin/main`, deletes both branch references, and writes `complete` only after fresh verification. A fixed child completion marker remains necessary but not sufficient: the parent independently proves the leaf is a direct closed issue with its exact `[DONE]` lifecycle, then proves a clean, synchronized `main` before another turn.

Parent title mutations and graph writes require explicit operator mode, freshness checks, centralized title mutation, and exact read-back. Final close re-fetches the graph before and after the mutation and refuses any open leaf or open non-leaf parent blocker. Audit gaps are filed through `/issue` with no deduplication because their identities are exact. Before filing, a read-only preflight confines and validates the bounded caller-owned title and body files. Before attachment, the graph owner compares the live new issue title and body byte-for-byte with those files, rejects another parent or any child, adds the sub-issue and parent blocked-by edges idempotently, and reads both back.

The inline final audit treats its snapshot as untrusted requirements data and keeps Write confined to the larch session scratch root through the token-gated hook. It does not delegate architectural judgment. Security-sensitive findings are not filed publicly. Child failure, malformed output, stale state, graph deadlock, an open orphan blocker, mutation ambiguity, dirty repository state, or failed sync proof terminates the run without advancing another leaf or claiming parent completion.

## Debate state and local handoff

The `debate` CLI treats its state file, agent output, and persisted session
handles as untrusted local workflow data. It accepts only canonical,
versioned JSON, binds every mutation to a full-state fingerprint, serializes
mutations with a state lock, and uses contained no-follow file operations and
atomic replacement. Active-round queues and completed bindings are persisted
before the protocol advances, so recovery never repeats a completed turn.

Cursor and Codex reuse the read-only external launcher and explicit persisted
session handles. The public skill gives every slot the same bounded, redacted
subject in its round-1 input as base64 data with a data-not-instructions preamble; round 2 carries only the validated mailbox delta. Claude runs in one
read-only `debater` Agent session and continues only through `SendMessage`; its
exact final ledger enters the protocol through a contained, bounded input file.
A dropped slot is recorded before panel membership changes.

The protocol verbs do not mutate GitHub. `python/larch/debate/publication.py`
owns the public title lifecycle through the shared issue-mutation compare-and-
swap and read-back boundary. Preparation snapshots one open, unowned source;
start requires the unchanged snapshot; finish accepts only its exact
`[DEBATING]` title; restore changes only that same title and skips a foreign
replacement. Missing `SendMessage`, two unavailable external vendors, and
failed persistent-session bootstrap stop before start. Free-form source and
proposal creation use `/issue` machine counters plus caller-owned sentinels.
Proposal and source links must both verify before finish. Abort comments use a
run-keyed upsert marker and fixed sanitized text, so retries cannot publish raw
vendor output or create duplicate abort records. These controls do not create
a security boundary between processes running as the same user.
