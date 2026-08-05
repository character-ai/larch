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
owning redaction and publication boundary before egress.

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

`python/larch/state/session_env.py` owns validation of the session route.
`python/larch/issue/issue_create.py` and the operation-specific issue modules
own their mutation entry points. Unauthorized calls fail before `gh`, emit the
documented refusal result, and do not retry through another route.

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
`crates/larch-cli/src/kill_background.rs`). Python still owns the shared
`process_identity` helpers consumed by bgjob, stall-recovery, and the
plan-review / review-and-fix loop-identity commands until later #7677 leaves
cut those callers over. A fixed-string comparison, field equality, or closed
parser must handle interpolated labels, markers, refs, and identifiers. Do not
interpolate untrusted data into a regular expression or shell program.

## Workflow Boundaries

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
read-back contracts in `python/larch/issue/triage.py`. The typed Rust
issue-dependency adapter applies the same security terms and exact security
labels across the target title, body, and every bounded comment page before a
triage-controlled public dependency mutation. The service transport and
pagination contract is canonical in
[`supply-chain-credentials-and-services.md`](supply-chain-credentials-and-services.md#pull-request-review-and-dependency-operations).

`/issue` treats fetched issue content as an untrusted corpus. Its delimiter
wrappers are prompt-level defenses. Deduplication runs through a read-only
verdict agent that cannot mutate the repository or GitHub. Issue creation uses
the scoped live-mutation gate and outbound redaction. Public issue text still
requires prompt-level removal of internal URLs, PII, and sensitive context that
token-pattern redaction does not cover.

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

`/cleanup` and SessionStart cleanup use fixed roots, name allowlists, age gates,
bounded nested-activity checks, and symlink rejection. Retention is not an
active-run lock. Stale private session state can be deleted permanently when it
passes those gates.

SessionStart maintenance hooks are fail-soft and non-blocking. They must not
turn local paths, logs, or subprocess diagnostics into advisory instructions.
Background admin merge remains gated on validated pull-request state and green
required checks.

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
OOS path. `python/larch/issue/file_oos.py`, review tally and aggregation modules,
and `python/larch/implement/ship.py` own the current routing and checkpoint
enforcement. Their tests cover fenced and unfenced tokens, field variants,
manifest materialization, mirror-copy failure, and checkpoint refusal.

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

## Debate state and local handoff

The `debate` CLI treats its state file, agent output, and persisted session
handles as untrusted local workflow data. It accepts only canonical,
versioned JSON, binds every mutation to a full-state fingerprint, serializes
mutations with a state lock, and uses contained no-follow file operations and
atomic replacement. Active-round queues and completed bindings are persisted
before the protocol advances, so recovery never repeats a completed turn.

Cursor and Codex reuse the read-only external launcher and explicit persisted
session handles. Claude transport is caller-owned: the default debate runner
fails before dispatch unless a caller injects its Agent-tool runner. A dropped
slot is recorded before panel membership changes. `debate abort` makes only a
fixed local title-restore handoff; these verbs make no GitHub mutation and do
not create a same-user security boundary.
