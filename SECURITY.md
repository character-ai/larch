# Security Policy

## Policy Scope

This policy covers the latest released larch plugin, including its runtime-only
plugin projection. It is the stable public entry point for supported versions,
responsible disclosure, security scope, and the high-level trust model. The
[security reference index](docs/security/README.md) maps detailed technical
security contracts to one canonical owner.

The detailed sections below remain authoritative while the focused references
are introduced. During that migration, the index records the current owner and
the target owner. A focused reference becomes authoritative only when the root
section points to it. This staged reorganization does not change security
behavior.

## Supported Versions

| Version | Supported |
|---------|-----------|
| Latest  | Yes       |
| Older   | No        |

Only the latest released version receives security updates.

## Reporting a Vulnerability

If you discover a security vulnerability in larch, please report it responsibly:

1. **Email**: Send details to <zhupanov@yahoo.com>
2. **Do not** open a public GitHub issue for security vulnerabilities
3. Include steps to reproduce the issue and any relevant context

You should receive an acknowledgment within 72 hours. We will work with you to
understand the issue and coordinate a fix before any public disclosure.

## Security Overview

Larch runs with the operator's permissions inside Claude Code. It treats
repository content, GitHub content, model output, and external-tool output as
untrusted data at workflow boundaries. Mutation and publication paths use
explicit authorization, bounded inputs, validation, and redaction. See
[Workflow Trust, Mutation, and Private Findings](docs/security/workflow-trust-and-mutations.md)
for the canonical technical contracts.

Larch verifies release provenance, dependency policy, archives, executable
identity, and atomic installation before it runs a downloaded binary. Operators
provide credentials through documented environment variables or standard
Application Default Credentials. Typed service adapters constrain credentials,
hosts, operations, redirects, retries, response sizes, and diagnostics. See
[Supply Chain, Credentials, and Services](docs/security/supply-chain-credentials-and-services.md)
for the canonical technical contracts.

These controls do not make larch a sandbox against hostile processes running as
the same operating-system user. Provenance proves how release bytes were built,
not that the source or build infrastructure is trustworthy. Checksums prove
integrity, not trust. Delegated tools may receive workspace access when a
workflow permits it. The [security reference index](docs/security/README.md)
maps the remaining trust boundaries and known limitations.

## Rust Release Build Provenance

Release builds bind immutable source, versions, supported targets, normalized
archives, checksums, and attestations before publication. Publication preserves
the prior Latest release until immutable assets verify. See the
[canonical release provenance and attestation contract](docs/security/supply-chain-credentials-and-services.md#release-provenance-and-attestations).

## Rust Bootstrap and Atomic Installation

The verified bootstrap rejects unsafe archives, validates the staged executable,
installs atomically, and preserves the prior executable on failure. Upgrade
failures leave the prior plugin cache intact. See the canonical
[bootstrap and atomic-installation contract](docs/security/supply-chain-credentials-and-services.md#bootstrap-and-atomic-installation)
and [upgrade and rollback contract](docs/security/supply-chain-credentials-and-services.md#upgrade-and-rollback-boundaries).

## Run-log Archive Materialization

Run-log archives are untrusted input. `python/cli.py run-log materialize`
validates canonical paths, metadata, inventory, sizes, and SHA-256 digests. It
rejects traversal, collisions, links, special files, corruption, and identity
mismatches. Fixed limits bound member count, file size, expansion, and ratio.
Extraction avoids `tarfile.extractall`, writes only no-follow regular files in
a private temporary sibling, verifies before and after atomic promotion, and
removes failed state. It never merges with or replaces an existing cache.

## Google ADC Trust Boundary

Only trusted operator configuration can select Google ADC. Larch does not shell
out to `gcloud`, persist tokens, or accept credential configuration from
repository, GitHub, workflow, or model data. See the
[canonical Google ADC contract](docs/security/supply-chain-credentials-and-services.md#google-application-default-credentials).

Cloud Storage uses the larch-owned port, official Rust client, and hardened ADC.
S3 and R2 use standard AWS credentials; R2 also requires its matching account ID
and HTTPS endpoint. Uploads are create-only, downloads atomic, and errors fixed.

## Rust GitHub Credential and Transport Boundary

The Rust GitHub service reads only `LARCH_GH_TOKEN`. Typed adapters constrain
credential propagation, hosts, transport, pagination, retries, mutations,
response data, and diagnostics. GitHub content remains untrusted data. See the
[canonical GitHub credential and transport contract](docs/security/supply-chain-credentials-and-services.md#github-credential-and-transport-boundary).

### Release and asset service operations

Release and asset calls use typed operations, reconcile ambiguous writes, and
withhold credentials from bounded cross-origin downloads. See the
[canonical release and asset service contract](docs/security/supply-chain-credentials-and-services.md#release-and-asset-operations).

## Rust GitHub Pull-Request, Review, and Dependency Operations

Pull-request, review, and dependency operations use typed inputs, explicit
mutation authorization, bounded reads, and exact read-back after uncertainty.
The current owner for each operation remains in the service inventory. See the
[canonical operation contract](docs/security/supply-chain-credentials-and-services.md#pull-request-review-and-dependency-operations).

## Rust Repository Metadata Read Boundary

Repository reads use one ownership-checking, strict, local-only adapter. It
exposes no mutation, network, credential, or arbitrary Git command surface. See
the [canonical repository-read contract](docs/security/supply-chain-credentials-and-services.md#repository-metadata-reads).

## Rust Git Mutation Compatibility Boundary

Git mutations use the verified runtime entrypoint and closed typed operations.
The installed Git executable retains compatibility behavior for hooks, filters,
signing, helpers, index and ref updates, and diagnostics. See the
[canonical Git mutation contract](docs/security/supply-chain-credentials-and-services.md#git-mutation-compatibility).

## Rust GitHub Actions Operation Boundary

Actions operations use typed paths, bounded reads, serialized mutations, and
read-back after uncertainty. Workflow log downloads constrain redirects,
credentials, content, size, and time. See the
[canonical GitHub Actions contract](docs/security/supply-chain-credentials-and-services.md#github-actions-operations).

## Scoped Live-Mutation Authorization Boundary

GitHub workflow mutations require explicit run or operator authority, current
identity and freshness evidence, and exact read-back where the operation
requires it. Dry-runs make no mutation calls. See the
[canonical mutation authorization and state-integrity contract](docs/security/workflow-trust-and-mutations.md#mutation-authorization-and-state-integrity).

## Security Findings in OOS Workflows

Security-sensitive or uncertain findings are private. Never file them through
`/issue`, include them in public OOS artifacts or committed logs, or fold them
into an unrelated change. Keep them in the session-local private sidecar and
follow [Reporting a Vulnerability](#reporting-a-vulnerability). The
[canonical private-finding contract](docs/security/workflow-trust-and-mutations.md#security-findings-in-oos-workflows)
defines classification, checkpoint, and workflow routing.

## Analyze-bugs and validate-merged state

Analysis caches, durable validation markers, dynamic scout notes, and
architectural knowledge remain untrusted state. Their publishers constrain
content, identity, paths, and mutation scope. See the
[canonical workflow trust contract](docs/security/workflow-trust-and-mutations.md#trust-model).

## Step 8 architectural-assessment trust boundary

Architectural knowledge, diffs, assessor output, and route diagnostics are
untrusted evidence. A read-only assessor authors the assessment, submission
revalidates live identity, and unresolved invariant violations hard-stop without
a waiver. See the
[canonical architectural-assessment contract](docs/security/workflow-trust-and-mutations.md#architectural-assessment).

## Workflow Artifact Publication

Committed breadcrumb publication stages only session-root quiet logs whose
basenames match `larch-quiet-*-*.log`. Each matched file is individually redacted
and the redacted content is concatenated into a single
`larch-logs/.../breadcrumbs/quiet.log` file (with per-source-file header lines
`=== <basename> ===`). Legacy `*.ndjson` breadcrumb stream files and
session-local monitor sidecars (`.quiet`, `.done`, `.status`, `.surfaced`,
`.bc-offset`) stay under the run tmpdir and are not copied into
`larch-logs/.../breadcrumbs/`; attempted quiet-log publication still fails
closed on staged-file symlinks, hardlinks, or redaction errors. The shared
helper now treats its input as a breadcrumbs-directory hint only: a hint outside
the active session tmpdir is a no-op (enforced by a defense-in-depth
confinement check that resolves the derived source root against the active
`IMPLEMENT/DESIGN/REVIEW/RESEARCH_TMPDIR` roots and publishes nothing when it
matches none), and the fail-closed enforcement happens at
per-file staging/redaction time for matched `larch-quiet-*-*.log` files rather
than by applying the removed source-directory-wide rejection rules.

Raw Codex `--json` event streams (`*.events.jsonl`) are session-local artifacts
only. `python/cli.py design log-publish` and `python/cli.py run-log` exclude them
from committed `larch-logs/` publication so prompt-bearing JSONL stays in the
tmpdir and is not treated as a publishable design artifact. This exclusion
covers launcher-generated `${TRANSCRIPT_PATH}.events.jsonl` files and
non-launcher telemetry inputs such as `coder-codex.events.jsonl`,
`codex.events.jsonl`, and `${OUTPUT_FILE%.txt}.events.jsonl`; those streams may
contain prompts, reviewer text, repo snippets, response bodies, and tool output.
Only sanitized per-bucket usage rows in `larch-tokens-*.jsonl`, extracted via
`external_launcher_record_usage_from_events`, are publishable telemetry.
`python/cli.py design log-publish` also excludes raw plan-review transcripts
(`cursor-plan-*-output*.txt`, `codex-primary-plan-*-output*.txt`,
`claude-plan-*-output*.txt`), producer-backed sidecars (Claude `.stderr` /
`.stderr-tail`, Cursor/Codex `.stderr-tail`, `.launch-stderr` for all tools,
`.meta`, `.tsv`, `.cap-hit`, Cursor `.json`, Codex primary `.json`), generic
Claude prompts (`claude-plan-*.prompt`) and rendered plan-review prompts
(`render-plan-*.prompt`), slot-named
collector failure logs, dropped-slot diagnostics
(`plan-review-slots.ndjson.output-files.dropped-slots`), and aggregate
`plan-review-collector.stderr`; `findings.md` / `voting-tally.md` remain
canonical. This exclusion is enforced by
`design_log_publish_flow._publish_excluded`, matched by basename at every depth
of the copied run tree (top level and `plan-review/round-N/`); it also drops the
`plan-autofix/` draft subtree, `.completed/` step sentinels for normal
final design logs, the `step2b-codex-raw.*` drafter family, and per-launch
`.token-record` / `.porcelain` carriers. Pause snapshots are the exception:
they retain top-level `.completed/` sentinels so resume can restore real
provenance evidence. The 2026-06 Python port of the publish flow
(`design-log-publish.sh` to `design_log_publish_flow.py`) regressed this filter:
it copied the whole `$DESIGN_TMPDIR` unfiltered and committed the raw streams,
inflating committed design logs roughly 40x until the filter was restored.

Design log publish and implement run-log commit fail closed when scrubber
execution fails or a detected secret survives scrubbing. Successful scrubbing
still proceeds with a loud rotation warning, because the redacted credential was
already exposed in the session and must be rotated. Scrub failures abort the
publish tail with fatal rc `5`, distinct from recoverable log-PR push/create
misses that leave `PUBLISH_OK=false` recovery breadcrumbs. This preserves the
distinction between failed scrubbing and successful redaction of an already
exposed credential.

## Stall recovery sanitization

`/implement` Step 18a stall recovery has two current public-boundary surfaces: the Tier A `/larch:issue --input-file` artifact (`issue-input`) and the Tier B upstream larch report artifact (`chat-print`). `python/stall-recovery-report-allowlists.tsv` is the mechanical allowlist for Tier B report fields; `python/cli.py stall-recovery lint` verifies TSV, code, and `python/stall-recovery-report.md` parity.

The report helper never publishes raw failure logs, stdout/stderr, plan text, branch names, repo paths, issue bodies, or session tmpdir paths in Tier B. Public fields are limited to closed classifier enums, sanitized step fields, `exit_code` as `integer-or-unknown`, a sanitized `Bail reason` row, the public `REPORT_DEDUP_SIGNATURE` marker, bounded attempts, allowlisted escalation site/trigger summaries, bounded root-cause prose, and fixed maintainer-controlled prose templates. The public dedup signature is separate from the retry `FAILURE_SIGNATURE` and excludes dispatcher, matched classifier, evidence digests, paths, branches, run IDs, raw state, raw logs, and `skill=implement`. The classifier KV output likewise sanitizes `STALL_STEP` / `PHASE` to allowlisted enums and emits `BAIL_REASON` only from a closed enum (`adopted-issue-closed`, `adopted-issue-is-pr`, `branch-create-failed`, `ci-fix-exhausted`, `dirty-state-after-timeout`, `dirty-tree`, `first-fixer-non-health`, `main-branch-post-dispatch`, `orchestrator-envelope-invalid`, `qa-loop-exceeded`, `recovery-out-of-scope`, `run-flags-persist-failed`, `tracking-init-failed`, `wrapper-validation-failure`); every other value is redacted before emission. Rendered `bail_reason` is closed-enum sanitized: allowlisted values render verbatim, empty values render as `none`, and all other values render as `redacted`. All body/comment content is still piped through `python/cli.py redact secrets` as a secrets-family backstop.

Tier B consumer and forked runs file public stall reports in the upstream larch repository under the operator's GitHub identity. The upstream target is resolved from `.claude-plugin/plugin.json` instead of a pinned constant; repository metadata containing newlines, tabs, non-GitHub hosts, malformed owner/repo parts, `..`, or absolute paths is rejected. Resolver failure, lookup failure, auth failure, network failure, create failure, comment failure, or comment success without a valid `html_url` falls back to printing the already sanitized report for manual filing. Exact-signature dedup reads open upstream issues with bodies, ignores pull requests, and comments `+1 occurrence` on a match instead of filing a duplicate. Tier B dedup comments are assembled only from bounded public slices and reuse the same sensitive-token rejection path before posting; if the validator or sensitive corpus is unavailable, the helper fails closed to fallback printing instead of posting publicly. Raw root-cause files, raw escalation ledgers, full report bodies, raw logs, paths, branches, and run IDs must not be passed to the Tier B comment path.

`--failure-detail-log` is accepted only when the path is absolute, physically canonical, regular, non-symlink, under `$IMPLEMENT_TMPDIR`, and at most 64 KiB. When such a validated detail log is present, the classifier treats it as the primary evidence surface rather than letting stale full-state/session notes override it. `init-attempts` / `record-attempt` `--attempts-file` writes are likewise confined to absolute, non-symlink paths under `$IMPLEMENT_TMPDIR`, preventing arbitrary same-UID overwrite via cross-tmpdir or symlink targets. `normalize-issue-env` treats captured `/larch:issue` stdout as data: it filters to `ISSUES_*` / `ISSUE_1_*` machine keys, writes canonical `ISSUE_NUMBER` / `ISSUE_URL` only after a zero exit, `ISSUES_FAILED=0`, no truthy `ISSUE_1_FAILED`, and resolvable create-or-dedup fields, and removes any stale env file on failed or partial issue filing. The persisted classification env emits sanitized `STALL_STEP`, `PHASE`, `BAIL_REASON`, and `EXIT_CODE` tokens only; `BAIL_REASON` is closed to allowlisted values, empty, or `redacted` before it can be copied into other artifacts, and empty/non-numeric `EXIT_CODE` renders as `unknown` while numeric values render unchanged. The helper's `retry-policy` subcommand is the mechanical projection of the documented retry-cap table, and the harness parses the markdown cap table directly to catch doc/code drift. The pytest harness (`python/tests/state/test_stall_recovery.py`) covers log validation (including oversize rejection), attempts-file write containment, body-file containment, issue-stdout normalization for create/dedup/failure paths, deny-list sentinel parity across public outputs including the consumer chat-print payload, redactor invocation, dry-run propagation across report surfaces, and allowlist doc/code/TSV parity. Residual risk: root-cause and mitigation prose templates are static maintainer-authored strings, so a malicious template patch could publish misleading text; that risk is reviewer-visible by construction.

The external implementer prompts (`agents/codex-implementer.md`, `agents/cursor-implementer.md`) likewise prohibit folding security findings inline and prohibit emitting them in `oos_observations[]`. `/implement` Step 9a.1 defensively re-excludes any security-tagged OOS entries that slip through upstream filters before the `/issue` handoff.

Malformed-manifest recovery in `/implement` Step 2 is intentionally narrower than ordinary `claude_fallback`. It only activates for a raw manifest that parses as a JSON object and represents either `status=complete` or the legacy `{status, summary, checks}` fingerprint, with an empty pre-launch index, a non-empty NUL-safe post-launch working-tree delta, and the same post-implementer safety gates as the normal external-implementer path. The recovery envelope preserves `ORCHESTRATOR_EDIT_AUTHORITY=allowed iff STATUS=claude_fallback`, but `RECOVERY_FROM=manifest-schema-invalid` means commit-only recovery: the orchestrator must not re-implement or sweep the index, and Step 4 commits only the dispatcher-provided NUL-delimited path list via `git commit --only --pathspec-from-file`.

`python/cli.py review-and-fix apply-findings` also treats round-local review metadata as untrusted data when persisting `review-and-fix.env`: values such as `REVIEW_CORE_STATUS` are written with `printf`-safe key/value lines, not an expanding heredoc, so tampered status strings cannot trigger shell expansion while the env file is emitted.

Step 5 pre-coder carryover snapshots are kept outside Codex writable grants. When the review round directory lives outside the repo workspace, snapshots are written as a sibling of the round parent rather than under the Codex-granted round directory. If the round parent resolves under `$PWD`, `pre_coder_snapshot_dir` relocates snapshots to `${TMPDIR:-/tmp}/larch-pre-coder-snapshots/<hash>/...` (this assumes `$TMPDIR` itself is outside `$PWD`, which holds on standard macOS/Linux). The relocated dir is not reaped by `cleanup-tmpdir.sh`; production writers clear per-round snapshot files before regeneration. Snapshot files are `chmod 0444` after write as defense-in-depth; `post-coder-head.txt` in `round_dir` is likewise hardened when written. Integrity assumes Codex `--sandbox workspace-write` confines writes to declared `--add-dir`/workspace roots; relocation and read-only bits do not substitute for sandbox confinement if the sandbox is more permissive; no CI sandbox-confinement probe. This is an integrity hardening against delegated fixer tampering, not a confidentiality boundary against same-UID local processes.

**`/design` Tier 3 plan-command dry-run (`python/cli.py plan validate-commands`)**: Tier 3 executes **only** scripts listed in `scripts/dry-runnable-scripts.tsv`, only after Tier 2 reports no defects for that command group, only when validating `plan.txt` (not pre-redaction `composed-plan.md`). Execution uses an **argv array** built from the resolved script path plus **long `--` flags only** from the parsed plan (short flags and non-flag positionals are omitted; see `python/larch/design/plan_quality.py` Tier 3 validation). The plan parser/validator does **not** `eval` plan markdown; the driver parses `ACTION=… ARGS=…` lines with `eval "argv=( $args_text )"` only for **mechanical** `printf '%q'`-shaped argv fragments emitted by `SKILL.md` and helper scripts. `cwd` is pinned to the repo root, probes use a **10s** wall-clock timeout, and `env -i` with a minimal allowlist (`PATH`, `HOME`, `TMPDIR`, `USER`, `LOGNAME`, optional `LANG`, plus `LARCH_DRY_RUN=1` or `--validate-only` per registry row — the **`hook`** column must be exactly one of those two literals; unknown values are defects) so dry-run children do not inherit the operator’s full environment (stdout/stderr captures therefore cannot accidentally vacuum unrelated secrets from inherited env). **Tier 2** (`--help` probe + flag documentation check + missing-script handling) runs in the validator’s Bash process: it inherits the parent environment like any shell helper, but resolves each repo script with `realpath` under `REPO_ROOT` before exec. The `--help` probe captures **merged stdout and stderr** (same surface as `validate-plan-commands.md`); Tier 2 treats the capture as usable for long-flag checks when it is **non-empty** and the probe exits **0**, or exits **1**/**2** with a non-empty capture (usage-style non-zero exits). Flag names are matched as **documented long options** (not raw substrings of that merged help text) via fixed-string / boundary-safe logic so strict-prefix pairs like `--file` vs `--files` do not false-validate. Tier 3 child output is written to `validate-plan-commands.log` only as a **bounded excerpt** passed through `python/cli.py redact secrets` when available, not as unlimited verbatim stdout/stderr — plan-derived argv can appear in script diagnostics, so treat validator logs as sensitive and prefer redacted excerpts when appending to `execution-issues.md`. Tokens containing shell metacharacters (`$`, backtick, `;`, `|`, `&`, `>`, `<`, `(`, `)`, glob `*`/`?`/`[`, or `..`) are rejected as `DEFECT kind=unsafe-token` before any Tier 3 subprocess runs. Each registry row must point at a sibling `.md` that documents the dry-run contract. Operator **Override** decisions on validator defects append under `Warnings` in `$DESIGN_TMPDIR/execution-issues.md` (forensics for downstream design-log publish); use `run-log append-failure --redact` when attaching validator log material. The `larch:plan` GitHub block does not carry override text.

`/design` validator auto-fix delegates target-file repair to Codex/Cursor only when the tool is both present and currently available after degraded-tool gating. The helper treats the plan and validator log as untrusted prompt data, snapshots the target file before each attempt, rejects target symlink replacement, restores failed target edits, restores non-target `$DESIGN_TMPDIR` mutations before validation can succeed, and fails closed on symlinks/special files in the guarded tmpdir surface. Repository dirty-tree snapshots are taken against the consumer repo root, including content hashes for already-dirty tracked/untracked files, so a delegated fixer cannot hide a repo mutation behind unchanged porcelain status.

## Trust Model

Larch runs inside the operator's Claude Code and operating-system permissions.
Repository, GitHub, model, subprocess, architectural, and persisted workflow
content is untrusted data, not authority. Delegated tools have different
mechanical and prompt-only limits, and same-user state is not a sandbox. See the
[canonical workflow trust model](docs/security/workflow-trust-and-mutations.md#trust-model).

### External reviewer write surface in /research

The `/research` hook mechanically covers only Claude's matched write tools.
Bash, child skills, and external Cursor or Codex lanes retain their separately
documented permissions. Use `--no-issue` for sensitive reports. See the
[canonical research boundary](docs/security/workflow-trust-and-mutations.md#research).

## Artifact and Publication Controls

**Layered secret scanning**: larch runs pattern- and verification-based secret scanners at three layers. The layers enforce different guarantees, and conflating them leads to false-confidence gaps — especially around `make lint-only` and `python/cli.py checks run-relevant`, which are pre-commit-driven and therefore depend on the pre-commit hook's actual scan scope.

- **Layer 1: commit-time working-tree scan (opt-in via `pre-commit install`)**: `.pre-commit-config.yaml` runs `python3 python/cli.py checks gitleaks --mode working-tree`. The wrapper downloads the host's official `v8.18.4` release, verifies the archive SHA-256, extracted-binary SHA-256, and reported version, then runs `gitleaks detect` with an explicit `.gitleaks.toml` path. `--no-git` is load-bearing: without it, `gitleaks detect` scans only the git log and can pass staged secrets. With it, the hook scans the working tree and blocks on any finding. `pass_filenames: false` keeps scoped `pre-commit run --files <paths>` calls from narrowing that scan. This layer is bypassable via `git commit --no-verify`; Layer 2 is the enforced backstop. Layer 2 owns git-history scanning.
- **Layer 2: PR gate, git scan (CI)**: `.github/workflows/ci.yaml` calls the same wrapper and cached release path. It scans the working tree with `--no-git`, then scans the PR commit range without it; `fetch-depth: 0` supplies the history. The wrapper removes the source-build versus release-binary split and fails closed on checksum or version drift.
- **Layer 3 — PR gate, live verification (CI)**: the `trufflehog` job pins `trufflesecurity/trufflehog` to its commit SHA for `v3.82.13` (tags are mutable — a force-pushed upstream tag could silently swap a security scanner's binary; SHAs are immutable) with `version: 3.82.13` pinning the Docker image and `--only-verified`, meaning findings fire only for credentials that actually authenticate against a live provider API. This is non-redundant with gitleaks: gitleaks catches regex-matched patterns including synthetic tokens; trufflehog catches ONLY exploitable live secrets. A finding in any layer blocks the PR.

The `.gitleaks.toml` path allowlist intentionally includes synthetic redaction
fixtures such as `python/tests/core/test_redact.py` and session-local Python cache
directories under `python/`. Those entries are blind spots for gitleaks pattern
matching in those paths, so test fixtures must stay obviously fake and live
credential coverage continues to rely on the independent TruffleHog CI job.

The ignored `target/` build directory is excluded because compiled dependency
metadata can contain dependency-owned key fixtures. Authored source and
committed artifacts remain in the working-tree and history scan scopes.

`.gitleaks.toml` maintains a narrow path-based allowlist: the config's self-allowlist (`^\.gitleaks\.toml$`), redaction/scrubber source (`python/larch/core/redact.py`, reached via `python/cli.py redact secrets` / `redact scrub-log-secrets`), redaction-scanner test fixtures (`python/tests/core/test_redact.py`), and the tracking-issue Python module (`python/larch/issue/tracking_issue.py`, `python/tests/issue/test_tracking_issue.py`). These paths legitimately carry token-shaped strings throughout — regex literals, token-family tables, and synthetic test inputs — so per-line allowlisting would churn without adding signal. **The committed run-log tree (`larch-logs/`) is intentionally NOT allowlisted**: gitleaks Layers 1–2 scan it like any other path. The UUID-shaped `LARCH_TOKEN_SESSION_ID` `generic-api-key` false positive that originally motivated a blanket `larch-logs/` exclusion does not fire under the pinned engine, so the exclusion was removed. The primary run-log leak defense is `python/cli.py redact scrub-log-secrets`, a larch-owned pre-flush secret gate invoked right before every flush (`run-log commit`, `design-log-publish.sh`, and the `python/` `ship-pr` rework's `run_logs._scrub_run_tree`): it scrubs secret-shaped values — including Cursor `crsr_` / `key_` keys, which gitleaks does NOT cover — from the entire staged run tree in place so the flush still proceeds, while emitting a very loud warning so the operator can rotate the exposed credential. Consumer repos therefore need no third-party scanner installed for covered secret-shaped token families, but run logs remain sensitive documents: secrets or PII outside the scrubber patterns, including non-standard tokens, private hostnames, and domain-specific sensitive data, still require operator discipline before publication. Publishable `*.stderr-tail` sidecars copied into `larch-logs/` are scrubbed by the same gate; treat run logs as sensitive regardless. **High-churn documentation is NOT allowlisted** (#375): `README.md`, `CHANGELOG.md`, `SECURITY.md` itself, `skills/issue/SKILL.md`, and the issue creation CLI surface are scanned by gitleaks in both Layer 1 (pre-commit, working tree) and Layer 2 (CI, full history). The layer responsibilities remain distinct: gitleaks Layers 1–2 catch regex-matched patterns including synthetic token-shaped literals in docs; trufflehog Layer 3 (`--only-verified`) catches ONLY live, authenticable credentials and is non-redundant with gitleaks for that reason, NOT a replacement for it — an accidental paste of a revoked token or a covered-family token in an unusual format is caught by gitleaks Layers 1–2, not by the verified-only scan. Tokens whose format falls outside gitleaks' covered rule families (see the "Outbound shell-layer redaction" subsection below for the covered families) may slip both Layer 1–2 (no matching regex rule) and Layer 3 (nothing to authenticate against a live API) — contributors must not rely on scanner layers as a substitute for editorial discipline in docs. Contributors adding new token-shaped examples to docs should use non-detector-matching forms: short prefixes without the high-entropy suffix (e.g., `ghp_` as a prefix mention rather than a full 40-character token) or an explicit placeholder like `<REDACTED-TOKEN>`.

**Dev-only PostToolUse audit log (`scripts/audit-edit-write.sh`)**: `scripts/audit-edit-write.sh` is a contributor-local debugging aid that, when opted in via the gitignored developer-local Claude settings file under the clone `.claude` directory, records a JSONL trail of every `Edit` / `Write` tool invocation to a gitignored generated hook-audit log in that same directory. The log is **intentionally unredacted** — it captures the raw PostToolUse payload including `tool_input` fields like `file_path`, `content`, and `old_string` / `new_string`, which may contain secrets, credentials, PII, or proprietary code. The generated audit log is **gitignored by default** (see `.gitignore`) and the script is **not registered in shipped config** (`hooks/hooks.json`) or in committed dev config (`.claude/settings.json`) — it runs only when a developer explicitly adds a `PostToolUse` entry to their local, gitignored Claude settings file. There is no automatic rotation or retention policy; the log grows until the developer clears it. Operational discipline: never commit the log, never paste its contents into issues/PRs/screenshots, clear it after debugging, and treat it as a secret-bearing artifact if the project handles secrets. See `docs/dev-hook-audit.md` for enable/disable/privacy details. The script always exits 0 so it cannot block tool use, and the regression test (`scripts/test-audit-edit-write.sh`, wired into `make lint`) uses `CLAUDE_PROJECT_DIR` override plus a tmpdir to verify behavior without touching the real log.

**Tracking-issue outbound path**: `python/cli.py tracking-issue` owns slim lifecycle writes (`create-issue`, `append-comment`, `rename`, and `mark-false-positive`). Durable run payloads moved out of GitHub comments and into committed `larch-logs/` files via `python/cli.py run-log`; marker-keyed summaries are posted by `python/cli.py tracking-issue`. The write helper keeps the fail-closed redaction posture: body and title content is composed in memory, passed through `redact tmpdir-paths` and `redact secrets`, and only then sent to `gh`; captured `gh` stderr is passed through `redact_gh_error` before surfacing in `ERROR=`. `redact_gh_error` fails closed: if the pipeline is unavailable, exits non-zero, or emits the truncation marker (`[content truncated: unterminated PEM block; tail of body dropped for safety]`), a generic token-free string is emitted in `ERROR=` and no original stderr bytes are included. The same fail-closed contract applies to the sibling `redact_gh_error` helpers in `python/larch/design/clarify.py` (`python/cli.py clarify state`, `python/cli.py clarify label`, and `python/cli.py clarify comment-post`), `python/cli.py named-block write --marker plan`, and `python/cli.py plan-block read`.

**`larch:diagrams` outbound path**: `python/cli.py diagrams upsert` owns the shared issue-scoped `<!-- larch:diagrams v1 -->` summary comment. `/design` Step 5c publishes the Architecture section via `python/cli.py design publish` (diagrams upsert) after the `larch:plan` block is successfully written; `/implement` Step 7a publishes the Code Flow section after successful code-flow generation. The helper accepts diagram source files only from temporary roots by default (`$TMPDIR`, `/tmp`, `/private/tmp`, `/var/folders`, or the larch session cache under `~/.cache/larch/sessions`) unless the operator explicitly opts into `--allow-external-paths`, so an accidental caller bug cannot publish arbitrary repository files. `--repo`, when supplied, must match `OWNER/REPO` before any `gh` call. Before composing the outbound comment, only newly supplied sections are revalidated with `python/cli.py mermaid sanitize`; preserved sections fetched from GitHub are carried forward byte-for-byte. Existing comment parsing is heading-based with generic fence-depth tracking, and the helper now fails closed on unclosed fences instead of silently truncating preserved content. The composed outbound body is then passed through `redact secrets` and `redact tmpdir-paths`; `tracking-issue-summary.sh upsert-summary` applies the same redaction chain again as defense in depth. Captured `gh` stderr and delegated helper stderr are flattened only after `redact_gh_error` redaction; if redaction is unavailable or suspicious, the helper fails closed with a generic token-free message rather than surfacing raw stderr bytes. Validation failures keep detailed path bytes on stderr only; the machine-readable `ERROR=` field uses fixed-token messages so tmpdir layout is not copied into contract consumers or logs. Architecture diagrams are now posted at `/design` completion rather than `/implement` completion, so their public exposure window starts earlier. The trust model is still joint-comment, not author-exclusive: `/implement` preserves any existing sibling section that remains in the marker comment, so on public repositories a foreign or stale marker comment can persist until `/design` rewrites or clears that section. Operators that need stronger provenance should restrict who can comment on the issue or force full replacement rather than preservation on every upsert. Reviewers should treat Architecture diagram labels like plan bodies: avoid high-risk path names, secret-adjacent symbols, private hosts, and other sensitive implementation details unless they are already safe to publish.

**Tracking-issue read/aggregate path**: `python/cli.py tracking-issue` (read mode) remains a pure reader that wraps fetched GitHub issue content in data-not-instructions tags and applies size caps. Its feedback-loop guard now skips the five larch summary markers (`metadata`, `diagrams`, `plan`, `token-report`, and `final-summary`) instead of the removed monolithic larch summary comments. Lifecycle-marker comments remain filtered.

**Final-summary stderr redaction**: Both terminal summary wrappers treat renderer stderr as secret-bearing. `skills/implement/scripts/write-final-report.sh` and `python/cli.py design render-final-summary` append degraded-render warnings to `execution-issues.md` via `python/cli.py run-log append-failure --redact`, so API/auth stderr from `python/cli.py render run-summary`, token reporters, or timing reporters is scrubbed before it can reach session artifacts or published tracking-issue summaries. When both renderer attempts fail and a wrapper writes its local self-composed body, `final-summary.md` must visibly identify the degraded path with the bold fallback banner after the outcome heading and `<!-- larch:final-summary-fallback v1 -->` after `<!-- larch:run-summary v=1 -->`; consumers must not treat that body as an unqualified full renderer result. This is a fail-closed documentation requirement for any future summary-warning callsites: if a helper persists tool stderr into execution-issues or a public-boundary artifact, it must route through the shared redaction pipeline first.

The local sentinel reader validates non-empty `ISSUE_NUMBER` values as digits only, non-empty `RUN_ID` values against `^[A-Za-z0-9._-]+$`, and non-empty `ADOPTED` values via strict equality against `true` / `false` (case-strict, no whitespace trimming other than trailing `\r`); empty values continue downstream as "sentinel unusable" so callers can re-adopt or create fresh state. Malformed `ISSUE_NUMBER`, `RUN_ID`, and `ADOPTED` sentinel `ERROR=` messages use the fixed token `'malformed-value-omitted'` rather than echoing attacker-controlled bytes into stdout, which is itself parsed as `KEY=VALUE` by callers. The `--issue` argv boundary on both `python3 python/cli.py issue state` and `python/cli.py tracking-issue` is also self-validated as numeric before any `gh` interpolation; current callers already validate upstream, so this is defense in depth for future callers.

**`/design` external delegation**: SIMPLE uses 0 external sketch slots and the full plan review panel. HARD uses 4 external sketch slots and the same full plan review panel. Both tiers use the 3-judge voting panel for plan-review findings.

**Issue-anchored plan/clarification `gh` write helpers**: `python/cli.py named-block write --marker plan` mutates GitHub issue bodies, and `python/larch/design/clarify.py` (`python/cli.py clarify comment-post`, `python/cli.py clarify label`, and `python/cli.py clarify state`) owns clarify comments, labels, and state reads. **Assumptions**: callers pass `--issue` as a positive integer (helpers reject `0` and non-numeric values); optional `--repo OWNER/REPO` is validated before any `gh` call, and malformed values fail with `ERROR=invalid-repo`; plan-block bodies pass through the shell redaction pipeline before network writes; clarify comment bodies pass through `python/larch/core/redact.py` before posting; redaction truncation in `python/larch/design/clarify.py` fails closed before posting a clarify comment; captured `gh` stderr is flattened and passed through a fail-closed redactor before surfacing in `ERROR=` machine lines; temporary working files stay under the platform tmpdir and are cleaned up by their owning helper. **Non-goals**: these helpers do not add a separate authorization layer beyond the operator’s existing `gh` auth and repository permissions; they do not scan issue or comment bodies fetched from GitHub for prompt injection (read/classify helpers are separate); they are not a substitute for repository branch protection, review, or pre-commit hooks on any follow-up git operations the operator performs locally.

**`/design` plan review apply boundary**: Step 3 plan review is single-pass and does not apply LLM-authored patches to `$DESIGN_TMPDIR/plan.txt`. Accepted findings are applied only at Gate B: by default Gate B auto-applies accepted in-scope findings with no operator prompt, while `--per-round-approval` restores the explicit Apply all / Go through each / Switch to discussion mode choice before revision. The prompt-side rewrite then runs the shared dedup/trailer guard and merged `design-postplan-emit.sh --with-plan-size` validation/plan-size fence before continuing. Historical `python/cli.py plan revise-waterfall` artifacts may still appear in old committed run logs, but new Step 3 runs do not launch that patch-apply path, and new design-log publish rejects `plan-review/round-N/revise/` artifacts so obsolete prompts, outputs, and candidate patches do not enter the public log boundary.

**`/design` design-log publish (`gh pr merge --admin`)**: `python/cli.py design log-publish --repo` is validated as `OWNER/REPO`; malformed values fail closed with exit 1 before `gh` / network operations. `python/cli.py design log-publish` copies trimmed + redacted `/design` session artifacts into `larch-logs/design/<RUN_ID>/` using the same sidecar trim (`CMD_JSON` lines in `*.meta`, top-level `.result` in every `*.json`) and `redact tmpdir-paths` / `redact secrets` pipeline as `run-log write-round`. Normal final design logs still exclude `.completed/`; pause snapshots retain the top-level sentinel directory so resume provenance checks see the real pre-pause step evidence. Both `plan-review/` and `render-cache/` subtrees are stricter than top-level design artifacts. `plan-review/` enforces a per-round allowlist rooted at `round-<N>/`: `findings.md`, `findings-oos.md`, `findings-classification.tsv`, `oos.md`, `oos-accepted-design.md`, `ballot.txt`, `voting-tally.md`, `plan-review-slots.ndjson`, `plan-voter-slots.ndjson`, `scout-plan-manifest.json`, `round-summary.env`, `plan.txt` (round 1 only; rounds ≥ 2 commit `plan.diff` instead), `*-vote-output.txt`, `*-vote-output-first-pass.txt`, and `voter*-diag.txt`. `accepted-plan-findings.md` and `rejected-findings.md` are excluded from round directories (#3721) — they are cumulative across rounds so only the top-level copies are committed. `findings-in-scope.md` is excluded from both top-level and round staging (#3715) — it is a strict subset of `findings.md` and is recoverable from `findings-classification.tsv` plus `findings-oos.md`. `ballot.txt` is present in round directories (session snapshot) but excluded from committed logs by `design_artifact_excluded()` — it is derived from `findings.md` / `findings-oos.md` scope split and is redundant in the published artifact. Top-level GitHub-redundant snapshots are also excluded (#3721): `issue-body.txt` (raw tracking-issue body; canonical home is the GitHub issue), `issue.json` (JSON snapshot of the same issue), and `architecture-diagram.md` (the same Mermaid body is upserted into the issue-scoped `larch:diagrams` comment by `/design` Step 5c). `round-<N>/revise/` has an empty allowlist and fails closed. The root must be a real directory (a dangling root symlink also fails publish), and any symlink anywhere under the resolved physical root fails publish. `render-cache/` requires the root to be a real directory (a dangling root symlink also fails publish), fails on any symlink anywhere under the resolved physical root, applies the same per-file recheck immediately before staging, and has no filename allowlist (content schema is open; the suffix denylist inside `design_publish_stage_file` remains the only basename filter). A per-file ancestor re-resolution (`design_publish_ancestor_within_root`) fails closed when any ancestor directory is swapped for a symlink before staging, closing the parent-directory race for the `plan-review/`, `render-cache/`, and `.completed` subtrees (in addition to the per-file leaf recheck). Dropping the `[skip ci]` marker means CI runs on the publish PR; the tail first waits for required checks to register for the pushed commit head within a bounded grace/probe budget, then watches those checks with `gh pr checks --required --watch --fail-fast`, and only then squash `--admin` merges (`gh pr merge --squash --admin --delete-branch`). Stale prior-head check state does not satisfy registration. Required-check failures, registration timeout (checks never register or the PR head does not match within the budget), and watch failures all refuse the merge with `PUBLISH_OK=false` and leave the PR open for diagnosis; registration timeout uses dedicated `did not register within` wording distinct from CI-failure `did not pass` wording. `--admin` bypasses the review-required branch protection (the repo's review ruleset has no bot reviewer, so a server-side `--auto` merge would enable but never complete) and requires a token with admin-merge privileges; it is intentional but not an unconditional bypass because it runs only after registration plus a successful required-check watch. Treat committed design logs as public-boundary artifacts scanned by the existing gitleaks/trufflehog CI jobs; do not paste secrets into design prompts.

**`larch-logs/` as durable run store**: reviewer findings, tallies, version-bump reasoning, OOS links, execution issues, run statistics, token reports, and timing reports are written through `python/cli.py run-log` into `larch-logs/<skill>/<run-id>/` and committed by explicit lifecycle log-flush paths before the business PR merges. Diagrams are not written through a larch-log batch; the public diagram surface is the `larch:diagrams` issue comment described above. After a merge-success result, the Python ship driver writes `$IMPLEMENT_TMPDIR/post-merge-sentinel`; `python/cli.py run-log flush` no-ops on that sentinel and `python/cli.py run-log commit` refuses, so prompt-side teardown cannot create or push new log-only commits to `main`. The sentinel check therefore depends on `IMPLEMENT_TMPDIR` being exported into subprocesses that may call `run-log commit`; Step 7a and `python/cli.py run-log refresh` provide that export before their transcript/log refresh paths run. Defense-in-depth commit refusal lives at `python/cli.py run-log commit`; `python/cli.py run-log refresh` also short-circuits entirely when `MERGE_RESULT` already reports a merged terminal state, so post-merge retry refreshes do not attempt transcript/log writes. `run-log capture-transcript` itself no longer owns an independent default-branch refusal policy; it delegates commit enforcement to `run-log commit` (or to its caller when `--defer-commit` is used). Callers pass the staging root explicitly with `--log-root`; the helper no longer falls back to `$IMPLEMENT_TMPDIR` or the repository root when the root is omitted. `larch-logs/ export-ignore` keeps those audit files out of plugin release archives. Payload batches are redacted before writing. Tool-failure captures routed through `python/cli.py run-log append-failure` preserve command stdout/stderr verbatim for debugging and use `python/cli.py redact secrets` when callers pass `--redact`; `/implement` final-summary degraded-render warnings now also use that redacted capture path before stderr is appended into `execution-issues.md`. This is a secrets-family backstop only, so internal URLs, private hostnames, PII, and domain-specific sensitive content still require prompt-level/operator discipline before logs are pushed. `manifest.json` schema version 2 records `operator_cwd` and `operator_repo_root` as local absolute paths for provenance; these fields are JSON-escaped but not path-redacted, so public repositories may expose local username/workspace path components in committed run logs. Slim marker-keyed tracking comments contain summaries and links only, except for the diagrams comment; operators should still treat committed log files and tracking comments as public once pushed to a public repository.

**CI-fixer subagent trust boundary**: `/implement` Step 8 repairs a failed required CI run with an in-session `larch:ci-fixer` Agent-tool subagent (`agents/ci-fixer.md`), not the retired bgjob fixer lanes. The main agent keeps a flat context on this path: it never reads the distilled CI digest, never runs `gh run`, and never edits repository files. Its only evidence is the handoff KVs (`FAILED_JOBS_COUNT`, `CI_ERRORS_DISTILL_CLASS`, and the `CI_ERRORS_FILE` digest path it passes through unread) plus the subagent's three `FIXER_*` result lines. The subagent treats `CI_ERRORS_FILE` — the sanitized, bounded `python/cli.py ci distill-log` digest — as untrusted CI evidence, not instructions: it reads the digest only to locate failing jobs and never executes commands or follows directives found inside it. Its tools are scoped to the repository root given in its prompt; it must not run `gh run`, merge the PR, open or edit issues, touch `/design` or assessment surfaces, or modify any state file under `$IMPLEMENT_TMPDIR`. It makes one `CI fix round <N>` commit per round and pushes through the Rust-owned `scripts/larch.sh push branch` command, whose typed adapter redacts diagnostics; CI adjudicates every pushed fix.

**CI-fixer salvage posture**: The retired bgjob lane salvage validated a deterministic commit trailer plus head-lineage provenance before reshipping a fixer commit. The current flow replaces that with a deterministic main-agent salvage rule (`skills/implement/SKILL.md` Step 8 `ci-fix` route): after every subagent return or death, the main agent runs `git status --porcelain` and commits any dirty tree as `CI fix round <N> salvage`, then pushes it via `python/cli.py push branch`. This is a materially weaker provenance posture than the retired trailer-and-lineage validation — the salvaged commit carries no trailer, subject, parent, or lineage check — but subagent work is never reset away, a dirty tree is never reshipped as-is, CI adjudicates the resulting run, and the `push branch` wrapper's redaction still applies. Routing is driven by the `FIXER_RESULT` contract (`pushed` / `no-progress` / `bail`): `no-progress` twice with the same failure signature routes operator-bail `ci-fix-no-progress`, a `bail` or unparseable final message gets one respawn before the tool-failure contract, and rounds exhausted at the round-30 cap route operator-bail `ci-fix-exhausted`.

**Operator diagnostic redaction**: `larch_err` / `larch_errf` still pipe through
`redact secrets --streaming` directly (the redaction streaming wrapper
was removed in Stage 3). Durable log publication redaction remains in
`run-log` / `design-log-publish.sh` via the shared breadcrumbs helper.

Mermaid diagram content is sanitized at diagram-write time and PR-body composition via `python/cli.py mermaid sanitize` so unsafe diagram content is dropped before it reaches public comments or PR bodies.

**Active Step 8+ post-review publication path**: `python/cli.py ship pr` (delegating to `python/larch/implement/ship.py`) centralizes `/implement`'s post-review PR publication, CI-fix, merge, and teardown mechanics. It preserves the existing public-output guards: PR bodies embed only sanitized Mermaid files or placeholders, `python/cli.py pr create` still redacts session tmpdir paths before `gh pr create`, and tracking issue lifecycle writes still route through `python3 python/cli.py tracking-issue`. Ship-pr CI fixing runs through the in-session `larch:ci-fixer` Agent-tool subagent described above, not a ship-driver agentic loop: the driver distills the failed run to a bounded, redacted `CI_ERRORS_FILE` digest and route-exits to the main agent, which spawns the subagent and relaunches the driver only after a `FIXER_RESULT=pushed` push or a deterministic salvage-rule commit. Passive CI wait runs as a blocking subprocess, not model polling, and Codex and Cursor are not CI-fix tiers on this path. For `--role resolve-conflict`, `--conflict-files` values are validated per path segment (reject control characters, absolute paths, `.`, `..`, empty entries, doubled slashes, and characters outside a narrow repo-relative path alphabet) before the launcher embeds them. Conflict fixers may edit conflict files only; staging and rebase continuation are driver-owned. `ci-fix-exhausted` is an operator bail and does not auto-resume through stall recovery.

The Python driver's `ship-pr-state.sh` merge path fails closed before reading or writing a symlinked state file and preserves only the documented state-key allowlist from pre-existing content. Unknown same-UID injected keys are dropped during the next state write instead of influencing later classification or context hydration.

**`python/cli.py checks lint-fix` coder-owned commits**: `python/cli.py checks lint-fix` dispatches Claude/Opus before Codex and Cursor, then prompts external fixers not to commit, but now accepts a fixer-created commit only on a narrow mechanical path: the pre-dispatch baseline must be clean, the symbolic branch before and after dispatch must match, and the post-dispatch `HEAD` must be a direct single-parent child of the pre-dispatch `HEAD`. Detached `HEAD`, branch switches, history rewrites, and dirty-baseline `HEAD` movement remain fail-closed. The post-dispatch HEAD-validation branches — detached HEAD, non-ancestor baseline, merge-commit advancement, branch switch, dirty-baseline HEAD movement, and same-branch multi-commit advancement — remain fail-closed: `LINT_FIX_STATUS=failed` is emitted with `FAILURE_REASON=head-changed-after-dispatch` and no coder-owned commit is accepted; the loop does not reset the working tree to `baseline_head` in these branches (only forbidden-path violations trigger an explicit reset). Accepted committed content is checked against `.gitmodules` and discovered submodule paths with the same prefix-aware forbidden-path contract as the working-tree cleanup; a committed forbidden path triggers `git reset --hard <baseline_head>` before failing. Even after accepting a coder-owned commit, the residual working tree is still scanned and reverted for forbidden `.gitmodules` or submodule-path edits before the helper reports `LINT_FIX_STATUS=applied`.

**Codex lint-fix sandbox and verification split**: The Codex lint-fix tier stays on `agent launch-codex-exec` workspace-write with only the repository root and per-run `run_dir` passed as `--add-dir` grants. It does not receive a session-root or `implement_tmpdir` grant. The Codex-specific lint-fix appendix makes Codex edit-only: it must not run `exec_command`, shell verification, `checks run-relevant`, or ad-hoc temporary verification roots. The parent orchestrator runs `python3 python/cli.py checks run-relevant` after Codex exits, outside the Codex sandbox. `launch-codex-exec` watches the Codex `--json` event stream for `exec_command failed` plus `blocked by policy` / `Rejected(` evidence, writes `FAILURE_CLASS=policy-rejection` / `POLICY_REJECTION=true`, terminates the child, and treats that deterministic rejection as non-retryable for auth and unclassified-empty retry paths. Codex lint-fix therefore must not receive write access to orchestrator-owned session files such as `session-env.sh`, `finalize-state.sh`, or timing ledgers. Claude and Cursor lint-fix tiers keep the shared prompt and are not restricted by the Codex-only appendix. Read-only Codex lanes remain unchanged.

**Cursor CI stall JSON sidecars** (`python/larch/agents/agents.py`): stall forensics JSON is assembled with `jq` when `jq` is installed; without `jq`, no sidecar is written (stall kill behavior is unchanged). Process-list and transcript blobs are intended to pass through `python/cli.py redact secrets` under an 8s `timeout`/`gtimeout` envelope when the redactor is executable and a wall-clock wrapper exists; a missing redactor, a missing `timeout`/`gtimeout`, redactor non-zero exit, or timeout substitutes omission placeholders in the JSON rather than embedding raw captures. `git status` / `git rebase --show-current-patch` excerpts use the same bounded redaction envelope as other sidecar fields (not an unbounded stdin pipe), scoped to the tree channel root when `channel` is `tree:…` else the launcher cwd. `lsof` runs only under a short `timeout`/`gtimeout` when both tools exist; otherwise the `lsof` field is left empty. When `jq` assembly fails after a stall, a single-line `cursor-ci-stall-json: jq assembly failed …` marker is appended to `${OUTPUT}.diag` instead of leaving the failure indistinguishable from a non-stall run. When the staged JSON cannot be renamed into the final sidecar path, a single-line `cursor-ci-stall-json: write failed …` marker is appended.

**External CLI startup locks**: Review, implement, and CI-fix spawn sites for Cursor and Codex share one Darwin-only `/tmp/larch-external-startup-$USER.lock` directory lock plus bounded auth-startup retry wrapper. Cursor's Darwin keychain preflight and preread sections use the same lock when `CURSOR_API_KEY` is not already usable. Codex and Cursor use the same startup lock because they can contend for the same per-user macOS Keychain resource. The lock is a reliability mechanism, not an authorization boundary: `/tmp` is shared scratch, the path includes the local username, stale locks are removed by age, and acquisition fails open after a bounded wait. Operators on multi-user hosts should not treat the lock directory as confidential or tamper-resistant; it only reduces concurrent CLI startup/auth races.

**Codex env-key auth**: Covered Codex paths (`python/cli.py agent launch-review --tool codex`, `python/cli.py agent launch-codex-ci`, `agent launch-codex-implement`, the Codex health probe in `python/cli.py agent check-reviewers`, `python/cli.py review-and-fix apply-findings`, `python/cli.py agent launch-codex-exec`, `/research` Codex research lanes, `/research` validation lane, shared Codex voter/judge fences, `python/cli.py checks lint-fix`, and `python/cli.py agent run-negotiation-round`) prefer a live non-whitespace `OPENAI_API_KEY`. Larch passes only the variable name `OPENAI_API_KEY` in ephemeral `-c` argv and non-secret config references, and strips larch-owned env-key artifacts plus literal `api_key` / `openai_api_key` assignments from copied temp configs before launch. The key value remains in the Codex child process environment, so same-UID or host-level process-environment introspection can observe it while Codex is running. Larch does not intentionally write the key value to config files, logs, argv metadata, `.meta` / `CMD_JSON`, probe output, `--output-last-message` artifacts, or xtrace output; however raw Codex stderr and `--json` event streams are session-local artifacts and can contain upstream tool diagnostics, so treat them as sensitive. When the env var is unset, empty, or whitespace-only, login fallback preserves the existing `~/.codex/auth.json` symlink behavior after stripping copied temp configs.

**Timing ledger containment**: `LARCH_TIMING_LEDGER` is an env-driven write primitive used so nested `/design` and `/review` invocations append to the parent `/implement` timing ledger. `/implement` rehydrates both `LARCH_TIMING_LEDGER` and `IMPLEMENT_TMPDIR` from its session-env contract before post-Step-0 timing ledger/report calls, keeping ordinary run telemetry on the private per-run ledger instead of the cwd-hash fallback shared by a clone. `python3 python/cli.py timing` constrains that env path to known session roots (`${TMPDIR:-/tmp}`, `$IMPLEMENT_TMPDIR`, `$DESIGN_TMPDIR`, `$REVIEW_TMPDIR`, or `dirname("$SESSION_ENV_PATH")`); invalid values warn and fall through to the next resolver step; when no per-run root is configured, the script fails closed (warns on stderr, writes no file, exits 0). Vendor rows store output basenames only, and rendered timing reports do not include an output-path column, so the public tracking-issue timing fragment does not expose absolute workspace layout.

**Plugin-root rehydration**: `LARCH_CLAUDE_PLUGIN_ROOT` is persisted in `session-env.sh` when `CLAUDE_PLUGIN_ROOT` is an absolute path using the existing session-env path character set. `python/cli.py session write-env` also emits a minimal sourceable `$IMPLEMENT_TMPDIR/plugin-root.env` sibling (only `CLAUDE_PLUGIN_ROOT=` + `export`). Post-Step-0 `/implement` Bash blocks source that sibling after `IMPLEMENT_TMPDIR` is known; pre-bootstrap sites may awk-extract from `session-env.sh` when the sibling is absent (legacy resume). Other session-env keys still use `read-session-env-key.sh` — the full `session-env.sh` file is not `source`d or `eval`d. Treat `plugin-root.env` like other session tmpdir artifacts under the same-user trust model (data produced by larch scripts in the operator's account, not an integrity boundary against a hostile same-UID writer).

**`/design` Step 0 `CLAUDE_PLUGIN_ROOT` export**: The first Bash block in `skills/design/SKILL.md` exports `CLAUDE_PLUGIN_ROOT` from a skill-loader-expanded template line (`export CLAUDE_PLUGIN_ROOT='${CLAUDE_PLUGIN_ROOT}'`). If expansion fails and the value is empty, Step 0 exits immediately with stderr — invoking `${CLAUDE_PLUGIN_ROOT}/scripts/...` with an empty root would otherwise resolve helpers under the wrong directory.
**Session writer guard**: session/state content files are written through `python/larch/state/session_env.py` approved verbs. The runtime validates each writer's key allowlist, rejects CR/LF in persisted values before rendering, writes atomically, refuses symlinked targets, and limits session-content destinations to temp/cache session roots. `/dev/null`, plugin-root-only rehydration, and the `/design` current-env symlink use explicit carve-outs with their own validators. These checks reduce prompt-side line-injection and accidental path-clobber risk; they do not protect against a hostile same-UID process that can mutate files in the operator's temp/cache directories.

**Runtime-only plugin projection**: The
[security reference index](docs/security/README.md#runtime-packaging-contract)
owns the projection's security packaging contract. Installation and upgrade
instructions remain in
[`docs/installation-and-setup.md`](docs/installation-and-setup.md).

**`/cleanup` session-tmpdir retention**: The cleanup skill prunes stale entries under `${XDG_CACHE_HOME:-$HOME/.cache}/larch/sessions/` and matching `/tmp` larch patterns by age, not by whether a skill run is still active. `pgrep -x claude` populates `SESSION_COUNT` for operator visibility only; multiple concurrent Claude sessions do not block or abort cleanup (there is no singleton gate). Retention is controlled by `LARCH_CLEANUP_RETENTION_DAYS` (default 7); non-positive or non-numeric values warn on stderr and fall back to 7. Age checks use `find -mtime` 24-hour blocks (platform rounding applies at block boundaries). The cache pass enumerates all non-symlink top-level entries (no age pre-filter, never delete through a symlink); the `/tmp` pass uses top-level `-mtime +N` plus larch name patterns and may remove stale files as well as directories. Directory deletion is gated by a bounded `find -maxdepth 5 -mtime -N` nested-activity scan, so a directory with fresh deep activity (≤ 5 levels) is retained even when its top-level mtime is old; activity deeper than five levels does not protect it (depth-bound tradeoff). Matching loose `/tmp` files do not receive nested-scan protection; they are removed by top-level age plus pattern match. A failed scan `find` warns and skips deletion for that directory entry (fail-safe); a failed top-level enumeration `find` or failure to allocate the temp list for enumeration warns via `larch_err` and skips that pass (count 0), while cleanup still exits 0 and still emits removal-count KVs. Dangling `current-design-env-*.sh` symlinks in the sessions parent are reaped separately (age-independent). Session tmpdirs are session-scoped private state and may hold secrets, prompts, and raw `.meta` `CMD_JSON` argv (see the Cursor API key section above); `/cleanup` permanently deletes stale directories that pass the age gate without redaction. Operators should not run `/cleanup` expecting keepalive alone to block deletion — retention and bounded nested-activity bound cache removal.

**Submodule edit guard anchor (`scripts/block-submodule-edit.sh`)**: The `PreToolUse` hook anchors its superproject-root detection to `CLAUDE_PROJECT_DIR` (with `$PWD` fallback for non-Claude-Code invocations), closing the cd-into-submodule bypass (issue #150) where a session that had `cd`'d into a submodule collapsed the guard's notion of "superproject root" to the submodule root, allowing same-submodule edits to slip past.

**`CURSOR_API_KEY` environment-auth posture (issue #1358)**: Cursor launchers normalize `CURSOR_API_KEY` before spawning the child: leading/trailing whitespace is trimmed, whitespace-only values are unset so Cursor can fall back to keychain/login auth, and embedded CR/LF values are unset as paste-corruption. Cursor call sites pass no `--api-key` argv element; the child authenticates from the inherited environment. On Darwin, shared launchers may best-effort pre-read the exact `cursor-user` / `cursor-access-token` keychain service when `CURSOR_API_KEY` is empty and export the token into the launcher process. This bypasses Cursor's own keychain access in the child process and eliminates the intermittent concurrent-launch failure mode (`Password not found for account 'cursor-user'` / `Security process exited with code: 45`) for those launcher lanes when the keychain service is readable. The environment path has two visibility surfaces operators should be aware of:

1. **Process environment visibility**: while the `cursor` child process is running, the API key can be visible to same-UID process-inspection surfaces that expose environments. Multi-user shared hosts where untrusted users have shell access on the same machine should treat the key as sensitive in that environment regardless of whether `CURSOR_API_KEY` is set or not (a `cursor login`-keychain user has their cleartext key on disk in the keychain blob, which is also the keychain's threat model).

2. **At-rest launcher metadata**: `python/cli.py agent run-external-agent` records the child argv into `${OUTPUT}.meta` as a `CMD_JSON=` line for retry reconstruction. Cursor API keys are not present in that argv under the environment-auth contract, but other prompt or path metadata can still be sensitive session state. The `${OUTPUT}.meta` sidecars live under `${XDG_CACHE_HOME:-$HOME/.cache}/larch/sessions/...` (session-tmpdir scoping; cleaned up by Step 18 of `/implement` and the parallel cleanup paths in `/design` / `/review` / `/research`). The session tmpdir is treated as session-scoped private state under existing `SECURITY.md` conventions.

Committed `larch-logs/.../round-<N>/` artifacts intentionally do not preserve that raw session-sidecar contract. `python/cli.py run-log write-round` copies only registered reviewer/voter artifacts, strips any `.meta` line whose first non-whitespace token is `CMD_JSON=`, removes the top-level `.result` field from included `*-output.txt.json` / `*-output-*.txt.json` sidecars, and then applies the shared tmpdir/secrets redaction pipeline. If the JSON trim cannot be produced, `write-round` fails closed instead of copying the raw sidecar. This yields two distinct at-rest classes for auditors: session tmpdirs are ephemeral private retry state and may contain raw argv/tool envelopes; committed round artifacts are the durable, additionally-trimmed record.

The dynamic Codex output families explicitly retained for committed run logs —
`dyn-*-codex-output.txt` and `dyn-*-codex-output-phase*.txt` plus their `.meta`,
`.json`, and `.cap-hit` sidecars — use the same pattern-based
`redact secrets` / `python/cli.py redact scrub-log-secrets` posture as other committed
`larch-logs/` artifacts; retry outputs (`dyn-*-codex-output-retry*`) remain
excluded. This is a by-design residual risk acknowledgement, not a new control.

Operators who require zero environment-secret propagation should not use the shared Cursor launcher lanes on Darwin with a readable `cursor-access-token` keychain service: leaving `CURSOR_API_KEY` unset may still export the pre-read keychain token into the child environment. Prefer Claude or Codex for those runs, or remove the readable Cursor keychain entry before launching and accept that Cursor auth may fail. The Darwin-gated pre-launch sanity check (`python/larch/agents/agents.py` `cursor_auth_preflight`) refuses to launch with both auth sources demonstrably absent, so a misconfigured `CURSOR_API_KEY=`-empty + missing-service state surfaces an actionable error rather than the cryptic `Security process exited with code: 45`. The check and pre-read are strictly read-only: they never invoke `security delete-*`, never spawn a Cursor subprocess, and never perform network I/O. `/design` plan-review panel waterfall failures redact stderr before writing `plan-review-panel-failure.log` and before re-surfacing stderr to the operator; residual risk follows the shared pattern-based redactor and can over-redact benign text.

### Automatic research-issue publication (`/research` Step 3.5)

By default, `/research` creates a GitHub issue at the end of each successful run containing the full research report and token spend metadata. This changes `/research` from producing a local/terminal-only artifact to publishing the full report to GitHub. The `--no-issue` flag suppresses this behavior.

**Redaction backstop**: `/issue`'s outbound shell scrubber (`python/cli.py redact secrets`) covers common secret patterns (API keys, tokens, passwords, certificates). It does NOT cover internal hostnames/URLs, PII, or domain-specific sensitive content.

**`/implement` Step 0 plan-materialization redaction**: bootstrap copy-plan and `gh issue view` hard-failure surfacing must pass captured stderr through both `python/cli.py redact secrets` and `python/cli.py redact tmpdir-paths` before it reaches the operator transcript; if either redactor fails, Step 0 prints a generic fallback warning instead of raw stderr. Goal text derived from the issue title now fails closed the same way: if the redaction pipeline errors, bootstrap logs a Warning and substitutes a placeholder goal string rather than forwarding the raw title into plan logs or committed `larch-logs/`.

**Failed-agent stderr tails (#3202)**: Codex/Cursor/Claude subprocess failures may surface a bounded, redacted stderr tail to the orchestrator chat (FD 2 via `larch_err` / collector §3.8) and to `python/cli.py agent run-external-agent` callers (`emit_failed_agent_stderr_tail_raw`). The same redaction path (`redact tmpdir-paths` → `redact secrets`, 30-line / 5120-byte cap) applies to implement/CI/lint-fix lanes surfaced from `implement step2-dispatch`, the Python ship driver, and Step 5 lint-fix callers (#3227). Control: `LARCH_FAILED_AGENT_STDERR_TAIL_LINES` (default **30**; **`0`** disables capture and emission). After line limiting, content passes `python/cli.py redact tmpdir-paths` then `python/cli.py redact secrets`, then a fixed **5120**-byte cap (`python/larch/agents/agents.py`). Sidecars (`${output}.stderr-tail`) are written only on failure/timeout paths; successful runs remove stale sidecars. Collector batch dedup collapses identical root-cause signatures to one full tail plus suppression lines; `--summary-only` collector calls skip §3.8 emission so waterfall phase collects do not false-alarm. Committed `larch-logs/` may include publishable `*.stderr-tail` artifacts when design/implement publish runs copy them; those files receive the same dual redaction at publish time, are additionally scrubbed by `python/cli.py redact scrub-log-secrets` before each flush, and — now that the blanket `larch-logs/` gitleaks exclusion is removed — are scanned by gitleaks Layers 1–2 like any other path. Treat run logs as sensitive regardless of redaction; the pre-flush scrubber (which, unlike gitleaks, covers Cursor `crsr_`/`key_` keys), not the scanner, is the authoritative backstop for stderr-tail content.

**Vendor failure-diagnostics batch (`*.failure-diag` / `vendor-failure-diagnostics`) (#3713)**: Each failing vendor-agent invocation (Codex/Cursor/Claude CI or implement launchers) composes a per-slot `${output}.failure-diag` carrier from available diagnostic sources (sidecar history, events, diag, stderr, launcher stderr) via `write_failure_diag` in `python/larch/agents/agents.py`. `append_vendor_failure_diagnostics` redacts (secrets → `<REDACTED-TOKEN>`; tmpdir paths via `python/cli.py redact tmpdir-paths`) and stages the result as a part under `$IMPLEMENT_TMPDIR/vendor-failure-diagnostics.parts/`. At `/implement` Step 7a pre-ship, `scripts/flush-vendor-failure-diagnostics.sh` concatenates all parts into `$IMPLEMENT_TMPDIR/vendor-failure-diagnostics.txt` and commits it as the `vendor-failure-diagnostics` larch-log batch. The batch is then part of the committed run-log artifact pushed with the PR and scanned by gitleaks Layers 1–2. Content caps: the carrier byte cap is defined by `vendor_failure_diag_byte_cap` (defaults to 16384 bytes per slot); the batch itself has no additional cap beyond this per-slot limit. The `*.failure-diag` carrier suffix is denied in the per-output `write-round` staging path (`run-log` allowlist) and in `design-log-publish.sh`; only the composed `vendor-failure-diagnostics.txt` batch reaches committed logs. Runs that bail before Step 7a — e.g., Step 2 dispatcher stall, Step 5 review stall — may not flush this batch; diagnostic parts then stay in the session tmpdir and are removed at Step 18 cleanup. The research validation lane (`skills/research/references/validation-phase.md`) uses `python/cli.py agent run-external-agent` directly and has no flush path for this batch; validation-lane failure diagnostics are session-tmpdir-only.

**Residual risk**: research reports may contain security-sensitive findings, internal architecture details, vulnerability assessments, or references to private infrastructure. Operators running `/research` against security-sensitive codebases should use `--no-issue` or review the generated issue after creation.

**Transitive callers**: `python/cli.py eval research` passes `--no-issue` to suppress auto-issue when `/research` is invoked as an intermediate step rather than a user-facing research task.

**`implement-finalize postbump` session-local inputs**: `/implement` Step 8 invokes `python3 python/cli.py implement-finalize postbump` with a session-local state file under `$IMPLEMENT_TMPDIR`. Phase 1 removed per-PR bump and changelog inputs from this path; `postbump` no longer reads bump reasoning or fallback changelog bullet files. The remaining state is limited to branch, issue, repo, fork, and version-placeholder keys needed to run the Step 8b rebase plus force-push gate. The state file follows the same no-source parsing, tmpdir containment, symlink rejection, and size guards documented for finalize state files.

## Breadcrumb stream redaction

Breadcrumb streams cross from session-local runtime state into durable logs only
through the redaction and publication path described here.

1. **Session breadcrumb directories are publication hints only**: session-tmpdir
   `breadcrumbs/` paths (`$IMPLEMENT_TMPDIR/breadcrumbs/`, `$DESIGN_TMPDIR/breadcrumbs/`,
   `$REVIEW_TMPDIR/breadcrumbs/`, or `$RESEARCH_TMPDIR/breadcrumbs/`) are hints only;
   committed publication stages matching `larch-quiet-<script>-<pid>.log` quiet logs
   from the session root, not live runtime streams under those directories. Legacy
   `*.ndjson` stream files and other non-quiet-log artifacts stay session-local.
2. **Committed copies are routed through `python/cli.py run-log commit` and
   `python/cli.py design log-publish`**: both entrypoints invoke
   `python/cli.py run-log publish-breadcrumbs` (implemented in
   `python/larch/report/run_log_commit.py`).
   The helper stages each accepted source file through
   `redact tmpdir-paths | redact secrets --streaming --state-file <tmp>`,
   then concatenates all redacted output into a single
   `larch-logs/<skill>/<run-id>/breadcrumbs/quiet.log` file (with per-source
   header lines `=== <basename> ===`) rather than publishing individual files.
   The staging and final atomic directory swap prevent partial publication.
   Source-directory resolution uses `LARCH_BREADCRUMB_SOURCE_DIR` when set
   (must still pass session-tmpdir containment), else the log-root parent's
   `breadcrumbs/`. Quiet-log sources are derived via `dirname` of that
   breadcrumbs path and are staged independently of whether `breadcrumbs/`
   exists. Each quiet-log candidate must stay under the session tmpdir, must
   not be a symlink, and must not be a hardlink.
   A source hint outside the active session tmpdir is treated as a no-op:
   breadcrumb staging is skipped and the helper returns success without
   creating, replacing, or clearing the committed destination.
   Missing sources, empty sources, or sources whose entries are all silently
   skipped are successful no-ops and do not create, replace, or clear an
   existing committed `breadcrumbs/` destination.
4. **What the helper enforces vs. silently skips**: publication is
   directory-level fail-closed on enforced triggers; no partial publication occurs
   on any enforced reject.
   - **Rejected** (whole helper returns 1; staging removed; destination not
     created or replaced): source directory not absolute, source directory or any
     candidate file outside `IMPLEMENT/DESIGN/REVIEW/RESEARCH_TMPDIR` via
     `larch_log_breadcrumbs_under_session_tmp`, source directory itself a
     symlink, source path exists but is not a directory, an existing file entry
     is a symlink, an entry has hardlink count greater than 1, an accepted
     quiet-log basename contains `/` / `..` / leading dot, or the redactor pipe
     exits non-zero on any accepted file.
   - **Silently ignored** (not rejected, not committed): legacy `*.ndjson` files
     under `breadcrumbs/`, hidden monitor sidecars (`.bc-offset`, `.quiet`,
     `.done`, `.status`, `.surfaced`, `.pid`), non-existent race-condition globs,
     non-regular files, and quiet-log candidates outside `larch-quiet-*-*.log`
     basenames.
5. **Rust and Python egress boundaries remain pattern-based**: Python breadcrumb
   publication uses the pipeline above. Rust uses `larch_core::SafeText` for
   errors, output, structured breadcrumbs, and journal fields; it redacts paths,
   token families, and PEM blocks, then re-scans and withholds the whole value if
   a recognized secret survives. Rust keeps human, machine, and contract writers
   distinct, and contract rows reject line breaks before writing. Future process
   and HTTP adapters must use this boundary instead of retaining raw responses in
   displayable errors. Unknown credentials, partial token fragments, internal
   hostnames, and PII can still survive. Minimize captured external text and treat
   redaction as a final egress backstop, not a comprehensive classifier.

See [docs/run-logs.md § breadcrumbs/](docs/run-logs.md#breadcrumbs) for the
operator-facing directory contract; the same helper applies to every skill
(`/implement`, `/design`, `/review`, `/research`) that publishes via
`larch_log_publish_breadcrumbs_shared`.

## Fixed-string matching for interpolated values (issue #775 unified grep -F doctrine)

Compare untrusted labels, markers, refs, and identifiers with fixed strings,
field equality, or closed parsers. Never interpolate them into a regular
expression or shell program. See
[Local mutation safety](docs/security/workflow-trust-and-mutations.md#local-mutation-safety).

## /design assessor thin-fence data handling

Assessor sidecars and result envs are parsed as fixed-key data, never sourced or
evaluated. See the
[canonical design boundary](docs/security/workflow-trust-and-mutations.md#design).

## /design reporting boundary

Design reporting treats plan, issue, log, path, repository, URL, and diagnostic
content as sensitive untrusted data. See the
[canonical design boundary](docs/security/workflow-trust-and-mutations.md#design)
and the artifact controls below.

## Review dropped-slot artifacts

Review waterfall `*.dropped-slots` ledgers and `dropped-*-*.txt` diagnostic carriers are committed round artifacts. `run-log write-round` stages them through the existing `redact.redact()` path. These artifacts must stay bounded and must not include raw reviewer findings, raw `.json` / `.meta` sidecars, or launch `CMD_JSON`.

## `/rejected-analysis` public-filing boundary

Rejected findings and run-log prose are untrusted. Only confirmed non-security
findings may reach `/issue`; confirmed or uncertain security findings stay
private. See the
[canonical rejected-analysis boundary](docs/security/workflow-trust-and-mutations.md#rejected-analysis).

## Reduced residual Bash surface

Residual Bash remains limited to the repository's documented allowlist. Hooks
and wrappers enforce only their named surface. See the
[canonical enforcement-level and workflow contracts](docs/security/workflow-trust-and-mutations.md#enforcement-levels).

## Assessment waiver and manual reconciliation boundaries

Waivers and reconciliation state remain confined to the validated run root,
bound to current identity, and verified after write. Invariant violations cannot
be waived. See the
[canonical implementation and shipping boundary](docs/security/workflow-trust-and-mutations.md#implementation-and-shipping).

## Coverage and review snapshot artifacts

Coverage and review snapshots are untrusted local state. Readers require a
complete, contained, regular-file set bound to current inputs; partial, stale,
malformed, or unsafe state fails closed. See the
[canonical review boundary](docs/security/workflow-trust-and-mutations.md#review).

### `/design` Step 5c publish diagnostics

Step 5c invalidates the prior publish result before each attempt. It trusts publish progress only when the result carries the current attempt identity. Publish checkpoints and bounded diagnostic tails use atomic, no-follow writes under `DESIGN_TMPDIR`. Terminal reporting validates structured progress, branch, and GitHub PR fields before classification. Raw diagnostics stay local and still pass through the existing sensitive-corpus and redaction gates before any public report. Captured publish stdout, stderr, and the bounded nested rename and log-publish subprocess stderr tails are local diagnostics only: raw traceback and subprocess content are never written into the line-oriented trusted result-env or terminal-state files, only fixed current-attempt, progress, class, pattern, rc-source, and resume tokens are. Public reports and committed run logs scrub those diagnostics before egress and fail closed when scrubbing cannot prove they are absent.
