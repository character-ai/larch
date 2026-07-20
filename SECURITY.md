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

Session artifacts, operator diagnostics, committed run logs, and public
GitHub content have distinct confidentiality rules. Redaction and scanning are
egress backstops, not complete content classifiers. See
[Artifacts, Redaction, and Publication](docs/security/artifacts-redaction-and-publication.md)
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

Run-log archives preserve the sanitized committed tree's confidentiality class.
Materialization validates paths, types, metadata, sizes, digests, limits, and
identity before atomic promotion. Remote publication is create-only and
identity-checked. See the canonical
[archive and remote-copy security contract](docs/security/artifacts-redaction-and-publication.md#archives-and-remote-copies)
and [run-log archive format](docs/run-log-archive.md).

`python/cli.py run-log sync` treats the remote inventory and every downloaded
archive as untrusted. It accepts only the exact
`run-logs/<skill>/<run-id>.tar.gz` layout, rejects invalid and colliding local
names before download, checks the downloaded size against the listing, and
routes all content through bounded materialization. Synchronization shares the
publisher's per-run lock. It never replaces a valid cache entry. An invalid
entry is quarantined and restored if repair fails; successful repair promotes a
fully verified directory before removing the quarantine. Stale private
download, extraction, promotion, and quarantine entries are removed under the
same lock.

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

Session state stays private unless a named publisher selects a bounded,
sanitized projection. Committed run logs exclude raw prompt-bearing streams
and retry sidecars, scrub the complete staged tree, and fail closed on unsafe
files or redaction errors. See the canonical
[committed run-log and breadcrumb security contract](docs/security/artifacts-redaction-and-publication.md#committed-run-logs-and-breadcrumbs)
and the operator-facing [run-log selection rules](docs/run-logs.md).

## Stall recovery sanitization

Cross-repository stall and failure reports publish only bounded, allowlisted,
sanitized fields. Raw logs, plans, issue bodies, repository identities, paths,
credentials, and session state stay local. Validation or publication failures
fall back to a sanitized local report, never raw evidence. See the canonical
[cross-repository failure-report contract](docs/security/artifacts-redaction-and-publication.md#cross-repository-failure-reports).

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

Larch distinguishes private session state, model-facing data,
operator-visible diagnostics, committed run logs, public GitHub content, and
remote run-log objects. Each class has a separate publication rule. Pattern
redaction and secret scanners may miss unknown credentials, private
infrastructure, personal data, and domain-specific sensitive content. See the
canonical [confidentiality classes](docs/security/artifacts-redaction-and-publication.md#confidentiality-and-publication-classes),
[redaction and scanner model](docs/security/artifacts-redaction-and-publication.md#redaction-and-secret-scanning),
and [public GitHub publication contract](docs/security/artifacts-redaction-and-publication.md#public-github-publication).

## Breadcrumb stream redaction

Committed breadcrumb publication accepts only contained session-root quiet
logs selected by the run-log publisher. It redacts each file and promotes one
combined `breadcrumbs/quiet.log` atomically. Raw streams and monitor sidecars
stay session-local. See the canonical
[breadcrumb security invariants](docs/security/artifacts-redaction-and-publication.md#breadcrumb-security-invariants)
and the detailed [run-log breadcrumb selection rules](docs/run-logs.md#breadcrumbs).

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
and [public GitHub publication contract](docs/security/artifacts-redaction-and-publication.md#public-github-publication).

## Review dropped-slot artifacts

Committed dropped-slot ledgers and diagnostic carriers stay bounded, exclude
raw findings and launch envelopes, and pass through the run-log redaction and
scrub pipeline. See the canonical
[committed run-log contract](docs/security/artifacts-redaction-and-publication.md#committed-run-logs-and-breadcrumbs).

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

Design publish state and diagnostics stay bound to the current attempt and
validated session root. Raw stdout, stderr, tracebacks, and subprocess bodies
remain local. Public reports and committed logs use bounded classifications
and fail-closed redaction. See the canonical
[operator-diagnostic](docs/security/artifacts-redaction-and-publication.md#operator-visible-diagnostics)
and [public-report](docs/security/artifacts-redaction-and-publication.md#cross-repository-failure-reports)
contracts.
